#!/usr/bin/env python3
"""
Exercise 2: LLM Call with Ollama

This script demonstrates how to use the OpenAI package with a local Ollama instance
to summarize websites.

BEFORE running this script: Install ollama & run `ollama serve`
"""

import sys
import requests
from openai import OpenAI
from scraper import fetch_website_contents


# Configuration
OLLAMA_BASE_URL = "http://localhost:11434/v1"


def check_ollama_running():
    """Check if Ollama is running on localhost:11434"""
    try:
        response = requests.get("http://localhost:11434", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def create_ollama_client():
    """Create and return an OpenAI client configured for Ollama"""
    return OpenAI(base_url=OLLAMA_BASE_URL, api_key='ollama')


# Define our system prompt
SYSTEM_PROMPT = """
You are a snarky assistant that analyzes the contents of a website,
and provides a short, snarky, humorous summary, ignoring text that might be navigation related.
Respond in markdown. Do not wrap the markdown in a code block - respond just with the markdown.
"""

# Define our user prompt prefix
USER_PROMPT_PREFIX = """
Here are the contents of a website.
Provide a short summary of this website.
If it includes news or announcements, then summarize these too.

"""


def messages_for(website):
    """Create message list for the LLM API call"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT_PREFIX + website}
    ]


def summarize(url, model="gemma3:4b", client=None):
    """
    Summarize a website using Ollama.
    
    Args:
        url: The URL of the website to summarize
        model: The Ollama model to use (default: "gemma3:4b")
        client: Optional OpenAI client (will create one if not provided)
    
    Returns:
        The summary text from the LLM
    """
    if client is None:
        client = create_ollama_client()
    
    website = fetch_website_contents(url)
    response = client.chat.completions.create(
        model=model,
        messages=messages_for(website)
    )
    return response.choices[0].message.content


def main():
    """Main function to run the script"""
    # Check if Ollama is running
    if not check_ollama_running():
        print("Error: Ollama is not running. Please start Ollama with 'ollama serve'", file=sys.stderr)
        sys.exit(1)
    
    # Get URL from command line arguments
    if len(sys.argv) < 2:
        print("Usage: uv run exercise_2_llm_call_ollama.py <url>", file=sys.stderr)
        print("Example: uv run exercise_2_llm_call_ollama.py https://cnn.com", file=sys.stderr)
        sys.exit(1)
    
    url = sys.argv[1]
    
    # Create Ollama client
    try:
        client = create_ollama_client()
    except Exception as e:
        print(f"Error creating Ollama client: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Summarize the website
    try:
        print(f"Summarizing {url}...", file=sys.stderr)
        summary = summarize(url, client=client)
        print("\n" + "="*80)
        print(summary)
        print("="*80)
    except Exception as e:
        print(f"Error summarizing website: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
