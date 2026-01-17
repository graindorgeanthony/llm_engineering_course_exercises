import os
import json
import concurrent.futures
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr

load_dotenv(override=True)

# LLM API clients
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

OPENROUTER_CLIENT = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Default model list shown in UI and used for batch runs.
# These are OpenRouter model IDs.
models = [
    "google/gemini-2.5-flash",
    "google/gemini-2.5-pro",
    "google/gemini-3-flash-preview",
    "google/gemini-3-pro-preview",
    "openai/gpt-5.2",
    "x-ai/grok-code-fast-1",
    "x-ai/grok-4.1-fast",
    "anthropic/claude-sonnet-4.5",
    "anthropic/claude-opus-4.5",
    "xiaomi/mimo-v2-flash:free",
    "deepseek/deepseek-v3.2"
]

# Registry mapping model IDs to OpenRouter client instances.
clients = {
    "google/gemini-2.5-flash": OPENROUTER_CLIENT,
    "google/gemini-2.5-pro": OPENROUTER_CLIENT,
    "google/gemini-3-flash-preview": OPENROUTER_CLIENT,
    "google/gemini-3-pro-preview": OPENROUTER_CLIENT,
    "openai/gpt-5.2": OPENROUTER_CLIENT,
    "x-ai/grok-code-fast-1": OPENROUTER_CLIENT,
    "x-ai/grok-4.1-fast": OPENROUTER_CLIENT,
    "anthropic/claude-sonnet-4.5": OPENROUTER_CLIENT,
    "anthropic/claude-opus-4.5": OPENROUTER_CLIENT,
    "xiaomi/mimo-v2-flash:free": OPENROUTER_CLIENT,
    "deepseek/deepseek-v3.2": OPENROUTER_CLIENT,
}

EVALUATOR_MODEL = "google/gemini-3-flash-preview"
EVALUATOR_CLIENT = OPENROUTER_CLIENT

OPENROUTER_MODEL_CACHE: set[str] | None = None


def fetch_openrouter_model_ids() -> set[str] | None:
    """Fetch all OpenRouter model IDs once and cache them for add-model validation."""
    global OPENROUTER_MODEL_CACHE
    if OPENROUTER_MODEL_CACHE is not None:
        return OPENROUTER_MODEL_CACHE
    try:
        model_list = OPENROUTER_CLIENT.models.list()
        OPENROUTER_MODEL_CACHE = {model.id for model in model_list.data}
        return OPENROUTER_MODEL_CACHE
    except Exception:
        return None


def normalize_criteria(criteria_text: str) -> list[str]:
    """Normalize criteria into a non-empty list; supports commas or newlines."""
    raw_lines = [line.strip() for line in criteria_text.splitlines()]
    criteria = []
    for line in raw_lines:
        if not line:
            continue
        if "," in line:
            criteria.extend([item.strip() for item in line.split(",") if item.strip()])
        else:
            criteria.append(line)
    if not criteria:
        criteria = ["Accuracy", "Completeness", "Clarity"]
    return criteria


def parse_examples(sample_input: str, sample_output: str) -> list[dict]:
    """
    Parse input and output fields into multiple examples.
    Examples are separated by '---' on its own line.
    Each field can have 0, 1, or multiple examples (they don't need to match).
    """
    def split_examples(text: str) -> list[str]:
        if not text.strip():
            return []
        # Split by --- and clean up
        examples = [ex.strip() for ex in text.split('\n---\n') if ex.strip()]
        return examples
    
    inputs = split_examples(sample_input)
    outputs = split_examples(sample_output)
    
    # Create pairs, allowing mismatched lengths
    max_len = max(len(inputs), len(outputs))
    examples = []
    for i in range(max_len):
        examples.append({
            "input": inputs[i] if i < len(inputs) else "",
            "output": outputs[i] if i < len(outputs) else ""
        })
    
    return examples


def build_task_prompt(task: str, sample_input: str, sample_output: str, include_output_in_prompt: bool) -> str:
    """
    Build the task prompt for generation.
    Supports multiple input-output examples separated by '---'.
    """
    task = task.strip()
    examples = parse_examples(sample_input, sample_output)
    
    if not examples:
        return f"Task:\n{task}\n\nRespond with the best possible answer for the task."
    
    prompt_parts = ["Task:", task, ""]
    
    # Add examples
    if len(examples) == 1:
        # Single example
        ex = examples[0]
        if ex["input"]:
            prompt_parts.extend(["Sample Input:", ex["input"], ""])
        if include_output_in_prompt and ex["output"]:
            prompt_parts.extend(["Expected Output:", ex["output"], ""])
    else:
        # Multiple examples
        prompt_parts.append("Examples:")
        for idx, ex in enumerate(examples, 1):
            if ex["input"] or ex["output"]:
                prompt_parts.append(f"\nExample {idx}:")
                if ex["input"]:
                    prompt_parts.extend(["Input:", ex["input"]])
                if include_output_in_prompt and ex["output"]:
                    prompt_parts.extend(["Output:", ex["output"]])
        prompt_parts.append("")
    
    prompt_parts.append("Respond with the best possible answer for the task.")
    return "\n".join(prompt_parts)


def messages_for_generation(task: str, sample_input: str, sample_output: str, include_output: bool) -> list[dict]:
    """Create chat messages for the generation call."""
    return [
        {"role": "system", "content": "You are an expert assistant. Provide a high-quality response."},
        {"role": "user", "content": build_task_prompt(task, sample_input, sample_output, include_output)},
    ]


def generate_answer(model: str, task: str, sample_input: str, sample_output: str, include_output: bool) -> str:
    """Generate an answer from a single model."""
    client = clients[model]
    reasoning_effort = "high" if "gpt" in model else None
    response = client.chat.completions.create(
        model=model,
        messages=messages_for_generation(task, sample_input, sample_output, include_output),
        reasoning_effort=reasoning_effort,
    )
    return response.choices[0].message.content or ""


def build_evaluator_prompt(
    criteria: list[str],
    answers: list[tuple[str, str]],
    sample_input: str,
    sample_output: str,
) -> str:
    """Create evaluation prompt that requests JSON-only scoring output."""
    criteria_block = "\n".join(f"- {criterion}" for criterion in criteria)
    sample_input = sample_input.strip()
    sample_output = sample_output.strip()
    prompt_parts = [
        "You are a strict evaluator. Score EACH answer against each criterion on a 1-10 scale.",
        "Return ONLY valid JSON with a top-level key: evaluations.",
        "Each evaluation must include: answer_id (string), criteria (list of objects with criterion, score, reason), summary (string).",
        "Do not guess or mention model names. Evaluate answers independently and fairly.",
        "",
        "Evaluation Criteria:",
        criteria_block,
        "",
    ]
    if sample_input:
        prompt_parts.extend(["Input:", sample_input, ""])
    if sample_output:
        prompt_parts.extend(["Target Output:", sample_output, ""])
    prompt_parts.append("Answers:")
    for answer_id, answer in answers:
        prompt_parts.extend([f"{answer_id}:", answer, ""])
    return "\n".join(prompt_parts).strip()


def compute_overall_score(criteria_scores: list[float]) -> float | None:
    """Average criteria scores to a 0-100 scale (None if no valid scores)."""
    valid_scores = [score for score in criteria_scores if isinstance(score, (int, float))]
    if not valid_scores:
        return None
    return round(sum(valid_scores) / len(valid_scores) * 10, 1)


def extract_criteria_scores(parsed: dict, criteria: list[str]) -> dict[str, float | None]:
    """Map criterion names to scores from evaluator output."""
    score_lookup = {}
    for item in parsed.get("criteria", []) if isinstance(parsed.get("criteria"), list) else []:
        criterion_name = str(item.get("criterion", "")).strip().lower()
        score_value = item.get("score")
        if isinstance(score_value, (int, float)):
            score_lookup[criterion_name] = float(score_value)
    scores = {}
    for criterion in criteria:
        scores[criterion] = score_lookup.get(criterion.strip().lower())
    return scores


def extract_json(payload: str) -> dict | None:
    """Best-effort JSON extraction for evaluator responses with extra text."""
    payload = payload.strip()
    if payload.startswith("{") and payload.endswith("}"):
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None
    start = payload.find("{")
    end = payload.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(payload[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


def evaluate_answers(answers: list[tuple[str, str]], criteria: list[str], sample_input: str, sample_output: str) -> dict:
    """Score answers with the evaluator model and return parsed JSON when possible."""
    response = EVALUATOR_CLIENT.chat.completions.create(
        model=EVALUATOR_MODEL,
        messages=[
            {"role": "system", "content": "You are a precise evaluator."},
            {"role": "user", "content": build_evaluator_prompt(criteria, answers, sample_input, sample_output)},
        ],
    )
    content = response.choices[0].message.content or ""
    parsed = extract_json(content)
    if parsed:
        evaluations = parsed.get("evaluations", []) if isinstance(parsed.get("evaluations"), list) else []
        by_label = {}
        for item in evaluations:
            answer_id = str(item.get("answer_id", "")).strip()
            if answer_id:
                by_label[answer_id] = item
        return {"ok": True, "raw": content, "parsed": parsed, "by_label": by_label}
    return {"ok": False, "raw": content, "parsed": None, "by_label": {}}


def make_answer_labels(count: int) -> list[str]:
    """Generate stable labels (A, B, C...) for evaluator prompts."""
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    labels = []
    for idx in range(count):
        if idx < len(alphabet):
            labels.append(alphabet[idx])
        else:
            labels.append(f"Answer{idx + 1}")
    return labels


def run_benchmark_single(model: str, task: str, sample_input: str, sample_output: str, criteria_text: str, include_output: bool):
    """Run generation + evaluation for one model and format a small results table."""
    criteria = normalize_criteria(criteria_text)
    try:
        answer = generate_answer(model, task, sample_input, sample_output, include_output)
        result = {"ok": True, "answer": answer}
    except Exception as exc:
        result = {"ok": False, "answer": f"❌ Generation error: {exc}"}

    if result["ok"]:
        label = make_answer_labels(1)[0]
        evaluation = evaluate_answers([(label, result["answer"])], criteria, sample_input, sample_output)
        evaluation_item = evaluation["by_label"].get(label)
    else:
        evaluation = {"ok": False, "raw": result["answer"], "parsed": None, "by_label": {}}
        evaluation_item = None

    criteria_scores = {criterion: None for criterion in criteria}
    overall_score = None
    summary = "Evaluation failed."
    if evaluation["ok"] and evaluation_item:
        criteria_scores = extract_criteria_scores(evaluation_item, criteria)
        overall_score = compute_overall_score(list(criteria_scores.values()))
        summary = evaluation_item.get("summary", "")
    elif result["ok"]:
        summary = "Evaluation parse failed."

    columns = ["Model", "Overall Score", "Status", "Summary", *criteria]
    row = [
        model,
        overall_score,
        "✅ OK" if result["ok"] else "❌ Error",
        summary,
        *[criteria_scores[criterion] for criterion in criteria],
    ]
    table_data = [row]

    log_lines = [
        f"{'='*80}",
        f"MODEL: {model}",
        f"SCORE: {overall_score}/100" if overall_score else "SCORE: N/A",
        f"{'='*80}",
        "",
        "📝 GENERATED ANSWER:",
        "-" * 80,
        result["answer"],
        "",
        "⭐ EVALUATION DETAILS:",
        "-" * 80,
        evaluation["raw"],
        "",
    ]

    return gr.update(value=table_data, headers=columns), "\n".join(log_lines)


def run_benchmark_all(
    task: str,
    sample_input: str,
    sample_output: str,
    criteria_text: str,
    include_output: bool,
    selected_models: list[str],
):
    """Run generation for selected models, evaluate them, and format leaderboard output."""
    criteria = normalize_criteria(criteria_text)
    selected_models = selected_models or []
    if not selected_models:
        columns = ["Model", "Overall Score", "Status", "Summary", *criteria]
        return gr.update(value=[], headers=columns), "No models selected."

    def run_generation(model: str):
        try:
            answer = generate_answer(model, task, sample_input, sample_output, include_output)
            return model, {"ok": True, "answer": answer}
        except Exception as exc:
            return model, {"ok": False, "answer": f"❌ Generation error: {exc}"}

    results = []
    max_workers = min(6, len(selected_models)) if selected_models else 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_model = {executor.submit(run_generation, model): model for model in selected_models}
        for future in concurrent.futures.as_completed(future_to_model):
            results.append(future.result())

    ok_results = [(model, result) for model, result in results if result["ok"]]
    labels = make_answer_labels(len(ok_results))
    labeled_answers = [(label, result["answer"]) for (label, (_, result)) in zip(labels, ok_results)]
    evaluation = evaluate_answers(labeled_answers, criteria, sample_input, sample_output) if ok_results else {
        "ok": False,
        "raw": "No successful answers to evaluate.",
        "parsed": None,
        "by_label": {},
    }
    eval_lookup = {}
    for label, (model, _) in zip(labels, ok_results):
        eval_lookup[model] = {
            "ok": evaluation["ok"] and label in evaluation["by_label"],
            "raw": evaluation["raw"],
            "parsed": evaluation["by_label"].get(label),
        }
    for model, result in results:
        if not result["ok"]:
            eval_lookup[model] = {"ok": False, "raw": result["answer"], "parsed": None}
    rows = []
    log_lines = []
    for model, result in results:
        evaluation = eval_lookup.get(model, {"ok": False, "raw": "No evaluation", "parsed": None})
        criteria_scores = {criterion: None for criterion in criteria}
        overall_score = None
        summary = "Evaluation failed."
        if evaluation["ok"] and evaluation["parsed"]:
            criteria_scores = extract_criteria_scores(evaluation["parsed"], criteria)
            overall_score = compute_overall_score(list(criteria_scores.values()))
            summary = evaluation["parsed"].get("summary", "")
        elif result["ok"]:
            summary = "Evaluation parse failed."
        rows.append(
            (
                model,
                overall_score,
                "✅ OK" if result["ok"] else "❌ Error",
                summary,
                criteria_scores,
            )
        )

        log_lines.append(f"\n{'='*100}")
        log_lines.append(f"MODEL: {model}")
        log_lines.append(f"SCORE: {overall_score}/100" if overall_score else "SCORE: N/A")
        log_lines.append(f"{'='*100}\n")
        log_lines.append("📝 GENERATED ANSWER:")
        log_lines.append("-" * 100)
        log_lines.append(result["answer"])
        log_lines.append("")
        log_lines.append("⭐ EVALUATION DETAILS:")
        log_lines.append("-" * 100)
        log_lines.append(evaluation["raw"])
        log_lines.append("")

    rows_sorted = sorted(rows, key=lambda row: row[1] if isinstance(row[1], (int, float)) else -1.0, reverse=True)
    columns = ["Model", "Overall Score", "Status", "Summary", *criteria]
    table_data = []
    for model, overall_score, status, summary, criteria_scores in rows_sorted:
        table_data.append(
            [
                model,
                overall_score,
                status,
                summary,
                *[criteria_scores[criterion] for criterion in criteria],
            ]
        )

    # Add summary header to logs
    log_header = [
        "=" * 100,
        "🏆 BENCHMARK RESULTS SUMMARY",
        "=" * 100,
        f"Models Tested: {len(results)}",
        f"Evaluation Criteria: {', '.join(criteria)}",
        "",
    ]
    
    # Add leaderboard
    leaderboard = ["📊 LEADERBOARD:", "-" * 50]
    for idx, (model, score, status, _, _) in enumerate(rows_sorted, 1):
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
        score_str = f"{score}/100" if isinstance(score, (int, float)) else "N/A"
        leaderboard.append(f"{medal} {model}: {score_str} {status}")
    
    leaderboard.extend(["", "=" * 100, "📝 DETAILED OUTPUTS:", "=" * 100, ""])
    
    formatted_logs = "\n".join(log_header + leaderboard + log_lines)
    
    return gr.update(value=table_data, headers=columns), formatted_logs


def prepare_all_results_view():
    """Initialize UI placeholders for the multi-model results."""
    return (
        gr.update(visible=True),
        gr.update(value=[]),
        "Running evaluations across all models...\n\n(Logs will appear here.)",
    )


def prepare_single_results_view():
    """Initialize UI placeholders for single-model results."""
    return (
        gr.update(visible=True),
        gr.update(value=[]),
        "Running evaluation for the selected model...\n\n(Logs will appear here.)",
    )


def parse_model_input(model_input: str) -> list[str]:
    """Parse user input for add-model textbox into list of model IDs."""
    raw = [item.strip() for item in model_input.replace("\n", ",").split(",")]
    return [item for item in raw if item]


def add_openrouter_models(model_input: str, current_choices: list[str], selected_choices: list[str]):
    """Validate and add new OpenRouter model IDs to the selector."""
    new_models = parse_model_input(model_input)
    if not new_models:
        return (
            gr.update(),
            selected_choices or [],
            "Enter one or more OpenRouter model IDs to add.",
            current_choices or [],
        )

    available = fetch_openrouter_model_ids()
    if available is None:
        return (
            gr.update(),
            selected_choices or [],
            "Could not verify model availability. Please try again later.",
            current_choices or [],
        )

    existing = set(current_choices or [])
    added = []
    invalid = []
    for model_id in new_models:
        if model_id not in available:
            invalid.append(model_id)
            continue
        if model_id not in existing:
            current_choices.append(model_id)
            existing.add(model_id)
            clients[model_id] = OPENROUTER_CLIENT
            added.append(model_id)

    selected = list({*(selected_choices or []), *added})
    status_parts = []
    if added:
        status_parts.append(f"Added {len(added)} model(s).")
    if invalid:
        status_parts.append(f"Unavailable: {', '.join(invalid)}")
    if not status_parts:
        status_parts.append("All models already exist in the list.")
    status = " ".join(status_parts)
    return gr.update(choices=current_choices), selected, status, current_choices


# Gradio UI - Example Test Cases

EXAMPLE_USE_CASES = {
    "Code Generation & Debugging": {
        "task": """Write a Python function that finds all prime numbers up to n using the Sieve of Eratosthenes algorithm. 
Include error handling for invalid inputs and add docstring documentation.""",
        "input": "n = 30",
        "output": """Expected: A complete function with:
- Proper algorithm implementation
- Input validation (n must be positive integer)
- Clear docstring with parameters and return type
- Returns list of primes: [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]""",
        "criteria": "Correctness\nCode Quality\nDocumentation\nError Handling\nEfficiency"
    },
    "Data Analysis & Extraction": {
        "task": "Extract and structure key information from this customer support conversation into JSON format.",
        "input": '''Customer: "Hi, my order #12345 hasn't arrived. I ordered it on Jan 5th and paid $89.99."
Agent: "I apologize. Let me check... It shows delivered on Jan 10th to 123 Main St."
Customer: "That's not my address! I live at 456 Oak Ave."''',
        "output": '''{"order_id": "12345", "order_date": "2024-01-05", "amount": 89.99, "issue": "wrong_delivery_address", 
"delivered_to": "123 Main St", "correct_address": "456 Oak Ave", "status": "unresolved"}''',
        "criteria": "Accuracy\nCompleteness\nJSON Validity\nKey Information Extraction"
    },
    "Creative Problem Solving": {
        "task": "You have a 3L jug and a 5L jug. How can you measure exactly 4L of water? Explain step-by-step.",
        "input": "No additional tools available. You have unlimited water source.",
        "output": """Should provide a clear, logical sequence of steps:
1. Fill 5L jug completely
2. Pour from 5L into 3L jug (5L jug now has 2L)
3. Empty 3L jug
4. Pour 2L from 5L jug into 3L jug
5. Fill 5L jug completely again
6. Pour from 5L into 3L until full (1L poured, 4L remains in 5L jug)""",
        "criteria": "Logical Correctness\nClarity\nStep-by-Step Detail\nPracticality"
    },
    "Technical Explanation": {
        "task": "Explain how HTTPS encryption works to a non-technical audience without using jargon.",
        "input": "Target audience: Business professionals with no cybersecurity background",
        "output": """Should explain:
- What HTTPS does (protects data in transit)
- Simple analogy (like a locked briefcase vs open envelope)
- Why it matters (prevents eavesdropping, tampering)
- How users know it's active (padlock icon)
WITHOUT technical terms like: asymmetric encryption, SSL/TLS, cipher suites, etc.""",
        "criteria": "Clarity\nAccessibility\nAccuracy\nUse of Analogies\nAvoidance of Jargon"
    },
    "Instruction Following & Constraints": {
        "task": "Write a product description for wireless headphones following these constraints exactly.",
        "input": """Constraints:
- Exactly 3 sentences
- First sentence must mention battery life (24hrs)
- Must include words: premium, comfortable, immersive
- No superlatives (best, greatest, most)
- Price point: mid-range ($150-200)""",
        "output": """Example: "Experience immersive sound quality with 24-hour battery life for all-day listening. 
These premium wireless headphones feature comfortable ear cushions designed for extended wear. 
At just $179, they deliver exceptional audio performance for the mid-range market."
(Evaluator should verify ALL constraints are met)""",
        "criteria": "Constraint Adherence\nWriting Quality\nPersuasiveness\nAccuracy"
    },
    "LLM Production Deployment": {
        "task": "Summarize the key risks and mitigations for deploying an LLM in production.",
        "input": "The system must handle sensitive data and run at low latency.",
        "output": "Provide risks (e.g., privacy leakage, latency spikes) and mitigations (e.g., PII redaction, caching).",
        "criteria": "Accuracy\nCompleteness\nClarity\nActionability"
    }
}


def load_example(example_name: str):
    """Load example use case and return values for all input fields."""
    if example_name not in EXAMPLE_USE_CASES:
        example_name = list(EXAMPLE_USE_CASES.keys())[0]
    
    example = EXAMPLE_USE_CASES[example_name]
    return (
        example["task"],
        example["input"],
        example["output"],
        example["criteria"]
    )


def format_results_summary(table_data, headers):
    """Generate a summary markdown of the benchmark results."""
    if not table_data or not headers:
        return "No results to summarize yet."
    
    # Find best model
    scores = [(row[0], row[1]) for row in table_data if isinstance(row[1], (int, float))]
    if not scores:
        return "No valid scores found."
    
    best_model, best_score = max(scores, key=lambda x: x[1])
    worst_model, worst_score = min(scores, key=lambda x: x[1])
    avg_score = sum(s for _, s in scores) / len(scores)
    
    summary = f"""
### 🏆 Benchmark Summary

**Best Performer:** {best_model} ({best_score}/100)
**Lowest Score:** {worst_model} ({worst_score}/100)
**Average Score:** {avg_score:.1f}/100
**Models Tested:** {len(scores)}

---
"""
    return summary

APP_THEME = gr.themes.Soft()
APP_CSS = """
    .gradio-container {max-width: 1400px !important;}
    .section-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 1.2em;
        margin-top: 1.5em;
        margin-bottom: 0.5em;
    }
    .card-box {
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px;
        background: #fafafa;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .compact-row {gap: 8px !important;}
    #results_tabs {margin-top: 24px;}
    .metric-card {
        text-align: center;
        padding: 16px;
        border-radius: 8px;
        background: white;
        border: 1px solid #e0e0e0;
    }
"""

with gr.Blocks() as ui:
    gr.Markdown("""
    # 🧪 Ultimate LLM Benchmark Tester
    ### Compare multiple LLM models side-by-side with custom evaluation criteria
    """)
    
    with gr.Accordion("ℹ️ How to Use This Tool", open=False):
        gr.Markdown("""
        **Quick Start:**
        1. 📋 Select a pre-built example or create your own test
        2. ✏️ Customize the task, inputs, and evaluation criteria
        3. 🎯 Choose Few-Shot (with examples) or Zero-Shot (pure capability test)
        4. 🚀 Run single model for quick tests, or all models for comprehensive comparison
        
        **Pro Tips:**
        - Separate multiple examples with `---` on its own line
        - Use specific evaluation criteria for better insights
        - Few-shot mode helps with formatting and consistency
        - Zero-shot mode tests pure model capabilities
        """)
    
    # Example selector with better prominence
    example_choices = list(EXAMPLE_USE_CASES.keys())
    gr.HTML('<div class="section-header">📋 Quick Start: Example Use Cases</div>')
    
    with gr.Row(elem_classes="compact-row"):
        example_selector = gr.Dropdown(
            choices=example_choices,
            value=example_choices[0],
            label="Select Example Template",
            info="Choose a pre-configured test case or start from scratch",
            scale=3
        )
        clear_btn = gr.Button("🔄 Clear All Fields", variant="secondary", scale=1)

    # Main configuration section
    gr.HTML('<div class="section-header">⚙️ Test Configuration</div>')
    
    task = gr.Textbox(
        label="📝 Task Description",
        lines=5,
        value=EXAMPLE_USE_CASES[example_choices[0]]["task"],
        placeholder="Describe what you want the LLM to do...",
        info="Be specific and clear about the expected behavior"
    )
    
    with gr.Accordion("📝 Sample Input/Output Examples (Optional)", open=True):
        gr.Markdown("💡 **Tip:** Provide examples to guide the models. Use `---` to separate multiple examples.")
        
        with gr.Row():
            sample_input = gr.Textbox(
                label="📥 Sample Input(s)",
                lines=5,
                value=EXAMPLE_USE_CASES[example_choices[0]]["input"],
                placeholder="Example 1 input\n---\nExample 2 input\n---\nExample 3 input",
            )
            sample_output = gr.Textbox(
                label="📤 Expected Output(s)",
                lines=5,
                value=EXAMPLE_USE_CASES[example_choices[0]]["output"],
                placeholder="Example 1 output\n---\nExample 2 output",
            )
        
        include_output_in_prompt = gr.Checkbox(
            label="🎯 Few-Shot Mode: Include expected outputs in generation prompt",
            value=False,
            info="✅ ON: Models see examples (better format matching) | ❌ OFF: Zero-shot test (pure capability)"
        )
    
    with gr.Accordion("⭐ Evaluation Criteria", open=True):
        gr.Markdown("Define how to judge model outputs. One criterion per line or comma-separated.")
        criteria = gr.Textbox(
            label="Evaluation Criteria",
            lines=4,
            value=EXAMPLE_USE_CASES[example_choices[0]]["criteria"],
            placeholder="Accuracy\nCompleteness\nClarity\nCode Quality",
            info="Each criterion will be scored 1-10 by the evaluator model"
        )

    # Model selection and run section
    gr.HTML('<div class="section-header">🚀 Run Benchmark</div>')

    gr.Markdown("Select one or more models to benchmark. All are selected by default.")
    model_choices_state = gr.State(models.copy())
    with gr.Row():
        model_selector = gr.CheckboxGroup(
            choices=models,
            value=models,
            label="✅ Models to Benchmark",
            info="These are OpenRouter model IDs. Add more below if needed.",
            scale=4,
        )
        with gr.Column(scale=1):
            select_all_btn = gr.Button("✅ Select All", variant="secondary")
            unselect_all_btn = gr.Button("🚫 Unselect All", variant="secondary")

    with gr.Accordion("➕ Add OpenRouter Models", open=False):
        gr.Markdown("Enter one or more OpenRouter model IDs (comma or newline separated).")
        with gr.Row():
            add_model_input = gr.Textbox(
                label="OpenRouter Model IDs",
                placeholder="e.g., openai/gpt-4.1, mistralai/mistral-large-latest",
                lines=2,
                scale=3,
            )
            add_model_btn = gr.Button("➕ Add to List", variant="secondary", scale=1)
        add_model_status = gr.Markdown("", visible=True)

    run_all = gr.Button("🔥 Benchmark Selected Models", variant="primary", size="lg")

    # Status/Info row
    status_box = gr.Markdown("", visible=False)

    # Results section with tabs
    with gr.Group(visible=False) as all_results_group:
        gr.HTML('<div class="section-header">📊 Benchmark Results</div>')
        
        with gr.Tabs() as results_tabs:
            with gr.Tab("📈 Overview"):
                all_results_table = gr.Dataframe(
                    row_count=(1, "dynamic"),
                    label="Scores & Summary (click column headers to sort)",
                    wrap=True,
                )
                gr.Markdown("💡 **Tip:** Click column headers to sort by score. Higher overall score = better performance.")
            
            with gr.Tab("📝 Detailed Logs"):
                all_results_log = gr.Textbox(
                    label="Complete Model Outputs & Evaluations",
                    lines=20,
                    interactive=False,
                    placeholder="Run the benchmark to see full model responses and evaluation details...",
                )
                export_btn = gr.Button("💾 Export Results", variant="secondary", visible=False)

    # Helper function to clear all fields
    def clear_all_fields():
        return (
            "",  # task
            "",  # sample_input
            "",  # sample_output
            "Accuracy\nCompleteness\nClarity",  # criteria (default)
            False,  # include_output_in_prompt
            gr.update(choices=models, value=models),  # model selection
            "",  # add model input
            "",  # add model status
            models,  # model choices state
            gr.update(visible=False),  # hide results
        )
    
    def show_status_running(selected: list[str]):
        count = len(selected or [])
        msg = f"🔄 **Running...** Testing {count} model(s) in parallel. This may take 30-60 seconds."
        return (
            gr.update(visible=True),  # results group
            gr.update(value=[]),  # clear table
            "⏳ Generating responses and evaluations...\n\n(Detailed logs will appear here shortly)",  # log placeholder
            gr.update(value=msg, visible=True)  # status
        )
    
    def show_status_complete():
        return gr.update(value="✅ **Complete!** Review results below.", visible=True)

    # Wire up clear button
    clear_btn.click(
        clear_all_fields,
        inputs=[],
        outputs=[
            task,
            sample_input,
            sample_output,
            criteria,
            include_output_in_prompt,
            model_selector,
            add_model_input,
            add_model_status,
            model_choices_state,
            all_results_group,
        ],
    )

    add_model_btn.click(
        add_openrouter_models,
        inputs=[add_model_input, model_choices_state, model_selector],
        outputs=[model_selector, model_selector, add_model_status, model_choices_state],
    )

    select_all_btn.click(
        lambda choices: choices,
        inputs=[model_choices_state],
        outputs=[model_selector],
    )
    unselect_all_btn.click(
        lambda: [],
        inputs=[],
        outputs=[model_selector],
    )

    # Wire up run button with status updates
    run_all.click(
        show_status_running,
        inputs=[model_selector],
        outputs=[all_results_group, all_results_table, all_results_log, status_box],
    ).then(
        run_benchmark_all,
        inputs=[task, sample_input, sample_output, criteria, include_output_in_prompt, model_selector],
        outputs=[all_results_table, all_results_log],
    ).then(
        show_status_complete,
        inputs=[],
        outputs=[status_box]
    )

    # Wire up example selector to update all input fields
    example_selector.change(
        load_example,
        inputs=[example_selector],
        outputs=[task, sample_input, sample_output, criteria],
    )

ui.launch(inbrowser=True, theme=APP_THEME, css=APP_CSS)