from huggingface_hub import login
from transformers import AutoTokenizer, AutoModelForCausalLM, TextStreamer, BitsAndBytesConfig
import torch
from mlx_lm import load, generate


import os
from dotenv import load_dotenv

load_dotenv(override=True)

hf_token = os.getenv('HF_TOKEN')

login(hf_token, add_to_git_credential=True)

# Quantization
MODEL = "meta-llama/Llama-3.2-1B-Instruct"
device = "mps"

# Generate a response from the model.
def generate_response(messages, quantized=False, max_new_tokens=100):
    
    # If we are using quantized model and the device is Apple Silicon (a recent Macbook), use MLX.
    if quantized and device == "mps":
        # Use MLX for quantized model (Apple Silicon optimized)
        model, tokenizer = load(MODEL, tokenizer_config={"trust_remote_code": True}, model_config={"quantize": {"group_size": 64, "bits": 4}})
        
        # Try to use chat template if available, otherwise fall back to manual formatting (instruct models do support chat template)
        try:
            formatted_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            response = generate(model, tokenizer, prompt=formatted_text, max_tokens=max_new_tokens, verbose=False)
            return response
        except (ValueError, AttributeError):
            return "Error: Use Chat/Instruct models instead."

    # If we are using quantized model and the device is CUDA, use HuggingFace quantization.
    elif quantized and device == "cuda":
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4"
        )

        tokenizer = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True)
        tokenizer.pad_token = tokenizer.eos_token
        
        # Try to use chat template if available, otherwise fall back to manual formatting
        try:
            formatted_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            input_ids = tokenizer(formatted_text, return_tensors="pt").input_ids.to(device)
            # Create attention mask
            attention_mask = torch.ones_like(input_ids, dtype=torch.long, device=device)
            # Load the model with quantization
            model = AutoModelForCausalLM.from_pretrained(MODEL, device_map="auto", quantization_config=quant_config)
            # Generate a response from the model.
            outputs = model.generate(input_ids=input_ids, attention_mask=attention_mask, max_new_tokens=max_new_tokens)
            # Decode the output to text
            response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            return response
        except (ValueError, AttributeError):
            return "Error: Use Chat/Instruct models instead."
    
    # If we are using a non-quantized model, use standard transformers.
    else:
        # Use standard transformers for non-quantized model
        tokenizer = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True)
        tokenizer.pad_token = tokenizer.eos_token
        
        # Try to use chat template if available, otherwise fall back to manual formatting
        try:
            formatted_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            input_ids = tokenizer(formatted_text, return_tensors="pt").input_ids.to(device)
            # Create attention mask
            attention_mask = torch.ones_like(input_ids, dtype=torch.long, device=device)
            # Load the model without quantization
            model = AutoModelForCausalLM.from_pretrained(MODEL, device_map=device)
            # Generate a response from the model.
            outputs = model.generate(input_ids=input_ids, attention_mask=attention_mask, max_new_tokens=max_new_tokens)
            # Decode the output to text
            response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            return response
        except (ValueError, AttributeError):
            return "Error: Use Chat/Instruct models instead."

messages = [{"role": "user", "content": "Tell me a joke about data sciencists."}]
print(f"Original model: {generate_response(messages, quantized=False, max_new_tokens=100)}")
print(f"Quantized model: {generate_response(messages, quantized=True, max_new_tokens=100)}")