# Ingest knowledge and turn it into a database
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from chromadb import PersistentClient
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from tenacity import retry, wait_exponential, stop_after_attempt
import traceback
import os
import re

load_dotenv(override=True)

MODEL = "google/gemini-2.5-flash"

DB_NAME = str(Path(__file__).parent.parent / "preprocessed_db")
collection_name = "docs"
embedding_model = "text-embedding-3-large"
KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "knowledge-base"
AVERAGE_CHUNK_SIZE = 100
wait = wait_exponential(multiplier=1, min=10, max=240)


WORKERS = int(os.getenv("INGEST_WORKERS", "50"))
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "128"))
OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "120"))
INGEST_MAX_RETRIES = int(os.getenv("INGEST_MAX_RETRIES", "6"))
INGEST_DOC_LIMIT = int(os.getenv("INGEST_DOC_LIMIT", "1000"))

openai = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    timeout=OPENAI_TIMEOUT_SECONDS,
    max_retries=0,
)


class Result(BaseModel):
    page_content: str
    metadata: dict


class Chunk(BaseModel):
    headline: str = Field(
        description="A brief heading for this chunk, typically a few words, that is most likely to be surfaced in a query",
    )
    summary: str = Field(
        description="A few sentences summarizing the content of this chunk to answer common questions"
    )
    original_text: str = Field(
        description="The original text of this chunk from the provided document, exactly as is, not changed in any way"
    )

    def as_result(self, document):
        metadata = {"source": document["source"], "type": document["type"]}
        return Result(
            page_content=self.headline + "\n\n" + self.summary + "\n\n" + self.original_text,
            metadata=metadata,
        )


class Chunks(BaseModel):
    chunks: list[Chunk]


CHUNKS_JSON_SCHEMA = {
    "name": "Chunks",
    "schema": Chunks.model_json_schema(),
    "strict": True,
}


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


def fetch_documents():
    """A homemade version of the LangChain DirectoryLoader"""

    documents = []

    for folder in KNOWLEDGE_BASE_PATH.iterdir():
        doc_type = folder.name
        for file in folder.rglob("*.md"):
            with open(file, "r", encoding="utf-8") as f:
                documents.append({"type": doc_type, "source": file.as_posix(), "text": f.read()})

    print(f"Loaded {len(documents)} documents")
    return documents


def make_prompt(document):
    how_many = (len(document["text"]) // AVERAGE_CHUNK_SIZE) + 1
    return f"""
You take a document and you split the document into overlapping chunks for a KnowledgeBase.

The document is from the shared drive of a company called Insurellm.
The document is of type: {document["type"]}
The document has been retrieved from: {document["source"]}

A chatbot will use these chunks to answer questions about the company.
You should divide up the document as you see fit, being sure that the entire document is returned across the chunks - don't leave anything out.
This document should probably be split into at least {how_many} chunks, but you can have more or less as appropriate, ensuring that there are individual chunks to answer specific questions.
There should be overlap between the chunks as appropriate; typically about 25% overlap or about 50 words, so you have the same text in multiple chunks for best retrieval results.

For each chunk, you should provide a headline, a summary, and the original text of the chunk.
Together your chunks should represent the entire document with overlap.
Do not drop any sections; ensure complete coverage of requirements, lists, dates, and procedures.

Here is the document:

{document["text"]}

Respond only with JSON in this format:
{{"chunks": [{{"headline": "...", "summary": "...", "original_text": "..."}}]}}
"""


def make_messages(document):
    return [
        {
            "role": "system",
            "content": "Return only valid JSON that matches the provided schema.",
        },
        {"role": "user", "content": make_prompt(document)},
    ]


@retry(wait=wait, stop=stop_after_attempt(INGEST_MAX_RETRIES))
def _log_retry(retry_state):
    document = retry_state.args[0]
    exc = retry_state.outcome.exception()
    attempt = retry_state.attempt_number
    print(
        f"Retrying ({attempt}/{INGEST_MAX_RETRIES}) for {document['source']} after error: {exc}"
    )


@retry(wait=wait, stop=stop_after_attempt(INGEST_MAX_RETRIES), before_sleep=_log_retry)
def process_document(document):
    print(f"Processing: {document['source']}")
    try:
        messages = make_messages(document)
        response = openai.chat.completions.create(
            model=MODEL,
            messages=messages,
            timeout=OPENAI_TIMEOUT_SECONDS,
            response_format={"type": "json_schema", "json_schema": CHUNKS_JSON_SCHEMA},
        )
        reply = response.choices[0].message.content
        doc_as_chunks = Chunks.model_validate_json(reply).chunks
    except Exception as exc:
        print(f"Error processing {document['source']}: {exc}")
        traceback.print_exc()
        raise
    print(f"Completed: {document['source']} -> {len(doc_as_chunks)} chunks")
    return [chunk.as_result(document) for chunk in doc_as_chunks]


def create_chunks(documents):
    """
    Create chunks using a number of workers in parallel.
    If you get a rate limit error, set the WORKERS to 1.
    """
    chunks = []
    failures = 0
    print(f"Submitting {len(documents)} documents with {WORKERS} workers...")
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(process_document, doc) for doc in documents]
        for future in tqdm(as_completed(futures), total=len(futures)):
            try:
                chunks.extend(future.result())
            except Exception as exc:
                failures += 1
                print(f"Failed to process document: {exc}")
    if failures:
        print(f"Failed documents: {failures}/{len(documents)}")
    return chunks


def create_embeddings(chunks):
    chroma = PersistentClient(path=DB_NAME)
    if collection_name in [c.name for c in chroma.list_collections()]:
        chroma.delete_collection(collection_name)

    texts = [chunk.page_content for chunk in chunks]
    collection = chroma.get_or_create_collection(collection_name)
    total_added = 0
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        end = min(start + EMBED_BATCH_SIZE, len(texts))
        batch_texts = texts[start:end]
        batch_metas = [chunk.metadata for chunk in chunks[start:end]]
        batch_ids = [str(i) for i in range(start, end)]

        emb = openai.embeddings.create(model=embedding_model, input=batch_texts).data
        if not emb:
            raise ValueError(
                "No embedding data received. Check OpenRouter embedding model access "
                f"or rate limits for model '{embedding_model}'."
            )
        vectors = [e.embedding for e in emb]
        collection.add(
            ids=batch_ids,
            embeddings=vectors,
            documents=batch_texts,
            metadatas=batch_metas,
        )
        total_added += len(batch_texts)
        print(f"Embedded {total_added}/{len(texts)} chunks")
    print(f"Vectorstore created with {collection.count()} documents")


if __name__ == "__main__":
    documents = fetch_documents()
    if INGEST_DOC_LIMIT > 0:
        documents = documents[:INGEST_DOC_LIMIT]
        print(f"Limiting ingestion to {len(documents)} documents")
    chunks = create_chunks(documents)
    create_embeddings(chunks)
    print("Ingestion complete")
