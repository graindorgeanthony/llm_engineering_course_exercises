import os
import io
import sys
import time
import tempfile
import concurrent.futures
from dotenv import load_dotenv
from openai import OpenAI
from system_info import retrieve_system_info
import gradio as gr
import subprocess

load_dotenv(override=True)

# LLM API clients

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

OPENROUTER_CLIENT = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

OLLAMA_CLIENT = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)

models = [
    "openai/gpt-5.2", 
    "x-ai/grok-code-fast-1",
    "anthropic/claude-opus-4.5",
    "google/gemini-3-pro-preview",
    "google/gemini-3-flash-preview",
    "z-ai/glm-4.7",
    "deepseek/deepseek-v3.2",
    "moonshotai/kimi-k2-thinking",
    "mistralai/devstral-2512:free",
    "mistral-nemo"
]

clients = {
    "openai/gpt-5.2": OPENROUTER_CLIENT,
    "x-ai/grok-code-fast-1": OPENROUTER_CLIENT,
    "anthropic/claude-opus-4.5": OPENROUTER_CLIENT,
    "google/gemini-3-pro-preview": OPENROUTER_CLIENT,
    "google/gemini-3-flash-preview": OPENROUTER_CLIENT,
    "z-ai/glm-4.7": OPENROUTER_CLIENT,
    "deepseek/deepseek-v3.2": OPENROUTER_CLIENT,
    "moonshotai/kimi-k2-thinking": OPENROUTER_CLIENT,
    "mistralai/devstral-2512:free":OPENROUTER_CLIENT,
    "mistral-nemo": OLLAMA_CLIENT
}

# Compile and run commands for C++ code

compile_command = ["clang++", "-std=c++17", "-Ofast", "-mcpu=native", "-flto=thin", "-fvisibility=hidden", "-DNDEBUG", "main.cpp", "-o", "main"]
run_command = ["./main"]

system_info = retrieve_system_info()

# System prompt for the LLM

system_prompt = """
Your task is to convert Python code into high performance C++ code.
Respond only with C++ code. Do not provide any explanation other than occasional comments.
The C++ response needs to produce an identical output in the fastest possible time.
"""

# User prompt for the LLM

def user_prompt_for(python):
    return f"""
Port this Python code to C++ with the fastest possible implementation that produces identical output in the least time.
The system information is:
{system_info}
Your response will be written to a file called main.cpp and then compiled and executed; the compilation command is:
{compile_command}
Respond only with C++ code.
Python code to port:

```python
{python}
```
"""

# Messages function to create the messages for the LLM

def messages_for(python):
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_for(python)}
    ]

# Function to transform Python to C++

def port(model, python):
    client = clients[model]
    reasoning_effort = "high" if 'gpt' in model else None
    response = client.chat.completions.create(model=model, messages=messages_for(python), reasoning_effort=reasoning_effort)
    reply = response.choices[0].message.content
    reply = reply.replace('```cpp','').replace('```','')
    return reply

# Function to convert Python to C++ and run benchmark

def convert_and_benchmark(model, python):
    """Convert Python to C++ and run benchmark"""
    cpp_code = port(model, python)
    with tempfile.TemporaryDirectory() as work_dir:
        benchmark = compile_and_run(cpp_code, work_dir)
    return cpp_code, benchmark["output"]

# Python code to convert 

python_code_to_convert = """
import time

def calculate(iterations, param1, param2):
    result = 1.0
    for i in range(1, iterations+1):
        j = i * param1 - param2
        result -= (1/j)
        j = i * param1 + param2
        result += (1/j)
    return result

start_time = time.time()
result = calculate(200_000_000, 4, 1) * 4
end_time = time.time()

print(f"Result: {result:.12f}")
print(f"Execution Time: {(end_time - start_time):.6f} seconds")
"""

# Function to compile and run C++ code

def compile_and_run(cpp_code, work_dir):
    results = []
    timings = []
    try:
        main_cpp_path = os.path.join(work_dir, "main.cpp")
        with open(main_cpp_path, "w", encoding="utf-8") as f:
            f.write(cpp_code)

        # Compile
        compile_start = time.perf_counter()
        subprocess.run(compile_command, check=True, text=True, capture_output=True, cwd=work_dir)
        compile_time = time.perf_counter() - compile_start
        results.append(f"✅ Compilation successful! ({compile_time:.4f}s)\n")

        # Run 3 times for benchmarking
        for i in range(3):
            run_start = time.perf_counter()
            run_result = subprocess.run(run_command, check=True, text=True, capture_output=True, cwd=work_dir)
            run_time = time.perf_counter() - run_start
            timings.append(run_time)
            results.append(f"Run {i+1} ({run_time:.6f}s):\n{run_result.stdout}\n")

        avg_time = sum(timings) / len(timings) if timings else None
        return {
            "ok": True,
            "output": "\n".join(results),
            "avg_time": avg_time,
            "timings": timings,
        }
    except subprocess.CalledProcessError as e:
        error_msg = f"❌ An error occurred:\n{e.stderr if e.stderr else e.stdout}"
        return {"ok": False, "output": error_msg, "avg_time": None, "timings": []}
    except Exception as e:
        return {"ok": False, "output": f"❌ Unexpected error: {str(e)}", "avg_time": None, "timings": []}

# Function to convert Python to C++ across models in parallel and benchmark

def convert_and_benchmark_all(python):
    """Convert Python to C++ across models in parallel (non-ollama) and benchmark."""
    ollama_models = {model for model, client in clients.items() if client is OLLAMA_CLIENT}
    non_ollama_models = [model for model in models if model not in ollama_models]

    def run_one(model):
        try:
            cpp_code = port(model, python)
            with tempfile.TemporaryDirectory() as work_dir:
                benchmark = compile_and_run(cpp_code, work_dir)
            return model, benchmark
        except Exception as e:
            return model, {"ok": False, "output": f"❌ Unexpected error: {str(e)}", "avg_time": None, "timings": []}

    results = []

    # Parallel execution for non-ollama models
    max_workers = min(6, len(non_ollama_models)) if non_ollama_models else 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_model = {executor.submit(run_one, model): model for model in non_ollama_models}
        for future in concurrent.futures.as_completed(future_to_model):
            results.append(future.result())

    # Sequential execution for ollama models (RAM constraints)
    for model in models:
        if model in ollama_models:
            results.append(run_one(model))

    # Build results table sorted by avg runtime
    def sort_key(item):
        _, benchmark = item
        return benchmark["avg_time"] if benchmark["avg_time"] is not None else float("inf")

    results_sorted = sorted(results, key=sort_key)
    table_lines = [
        "| Model | Avg Runtime (s) | Runs | Status |",
        "| --- | --- | --- | --- |"
    ]
    for model, benchmark in results_sorted:
        if benchmark["ok"] and benchmark["avg_time"] is not None:
            avg_time = f"{benchmark['avg_time']:.6f}"
            runs = ", ".join(f"{t:.6f}" for t in benchmark["timings"])
            status = "✅ OK"
        else:
            avg_time = "—"
            runs = "—"
            status = "❌ Error"
        table_lines.append(f"| {model} | {avg_time} | {runs} | {status} |")

    log_lines = []
    for model, benchmark in results_sorted:
        log_lines.append(f"=== {model} ===\n{benchmark['output']}\n")

    return "\n".join(table_lines), "\n".join(log_lines)


def prepare_all_results_view():
    return (
        gr.update(visible=False),
        gr.update(visible=True),
        "**All Models Benchmark (Parallel)**\n\nRunning benchmarks...",
        "Running benchmarks across all models...\n\n(Logs will appear here.)",
    )

# Gradio UI

with gr.Blocks() as ui:
    gr.Markdown("# 🚀 Python to C++ Code Converter & Benchmark")
    gr.Markdown("Convert Python code to optimized C++ and benchmark the performance")
    
    with gr.Row():
        python = gr.Textbox(label="Python code:", lines=28, value=python_code_to_convert)
        cpp = gr.Textbox(label="C++ code:", lines=28)
    
    with gr.Row():
        model = gr.Dropdown(models, label="Select model", value=models[0])
        convert = gr.Button("Convert & Benchmark", variant="primary")
        convert_all = gr.Button("Convert & Benchmark All (Parallel)", variant="secondary")
    
    with gr.Group(visible=True) as single_results_group:
        results = gr.Textbox(
            label="Benchmark Results:",
            lines=15,
            interactive=False,
            placeholder="Click 'Convert & Benchmark' to see results here..."
        )

    with gr.Group(visible=False) as all_results_group:
        all_results_table = gr.Markdown("**All Models Benchmark (Parallel)**\n\nRun to see a timing table.")
        all_results_log = gr.Textbox(
            label="All Models Logs:",
            lines=15,
            interactive=False,
            placeholder="Click 'Convert & Benchmark All (Parallel)' to see logs here..."
        )
    
    convert.click(
        convert_and_benchmark,
        inputs=[model, python],
        outputs=[cpp, results]
    ).then(
        lambda: (gr.update(visible=True), gr.update(visible=False)),
        inputs=[],
        outputs=[single_results_group, all_results_group]
    )

    convert_all.click(
        prepare_all_results_view,
        inputs=[],
        outputs=[single_results_group, all_results_group, all_results_table, all_results_log],
    ).then(
        convert_and_benchmark_all,
        inputs=[python],
        outputs=[all_results_table, all_results_log],
    )

ui.launch(inbrowser=True)