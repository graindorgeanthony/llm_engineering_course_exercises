import os
import sys
from pathlib import Path
import subprocess
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file, allowing overrides
load_dotenv(override=True)

# Validate that the required API key is available
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY is not set in the environment.")

# Initialize the OpenAI client configured for OpenRouter
OPENROUTER_CLIENT = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# The specific LLM model ID to use for code generation
MODEL_ID = "openai/gpt-5.2-codex"

# System instructions to guide the LLM's behavior as a test specialist
SYSTEM_PROMPT = """
You are a unit test specialist.
Generate robust Python unit tests using the standard library unittest module only.
Do not modify the production code. Use clear, deterministic tests.
Return ONLY the Python test code (no Markdown fences, no explanations).
"""


def build_messages(python_code: str, module_name: str) -> list[dict]:
    """
    Constructs the message payload for the LLM chat completion API.

    Args:
        python_code: The source code of the module to be tested.
        module_name: The name of the module file (without extension).

    Returns:
        A list of message dictionaries (system and user roles).
    """
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Create unit tests for the following Python module using unittest.\n"
                "The tests will be saved to unittests/unittests_<module>.py next to the module.\n"
                "Import the module by name and ensure sys.path handles parent-folder imports.\n"
                f"Module name: {module_name}\n\n"
                "Python module code:\n"
                f"{python_code}"
            ),
        },
    ]


def generate_tests(python_code: str, module_name: str) -> str:
    """
    Sends the code to the LLM and returns the extracted unit test code.

    Args:
        python_code: Source code to analyze.
        module_name: Name of the module.

    Returns:
        The generated Python test code as a string, stripped of Markdown markers.
    """
    response = OPENROUTER_CLIENT.chat.completions.create(
        model=MODEL_ID,
        messages=build_messages(python_code, module_name),
    )
    content = response.choices[0].message.content or ""
    # Remove common Markdown formatting if the model included it despite instructions
    return content.replace("```python", "").replace("```", "").strip()


def run_tests(test_path: Path) -> subprocess.CompletedProcess:
    """
    Executes the generated unit tests using the current Python interpreter.

    Args:
        test_path: The Path object pointing to the generated test file.

    Returns:
        A CompletedProcess object containing the result of the test execution.
    """
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            str(test_path.parent),
            "-p",
            test_path.name,
        ],
        text=True,
        capture_output=True,
    )


def main() -> int:
    """
    Orchestrates the test generation process: parses CLI args, interacts with AI,
    writes the file, and runs the tests.

    Returns:
        The exit code (0 for success, non-zero for errors).
    """
    # Verify command line arguments
    if len(sys.argv) != 2:
        print("Usage: uv run exercise_5_llm_unit_tester_specialist.py <python_file>")
        return 1

    # Resolve and validate the target file path
    target_path = Path(sys.argv[1]).expanduser().resolve()
    if not target_path.exists():
        print(f"File not found: {target_path}")
        return 1
    if target_path.suffix != ".py":
        print("Please provide a .py file.")
        return 1

    # Prepare the 'unittests' subfolder relative to the target file
    module_name = target_path.stem
    tests_dir = target_path.parent / "unittests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    test_path = tests_dir / f"unittests_{module_name}.py"

    # Read original code and request tests from the LLM
    original_code = target_path.read_text(encoding="utf-8")
    test_code = generate_tests(original_code, module_name)
    if not test_code.strip():
        print("Model returned empty output; tests not written.")
        return 1

    # Save the generated test code to disk
    test_path.write_text(test_code + "\n", encoding="utf-8")
    print(f"Wrote tests to: {test_path}")

    # Immediately run the generated tests and report output
    result = run_tests(test_path)
    output = (result.stdout or "") + (result.stderr or "")
    print(output.strip())
    
    # Propagate the exit status of the test runner
    return result.returncode


if __name__ == "__main__":
    # Ensure the script exits with the appropriate return code
    raise SystemExit(main())
