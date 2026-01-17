import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

"""
This script serves as an automated documentation specialist using the OpenRouter API.
It reads a Python file, sends it to an LLM to add docstrings and comments, 
and overwrites the original file with the documented version.
"""

# Load environment variables from .env file
load_dotenv(override=True)

# Retrieve the OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Validate that the API key is present
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY is not set in the environment.")

# Initialize the OpenAI client configured for OpenRouter
OPENROUTER_CLIENT = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Define the target model and the system instructions
MODEL_ID = "google/gemini-3-flash-preview"

SYSTEM_PROMPT = """
You are a documentation specialist.
Add clear, concise docstrings and inline comments to the provided Python code.
Preserve behavior exactly. Do not refactor or change logic.
Return ONLY the updated Python code (no Markdown fences, no explanations).
"""


def build_messages(python_code: str) -> list[dict]:
    """
    Constructs the message payload for the OpenRouter chat completion.

    Args:
        python_code (str): The raw source code to be documented.

    Returns:
        list[dict]: A list of message dictionaries for the API request.
    """
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Please document this Python file. Add docstrings and inline comments where helpful, "
                "but keep the code unchanged otherwise.\n\n"
                "Python file:\n"
                f"{python_code}"
            ),
        },
    ]


def add_documentation(python_code: str) -> str:
    """
    Sends code to the LLM and processes the response to extract documented code.

    Args:
        python_code (str): The original source code.

    Returns:
        str: The source code updated with documentation, stripped of markdown formatting.
    """
    response = OPENROUTER_CLIENT.chat.completions.create(
        model=MODEL_ID,
        messages=build_messages(python_code),
    )
    # Extract response content and clean up potential markdown formatting
    content = response.choices[0].message.content or ""
    return content.replace("", "").replace("", "").strip()


def main() -> int:
    """
    Main execution logic: parses arguments, reads the file, calls the API, and saves changes.

    Returns:
        int: Exit status code (0 for success, 1 for failure).
    """
    # Check for correct command line arguments
    if len(sys.argv) != 2:
        print("Usage: uv run exercise_4_llm_documentation_specialist.py <python_file>")
        return 1

    # Resolve and validate the target file path
    target_path = Path(sys.argv[1]).expanduser().resolve()
    if not target_path.exists():
        print(f"File not found: {target_path}")
        return 1
    if target_path.suffix != ".py":
        print("Please provide a .py file.")
        return 1

    # Read the original file content
    original_code = target_path.read_text(encoding="utf-8")
    
    # Generate documented version via LLM API
    documented_code = add_documentation(original_code)
    
    # Ensure we don't wipe a file if the API returns an empty string
    if not documented_code.strip():
        print("Model returned empty output; file not modified.")
        return 1

    # Write the documented code back to the file
    target_path.write_text(documented_code + "\n", encoding="utf-8")
    print(f"Updated documentation in: {target_path}")
    return 0


if __name__ == "__main__":
    # Execute the script and return the exit code to the system
    raise SystemExit(main())
