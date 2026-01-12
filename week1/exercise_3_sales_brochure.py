#!/usr/bin/env python3
"""
Exercise 3: Sales Brochure Generator

This script creates a sales brochure for a company by:
1. Fetching the company's website and relevant links
2. Using an LLM to select relevant links (About, Careers, etc.)
3. Fetching content from those relevant pages
4. Generating a comprehensive brochure using an LLM

Usage:
    uv run exercise_3_sales_brochure.py <company_name> <url> [language]
    Example: uv run exercise_3_sales_brochure.py HuggingFace https://huggingface.co
    Example: uv run exercise_3_sales_brochure.py HuggingFace https://huggingface.co french
    Example: uv run exercise_3_sales_brochure.py HuggingFace https://huggingface.co spanish
    
    Supported languages: english (default), french, spanish
"""

import sys
import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from scraper import fetch_website_links, fetch_website_contents


# Initialize environment and OpenRouter client
load_dotenv(override=True)
api_key = os.getenv('OPENROUTER_API_KEY')

if not api_key:
    print("Warning: OPENROUTER_API_KEY not found in environment", file=sys.stderr)

MODEL_JSON = 'google/gemini-2.5-flash'
MODEL_BROCHURE = 'google/gemini-2.5-pro'
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)


# System prompt for selecting relevant links
link_system_prompt = """
You are provided with a list of links found on a webpage.
You are able to decide which of the links would be most relevant to include in a brochure about the company,
such as links to an About page, or a Company page, or Careers/Jobs pages.
You should respond in JSON as in this example:

{
    "links": [
        {"type": "about page", "url": "https://full.url/goes/here/about"},
        {"type": "careers page", "url": "https://another.full.url/careers"}
    ]
}
"""


def get_links_user_prompt(url):
    """Create user prompt for link selection"""
    user_prompt = f"""
Here is the list of links on the website {url} -
Please decide which of these are relevant web links for a brochure about the company, 
respond with the full https URL in JSON format.
Do not include Terms of Service, Privacy, email links.

Links (some might be relative links):

"""
    links = fetch_website_links(url)
    user_prompt += "\n".join(links)
    return user_prompt


def select_relevant_links(url):
    """Use LLM to select relevant links from a website"""
    print(f"Selecting relevant links for {url} by calling {MODEL_JSON}", file=sys.stderr)
    response = client.chat.completions.create(
        model=MODEL_JSON,
        messages=[
            {"role": "system", "content": link_system_prompt},
            {"role": "user", "content": get_links_user_prompt(url)}
        ],
        response_format={"type": "json_object"}
    )
    result = response.choices[0].message.content
    links = json.loads(result)
    print(f"Found {len(links['links'])} relevant links", file=sys.stderr)
    return links


def fetch_page_and_all_relevant_links(url):
    """Fetch the main page content and all relevant linked pages"""
    contents = fetch_website_contents(url)
    relevant_links = select_relevant_links(url)
    result = f"## Landing Page:\n\n{contents}\n## Relevant Links:\n"
    for link in relevant_links['links']:
        result += f"\n\n### Link: {link['type']}\n"
        result += fetch_website_contents(link["url"])
    return result


def get_brochure_system_prompt(language="english"):
    """Generate system prompt for brochure generation with language support"""
    language_instruction = ""
    if language.lower() == "french":
        language_instruction = "\nIMPORTANT: Write the entire brochure in French. All content, headings, and text must be in French."
    elif language.lower() == "spanish":
        language_instruction = "\nIMPORTANT: Write the entire brochure in Spanish. All content, headings, and text must be in Spanish."
    else:
        language_instruction = "\nIMPORTANT: Write the entire brochure in English. All content, headings, and text must be in English."
    
    return f"""
You are an expert marketing writer who creates compelling, professional brochures for companies.

Your task is to analyze the contents of several relevant pages from a company website and create a 
comprehensive yet concise brochure that effectively communicates the company's value proposition 
to three key audiences: prospective customers, investors, and potential recruits.
{language_instruction}

Guidelines for the brochure:
- Write in a professional, engaging tone that balances enthusiasm with credibility
- Use clear, well-structured markdown formatting (headings, bullet points, emphasis)
- Do NOT wrap your response in code blocks - output pure markdown
- Organize content into logical sections with descriptive headings
- Highlight the company's unique value proposition and competitive advantages
- Include specific details about products/services, target customers, and market positioning
- Describe company culture, values, and mission if available
- Mention notable customers, partnerships, or achievements if present
- Include information about career opportunities, company growth, and team culture if available
- Use concrete examples and specifics rather than generic statements

Focus on making the brochure informative, persuasive, and appealing to all three target audiences.
"""


def get_brochure_user_prompt(company_name, url, language="english"):
    """Create user prompt for brochure generation"""
    language_note = ""
    if language.lower() == "french":
        language_note = " (in French)"
    elif language.lower() == "spanish":
        language_note = " (in Spanish)"
    
    user_prompt = f"""
You are looking at a company called: {company_name}
Here are the contents of its landing page and other relevant pages;
use this information to build a short brochure of the company{language_note} in markdown without code blocks.\n\n
"""
    user_prompt += fetch_page_and_all_relevant_links(url)
    user_prompt = user_prompt[:5_000]  # Truncate if more than 5,000 characters
    return user_prompt


def create_brochure(company_name, url, language="english"):
    """Create a brochure for a company using streaming"""
    print(f"Creating brochure for {company_name} in {language}...", file=sys.stderr)
    print("\n" + "="*80, file=sys.stderr)
    print("Brochure:", file=sys.stderr)
    print("="*80, file=sys.stderr)
    
    stream = client.chat.completions.create(
        model=MODEL_BROCHURE,
        messages=[
            {"role": "system", "content": get_brochure_system_prompt(language)},
            {"role": "user", "content": get_brochure_user_prompt(company_name, url, language)}
        ],
        stream=True
    )
    
    response = ""
    for chunk in stream:
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            response += content
            print(content, end='', flush=True)
    
    print("\n" + "="*80, file=sys.stderr)
    return response


def main():
    """Main function to run the script"""
    if len(sys.argv) < 3:
        print("Usage: uv run exercise_3_sales_brochure.py <company_name> <url> [language]", file=sys.stderr)
        print("Example: uv run exercise_3_sales_brochure.py HuggingFace https://huggingface.co", file=sys.stderr)
        print("Example: uv run exercise_3_sales_brochure.py HuggingFace https://huggingface.co french", file=sys.stderr)
        print("Example: uv run exercise_3_sales_brochure.py HuggingFace https://huggingface.co spanish", file=sys.stderr)
        print("\nSupported languages: english (default), french, spanish", file=sys.stderr)
        sys.exit(1)
    
    company_name = sys.argv[1]
    url = sys.argv[2]
    
    # Get language from command line, default to english
    language = sys.argv[3].lower() if len(sys.argv) > 3 else "english"
    
    # Validate language
    valid_languages = ["english", "french", "spanish"]
    if language not in valid_languages:
        print(f"Warning: '{language}' is not a supported language. Using 'english' (default).", file=sys.stderr)
        print(f"Supported languages: {', '.join(valid_languages)}", file=sys.stderr)
        language = "english"
    
    try:
        brochure = create_brochure(company_name, url, language)
        # Brochure is already printed during streaming, but we return it for completeness
    except Exception as e:
        print(f"\nError creating brochure: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
