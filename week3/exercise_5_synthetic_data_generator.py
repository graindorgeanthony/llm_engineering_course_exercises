import json
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

#HUGGINGFACE_CLIENT = pipeline("text-generation", model="meta-llama/Llama-3.2-3B-Instruct")


def generate_synthetic_data(model, dataset_type, num_records, model_type="frontier"):
    messages = [
        {"role": "system", "content": "You are a data generation expert. Create realistic, diverse synthetic data in JSON format."},
        {"role": "user", "content": f"Generate {num_records} synthetic {dataset_type} data in JSON format. Output only the JSON data, no other text or formatting, nor additional information. Start your response with a JSON object starting with '{' and ending with '}'."}
    ]

    if (model_type):
        if (model_type == "frontier"):
            client = FRONTIER_CLIENT
        elif (model_type == "ollama"):
            client = OLLAMA_CLIENT
        elif (model_type == "huggingface"):
            tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.2-1B-Instruct")
            model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-3.2-1B-Instruct", device_map="mps")
        else:
            raise ValueError(f"Invalid model type: {model_type}")

    if (model_type == "frontier" or model_type == "ollama"):
        response = client.chat.completions.create(
            model=model, 
            messages=messages,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    elif (model_type == "huggingface"):
        
        streamer = TextStreamer(tokenizer)

        inputs = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
            forced_bos_token_id=tokenizer.encode("{", add_special_tokens=False)[0]
        ).to(model.device)

        outputs = model.generate(**inputs, max_new_tokens=20000, streamer=streamer)
        return json.loads(tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:]).replace("<|eot_id|>", "").replace("```json", "").replace("```", ""))

print("response: ", generate_synthetic_data(
    "meta-llama/Llama-3.2-1B-Instruct",
    "employees (employee_id, first_name, last_name, email, phone, department, salary, hire_date, address, city, state, country)",
    2,
    "huggingface"
))