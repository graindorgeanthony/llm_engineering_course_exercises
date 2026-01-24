import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

"""
Post-generation consistency audit for a RAG knowledge base.

This script:
1) Reads all markdown files under the knowledge-base folder.
2) Sends the full corpus to the model to detect MAJOR inconsistencies.
3) Optionally writes updated markdown for any files that require adjustment.
"""


load_dotenv(override=True)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY is not set in the environment.")

OPENROUTER_CLIENT = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

DEFAULT_AUDIT_MODEL_ID = os.getenv(
    "KB_AUDIT_MODEL_ID",
    "google/gemini-3-pro-preview",
)


@dataclass(frozen=True)
class SourceDoc:
    path: str
    content: str


DEFAULT_AUDIT_SYSTEM_PROMPT = (
    "You are an expert knowledge-base consistency auditor.\n\n"
    "# TASK\n"
    "Detect and correct ONLY MAJOR inconsistencies across the provided documents.\n\n"
    "# DEFINITION OF MAJOR INCONSISTENCY\n"
    "A contradiction that could materially change a decision, outcome, or compliance result.\n"
    "Examples:\n"
    "- Different coverage limits for the same policy type\n"
    "- Conflicting eligibility criteria for the same benefit\n"
    "- Conflicting timelines or deadlines for the same process\n"
    "- Opposing approval/refusal rules for the same scenario\n\n"
    "# NON-GOALS\n"
    "- Do NOT fix minor wording differences\n"
    "- Do NOT normalize style, tone, or formatting unless required to resolve a major conflict\n"
    "- Do NOT invent new policies or facts; reconcile using the most authoritative or common rule\n\n"
    "# OUTPUT SCHEMA (JSON ONLY)\n"
    "Return a JSON object with:\n"
    "- issues: Array of objects, each with:\n"
    "  * id (string)\n"
    "  * severity (string; must be 'major')\n"
    "  * description (string)\n"
    "  * impacted_files (array of file paths)\n"
    "  * evidence (array of short quotes)\n"
    "- updates: Array of objects, each with:\n"
    "  * paths (array of file paths to update)\n"
    "  * search_pattern (string; literal search text)\n"
    "  * replace_pattern (string; literal replacement text)\n\n"
    "If there are no major inconsistencies, return empty arrays for issues and updates."
)

DEFAULT_AUDIT_USER_PROMPT = (
    "# SOURCE DOCUMENTS\n{context}\n\n"
    "# INSTRUCTIONS\n"
    "1. Identify only major inconsistencies across documents\n"
    "2. Propose minimal edits using literal search/replace\n"
    "3. Ensure search_pattern is an exact substring from the target file(s)\n"
    "4. Include only the file paths to update plus search/replace patterns\n\n"
    "Return the JSON now."
)

DEFAULT_RETRY_SYSTEM_PROMPT = (
    "You are a meticulous editor fixing a failed search/replace update.\n\n"
    "# TASK\n"
    "Given the target file content and the intended change, provide a NEW literal\n"
    "search_pattern that exists in the file and a replacement that achieves the\n"
    "same intent with minimal edits.\n\n"
    "# RULES\n"
    "- search_pattern MUST be an exact substring from the file content\n"
    "- replace_pattern MUST be the literal replacement text\n"
    "- Do NOT use regex or placeholders\n"
    "- Keep changes as small as possible\n\n"
    "# OUTPUT SCHEMA (JSON ONLY)\n"
    "Return a JSON object with:\n"
    "- search_pattern (string)\n"
    "- replace_pattern (string)"
)

DEFAULT_RETRY_USER_PROMPT = (
    "# FILE PATH\n{path}\n\n"
    "# FILE CONTENT\n{content}\n\n"
    "# INTENDED CHANGE\n"
    "Previous search_pattern (not found): {search_pattern}\n"
    "Previous replace_pattern: {replace_pattern}\n\n"
    "Provide a corrected literal search_pattern and replace_pattern now."
)


def render_prompt(template: str, **kwargs: str) -> str:
    try:
        return template.format(**kwargs)
    except KeyError as exc:
        missing = exc.args[0]
        raise ValueError(f"Missing prompt variable: {missing}") from exc


def build_audit_prompt(
    context: str,
    audit_system_prompt: str,
    audit_user_prompt: str,
) -> list[dict]:
    system_prompt = render_prompt(
        audit_system_prompt,
        context=context,
    )
    user_prompt = render_prompt(
        audit_user_prompt,
        context=context,
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_retry_prompt(
    path: str,
    content: str,
    search_pattern: str,
    replace_pattern: str,
    retry_system_prompt: str,
    retry_user_prompt: str,
) -> list[dict]:
    system_prompt = render_prompt(
        retry_system_prompt,
        path=path,
        content=content,
        search_pattern=search_pattern,
        replace_pattern=replace_pattern,
    )
    user_prompt = render_prompt(
        retry_user_prompt,
        path=path,
        content=content,
        search_pattern=search_pattern,
        replace_pattern=replace_pattern,
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


def build_documents_block(docs: list[SourceDoc]) -> str:
    parts: list[str] = []
    for doc in docs:
        parts.append(f"### {doc.path}\n{doc.content}")
    return "\n\n".join(parts)


def validate_audit_payload(payload: dict) -> tuple[list[dict], list[dict]]:
    if not isinstance(payload, dict):
        raise ValueError("Audit payload must be a JSON object.")
    issues = payload.get("issues", [])
    updates = payload.get("updates", [])
    if not isinstance(issues, list):
        raise ValueError("'issues' must be an array.")
    if not isinstance(updates, list):
        raise ValueError("'updates' must be an array.")
    for issue in issues:
        for key in ("id", "severity", "description", "impacted_files", "evidence"):
            if key not in issue:
                raise ValueError(f"Missing issue key '{key}'.")
        if issue["severity"] != "major":
            raise ValueError("Issue severity must be 'major'.")
    for update in updates:
        for key in ("search_pattern", "replace_pattern"):
            if key not in update:
                raise ValueError(f"Missing update key '{key}'.")
        if "paths" not in update and "path" not in update:
            raise ValueError("Update must include 'paths' or 'path'.")
    return issues, updates


def resolve_update_path(output_root: Path, relative_path: str) -> Path:
    target = (output_root / relative_path).resolve()
    root_resolved = output_root.resolve()
    if root_resolved not in target.parents and target != root_resolved:
        raise ValueError(f"Update path escapes output root: {relative_path}")
    return target


def apply_updates(
    output_root: Path,
    updates: list[dict],
    overwrite: bool,
    dry_run: bool,
) -> tuple[list[Path], list[dict]]:
    updated_paths: list[Path] = []
    missing_matches: list[dict] = []
    for update in updates:
        raw_paths = update.get("paths") or update.get("path")
        if isinstance(raw_paths, str):
            paths = [raw_paths]
        else:
            paths = list(raw_paths or [])

        search_pattern = str(update["search_pattern"])
        replace_pattern = str(update["replace_pattern"])
        if not paths:
            raise ValueError("Update must specify at least one path.")
        if not search_pattern:
            raise ValueError("Update search_pattern cannot be empty.")

        for relative_path in paths:
            relative_path = str(relative_path).strip()
            if not relative_path:
                raise ValueError("Update path cannot be empty.")
            target = resolve_update_path(output_root, relative_path)
            if not target.exists():
                raise FileNotFoundError(f"Update path does not exist: {relative_path}")

            original = target.read_text(encoding="utf-8")
            count = original.count(search_pattern)
            updated = original.replace(search_pattern, replace_pattern)
            if count == 0:
                missing_matches.append(
                    {
                        "path": relative_path,
                        "search_pattern": search_pattern,
                        "replace_pattern": replace_pattern,
                        "content": original,
                    }
                )
                continue
            if not overwrite and original == updated:
                continue
            if not dry_run:
                target.write_text(updated, encoding="utf-8")
            updated_paths.append(target)
    return updated_paths, missing_matches


def apply_retry_updates(
    output_root: Path,
    failures: list[dict],
    audit_model_id: str,
    overwrite: bool,
    dry_run: bool,
    retry_system_prompt: str,
    retry_user_prompt: str,
) -> list[Path]:
    updated_paths: list[Path] = []
    for failure in failures:
        path = failure["path"]
        content = failure["content"]
        messages = build_retry_prompt(
            path=path,
            content=content,
            search_pattern=failure["search_pattern"],
            replace_pattern=failure["replace_pattern"],
            retry_system_prompt=retry_system_prompt,
            retry_user_prompt=retry_user_prompt,
        )
        retry_payload = request_json(messages, audit_model_id)
        if "search_pattern" not in retry_payload or "replace_pattern" not in retry_payload:
            raise RuntimeError(f"Retry payload missing fields for {path}.")

        search_pattern = str(retry_payload["search_pattern"])
        replace_pattern = str(retry_payload["replace_pattern"])
        if not search_pattern:
            raise RuntimeError(f"Retry search_pattern is empty for {path}.")

        target = resolve_update_path(output_root, path)
        original = content
        count = original.count(search_pattern)
        updated = original.replace(search_pattern, replace_pattern)
        if count == 0:
            raise RuntimeError(
                "Retry update failed: search_pattern not found in "
                f"{path}: {search_pattern}"
            )
        if not overwrite and original == updated:
            continue
        if not dry_run:
            target.write_text(updated, encoding="utf-8")
        updated_paths.append(target)
    return updated_paths


def run_audit(
    output_root: Path,
    audit_model_id: str,
    overwrite: bool,
    dry_run: bool,
    audit_system_prompt: str,
    audit_user_prompt: str,
) -> None:
    docs = read_markdown_files(output_root)
    if not docs:
        raise RuntimeError("No markdown files found to include.")
    context = build_documents_block(docs)

    messages = build_audit_prompt(
        context,
        audit_system_prompt=audit_system_prompt,
        audit_user_prompt=audit_user_prompt,
    )
    payload = request_json(messages, audit_model_id)
    issues, updates = validate_audit_payload(payload)

    print(f"Major inconsistencies found: {len(issues)}")
    for issue in issues:
        print(f"- {issue['id']}: {issue['description']}")
        print(f"  Impacted: {', '.join(issue['impacted_files'])}")

    updated_paths, missing_matches = apply_updates(
        output_root=output_root,
        updates=updates,
        overwrite=overwrite,
        dry_run=dry_run,
    )
    if missing_matches:
        print(f"Retrying {len(missing_matches)} failed updates.")
        retry_paths = apply_retry_updates(
            output_root=output_root,
            failures=missing_matches,
            audit_model_id=audit_model_id,
            overwrite=overwrite,
            dry_run=dry_run,
            retry_system_prompt=DEFAULT_RETRY_SYSTEM_PROMPT,
            retry_user_prompt=DEFAULT_RETRY_USER_PROMPT,
        )
        updated_paths.extend(retry_paths)
    if dry_run:
        print(f"Dry run: {len(updated_paths)} files would be updated.")
    else:
        print(f"Files updated: {len(updated_paths)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit and fix major inconsistencies in a markdown knowledge base."
    )
    parser.add_argument(
        "--output-root",
        default=str(Path(__file__).resolve().parent),
        help="Root folder containing markdown files (default: knowledge-base).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite files if updates are required.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Detect inconsistencies but do not write updates.",
    )
    parser.add_argument(
        "--audit-model",
        default=DEFAULT_AUDIT_MODEL_ID,
        help="OpenRouter model ID for the audit step.",
    )
    parser.add_argument(
        "--audit-system-prompt",
        default=DEFAULT_AUDIT_SYSTEM_PROMPT,
        help="System prompt template for the audit step.",
    )
    parser.add_argument(
        "--audit-user-prompt",
        default=DEFAULT_AUDIT_USER_PROMPT,
        help="User prompt template for the audit step.",
    )

    args = parser.parse_args()
    output_root = Path(args.output_root).expanduser().resolve()
    run_audit(
        output_root=output_root,
        audit_model_id=args.audit_model,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        audit_system_prompt=args.audit_system_prompt,
        audit_user_prompt=args.audit_user_prompt,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
