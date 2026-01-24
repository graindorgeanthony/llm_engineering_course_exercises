# TO UPDATE

import json
from pathlib import Path
from pydantic import BaseModel, Field

TEST_FILE = str(Path(__file__).parent / "tests.jsonl")


class TestQuestion(BaseModel):
    """A test question with expected keywords and reference answer."""

    question: str = Field(description="The question to ask the RAG system")
    keywords: list[str] = Field(description="Keywords that must appear in retrieved context")
    reference_answer: str = Field(description="The reference answer for this question")
    final_decision: str = Field(description="Expected decision outcome (e.g., approval, refusal)")
    reason: str = Field(description="Concise rationale for the expected decision")
    category: str = Field(
        default="uncategorized",
        description="Optional question category (e.g., direct_fact, spanning, temporal)",
    )


def load_tests(test_file: str | None = None) -> list[TestQuestion]:
    """Load test questions from JSONL file."""
    tests = []
    file_path = test_file or TEST_FILE
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line.strip())
            tests.append(TestQuestion(**data))
    return tests
