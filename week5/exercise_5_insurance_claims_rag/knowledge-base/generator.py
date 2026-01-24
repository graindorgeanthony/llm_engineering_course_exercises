import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv
from openai import OpenAI

"""
Generate knowledge-base markdown files for any RAG project.

This script:
1) Builds a file plan (paths + short spec) based on user use-cases.
2) Generates each file in parallel using the LLM.
3) Writes files to the output directory, creating folders as needed.
"""


load_dotenv(override=True)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY is not set in the environment.")

OPENROUTER_CLIENT = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

DEFAULT_MODEL_ID = os.getenv("KNOWLEDGE_BASE_MODEL_ID", "google/gemini-2.5-flash")


@dataclass(frozen=True)
class FileSpec:
    path: str
    title: str
    doc_type: str
    summary: str


DEFAULT_PLAN_SYSTEM_PROMPT = (
    "You are a documentation planner for a RAG knowledge base. "
    "Return a JSON object with a 'files' array of length exactly {num_files}. "
    "Each item must include: path, title, doc_type, summary. "
    "Paths must be relative and end with .md. "
    "Do not include markdown or extra text; output JSON only. "
    "Ensure each file path aligns with its category. Prefer these folders: "
    "company-policies/, customer-contracts/, customer-claims/. "
    "If the domain is not insurance, you may introduce additional folders or rename categories "
    "to fit the domain, but keep paths consistent with content."
)

DEFAULT_PLAN_USER_PROMPT = (
    "Use-cases for the knowledge base:\n"
    "{use_cases}\n\n"
    "Generate a balanced set of documents that enable accurate retrieval."
)

DEFAULT_FILE_SYSTEM_PROMPT = (
    "You are a documentation writer. Return ONLY the markdown for the requested file. "
    "Use clear sections and consistent formatting. Include YAML front matter if helpful. "
    "The content MUST match the folder/category of the target path. "
    "Folder expectations: "
    "company-policies/ => policies, standards, rules, eligibility criteria, SOPs; "
    "customer-contracts/ => contracts, agreements, vendor/service terms, SLAs, pricing; "
    "customer-claims/ => case examples, incidents, tickets, claim narratives and decisions. "
    "If the path uses a different folder, infer the category from the folder name and ensure "
    "the content matches that category. "
    "Make the document as complete and exhaustive as reasonable: include definitions, scope, "
    "requirements, exceptions, process steps, decision criteria, evidence requirements, "
    "and record retention where applicable. "
    "If the domain has decision logic, include a section that makes criteria explicit."
)

DEFAULT_FILE_USER_PROMPT = (
    "Use-cases:\n{use_cases}\n\n"
    "Target file path: {path}\n"
    "Title: {title}\n"
    "Doc type: {doc_type}\n"
    "Summary: {summary}\n\n"
    "Generate the full markdown content now."
)


def render_prompt(template: str, **kwargs: str) -> str:
    try:
        return template.format(**kwargs)
    except KeyError as exc:
        missing = exc.args[0]
        raise ValueError(f"Missing prompt variable: {missing}") from exc


def build_plan_prompt(
    use_cases: str,
    num_files: int,
    plan_system_prompt: str,
    plan_user_prompt: str,
) -> list[dict]:
    system_prompt = render_prompt(
        plan_system_prompt,
        use_cases=use_cases,
        num_files=str(num_files),
    )
    user_prompt = render_prompt(plan_user_prompt, use_cases=use_cases, num_files=str(num_files))
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_file_prompt(
    use_cases: str,
    file_spec: FileSpec,
    file_system_prompt: str,
    file_user_prompt: str,
) -> list[dict]:
    system_prompt = render_prompt(
        file_system_prompt,
        use_cases=use_cases,
        path=file_spec.path,
        title=file_spec.title,
        doc_type=file_spec.doc_type,
        summary=file_spec.summary,
    )
    user_prompt = render_prompt(
        file_user_prompt,
        use_cases=use_cases,
        path=file_spec.path,
        title=file_spec.title,
        doc_type=file_spec.doc_type,
        summary=file_spec.summary,
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def request_json(messages: list[dict], model_id: str) -> dict:
    response = OPENROUTER_CLIENT.chat.completions.create(
        model=model_id,
        messages=messages,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or ""
    return json.loads(content)


def request_markdown(messages: list[dict], model_id: str) -> str:
    response = OPENROUTER_CLIENT.chat.completions.create(
        model=model_id,
        messages=messages,
    )
    return (response.choices[0].message.content or "").strip()


def parse_file_specs(payload: dict) -> list[FileSpec]:
    files = payload.get("files", [])
    specs: list[FileSpec] = []
    for item in files:
        specs.append(
            FileSpec(
                path=str(item["path"]).strip(),
                title=str(item["title"]).strip(),
                doc_type=str(item["doc_type"]).strip(),
                summary=str(item["summary"]).strip(),
            )
        )
    return specs


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_file(path: Path, content: str, overwrite: bool) -> bool:
    if path.exists() and not overwrite:
        return False
    ensure_parent(path)
    path.write_text(content + "\n", encoding="utf-8")
    return True


def generate_one_file(
    output_root: Path,
    use_cases: str,
    file_spec: FileSpec,
    model_id: str,
    overwrite: bool,
    file_system_prompt: str,
    file_user_prompt: str,
) -> tuple[str, bool, str]:
    messages = build_file_prompt(
        use_cases,
        file_spec,
        file_system_prompt=file_system_prompt,
        file_user_prompt=file_user_prompt,
    )
    markdown = request_markdown(messages, model_id)
    if not markdown:
        return file_spec.path, False, "empty_output"
    target_path = output_root / file_spec.path
    wrote = write_file(target_path, markdown, overwrite=overwrite)
    return file_spec.path, wrote, "ok" if wrote else "skipped"


def chunked(iterable: Iterable[FileSpec], size: int) -> Iterable[list[FileSpec]]:
    batch: list[FileSpec] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def run_generation(
    use_cases: str,
    num_files: int,
    output_root: Path,
    model_id: str,
    max_workers: int,
    overwrite: bool,
    plan_system_prompt: str,
    plan_user_prompt: str,
    file_system_prompt: str,
    file_user_prompt: str,
) -> None:
    plan_payload = request_json(
        build_plan_prompt(
            use_cases,
            num_files,
            plan_system_prompt=plan_system_prompt,
            plan_user_prompt=plan_user_prompt,
        ),
        model_id,
    )
    file_specs = parse_file_specs(plan_payload)
    if not file_specs:
        raise RuntimeError("No file specs returned by the model.")

    results: list[tuple[str, bool, str]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(
                generate_one_file,
                output_root,
                use_cases,
                spec,
                model_id,
                overwrite,
                file_system_prompt,
                file_user_prompt,
            ): spec
            for spec in file_specs
        }
        for future in as_completed(future_map):
            spec = future_map[future]
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001 - surface error and continue
                results.append((spec.path, False, f"error:{exc}"))
            else:
                results.append(result)

    created = [r for r in results if r[1]]
    skipped = [r for r in results if r[2] == "skipped"]
    failed = [r for r in results if r[2].startswith("error") or r[2] == "empty_output"]

    print(f"Generated files: {len(created)}")
    print(f"Skipped (exists): {len(skipped)}")
    print(f"Failed: {len(failed)}")
    if failed:
        print("Failures:")
        for path, _, reason in failed:
            print(f"- {path}: {reason}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate knowledge-base markdown files in parallel for any RAG project."
    )
    parser.add_argument(
        "--use-cases",
        required=True,
        help="Description of target use-cases for the knowledge base.",
    )
    parser.add_argument(
        "--num-files",
        type=int,
        required=True,
        help="Total number of markdown files to generate.",
    )
    parser.add_argument(
        "--output-root",
        default=str(Path(__file__).resolve().parent),
        help="Root folder to write files (default: knowledge-base).",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_ID,
        help="OpenRouter model ID (default from KNOWLEDGE_BASE_MODEL_ID).",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=6,
        help="Number of parallel workers for file generation.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files if they exist.",
    )
    parser.add_argument(
        "--plan-system-prompt",
        default=DEFAULT_PLAN_SYSTEM_PROMPT,
        help="System prompt template for the planning step.",
    )
    parser.add_argument(
        "--plan-user-prompt",
        default=DEFAULT_PLAN_USER_PROMPT,
        help="User prompt template for the planning step.",
    )
    parser.add_argument(
        "--file-system-prompt",
        default=DEFAULT_FILE_SYSTEM_PROMPT,
        help="System prompt template for the file generation step.",
    )
    parser.add_argument(
        "--file-user-prompt",
        default=DEFAULT_FILE_USER_PROMPT,
        help="User prompt template for the file generation step.",
    )

    args = parser.parse_args()
    output_root = Path(args.output_root).expanduser().resolve()
    run_generation(
        use_cases=args.use_cases,
        num_files=args.num_files,
        output_root=output_root,
        model_id=args.model,
        max_workers=args.max_workers,
        overwrite=args.overwrite,
        plan_system_prompt=args.plan_system_prompt,
        plan_user_prompt=args.plan_user_prompt,
        file_system_prompt=args.file_system_prompt,
        file_user_prompt=args.file_user_prompt,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())