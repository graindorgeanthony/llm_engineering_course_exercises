import argparse
import json
import os
import random
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from chromadb import PersistentClient

"""
Generate JSONL test cases for a RAG knowledge base.

This script:
1) Reads all markdown files under the knowledge-base folder.
2) Feeds the full content directly to the model.
3) Generates a JSONL file of QA test cases tailored to the use cases.
"""


load_dotenv(override=True)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY is not set in the environment.")

OPENROUTER_CLIENT = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

DEFAULT_GENERATOR_MODEL_ID = os.getenv(
    "KB_TEST_CASE_MODEL_ID",
    "google/gemini-3-flash-preview",
)


@dataclass(frozen=True)
class SourceDoc:
    path: str
    content: str


DEFAULT_TEST_CASE_SYSTEM_PROMPT = (
    "You are an expert test-case generator for RAG system evaluation.\n\n"
    "# TASK\n"
    "Generate high-quality question-answer test cases in JSONL format (one JSON object per line).\n\n"
    "# OUTPUT SCHEMA\n"
    "Each JSON object MUST contain these mandatory fields:\n"
    "- question: A natural, realistic question a user would ask\n"
    "- keywords: An array of key terms/entities relevant to answering the question\n"
    "- reference_answer: The ground-truth answer extracted from the provided documents\n\n"
    "IMPORTANT: Analyze the use-cases to determine what ADDITIONAL fields are appropriate.\n"
    "Adapt the schema to the domain:\n\n"
    "Examples of domain-specific adaptations:\n"
    "• Insurance claims → Add: final_decision (approval/refusal), reason (justification)\n"
    "• Legal contracts → Add: clause_type, jurisdiction, legal_risk_level\n"
    "• Technical documentation → Add: category (setup/troubleshooting/api), severity\n"
    "• Customer support → Add: category (billing/technical/account), urgency, resolution_type\n"
    "• Medical records → Add: diagnosis_category, urgency, recommended_action\n\n"
    "# QUESTION QUALITY REQUIREMENTS\n"
    "1. NATURAL & REALISTIC: Questions must sound like real user queries, NOT academic test questions\n"
    "2. NO SOURCE ATTRIBUTION: NEVER mention where information comes from:\n"
    "   ❌ BAD: 'According to the policy document, what is...'\n"
    "   ❌ BAD: 'What does section 4.2 say about...'\n"
    "   ❌ BAD: 'The document states that... Is this correct?'\n"
    "   ❌ BAD: 'Based on the company policy, ...'\n"
    "   ✅ GOOD: 'What is the coverage limit for water damage?'\n"
    "   ✅ GOOD: 'Am I eligible for reimbursement if I lost my receipt?'\n"
    "   ✅ GOOD: 'How long does claim approval usually take?'\n"
    "3. ANSWERABLE: All answers must be directly found in the provided documents\n"
    "4. DIVERSE: Cover different aspects (direct facts, procedures, edge cases, calculations, decisions)\n"
    "5. SPECIFIC: Include concrete details (names, amounts, dates, conditions) when relevant\n\n"
    "# OUTPUT FORMAT\n"
    "Return ONLY valid JSONL. No markdown, no explanations, no preamble.\n"
    "Each JSON object MUST be on its own line, and each line must be a single JSON object."
)

DEFAULT_TEST_CASE_USER_PROMPT = (
    "# USE-CASES\n{use_cases}\n\n"
    "# SOURCE DOCUMENTS\n{context}\n\n"
    "# INSTRUCTIONS\n"
    "1. First, analyze the use-cases above to determine the most appropriate schema\n"
    "2. Identify what additional fields beyond (question, keywords, reference_answer) would be valuable\n"
    "3. Generate exactly {num_cases} diverse, high-quality test cases\n"
    "4. Ensure questions are natural and do NOT reference document sources\n\n"
    "Generate {num_cases} test cases now in JSONL format:"
)

DEFAULT_REPAIR_SYSTEM_PROMPT = (
    "You are a JSONL repair assistant.\n\n"
    "# TASK\n"
    "Fix a single malformed JSONL line so it becomes a valid JSON object.\n\n"
    "# REQUIREMENTS\n"
    "- Return ONLY a JSON object (no markdown, no extra text)\n"
    "- Include required fields: question, keywords, reference_answer\n"
    "- Ensure keywords is an array\n"
    "- Preserve the intent of the original line as much as possible\n"
)

DEFAULT_REPAIR_USER_PROMPT = (
    "# MALFORMED LINE\n"
    "{line}\n\n"
    "Return the repaired JSON object now."
)


def render_prompt(template: str, **kwargs: str) -> str:
    try:
        return template.format(**kwargs)
    except KeyError as exc:
        missing = exc.args[0]
        raise ValueError(f"Missing prompt variable: {missing}") from exc


def build_test_case_prompt(
    use_cases: str,
    context: str,
    num_cases: int,
    test_case_system_prompt: str,
    test_case_user_prompt: str,
) -> list[dict]:
    system_prompt = render_prompt(
        test_case_system_prompt,
        use_cases=use_cases,
        context=context,
        num_cases=str(num_cases),
    )
    user_prompt = render_prompt(
        test_case_user_prompt,
        use_cases=use_cases,
        context=context,
        num_cases=str(num_cases),
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def request_markdown(messages: list[dict], model_id: str) -> str:
    response = OPENROUTER_CLIENT.chat.completions.create(
        model=model_id,
        messages=messages,
    )
    return (response.choices[0].message.content or "").strip()


def request_stream(messages: list[dict], model_id: str) -> str:
    response = OPENROUTER_CLIENT.chat.completions.create(
        model=model_id,
        messages=messages,
        stream=True,
    )
    for event in response:
        delta = event.choices[0].delta
        if delta and delta.content:
            yield delta.content


def read_markdown_files(root: Path) -> list[SourceDoc]:
    docs: list[SourceDoc] = []
    for path in sorted(root.rglob("*.md")):
        try:
            content = path.read_text(encoding="utf-8").strip()
        except UnicodeDecodeError:
            content = path.read_text(encoding="utf-8", errors="ignore").strip()
        if content:
            docs.append(SourceDoc(path=str(path.relative_to(root)), content=content))
    return docs


def read_chroma_chunks(
    db_path: Path,
    collection_name: str,
    max_chunks: int | None = None,
) -> list[SourceDoc]:
    client = PersistentClient(path=str(db_path))
    collection = client.get_or_create_collection(collection_name)
    total = collection.count()
    if total == 0:
        return []

    limit = min(total, max_chunks) if max_chunks else total
    fetched = collection.get(limit=limit)
    docs: list[SourceDoc] = []
    for chunk_text, metadata in zip(
        fetched.get("documents", []), fetched.get("metadatas", [])
    ):
        if not chunk_text:
            continue
        source = (metadata or {}).get("source", "chroma_chunk")
        docs.append(SourceDoc(path=str(source), content=str(chunk_text).strip()))
    return docs


def read_chroma_chunk_window(
    db_path: Path,
    collection_name: str,
    limit: int,
    offset: int,
) -> list[SourceDoc]:
    client = PersistentClient(path=str(db_path))
    collection = client.get_or_create_collection(collection_name)
    fetched = collection.get(limit=limit, offset=offset)
    docs: list[SourceDoc] = []
    for chunk_text, metadata in zip(
        fetched.get("documents", []), fetched.get("metadatas", [])
    ):
        if not chunk_text:
            continue
        source = (metadata or {}).get("source", "chroma_chunk")
        docs.append(SourceDoc(path=str(source), content=str(chunk_text).strip()))
    return docs


def build_documents_block(docs: list[SourceDoc]) -> str:
    parts: list[str] = []
    for doc in docs:
        parts.append(f"### {doc.path}\n{doc.content}")
    return "\n\n".join(parts)


def validate_json_row(parsed: dict, source_line: str) -> None:
    for key in ("question", "keywords", "reference_answer"):
        if key not in parsed:
            raise ValueError(f"Missing mandatory key '{key}' in JSONL line: {source_line}")
    if not isinstance(parsed["keywords"], list):
        raise ValueError(f"'keywords' must be an array in JSONL line: {source_line}")


def repair_jsonl_line(line: str, model_id: str) -> dict:
    messages = [
        {"role": "system", "content": DEFAULT_REPAIR_SYSTEM_PROMPT},
        {"role": "user", "content": render_prompt(DEFAULT_REPAIR_USER_PROMPT, line=line)},
    ]
    payload = OPENROUTER_CLIENT.chat.completions.create(
        model=model_id,
        messages=messages,
        response_format={"type": "json_object"},
    )
    content = payload.choices[0].message.content or ""
    parsed = json.loads(content)
    validate_json_row(parsed, line)
    return parsed


def write_jsonl(path: Path, rows: list[dict], overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists. Use --overwrite to replace it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_generation(
    use_cases: str,
    output_root: Path,
    output_file: Path,
    num_cases: int,
    generator_model_id: str,
    overwrite: bool,
    test_case_system_prompt: str,
    test_case_user_prompt: str,
    use_chunks: bool,
    chroma_path: Path,
    chroma_collection: str,
    max_chunks: int | None,
    chunks_per_case: int,
    random_seed: int | None,
) -> None:
    if output_file.exists() and not overwrite:
        raise FileExistsError(f"{output_file} already exists. Use --overwrite to replace it.")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if use_chunks:
        client = PersistentClient(path=str(chroma_path))
        collection = client.get_or_create_collection(chroma_collection)
        total_chunks = collection.count()
        if total_chunks == 0:
            raise RuntimeError("No chunks found in the Chroma collection.")

        rng = random.Random(random_seed)
        max_offset = max(0, total_chunks - chunks_per_case)
        written = 0
        with output_file.open("w", encoding="utf-8") as handle:
            while written < num_cases:
                offset = rng.randint(0, max_offset) if max_offset else 0
                docs = read_chroma_chunk_window(
                    db_path=chroma_path,
                    collection_name=chroma_collection,
                    limit=min(chunks_per_case, total_chunks),
                    offset=offset,
                )
                if not docs:
                    raise RuntimeError("Failed to fetch chunks from Chroma.")

                context = build_documents_block(docs)
                messages = build_test_case_prompt(
                    use_cases,
                    context,
                    1,
                    test_case_system_prompt=test_case_system_prompt,
                    test_case_user_prompt=test_case_user_prompt,
                )
                response_text = request_markdown(messages, generator_model_id)
                if not response_text:
                    continue

                for candidate in response_text.replace("}{", "}\n{").splitlines():
                    if not candidate.strip():
                        continue
                    try:
                        parsed = json.loads(candidate)
                        validate_json_row(parsed, candidate)
                    except json.JSONDecodeError:
                        parsed = repair_jsonl_line(candidate, generator_model_id)
                    handle.write(json.dumps(parsed, ensure_ascii=False) + "\n")
                    handle.flush()
                    written += 1
                    if written >= num_cases:
                        break
        return

    docs = read_markdown_files(output_root)
    if not docs:
        raise RuntimeError("No markdown files found to include.")
    context = build_documents_block(docs)

    messages = build_test_case_prompt(
        use_cases,
        context,
        num_cases,
        test_case_system_prompt=test_case_system_prompt,
        test_case_user_prompt=test_case_user_prompt,
    )

    buffer = ""
    written = 0
    with output_file.open("w", encoding="utf-8") as handle:
        for chunk in request_stream(messages, generator_model_id):
            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue
                line = line.replace("}{", "}\n{")
                for candidate in line.splitlines():
                    if not candidate.strip():
                        continue
                    try:
                        parsed = json.loads(candidate)
                        validate_json_row(parsed, candidate)
                    except json.JSONDecodeError:
                        parsed = repair_jsonl_line(candidate, generator_model_id)
                    handle.write(json.dumps(parsed, ensure_ascii=False) + "\n")
                    handle.flush()
                    written += 1
                    if written >= num_cases:
                        break
                if written >= num_cases:
                    break
            if written >= num_cases:
                break

        if written < num_cases and buffer.strip():
            candidate = buffer.strip()
            try:
                parsed = json.loads(candidate)
                validate_json_row(parsed, candidate)
            except json.JSONDecodeError:
                parsed = repair_jsonl_line(candidate, generator_model_id)
            handle.write(json.dumps(parsed, ensure_ascii=False) + "\n")
            handle.flush()
            written += 1

    if written < num_cases:
        raise RuntimeError(
            f"Only wrote {written} JSONL rows; expected {num_cases}."
        )

    print(f"Wrote JSONL test cases: {output_file}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate JSONL test cases from a markdown knowledge base."
    )
    parser.add_argument(
        "--use-cases",
        required=True,
        help="Description of target use-cases for the knowledge base.",
    )
    parser.add_argument(
        "--output-root",
        default=str(Path(__file__).resolve().parent),
        help="Root folder containing markdown files (default: knowledge-base).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the output file if it exists.",
    )
    parser.add_argument(
        "--output-file",
        default="tests.jsonl",
        help="Output JSONL filename or path (default: test_cases.jsonl).",
    )
    parser.add_argument(
        "--num-cases",
        type=int,
        default=50,
        help="Number of JSONL test cases to generate.",
    )
    parser.add_argument(
        "--generator-model",
        default=DEFAULT_GENERATOR_MODEL_ID,
        help="OpenRouter model ID for JSONL generation.",
    )
    parser.add_argument(
        "--test-case-system-prompt",
        default=DEFAULT_TEST_CASE_SYSTEM_PROMPT,
        help="System prompt template for test-case generation.",
    )
    parser.add_argument(
        "--test-case-user-prompt",
        default=DEFAULT_TEST_CASE_USER_PROMPT,
        help="User prompt template for test-case generation.",
    )
    parser.add_argument(
        "--use-chunks",
        action="store_true",
        help="Generate test cases from chunked content in Chroma instead of markdown.",
    )
    parser.add_argument(
        "--chroma-path",
        default=str(Path(__file__).resolve().parent.parent / "preprocessed_db"),
        help="Path to the Chroma persistent DB (default: preprocessed_db).",
    )
    parser.add_argument(
        "--chroma-collection",
        default="docs",
        help="Chroma collection name to read chunks from (default: docs).",
    )
    parser.add_argument(
        "--max-chunks",
        type=int,
        default=None,
        help="Optional limit on number of chunks to use from Chroma.",
    )
    parser.add_argument(
        "--chunks-per-case",
        type=int,
        default=30,
        help="Number of chunks to include per generated test case (default: 30).",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=None,
        help="Optional random seed for chunk sampling.",
    )

    args = parser.parse_args()
    output_root = Path(args.output_root).expanduser().resolve()
    output_file = Path(args.output_file)
    if not output_file.is_absolute():
        output_file = output_root / output_file
    run_generation(
        use_cases=args.use_cases,
        output_root=output_root,
        output_file=output_file,
        num_cases=args.num_cases,
        generator_model_id=args.generator_model,
        overwrite=args.overwrite,
        test_case_system_prompt=args.test_case_system_prompt,
        test_case_user_prompt=args.test_case_user_prompt,
        use_chunks=args.use_chunks,
        chroma_path=Path(args.chroma_path).expanduser().resolve(),
        chroma_collection=args.chroma_collection,
        max_chunks=args.max_chunks,
        chunks_per_case=args.chunks_per_case,
        random_seed=args.random_seed,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())