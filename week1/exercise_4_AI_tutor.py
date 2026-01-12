#!/usr/bin/env python3
"""
Exercise 4: Technical Question Answering Tool

This script demonstrates how to use both OpenAI API (via OpenRouter) and Ollama
to answer technical questions in a chat-based interface.

Usage:
    uv run exercise_4_AI_tutor.py                    # Uses Ollama (default)
    uv run exercise_4_AI_tutor.py --type=open        # Uses Ollama
    uv run exercise_4_AI_tutor.py --type=closed      # Uses OpenRouter

BEFORE running this script: 
- Set OPENROUTER_API_KEY in your .env file (for --type=closed)
- Install ollama & run `ollama serve` (for --type=open)
"""

import os
import sys
import argparse
import requests
from dotenv import load_dotenv
from openai import OpenAI

# constants
MODEL_GPT = 'openai/gpt-5-nano'
MODEL_LLAMA = 'llama3.2'

# set up environment
load_dotenv(override=True)
api_key = os.getenv('OPENROUTER_API_KEY')

# Create Ollama client
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

def create_openrouter_client():
    """Create and return an OpenAI client configured for OpenRouter"""
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in environment variables")
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

def get_response_ollama(client, messages, model=MODEL_LLAMA):
    """Get response from Ollama with streaming"""
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True
    )
    
    full_response = ""
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            print(content, end="", flush=True)
            full_response += content
    
    print()  # New line after streaming
    return full_response

def get_response_openrouter(client, messages, model=MODEL_GPT):
    """Get response from OpenRouter with streaming"""
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True
    )
    
    full_response = ""
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            print(content, end="", flush=True)
            full_response += content
    
    print()  # New line after streaming
    return full_response

def chat_loop(model_type):
    """Main chat loop"""
    # Initialize conversation history
    messages = [
        {
            "role": "system",
            "content": "You are a helpful technical assistant that explains code clearly and concisely."
        }
    ]
    
    # Set up client based on model type
    if model_type == "open":
        if not check_ollama_running():
            print("Error: Ollama is not running. Please start Ollama with 'ollama serve'", file=sys.stderr)
            sys.exit(1)
        client = create_ollama_client()
        model = MODEL_LLAMA
        model_name = f"Ollama ({model})"
    else:  # closed
        try:
            client = create_openrouter_client()
            model = MODEL_GPT
            model_name = f"OpenRouter ({model})"
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    print("=" * 80)
    print(f"Chat with {model_name}")
    print("Type 'quit', 'exit', or 'q' to end the conversation")
    print("=" * 80)
    print()
    
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break
            
            if not user_input:
                continue
            
            # Add user message to history
            messages.append({"role": "user", "content": user_input})
            
            # Get and display response
            print(f"\n{model_name}: ", end="", flush=True)
            
            if model_type == "open":
                response = get_response_ollama(client, messages, model)
            else:
                response = get_response_openrouter(client, messages, model)
            
            # Add assistant response to history
            messages.append({"role": "assistant", "content": response})
            
            print()  # Extra newline for readability
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}", file=sys.stderr)
            # Remove the last user message if there was an error
            if messages and messages[-1]["role"] == "user":
                messages.pop()

def main():
    """Main function to parse arguments and start chat"""
    parser = argparse.ArgumentParser(
        description="Chat-based technical question answering tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--type',
        choices=['open', 'closed'],
        default='open',
        help='Model type: "open" for Ollama (default), "closed" for OpenRouter'
    )
    
    args = parser.parse_args()
    chat_loop(args.type)

if __name__ == "__main__":
    main()
