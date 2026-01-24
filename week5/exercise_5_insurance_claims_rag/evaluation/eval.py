# TO UPDATE

# Evaluate RAG efficay (loads & assess indicators)import sys
import math
import sys
import re
import json
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv
import os

from evaluation.test import TestQuestion, load_tests
from implementation.answer import answer_question, fetch_context


load_dotenv(override=True)

MODEL = "google/gemini-2.5-flash"
DEFAULT_MAX_WORKERS = int(os.getenv("EVAL_MAX_WORKERS", "12"))

openai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))


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


def _sanitize_json_text(text: str) -> str:
    """Remove ASCII control characters that break JSON parsing."""
    return re.sub(r"[\x00-\x1f]", "", text)


def _repair_json_response(raw_text: str) -> str:
    """Ask the model to repair invalid JSON into the AnswerEval schema."""
    repair_messages = [
        {
            "role": "system",
            "content": (
                "You fix invalid JSON into a valid JSON object. "
                "Return only JSON with keys: feedback, accuracy, completeness, relevance. "
                "accuracy/completeness/relevance must be numbers 1-5."
            ),
        },
        {"role": "user", "content": raw_text},
    ]
    repair_response = openai.chat.completions.create(
        model=MODEL,
        messages=repair_messages,
        response_format={"type": "json_object"},
    )
    return repair_response.choices[0].message.content or ""


class RetrievalEval(BaseModel):
    """Evaluation metrics for retrieval performance."""

    mrr: float = Field(description="Mean Reciprocal Rank - average across all keywords")
    ndcg: float = Field(description="Normalized Discounted Cumulative Gain (binary relevance)")
    keywords_found: int = Field(description="Number of keywords found in top-k results")
    total_keywords: int = Field(description="Total number of keywords to find")
    keyword_coverage: float = Field(description="Percentage of keywords found")


class AnswerEval(BaseModel):
    """LLM-as-a-judge evaluation of answer quality."""

    feedback: str = Field(
        description="Concise feedback on the answer quality, comparing it to the reference answer and evaluating based on the retrieved context"
    )
    accuracy: float = Field(
        description="How factually correct is the answer compared to the reference answer? 1 (wrong. any wrong answer must score 1) to 5 (ideal - perfectly accurate). An acceptable answer would score 3."
    )
    completeness: float = Field(
        description="How complete is the answer in addressing all aspects of the question? 1 (very poor - missing key information) to 5 (ideal - all the information from the reference answer is provided completely). Only answer 5 if ALL information from the reference answer is included."
    )
    relevance: float = Field(
        description="How relevant is the answer to the specific question asked? 1 (very poor - off-topic) to 5 (ideal - directly addresses question and gives no additional information). Only answer 5 if the answer is completely relevant to the question and gives no additional information."
    )


def _safe_retrieval_eval(test: TestQuestion, error: Exception | None = None) -> RetrievalEval:
    if error:
        print(f"[eval] Retrieval failed for '{test.question}': {error}", file=sys.stderr)
    return RetrievalEval(
        mrr=0.0,
        ndcg=0.0,
        keywords_found=0,
        total_keywords=len(test.keywords),
        keyword_coverage=0.0,
    )


def _safe_answer_eval(test: TestQuestion, error: Exception | None = None) -> AnswerEval:
    feedback = "Evaluation failed; returning neutral fallback scores."
    if error:
        feedback = f"Evaluation failed: {error}"
        print(f"[eval] Answer eval failed for '{test.question}': {error}", file=sys.stderr)
    return AnswerEval(feedback=feedback, accuracy=1.0, completeness=1.0, relevance=1.0)


def calculate_mrr(keyword: str, retrieved_docs: list) -> float:
    """Calculate reciprocal rank for a single keyword (case-insensitive)."""
    keyword_lower = keyword.lower()
    for rank, doc in enumerate(retrieved_docs, start=1):
        if keyword_lower in doc.page_content.lower():
            return 1.0 / rank
    return 0.0


def calculate_dcg(relevances: list[int], k: int) -> float:
    """Calculate Discounted Cumulative Gain."""
    dcg = 0.0
    for i in range(min(k, len(relevances))):
        dcg += relevances[i] / math.log2(i + 2)  # i+2 because rank starts at 1
    return dcg


def calculate_ndcg(keyword: str, retrieved_docs: list, k: int = 10) -> float:
    """Calculate nDCG for a single keyword (binary relevance, case-insensitive)."""
    keyword_lower = keyword.lower()

    # Binary relevance: 1 if keyword found, 0 otherwise
    relevances = [
        1 if keyword_lower in doc.page_content.lower() else 0 for doc in retrieved_docs[:k]
    ]

    # DCG
    dcg = calculate_dcg(relevances, k)

    # Ideal DCG (best case: keyword in first position)
    ideal_relevances = sorted(relevances, reverse=True)
    idcg = calculate_dcg(ideal_relevances, k)

    return dcg / idcg if idcg > 0 else 0.0


def evaluate_retrieval(test: TestQuestion, k: int = 10) -> RetrievalEval:
    """
    Evaluate retrieval performance for a test question.

    Args:
        test: TestQuestion object containing question and keywords
        k: Number of top documents to retrieve (default 10)

    Returns:
        RetrievalEval object with MRR, nDCG, and keyword coverage metrics
    """
    # Retrieve documents using shared answer module
    try:
        retrieved_docs = fetch_context(test.question)
    except Exception as exc:
        return _safe_retrieval_eval(test, exc)

    # Calculate MRR (average across all keywords)
    mrr_scores = [calculate_mrr(keyword, retrieved_docs) for keyword in test.keywords]
    avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0.0

    # Calculate nDCG (average across all keywords)
    ndcg_scores = [calculate_ndcg(keyword, retrieved_docs, k) for keyword in test.keywords]
    avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0

    # Calculate keyword coverage
    keywords_found = sum(1 for score in mrr_scores if score > 0)
    total_keywords = len(test.keywords)
    keyword_coverage = (keywords_found / total_keywords * 100) if total_keywords > 0 else 0.0

    return RetrievalEval(
        mrr=avg_mrr,
        ndcg=avg_ndcg,
        keywords_found=keywords_found,
        total_keywords=total_keywords,
        keyword_coverage=keyword_coverage,
    )


def evaluate_answer(test: TestQuestion) -> tuple[AnswerEval, str, list]:
    """
    Evaluate answer quality using LLM-as-a-judge (async).

    Args:
        test: TestQuestion object containing question and reference answer

    Returns:
        Tuple of (AnswerEval object, generated_answer string, retrieved_docs list)
    """
    # Get RAG response using shared answer module
    try:
        generated_answer, retrieved_docs = answer_question(test.question)
    except Exception as exc:
        return _safe_answer_eval(test, exc), "Error generating answer.", []

    # LLM judge prompt
    judge_messages = [
        {
            "role": "system",
            "content": "You are an expert evaluator assessing the quality of answers. Evaluate the generated answer by comparing it to the reference answer. Only give 5/5 scores for perfect answers. Respond only with JSON in this format: {\"feedback\": \"...\", \"accuracy\": 1-5, \"completeness\": 1-5, \"relevance\": 1-5}.",
        },
        {
            "role": "user",
            "content": f"""Question:
{test.question}

Generated Answer:
{generated_answer}

Reference Answer:
{test.reference_answer}

Please evaluate the generated answer on three dimensions:
1. Accuracy: How factually correct is it compared to the reference answer? Only give 5/5 scores for perfect answers.
2. Completeness: How thoroughly does it address all aspects of the question, covering all the information from the reference answer?
3. Relevance: How well does it directly answer the specific question asked, giving no additional information?

Provide detailed feedback and scores from 1 (very poor) to 5 (ideal) for each dimension. If the answer is wrong, then the accuracy score must be 1.""",
        },
    ]

    # Call LLM judge with structured outputs
    judge_response = openai.chat.completions.create(
        model=MODEL,
        messages=judge_messages,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "answer_eval",
                "schema": AnswerEval.model_json_schema(),
                "strict": True,
            },
        },
    )

    response_text = judge_response.choices[0].message.content or ""
    response_text = _sanitize_json_text(response_text)
    if not (response_text.startswith("{") or response_text.startswith("[")):
        response_text = _extract_json(response_text)
    try:
        answer_eval = AnswerEval.model_validate_json(response_text)
    except Exception as exc:
        try:
            repaired = _repair_json_response(response_text)
            repaired = _sanitize_json_text(repaired)
            if not (repaired.startswith("{") or repaired.startswith("[")):
                repaired = _extract_json(repaired)
            answer_eval = AnswerEval.model_validate_json(repaired)
        except Exception as repair_exc:
            return _safe_answer_eval(test, repair_exc), generated_answer, retrieved_docs

    return answer_eval, generated_answer, retrieved_docs


def evaluate_all_retrieval(max_workers: int | None = None, heartbeat_seconds: float = 5.0):
    """Evaluate all retrieval tests using parallel execution."""
    tests = load_tests()
    total_tests = len(tests)
    if total_tests == 0:
        return

    max_workers = max_workers or min(DEFAULT_MAX_WORKERS, total_tests)
    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_test = {executor.submit(evaluate_retrieval, test): test for test in tests}
        while future_to_test:
            done, _ = wait(
                future_to_test.keys(),
                timeout=heartbeat_seconds,
                return_when=FIRST_COMPLETED,
            )
            if not done:
                progress = completed / total_tests
                yield None, None, progress
                continue
            for future in done:
                test = future_to_test.pop(future)
                try:
                    result = future.result()
                except Exception as exc:
                    result = _safe_retrieval_eval(test, exc)
                completed += 1
                progress = completed / total_tests
                yield test, result, progress


def evaluate_all_answers(max_workers: int | None = None, heartbeat_seconds: float = 5.0):
    """Evaluate all answers to tests using parallel execution."""
    tests = load_tests()
    total_tests = len(tests)
    if total_tests == 0:
        return

    max_workers = max_workers or min(DEFAULT_MAX_WORKERS, total_tests)
    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_test = {executor.submit(evaluate_answer, test): test for test in tests}
        while future_to_test:
            done, _ = wait(
                future_to_test.keys(),
                timeout=heartbeat_seconds,
                return_when=FIRST_COMPLETED,
            )
            if not done:
                progress = completed / total_tests
                yield None, None, progress
                continue
            for future in done:
                test = future_to_test.pop(future)
                try:
                    result = future.result()[0]
                except Exception as exc:
                    result = _safe_answer_eval(test, exc)
                completed += 1
                progress = completed / total_tests
                yield test, result, progress


def run_cli_evaluation(test_number: int):
    """Run evaluation for a specific test (async helper for CLI)."""
    # Load tests
    tests = load_tests("tests.jsonl")

    if test_number < 0 or test_number >= len(tests):
        print(f"Error: test_row_number must be between 0 and {len(tests) - 1}")
        sys.exit(1)

    # Get the test
    test = tests[test_number]

    # Print test info
    print(f"\n{'=' * 80}")
    print(f"Test #{test_number}")
    print(f"{'=' * 80}")
    print(f"Question: {test.question}")
    print(f"Keywords: {test.keywords}")
    print(f"Category: {test.category}")
    print(f"Reference Answer: {test.reference_answer}")
    print(f"Final Decision: {test.final_decision}")
    print(f"Reason: {test.reason}")

    # Retrieval Evaluation
    print(f"\n{'=' * 80}")
    print("Retrieval Evaluation")
    print(f"{'=' * 80}")

    retrieval_result = evaluate_retrieval(test)

    print(f"MRR: {retrieval_result.mrr:.4f}")
    print(f"nDCG: {retrieval_result.ndcg:.4f}")
    print(f"Keywords Found: {retrieval_result.keywords_found}/{retrieval_result.total_keywords}")
    print(f"Keyword Coverage: {retrieval_result.keyword_coverage:.1f}%")

    # Answer Evaluation
    print(f"\n{'=' * 80}")
    print("Answer Evaluation")
    print(f"{'=' * 80}")

    answer_result, generated_answer, retrieved_docs = evaluate_answer(test)

    print(f"\nGenerated Answer:\n{generated_answer}")
    print(f"\nFeedback:\n{answer_result.feedback}")
    print("\nScores:")
    print(f"  Accuracy: {answer_result.accuracy:.2f}/5")
    print(f"  Completeness: {answer_result.completeness:.2f}/5")
    print(f"  Relevance: {answer_result.relevance:.2f}/5")
    print(f"\n{'=' * 80}\n")


def main():
    """CLI to evaluate a specific test by row number."""
    if len(sys.argv) != 2:
        print("Usage: uv run eval.py <test_row_number>")
        sys.exit(1)

    try:
        test_number = int(sys.argv[1])
    except ValueError:
        print("Error: test_row_number must be an integer")
        sys.exit(1)

    run_cli_evaluation(test_number)


if __name__ == "__main__":
    main()
