"""
Evaluating the Fine-Tuned Freight Rate Model

This script:
- Logs in to Hugging Face
- Loads the freight rates test dataset
- Loads the base Llama 3.2-3B model with quantization
- Loads the fine-tuned adapter weights with PEFT
- Evaluates the fine-tuned model using the freight evaluator

This will show the improvement from fine-tuning compared to the base model
and frontier models evaluated in exercise_2.

Based on exercise_4_evaluating_finetuned_model.py from the pricer project.
"""

import os
import torch
from dotenv import load_dotenv
from huggingface_hub import login
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, set_seed
from datasets import load_dataset
from peft import PeftModel
import sys
from pathlib import Path

# Add the current directory to Python path
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from evaluator import evaluate


# ============================================================================
# CONFIGURATION - UPDATE THESE VALUES
# ============================================================================

BASE_MODEL = "meta-llama/Llama-3.2-3B"
PROJECT_NAME = "freight_rates"  # Project name for your fine-tuning runs
HF_USER = "Anthonygdg123"  # Your Hugging Face username

LITE_MODE = True  # Must match what you used for training

DATA_USER = "Anthonygdg123"  # Your HF username for dataset
DATASET_NAME = f"{DATA_USER}/freight_rates_lite" if LITE_MODE else f"{DATA_USER}/freight_rates_full"

# ⚠️ IMPORTANT: Update these after fine-tuning in Colab!
# Choose the best run (with the lowest eval/loss metric in wandb)
RUN_NAME = "2026-01-28_10.25.50-lite"  # UPDATE THIS! e.g., "2026-01-28_15.30.45-lite"
REVISION = None  # Set to specific revision if needed (usually None for latest)

PROJECT_RUN_NAME = f"{PROJECT_NAME}-{RUN_NAME}"
HUB_MODEL_NAME = f"{HF_USER}/{PROJECT_RUN_NAME}"

# Quantization settings
QUANT_4_BIT = True
if torch.cuda.is_available():
    capability = torch.cuda.get_device_capability()
    use_bf16 = capability[0] >= 8
else:
    capability = None
    use_bf16 = False

EVAL_SIZE = 200  # Number of test examples to evaluate


def main():
    """Main function to evaluate the fine-tuned freight rate model."""
    
    print("=" * 60)
    print("Evaluating Fine-Tuned Freight Rate Model")
    print("=" * 60)
    print(f"Base Model: {BASE_MODEL}")
    print(f"Fine-tuned Model: {HUB_MODEL_NAME}")
    print(f"Dataset: {DATASET_NAME}")
    print(f"Mode: {'LITE' if LITE_MODE else 'FULL'}")
    print("=" * 60)
    
    # Check if model name has been updated
    if "XX.XX.XX" in RUN_NAME:
        print("\n❌ ERROR: You need to update the RUN_NAME!")
        print("After fine-tuning in Colab, update line ~28 with your actual run name.")
        print("Example: RUN_NAME = '2026-01-28_15.30.45-lite'")
        print("\nYou can find your run name:")
        print("1. Check your Weights & Biases dashboard")
        print("2. Check your Hugging Face profile for uploaded models")
        print("3. Look at the output from your Colab fine-tuning notebook")
        return
    
    # Step 1: Load environment and login to HuggingFace
    load_dotenv(override=True)
    hf_token = os.environ.get("HF_TOKEN")
    
    if not hf_token:
        raise ValueError(
            "HF_TOKEN not found, set the environment variable HF_TOKEN. "
            "You can get a token from: https://huggingface.co/settings/tokens"
        )
    
    login(hf_token, add_to_git_credential=True)
    print("✓ Logged in to Hugging Face")
    
    # Step 2: Load test dataset
    print(f"\nLoading test dataset: {DATASET_NAME}...")
    dataset = load_dataset(DATASET_NAME)
    test = dataset["test"]
    print(f"✓ Loaded {len(test):,} test examples")
    
    # Step 3: Determine device and quantization config
    device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"\nUsing device: {device}")
    
    if torch.cuda.is_available():
        if QUANT_4_BIT:
            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.bfloat16 if use_bf16 else torch.float16,
                bnb_4bit_quant_type="nf4",
            )
            print("Using 4-bit quantization")
        else:
            quant_config = BitsAndBytesConfig(
                load_in_8bit=True,
                bnb_8bit_compute_dtype=torch.bfloat16 if use_bf16 else torch.float16,
            )
            print("Using 8-bit quantization")
    else:
        quant_config = None
        print("No quantization (CUDA not available)")
    
    # Step 4: Load tokenizer
    print(f"\nLoading tokenizer for {BASE_MODEL}...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    print("✓ Tokenizer loaded")
    
    # Step 5: Load base model with quantization
    print(f"\nLoading base model {BASE_MODEL}...")
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
    print("✓ Base model loaded")
    
    # Step 6: Load fine-tuned adapter
    print(f"\nLoading fine-tuned adapter from {HUB_MODEL_NAME}...")
    try:
        if REVISION:
            fine_tuned_model = PeftModel.from_pretrained(base_model, HUB_MODEL_NAME, revision=REVISION)
        else:
            fine_tuned_model = PeftModel.from_pretrained(base_model, HUB_MODEL_NAME)
        print("✓ Fine-tuned adapter loaded successfully")
    except Exception as e:
        print(f"\n❌ ERROR: Could not load fine-tuned model from {HUB_MODEL_NAME}")
        print(f"Error: {e}")
        print("\nPossible issues:")
        print("1. The model hasn't been uploaded yet (check your Colab training output)")
        print("2. The RUN_NAME is incorrect")
        print("3. The model is private and you need to be logged in")
        print("4. The training didn't complete successfully")
        return
    
    # Print memory footprint
    memory_mb = fine_tuned_model.get_memory_footprint() / 1e6
    print(f"Memory footprint: {memory_mb:.1f} MB")
    
    # Step 7: Create prediction function
    def model_predict(item):
        """Predict freight rate using fine-tuned model."""
        inputs = tokenizer(item["prompt"], return_tensors="pt").to(device)
        with torch.no_grad():
            output_ids = fine_tuned_model.generate(**inputs, max_new_tokens=12)
        prompt_len = inputs["input_ids"].shape[1]
        generated_ids = output_ids[0, prompt_len:]
        return tokenizer.decode(generated_ids, skip_special_tokens=True)
    
    # Step 8: Test single prediction
    print("\n" + "=" * 60)
    print("Testing Single Prediction")
    print("=" * 60)
    example = test[0]
    print(f"\nPrompt:\n{example['prompt']}")
    print(f"\nActual: {example['completion']}")
    
    prediction = model_predict(example)
    print(f"Predicted: {prediction}")
    print("=" * 60)
    
    # Step 9: Run full evaluation
    print("\n" + "=" * 60)
    print(f"Evaluating Fine-Tuned Model on {EVAL_SIZE} Examples")
    print("=" * 60)
    print("This will show performance metrics and visualizations...")
    print()
    
    set_seed(42)
    evaluate(model_predict, test, size=EVAL_SIZE)
    
    print("\n" + "=" * 60)
    print("Evaluation Complete!")
    print("=" * 60)
    print("\n📊 Compare these results with exercise_2 (base model + frontier models)")
    print("\nExpected improvement:")
    print("✅ Fine-tuned model should have MUCH lower error")
    print("✅ Better R² score (closer to 100%)")
    print("✅ Better MAPE (lower percentage error)")
    print("✅ More points in green zone on the scatter plot")
    print("\nThis demonstrates that fine-tuning a smaller model on specific")
    print("domain data (freight rates) beats general-purpose frontier models!")


if __name__ == "__main__":
    main()
