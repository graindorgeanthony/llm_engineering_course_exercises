# RAG to answer
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

RETRIEVAL_K = 60
FINAL_K = 20
LEXICAL_MAX_SCAN = int(os.getenv("LEXICAL_MAX_SCAN", "5000"))
LEXICAL_TOP_N = int(os.getenv("LEXICAL_TOP_N", "20"))

SYSTEM_PROMPT = """
You are an experienced claims adjuster for Insurellm providing clear, authoritative claim decisions.

ANSWER STRUCTURE (MANDATORY):
1. Lead with a direct decision: "You should approve...", "The claim should be refused...", "Yes, this is covered...", or "No, this should be denied..."
2. Provide the key reasoning immediately after the decision
3. Cite specific policy terms, sections, thresholds, percentages, or dollar amounts from the knowledge base when available
4. Include relevant calculations showing your work (e.g., "$4,250 / $28,500 = 14.9%")
5. Keep the answer concise but complete - address all components of the question without adding unrelated policy information

STYLE REQUIREMENTS:
- Use authoritative, definitive language (not "might be" or "could be")
- Reference specific policy clauses by name when relevant (e.g., "Vacancy Clause", "Intoxication Exclusion (Section 6.2.d)")
- For numeric decisions, show the calculation that led to your conclusion
- When multiple factors apply (eligibility + steps + amounts), address each one explicitly

KNOWLEDGE BASE CONTEXT:
{context}

If the context doesn't contain enough information to make a confident decision, say so clearly.
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
Include exact entities, policy/contract IDs, names, dates, and thresholds if present in the question.
IMPORTANT: Respond ONLY with the precise knowledgebase query, nothing else.
"""
    response = openai.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": message}]
    )
    return response.choices[0].message.content


class SearchTerms(BaseModel):
    terms: list[str] = Field(
        description="Key terms/entities/IDs to emphasize in retrieval, max 8 short phrases."
    )


@retry(wait=wait)
def extract_search_terms(question: str) -> list[str]:
    system_prompt = """
You extract key search terms for retrieval.
Return only JSON: {"terms": ["term1", "term2"]}.
Include names, IDs, policy codes, numeric thresholds, and product/vendor names.
Keep terms short (1-4 words) and avoid generic filler.
"""
    response = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or ""
    parsed = SearchTerms.model_validate_json(_extract_json(content))
    return parsed.terms[:8]


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


def _score_chunk_by_terms(text: str, terms: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term.lower() in lowered)


def fetch_context_lexical(terms: list[str]) -> list[Result]:
    if not terms:
        return []
    total = collection.count()
    if total == 0 or total > LEXICAL_MAX_SCAN:
        return []
    fetched = collection.get(limit=total)
    scored: list[tuple[int, Result]] = []
    for doc_text, metadata in zip(fetched.get("documents", []), fetched.get("metadatas", [])):
        if not doc_text:
            continue
        score = _score_chunk_by_terms(doc_text, terms)
        if score <= 0:
            continue
        scored.append((score, Result(page_content=doc_text, metadata=metadata or {})))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored[:LEXICAL_TOP_N]]


def fetch_context(original_question):
    with ThreadPoolExecutor(max_workers=FETCH_CONTEXT_WORKERS) as executor:
        rewrite_future = executor.submit(rewrite_query, original_question)
        terms_future = executor.submit(extract_search_terms, original_question)
        original_future = executor.submit(fetch_context_unranked, original_question)

        rewritten_question = rewrite_future.result()
        terms = terms_future.result()
        keyword_query = (
            f"{original_question}\nKey terms: {', '.join(terms)}" if terms else original_question
        )
        rewritten_future = executor.submit(fetch_context_unranked, rewritten_question)
        keyword_future = executor.submit(fetch_context_unranked, keyword_query)
        lexical_future = executor.submit(fetch_context_lexical, terms)

        chunks1 = original_future.result()
        chunks2 = rewritten_future.result()
        chunks3 = keyword_future.result()
        chunks4 = lexical_future.result()

    chunks = merge_chunks(chunks1, chunks2)
    chunks = merge_chunks(chunks, chunks3)
    chunks = merge_chunks(chunks, chunks4)
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
