"""
Evaluating the Base Model

This script:
1. Loads the base Llama 3.2-3B model with quantization (4-bit or 8-bit)
2. Loads the test dataset from Hugging Face
3. Evaluates the base model's performance on price prediction
4. Generates evaluation metrics and visualizations

The evaluation compares predicted prices against actual prices and provides:
- Average error
- Mean Squared Error (MSE)
- R² score
- Visual charts showing prediction accuracy
"""

import os
from dotenv import load_dotenv
from huggingface_hub import login
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from datasets import load_dataset
import sys
from pathlib import Path

# Add the current directory to Python path to ensure imports work
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from util import evaluate

# Import MLX for Mac (Apple Silicon) support
try:
    from mlx_lm import load, generate
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False

# Configuration constants
BASE_MODEL = "meta-llama/Llama-3.2-3B"  # Base model to evaluate
LITE_MODE = True  # Set to True for lite dataset, False for full dataset
QUANT_4_BIT = True  # Set to True for 4-bit quantization, False for 8-bit
DATA_USER = "Anthonygdg123"  # Hugging Face username for dataset
EVAL_SIZE = 200  # Number of test examples to evaluate (default: 200)

def get_device():
    """
    Detect the available device (CUDA, MPS for Apple Silicon, or CPU).
    
    Returns:
        String device name: "cuda", "mps", or "cpu"
    """
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_environment():
    """
    Load environment variables and authenticate with Hugging Face.
    
    Requires HF_TOKEN environment variable to be set.
    You can set this via:
    - .env file with load_dotenv()
    - Environment variable: export HF_TOKEN=your_token_here
    """
    # Load environment variables from .env file if it exists
    load_dotenv(override=True)
    
    # Get Hugging Face token from environment
    hf_token = os.environ.get('HF_TOKEN')
    if not hf_token:
        raise ValueError(
            "HF_TOKEN not found. Please set it as an environment variable or in a .env file.\n"
            "You can get a token from: https://huggingface.co/settings/tokens"
        )
    
    # Login to Hugging Face
    login(hf_token, add_to_git_credential=True)
    print("✓ Successfully logged in to Hugging Face")
    return hf_token


def load_dataset_from_hub(lite_mode: bool = True, username: str = "ed-donner"):
    """
    Load the prompts dataset from Hugging Face Hub.
    
    Args:
        lite_mode: If True, loads items_prompts_lite, else loads items_prompts_full
        username: Hugging Face username for the dataset
        
    Returns:
        Tuple of (train, val, test) datasets
    """
    # Determine which dataset to load
    dataset_name = f"{username}/items_prompts_lite" if lite_mode else f"{username}/items_prompts_full"
    
    print(f"Loading dataset: {dataset_name}")
    
    # Load dataset from Hugging Face Hub
    dataset = load_dataset(dataset_name)
    train = dataset['train']
    val = dataset['val']
    test = dataset['test']
    
    print(f"✓ Loaded {len(train):,} training examples")
    print(f"✓ Loaded {len(val):,} validation examples")
    print(f"✓ Loaded {len(test):,} test examples")
    
    # Show example from dataset
    if test:
        print("\nExample test item:")
        print(f"  Prompt: {test[0]['prompt'][:100]}...")
        print(f"  Completion: {test[0]['completion']}")
    
    return train, val, test


def create_quantization_config(use_4bit: bool = True, device: str = "cuda"):
    """
    Create quantization configuration for model loading.
    
    Quantization reduces memory usage:
    - 4-bit: Most memory efficient, uses NF4 quantization with double quantization
    - 8-bit: Less memory efficient but may have slightly better quality
    
    Args:
        use_4bit: If True, use 4-bit quantization, else use 8-bit
        device: Device type ("cuda", "mps", or "cpu")
        
    Returns:
        BitsAndBytesConfig object (only used for CUDA, not for MLX on Mac)
    """
    if device != "cuda":
        # BitsAndBytes quantization requires CUDA. On Mac, we use MLX instead.
        return None

    if use_4bit:
        print("Using 4-bit quantization (NF4 with double quantization)")
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,  # Double quantization for better compression
            bnb_4bit_compute_dtype=torch.bfloat16,  # Compute dtype for 4-bit base
            bnb_4bit_quant_type="nf4"  # Normal Float 4-bit quantization
        )
    else:
        print("Using 8-bit quantization")
        quant_config = BitsAndBytesConfig(
            load_in_8bit=True,
            bnb_8bit_compute_dtype=torch.bfloat16
        )
    
    return quant_config


def load_base_model(
    base_model_name: str,
    quant_config: BitsAndBytesConfig,
    device: str = "cuda",
    use_4bit: bool = True,
):
    """
    Load the base model with quantization.
    
    On Mac (MPS), uses MLX for faster performance with quantization.
    On CUDA, uses transformers with BitsAndBytesConfig.
    
    Args:
        base_model_name: Name of the model on Hugging Face Hub
        quant_config: Quantization configuration (only used for CUDA)
        device: Device type ("cuda", "mps", or "cpu")
        use_4bit: Whether to use 4-bit quantization
        
    Returns:
        Tuple of (tokenizer, model, device_string, use_mlx)
    """
    # Use MLX on Mac (Apple Silicon) for faster quantization
    if device == "mps" and MLX_AVAILABLE and use_4bit:
        print(f"\nLoading model {base_model_name} with MLX (4-bit quantization)...")
        print("Using MLX for optimized Apple Silicon performance")
        
        model, tokenizer = load(
            base_model_name,
            tokenizer_config={"trust_remote_code": True},
            model_config={"quantize": {"group_size": 64, "bits": 4}},
        )
        
        print("✓ Model loaded with MLX")
        return tokenizer, model, "mps", True

    print(f"\nLoading tokenizer for {base_model_name}...")
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
    
    # Set padding token (required for batch processing)
    # Use EOS token as pad token if pad token doesn't exist
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Set padding side to right (standard for causal LMs)
    tokenizer.padding_side = "right"
    
    print("✓ Tokenizer loaded")
    
    print(f"\nLoading model {base_model_name} with quantization...")
    print("This may take a few minutes...")
    
    # Determine device mapping
    if device == "cuda":
        device_map = "auto"
        actual_device = "cuda"
    elif device == "mps":
        device_map = "mps"
        actual_device = "mps"
    else:
        device_map = "cpu"
        actual_device = "cpu"

    # Load model (quantization only valid for CUDA)
    if device == "cuda" and quant_config is not None:
        model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            quantization_config=quant_config,
            device_map=device_map,
        )
    else:
        if quant_config is not None:
            print("⚠️  BitsAndBytes quantization requires CUDA; loading without quantization.")
        model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            device_map=device_map,
        )
    
    # Set pad token ID in generation config
    model.generation_config.pad_token_id = tokenizer.pad_token_id
    
    # Print memory footprint
    memory_gb = model.get_memory_footprint() / 1e9
    print(f"✓ Model loaded on {actual_device}")
    print(f"  Memory footprint: {memory_gb:.1f} GB")
    
    return tokenizer, model, actual_device, False


def create_prediction_function(
    tokenizer,
    model,
    device: str = "cuda",
    use_mlx: bool = False,
    max_new_tokens: int = 8,
):
    """
    Create a prediction function that takes a dataset item and returns a price prediction.
    
    The function:
    1. Tokenizes the prompt
    2. Generates text using the model (MLX on Mac, transformers on CUDA/CPU)
    3. Extracts only the newly generated tokens (completion)
    4. Returns the decoded completion
    
    Args:
        tokenizer: Tokenizer instance
        model: Loaded model instance (MLX or transformers)
        device: Device to use for inference ("cuda", "mps", or "cpu")
        use_mlx: Whether model is MLX (True) or transformers (False)
        max_new_tokens: Maximum number of new tokens to generate (default: 8 for price)
        
    Returns:
        Function that takes an item dict and returns a string prediction
    """
    def model_predict(item):
        """
        Predict price for a given item.
        
        Args:
            item: Dictionary with 'prompt' key containing the input text
            
        Returns:
            String containing the model's price prediction
        """
        if use_mlx:
            # Use MLX for generation (Mac/Apple Silicon)
            prompt = item["prompt"]
            response = generate(model, tokenizer, prompt=prompt, max_tokens=max_new_tokens, verbose=False)
            if response.startswith(prompt):
                return response[len(prompt):].strip()
            return response.strip()

        # Use transformers for generation (CUDA/MPS/CPU)
        inputs = tokenizer(item["prompt"], return_tensors="pt").to(device)
        
        # Generate prediction (disable gradient computation for inference)
        with torch.no_grad():
            output_ids = model.generate(**inputs, max_new_tokens=max_new_tokens)
        
        # Extract only the newly generated tokens (exclude the prompt)
        prompt_len = inputs["input_ids"].shape[1]
        generated_ids = output_ids[0, prompt_len:]
        
        # Decode the generated tokens to get the prediction string
        return tokenizer.decode(generated_ids)
    
    return model_predict


def test_single_prediction(model_predict, test_data):
    """
    Test the prediction function on a single example.
    
    Args:
        model_predict: Prediction function
        test_data: Test dataset
    """
    if len(test_data) == 0:
        print("No test data available for single prediction test")
        return
    
    print("\n" + "=" * 60)
    print("Testing single prediction")
    print("=" * 60)
    
    example = test_data[0]
    print("\nExample item:")
    print(f"Prompt:\n{example['prompt']}")
    print(f"\nActual completion: {example['completion']}")
    
    print("\nGenerating prediction...")
    prediction = model_predict(example)
    print(f"Model prediction: {prediction}")
    
    print("=" * 60)


def run_evaluation(model_predict, test_data, eval_size: int = 200):
    """
    Run full evaluation on the test dataset.
    
    This will:
    - Evaluate predictions on eval_size examples
    - Calculate average error, MSE, and R² score
    - Generate visualizations showing prediction accuracy
    
    Args:
        model_predict: Prediction function
        test_data: Test dataset
        eval_size: Number of examples to evaluate
    """
    print("\n" + "=" * 60)
    print("Running Full Evaluation")
    print("=" * 60)
    print(f"Evaluating on {eval_size} test examples...")
    print("This may take several minutes depending on your hardware...")
    print()
    
    # Run evaluation using the evaluate function from util.py
    # This will generate metrics and visualizations
    evaluate(model_predict, test_data, size=eval_size)
    
    print("\n" + "=" * 60)
    print("Evaluation complete!")
    print("=" * 60)


def main():
    """
    Main function to orchestrate the base model evaluation process.
    """
    device = get_device()

    print("=" * 60)
    print("Evaluating Base Model")
    print("=" * 60)
    print(f"Model: {BASE_MODEL}")
    print(f"Quantization: {'4-bit' if QUANT_4_BIT else '8-bit'}")
    print(f"Dataset: {'items_prompts_lite' if LITE_MODE else 'items_prompts_full'}")
    print(f"Device: {device}")
    if device == "mps" and QUANT_4_BIT:
        print("Using MLX for quantized evaluation on Apple Silicon")
    print("=" * 60)
    
    # Step 1: Authenticate with Hugging Face
    load_environment()
    
    # Step 2: Load dataset
    train, val, test = load_dataset_from_hub(lite_mode=LITE_MODE, username=DATA_USER)
    
    # Step 3: Create quantization configuration
    quant_config = create_quantization_config(use_4bit=QUANT_4_BIT, device=device)
    
    # Step 4: Load base model with quantization
    tokenizer, model, actual_device, use_mlx = load_base_model(
        BASE_MODEL,
        quant_config,
        device=device,
        use_4bit=QUANT_4_BIT,
    )
    
    # Step 5: Create prediction function
    model_predict = create_prediction_function(
        tokenizer,
        model,
        device=actual_device,
        use_mlx=use_mlx,
        max_new_tokens=8,
    )
    
    # Step 6: Test single prediction
    test_single_prediction(model_predict, test)
    
    # Step 7: Run full evaluation
    run_evaluation(model_predict, test, eval_size=EVAL_SIZE)
    
    print("\nNote: The base model performance serves as a baseline.")
    print("After fine-tuning, you can compare the fine-tuned model's performance")
    print("against these baseline metrics to measure improvement.")


if __name__ == "__main__":
    main()
