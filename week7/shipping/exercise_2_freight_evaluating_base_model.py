"""
Evaluating the Base Model + Frontier Models for Freight Rate Prediction

This script:
1. Loads the base Llama 3.2-3B model via OpenRouter API
2. Loads frontier models (Gemini 2.5 Flash) via OpenRouter
3. Loads the test dataset from Hugging Face
4. Evaluates all models' performance on freight rate prediction
5. Compares base Llama vs frontier models

The evaluation compares predicted freight rates against actual rates and provides:
- Average error (MAE)
- Mean Squared Error (MSE)
- R² score
- Mean Absolute Percentage Error (MAPE)
- Visual charts showing prediction accuracy

Based on exercise_6_LLM_Evaluation.py approach using OpenRouter API.
"""

import os
from dotenv import load_dotenv
from huggingface_hub import login
from datasets import load_dataset
import sys
from pathlib import Path
from openai import OpenAI
import re

# Add the current directory to Python path to ensure imports work
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from evaluator import evaluate

# Configuration constants
BASE_MODEL = "meta-llama/llama-3.2-3b-instruct"  # Base model via OpenRouter
LITE_MODE = True  # Set to True for lite dataset, False for full dataset
DATA_USER = "Anthonygdg123"  # Hugging Face username for dataset
EVAL_SIZE = 200  # Number of test examples to evaluate (default: 200)

# OpenRouter configuration
EVALUATE_FRONTIER_MODELS = True  # Set to False to skip frontier model evaluation


def load_environment():
    """
    Load environment variables and authenticate with Hugging Face.
    
    Requires HF_TOKEN environment variable to be set for loading dataset.
    Requires OPENROUTER_API_KEY for model evaluation.
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
    
    # Check for OpenRouter API key (required for all model evaluations)
    openrouter_key = os.environ.get('OPENROUTER_API_KEY')
    if not openrouter_key:
        raise ValueError(
            "OPENROUTER_API_KEY not found. Please set it as an environment variable or in a .env file.\n"
            "You can get a key from: https://openrouter.ai/keys"
        )
    print("✓ OpenRouter API key found")
    
    return hf_token, openrouter_key


def load_dataset_from_hub(lite_mode: bool = True, username: str = "username"):
    """
    Load the freight rates dataset from Hugging Face Hub.
    
    Args:
        lite_mode: If True, loads freight_rates_lite, else loads freight_rates_full
        username: Hugging Face username for the dataset
        
    Returns:
        Tuple of (train, val, test) datasets
    """
    # Determine which dataset to load
    dataset_name = f"{username}/freight_rates_lite" if lite_mode else f"{username}/freight_rates_full"
    
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
        print(f"  Prompt: {test[0]['prompt'][:150]}...")
        print(f"  Completion: {test[0]['completion']}")
    
    return train, val, test


def extract_price_from_response(response_text: str) -> str:
    """
    Extract numeric price from LLM response.
    Handles various formats and extracts only the numeric value.
    
    Args:
        response_text: The text response from the LLM
        
    Returns:
        Formatted string with just the price (e.g., "1234.56")
    """
    if not response_text:
        return "0"
    
    text = response_text.strip()
    
    # Try to extract numeric price (handle commas, decimals, dollar signs)
    # Patterns to try in order of specificity
    price_patterns = [
        r'\$?\s*(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?)',  # $1,234.56 or 1,234.56 (with commas)
        r'\$?\s*(\d+\.\d{1,2})',  # 1234.56 (with decimals)
        r'\$?\s*(\d+)',  # 1234 (integers only)
    ]
    
    for pattern in price_patterns:
        matches = re.findall(pattern, text)
        if matches:
            # Take the first numeric match
            price_str = matches[0].replace(',', '')
            try:
                price = float(price_str)
                # Return just the number, formatted to 2 decimal places
                return f"{price:.2f}"
            except ValueError:
                continue
    
    # If no valid price found, return 0
    return "0"


def create_model_predictor(model_name: str, api_key: str, max_tokens: int = 30, debug: bool = False):
    """
    Create a prediction function for any model via OpenRouter API.
    
    Args:
        model_name: Model name on OpenRouter (e.g., "meta-llama/llama-3.2-3b-instruct")
        api_key: OpenRouter API key
        max_tokens: Maximum number of tokens to generate
        debug: If True, print raw responses for first few predictions
        
    Returns:
        Function that takes an item dict and returns a string prediction
    """
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    # Counter for debug output (only show first 5)
    call_count = [0]
    
    def model_predict(item):
        """Predict freight rate using the specified model."""
        try:
            # Create message for the LLM with explicit instructions
            prompt = item["prompt"]
            
            # Add clear instructions with few-shot examples and context
            system_message = """You are a freight rate estimation system. You will receive shipment details ending with "Freight rate:".

Context: Container freight rates (in USD) typically range from $500 to $50,000 depending on route, volume (TEU), commodity type, and other factors. 
- Short routes or small volumes: $500-$5,000
- Medium routes: $5,000-$15,000  
- Long international routes or large volumes: $15,000-$50,000

Your task is to estimate a reasonable freight rate in USD and respond with ONLY the numeric price (no currency symbol, no text).

Examples:
- For a 1 TEU shipment from Shanghai to Los Angeles, respond: "3500"
- For a 20 TEU shipment from Rotterdam to New York, respond: "28000"
- For a 5 TEU shipment within Europe, respond: "4200"

IMPORTANT: 
- You must provide a numeric estimate
- Output ONLY the number (e.g., "3500" not "$3500 USD" or "3500 USD")
- Do NOT provide explanations, disclaimers, or say you cannot estimate
- Just provide the number"""
            
            # Call the API with system message and few-shot examples
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3,  # Slightly higher for some creativity in estimation
            )
            
            # Extract and parse response
            if completion.choices and len(completion.choices) > 0:
                response = completion.choices[0].message.content
                
                # Debug output for first few calls
                if debug and call_count[0] < 5:
                    print(f"\n[Debug] Raw response #{call_count[0] + 1}: '{response}'")
                    call_count[0] += 1
                
                if response:
                    # Parse the response to extract numeric price
                    parsed = extract_price_from_response(response)
                    
                    if debug and call_count[0] <= 5:
                        print(f"[Debug] Parsed as: '{parsed}'")
                    
                    return parsed
            
            return "0"
            
        except Exception as e:
            print(f"Error calling {model_name}: {e}")
            return "0"
    
    return model_predict


def main():
    """
    Main function to orchestrate the base model and frontier model evaluation.
    """
    print("=" * 60)
    print("Evaluating Base Model + Frontier Models for Freight Rates")
    print("=" * 60)
    print(f"Base Model: {BASE_MODEL} (via OpenRouter API)")
    print(f"Dataset: {'freight_rates_lite' if LITE_MODE else 'freight_rates_full'}")
    print("=" * 60)
    
    # Step 1: Authenticate with Hugging Face and OpenRouter
    hf_token, openrouter_key = load_environment()
    
    # Step 2: Load dataset
    train, val, test = load_dataset_from_hub(lite_mode=LITE_MODE, username=DATA_USER)
    
    # Step 3: Evaluate Base Llama Model via OpenRouter
    print("\n" + "=" * 60)
    print("EVALUATING BASE LLAMA 3.2-3B MODEL (via OpenRouter)")
    print("=" * 60)
    
    base_predictor = create_model_predictor(BASE_MODEL, openrouter_key, max_tokens=30, debug=True)
    
    # Test single prediction
    print("\nTesting single prediction...")
    example = test[0]
    print(f"Prompt: {example['prompt'][:100]}...")
    prediction = base_predictor(example)
    print(f"Prediction: {prediction}")
    print(f"Actual: {example['completion']}")
    
    # Run full evaluation (debug output will show first 5 responses)
    print("\nRunning full evaluation (showing debug output for first 5 predictions)...")
    evaluate(base_predictor, test, size=EVAL_SIZE)
    
    # Step 4: Evaluate Frontier Models (if enabled)
    if EVALUATE_FRONTIER_MODELS:
        print("\n" + "=" * 60)
        print("EVALUATING FRONTIER MODELS")
        print("=" * 60)
        
        frontier_models = [
            ("google/gemini-2.5-flash", "Gemini 2.5 Flash")
        ]
        
        for model_id, model_display_name in frontier_models:
            print(f"\n{'='*60}")
            print(f"Evaluating: {model_display_name}")
            print(f"{'='*60}")
            
            try:
                frontier_predictor = create_model_predictor(model_id, openrouter_key, max_tokens=30, debug=False)
                
                # Test single prediction
                print("\nTesting single prediction...")
                prediction = frontier_predictor(test[0])
                print(f"Prediction: {prediction}")
                print(f"Actual: {test[0]['completion']}")
                
                # Run evaluation
                evaluate(frontier_predictor, test, size=EVAL_SIZE)
                
            except Exception as e:
                print(f"❌ Error evaluating {model_display_name}: {e}")
                print("Skipping this model...")
                continue
    
    print("\n" + "=" * 60)
    print("Evaluation Complete!")
    print("=" * 60)
    print("\nCompare the results above:")
    print("- Base Llama 3.2-3B (untrained on freight rates)")
    if EVALUATE_FRONTIER_MODELS:
        print("- Gemini 2.5 Flash (frontier model)")
    print("\nExpectation: All models will perform poorly because they don't")
    print("have specific knowledge of freight rates. After fine-tuning,")
    print("your Llama model should significantly outperform these baselines!")


if __name__ == "__main__":
    main()
