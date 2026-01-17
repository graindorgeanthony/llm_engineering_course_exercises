import json
import gradio as gr
from openai import OpenAI
from transformers import AutoTokenizer, AutoModelForCausalLM, TextStreamer
import torch
import os
from dotenv import load_dotenv

load_dotenv(override=True)

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
os.environ['CURL_CA_BUNDLE'] = ''

FRONTIER_CLIENT = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

OLLAMA_CLIENT = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)

# Cache for HuggingFace models
hf_model_cache = {}

def generate_synthetic_data(model, dataset_type, num_records, model_type="frontier"):
    """Generate synthetic data using specified model and parameters."""
    messages = [
        {"role": "system", "content": "You are a data generation expert. Create realistic, diverse synthetic data in JSON format."},
        {"role": "user", "content": f"Generate {num_records} synthetic {dataset_type} data in JSON format. Output only the JSON data, no other text or formatting, nor additional information. Start your response with a JSON object starting with '{{' and ending with '}}'."}
    ]

    if model_type == "frontier":
        client = FRONTIER_CLIENT
    elif model_type == "ollama":
        client = OLLAMA_CLIENT
    elif model_type == "huggingface":
        # Load model and tokenizer (with caching)
        if model not in hf_model_cache:
            tokenizer = AutoTokenizer.from_pretrained(model)
            hf_model = AutoModelForCausalLM.from_pretrained(model, device_map="mps")
            hf_model_cache[model] = (tokenizer, hf_model)
        else:
            tokenizer, hf_model = hf_model_cache[model]
    else:
        raise ValueError(f"Invalid model type: {model_type}")

    if model_type in ["frontier", "ollama"]:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    elif model_type == "huggingface":
        streamer = TextStreamer(tokenizer)
        
        inputs = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
            forced_bos_token_id=tokenizer.encode("{", add_special_tokens=False)[0]
        ).to(hf_model.device)
        
        outputs = hf_model.generate(**inputs, max_new_tokens=20000, streamer=streamer)
        result = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:]).replace("<|eot_id|>", "").replace("```json", "").replace("```", "")
        return json.loads(result)

def generate_data_gradio(model_type, model_name, dataset_type, num_records):
    """Wrapper function for Gradio interface."""
    try:
        result = generate_synthetic_data(
            model=model_name,
            dataset_type=dataset_type,
            num_records=int(num_records),
            model_type=model_type
        )
        # Format JSON for better readability
        formatted_json = json.dumps(result, indent=2)
        return formatted_json, "✅ Generation successful!"
    except Exception as e:
        return "", f"❌ Error: {str(e)}"

# Define example inputs
examples = [
    [
        "frontier",
        "meta-llama/llama-3.2-3b-instruct",
        "employees (employee_id, first_name, last_name, email, phone, department, salary, hire_date, address, city, state, country)",
        5
    ],
    [
        "ollama",
        "llama3.2",
        "customers (customer_id, name, email, phone, registration_date, loyalty_points)",
        3
    ],
    [
        "huggingface",
        "meta-llama/Llama-3.2-1B-Instruct",
        "products (product_id, name, description, price, category, stock_quantity)",
        4
    ],
]

# Create Gradio interface
with gr.Blocks(title="Synthetic Data Generator", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # 🎲 Synthetic Data Generator
        Generate realistic synthetic datasets using different AI models.
        Choose your model type, specify the data structure, and let AI create the data!
        """
    )
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### ⚙️ Configuration")
            
            model_type = gr.Dropdown(
                choices=["frontier", "ollama", "huggingface"],
                value="frontier",
                label="Model Type",
                info="Choose the backend for generation"
            )
            
            model_name = gr.Textbox(
                label="Model Name",
                value="meta-llama/llama-3.2-3b-instruct",
                placeholder="e.g., meta-llama/llama-3.2-3b-instruct",
                info="Specify the exact model to use"
            )
            
            dataset_type = gr.Textbox(
                label="Dataset Schema",
                value="employees (employee_id, first_name, last_name, email, department, salary)",
                placeholder="e.g., users (id, name, email, age)",
                lines=3,
                info="Describe the fields you want in your dataset"
            )
            
            num_records = gr.Slider(
                minimum=1,
                maximum=10000,
                value=5,
                step=1,
                label="Number of Records",
                info="How many records to generate"
            )
            
            generate_btn = gr.Button("🚀 Generate Data", variant="primary", size="lg")
            
            gr.Markdown("### 📚 Examples")
            gr.Examples(
                examples=examples,
                inputs=[model_type, model_name, dataset_type, num_records],
                label="Try these examples:"
            )
        
        with gr.Column(scale=2):
            gr.Markdown("### 📊 Generated Data")
            
            status_box = gr.Textbox(
                label="Status",
                value="Ready to generate",
                interactive=False
            )
            
            output_json = gr.Code(
                label="JSON Output",
                language="json",
                lines=20,
                value=""
            )
            
            gr.Markdown(
                """
                ### 💡 Tips
                - **Frontier**: Uses OpenRouter API (requires API key)
                - **Ollama**: Uses local Ollama models (requires Ollama running)
                - **HuggingFace**: Downloads and runs models locally (first run may be slow)
                - Describe your schema clearly for best results
                - Start with fewer records for testing
                """
            )
    
    # Connect the button to the function
    generate_btn.click(
        fn=generate_data_gradio,
        inputs=[model_type, model_name, dataset_type, num_records],
        outputs=[output_json, status_box]
    )

if __name__ == "__main__":
    demo.launch(share=False, server_name="127.0.0.1", server_port=7860, inbrowser=True)
