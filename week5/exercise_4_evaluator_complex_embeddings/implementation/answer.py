from openai import OpenAI
from dotenv import load_dotenv
from chromadb import PersistentClient
from pydantic import BaseModel, Field
from pathlib import Path
from tenacity import retry, wait_exponential
from concurrent.futures import ThreadPoolExecutor
import os
import re


load_dotenv(override=True)

#MODEL = "openai/gpt-4.1-nano"
MODEL = "google/gemini-2.5-flash"
DB_NAME = str(Path(__file__).parent.parent / "preprocessed_db")
KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "knowledge-base"
FETCH_CONTEXT_WORKERS = int(os.getenv("FETCH_CONTEXT_WORKERS", "4"))

collection_name = "docs"
embedding_model = "text-embedding-3-large"
wait = wait_exponential(multiplier=1, min=10, max=240)

openai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

chroma = PersistentClient(path=DB_NAME)
collection = chroma.get_or_create_collection(collection_name)

RETRIEVAL_K = 30
FINAL_K = 15

SYSTEM_PROMPT = """
You are a knowledgeable, friendly assistant representing the company Insurellm.
You are chatting with a user about Insurellm.
Your answer will be evaluated for accuracy, relevance and completeness, so make sure it only answers the question and fully answers it.
Provide a complete answer covering all distinct facts relevant to the question. If there are multiple components (such as benefits, dates, eligibility, or steps), explicitly address each one.
If you don't know the answer, say so.
For context, here are specific extracts from the Knowledge Base that might be directly relevant to the user's question:
{context}

With this context, please answer the user's question. Be accurate, relevant and complete.
"""


class Result(BaseModel):
    page_content: str
    metadata: dict


class RankOrder(BaseModel):
    order: list[int] = Field(
        description="The order of relevance of chunks, from most relevant to least relevant, by chunk id number"
    )


def _extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("{") or text.startswith("["):
        return text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return match.group(0)
    raise ValueError("No JSON found in response")


@retry(wait=wait)
def rerank(question, chunks):
    system_prompt = """
You are a document re-ranker.
You are provided with a question and a list of relevant chunks of text from a query of a knowledge base.
The chunks are provided in the order they were retrieved; this should be approximately ordered by relevance, but you may be able to improve on that.
You must rank order the provided chunks by relevance to the question, with the most relevant chunk first.
Reply only with JSON in this exact format: {"order": [1, 2, 3]} and include all chunk ids you are provided with, reranked.
"""
    user_prompt = f"The user has asked the following question:\n\n{question}\n\nOrder all the chunks of text by relevance to the question, from most relevant to least relevant. Include all the chunk ids you are provided with, reranked.\n\n"
    user_prompt += "Here are the chunks:\n\n"
    for index, chunk in enumerate(chunks):
        user_prompt += f"# CHUNK ID: {index + 1}:\n\n{chunk.page_content}\n\n"
    user_prompt += 'Reply only with JSON: {"order": [1, 2, 3]}'
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    response = openai.chat.completions.create(
        model=MODEL,
        messages=messages
    )
    reply = response.choices[0].message.content
    order = RankOrder.model_validate_json(_extract_json(reply)).order
    return [chunks[i - 1] for i in order]


def make_rag_messages(question, history, chunks):
    context = "\n\n".join(
        f"Extract from {chunk.metadata['source']}:\n{chunk.page_content}" for chunk in chunks
    )
    system_prompt = SYSTEM_PROMPT.format(context=context)
    return (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": question}]
    )


@retry(wait=wait)
def rewrite_query(question, history=None):
    """Rewrite the user's question to be a more specific question that is more likely to surface relevant content in the Knowledge Base."""
    history = history or []
    message = f"""
You are in a conversation with a user, answering questions about the company Insurellm.
You are about to look up information in a Knowledge Base to answer the user's question.

This is the history of your conversation so far with the user:
{history}

And this is the user's current question:
{question}

Respond only with a short, refined question that you will use to search the Knowledge Base.
It should be a VERY short specific question most likely to surface content. Focus on the question details.
IMPORTANT: Respond ONLY with the precise knowledgebase query, nothing else.
"""
    response = openai.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": message}]
    )
    return response.choices[0].message.content


def merge_chunks(chunks, reranked):
    merged = chunks[:]
    existing = [chunk.page_content for chunk in chunks]
    for chunk in reranked:
        if chunk.page_content not in existing:
            merged.append(chunk)
    return merged


def fetch_context_unranked(question):
    query = openai.embeddings.create(model=embedding_model, input=[question]).data[0].embedding
    results = collection.query(query_embeddings=[query], n_results=RETRIEVAL_K)
    chunks = []
    for result in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append(Result(page_content=result[0], metadata=result[1]))
    return chunks


def fetch_context(original_question):
    with ThreadPoolExecutor(max_workers=FETCH_CONTEXT_WORKERS) as executor:
        rewrite_future = executor.submit(rewrite_query, original_question)
        original_future = executor.submit(fetch_context_unranked, original_question)

        rewritten_question = rewrite_future.result()
        rewritten_future = executor.submit(fetch_context_unranked, rewritten_question)

        chunks1 = original_future.result()
        chunks2 = rewritten_future.result()

    chunks = merge_chunks(chunks1, chunks2)
    reranked = rerank(original_question, chunks)
    return reranked[:FINAL_K]


@retry(wait=wait)
def answer_question(question: str, history: list[dict] | None = None) -> tuple[str, list]:
    """
    Answer a question using RAG and return the answer and the retrieved context
    """
    history = history or []
    chunks = fetch_context(question)
    messages = make_rag_messages(question, history, chunks)
    response = openai.chat.completions.create(
        model=MODEL,
        messages=messages
    )
    return response.choices[0].message.content, chunks
