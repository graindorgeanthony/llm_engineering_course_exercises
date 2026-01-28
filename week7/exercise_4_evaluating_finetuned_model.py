"""
Evaluating the Fine-tuned Model (translated from NEW_Week_7_Day_5_Testing_our_Fine_tuned_model.ipynb)

This script:
- Logs in to Hugging Face
- Loads the prompts dataset (test split)
- Loads the base model with quantization
- Loads the fine-tuned adapter weights with PEFT
- Evaluates the fine-tuned model using util.evaluate()

Notes:
- This script assumes a CUDA GPU is available (the notebook uses .to("cuda")).
- Update HF_USER / RUN_NAME / REVISION to match your own fine-tuned run on Hugging Face.
"""

# imports (mirrors the notebook)

import os
import re
import math
from tqdm import tqdm

from huggingface_hub import login
import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, set_seed
from datasets import load_dataset, Dataset, DatasetDict
from datetime import datetime
from peft import PeftModel

from dotenv import load_dotenv

load_dotenv()
from util import evaluate


# Constants (mirrors the notebook)

BASE_MODEL = "meta-llama/Llama-3.2-3B"
PROJECT_NAME = "price"
HF_USER = "Anthonygdg123"

LITE_MODE = True

DATA_USER = "Anthonygdg123"
DATASET_NAME = f"{DATA_USER}/items_prompts_lite" if LITE_MODE else f"{DATA_USER}/items_prompts_full"

# Choose the best run (with the lowest eval/loss metric in wandb)
RUN_NAME = "2026-01-28_06.12.23-lite"
REVISION = None

PROJECT_RUN_NAME = f"{PROJECT_NAME}-{RUN_NAME}"
HUB_MODEL_NAME = f"{HF_USER}/{PROJECT_RUN_NAME}"


# Hyper-parameters - QLoRA (mirrors the notebook)

QUANT_4_BIT = True
if torch.cuda.is_available():
    capability = torch.cuda.get_device_capability()
    use_bf16 = capability[0] >= 8
else:
    capability = None
    use_bf16 = False


def main():
    # Log in to HuggingFace
    hf_token = os.environ.get("HF_TOKEN")

    if not hf_token:
        raise ValueError(
            "HF_TOKEN not found, set the environment variable HF_TOKEN. "
            "Locally, set the environment variable HF_TOKEN."
        )

    login(hf_token, add_to_git_credential=True)

    dataset = load_dataset(DATASET_NAME)
    test = dataset["test"]

    # pick the right quantization (only valid for CUDA)
    if torch.cuda.is_available():
        if QUANT_4_BIT:
            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.bfloat16 if use_bf16 else torch.float16,
                bnb_4bit_quant_type="nf4",
            )
        else:
            quant_config = BitsAndBytesConfig(
                load_in_8bit=True,
                bnb_8bit_compute_dtype=torch.bfloat16 if use_bf16 else torch.float16,
            )
    else:
        quant_config = None

    # Load the Tokenizer and the Model
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")

    if device == "cuda":
        base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL,
            quantization_config=quant_config,
            device_map="auto",
        )
    else:
        base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL,
            torch_dtype=torch.float16 if device == "mps" else torch.float32,
        ).to(device)
    base_model.generation_config.pad_token_id = tokenizer.pad_token_id

    # Load the fine-tuned model with PEFT
    if REVISION:
        fine_tuned_model = PeftModel.from_pretrained(base_model, HUB_MODEL_NAME, revision=REVISION)
    else:
        fine_tuned_model = PeftModel.from_pretrained(base_model, HUB_MODEL_NAME)

    print(f"Memory footprint: {fine_tuned_model.get_memory_footprint() / 1e6:.1f} MB")

    # Use the model in inference mode
    def model_predict(item):
        inputs = tokenizer(item["prompt"], return_tensors="pt").to(device)
        with torch.no_grad():
            output_ids = fine_tuned_model.generate(**inputs, max_new_tokens=8)
        prompt_len = inputs["input_ids"].shape[1]
        generated_ids = output_ids[0, prompt_len:]
        return tokenizer.decode(generated_ids)

    set_seed(42)
    evaluate(model_predict, test)


if __name__ == "__main__":
    main()
