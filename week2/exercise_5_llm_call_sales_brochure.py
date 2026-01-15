import os
import sys
import json
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr
from scraper import fetch_website_links, fetch_website_contents

# Load API key & config
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


# Streaming function
def create_brochure_streaming(company_name, url, language="english"):
    """Create a brochure for a company using streaming"""
    try:
        stream = client.chat.completions.create(
            model=MODEL_BROCHURE,
            messages=[
                {"role": "system", "content": get_brochure_system_prompt(language)},
                {"role": "user", "content": get_brochure_user_prompt(company_name, url, language)}
            ],
            stream=True
        )
        
        result = ""
        for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                result += content
                yield result
    except Exception as e:
        yield f"Error creating brochure: {str(e)}"


# Gradio interface inputs & outputs
company_input = gr.Textbox(
    label="Company Name:",
    info="Enter the name of the company",
    placeholder="e.g., HuggingFace"
)
url_input = gr.Textbox(
    label="Company URL:",
    info="Enter the company's website URL",
    placeholder="e.g., https://huggingface.co"
)
language_selector = gr.Dropdown(
    choices=["english", "french", "spanish"],
    value="english",
    label="Language:",
    info="Select the language for the brochure"
)
brochure_output = gr.Markdown(
    label="Generated Brochure:",
    value="Enter company name and URL, then click 'Generate Brochure' to start."
)

# Gradio interface
gr.Interface(
    fn=create_brochure_streaming,
    title="Sales Brochure Generator",
    description="Generate professional sales brochures for companies by analyzing their website content. The brochure will be tailored for prospective customers, investors, and potential recruits.",
    inputs=[company_input, url_input, language_selector],
    outputs=[brochure_output],
    examples=[
        ["HuggingFace", "https://huggingface.co", "english"],
        ["HuggingFace", "https://huggingface.co", "french"],
        ["HuggingFace", "https://huggingface.co", "spanish"],
    ],
    flagging_mode="never"
).launch(
    inbrowser=True
)