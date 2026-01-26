"""
Exercise 6: LLM Evaluation with OpenRouter

This script evaluates various frontier LLMs (Large Language Models) for price prediction
using the OpenRouter API. It tests how well different models can estimate product prices
based on their descriptions, without any training - just using their world knowledge.

Models tested include GPT, Claude, Gemini, Grok, and others.
"""

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from openai import OpenAI

# Import Item and evaluator if available
try:
    from pricer.items import Item
    from pricer.evaluator import evaluate
except ImportError:
    # Fallback for different import paths
    try:
        from items import Item
        from evaluator import evaluate
    except ImportError:
        print("Warning: Could not import Item or evaluate. Some functionality may be limited.")
        Item = None
        evaluate = None


# Load API key & config
load_dotenv(override=True)
api_key = os.getenv('OPENROUTER_API_KEY')

if not api_key:
    print("Warning: OPENROUTER_API_KEY not found in environment variables.")
    print("Please set it in your .env file or environment.")
    client = None
else:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def load_data(lite_mode=False, username="ed-donner"):
    """
    Load the dataset from HuggingFace Hub.
    
    Args:
        lite_mode: If True, use the lite dataset, otherwise use full dataset
        username: HuggingFace username for the dataset
        
    Returns:
        Tuple of (train, val, test) lists of Item objects
    """
    dataset = f"{username}/items_lite" if lite_mode else f"{username}/items_full"
    
    if Item is None:
        raise ImportError("Item class not available. Cannot load data.")
    
    train, val, test = Item.from_hub(dataset)
    
    print(f"Loaded {len(train):,} training items, {len(val):,} validation items, {len(test):,} test items")
    
    return train, val, test


def messages_for(item):
    """
    Create messages for LLM price estimation.
    
    Args:
        item: Item object with summary text
        
    Returns:
        List of message dictionaries for the LLM
    """
    message = f"Estimate the price of this product. Respond with the price, no explanation\n\n{item.summary}"
    return [{"role": "user", "content": message}]


def extract_price_from_response(response_text):
    """
    Extract price from LLM response text.
    Handles various formats like "$123.45", "123.45", "$123", etc.
    
    Args:
        response_text: The text response from the LLM
        
    Returns:
        Float price value, or 0.0 if no price found
    """
    if not response_text:
        return 0.0
    
    # Remove common prefixes/suffixes
    text = response_text.strip()
    
    # Try to find price patterns
    # Pattern 1: $123.45 or $123
    price_patterns = [
        r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $123.45 or $1,234.56
        r'\$?\s*(\d+\.?\d*)',  # $123 or 123.45
        r'(\d+\.\d{2})',  # 123.45
        r'(\d+)',  # 123
    ]
    
    for pattern in price_patterns:
        matches = re.findall(pattern, text)
        if matches:
            # Take the first match and clean it
            price_str = matches[0].replace(',', '')
            try:
                price = float(price_str)
                return max(0.0, price)  # Ensure non-negative
            except ValueError:
                continue
    
    # If no pattern matches, try to extract any number
    numbers = re.findall(r'\d+\.?\d*', text)
    if numbers:
        try:
            price = float(numbers[0])
            return max(0.0, price)
        except ValueError:
            pass
    
    return 0.0


def extract_response_text(completion):
    """
    Safely extract text content from an OpenRouter completion response.
    Returns an empty string if content is missing.
    """
    if completion is None:
        return ""
    choices = getattr(completion, "choices", None)
    if not choices:
        return ""
    first = choices[0]
    message = getattr(first, "message", None)
    if message is None:
        return ""
    content = getattr(message, "content", None)
    if content is None:
        return ""
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
            elif isinstance(part, str):
                parts.append(part)
        return "\n".join(parts).strip()
    if isinstance(content, str):
        return content.strip()
    return str(content).strip()


def create_llm_pricer(model_name, **kwargs):
    """
    Create a pricer function for a specific LLM model.
    
    Args:
        model_name: The model name for OpenRouter (e.g., "openai/gpt-4.1-nano")
        **kwargs: Additional parameters to pass to the API call
                 (e.g., reasoning_effort, seed, etc.)
        
    Returns:
        A pricer function that takes an Item and returns a predicted price
    """
    def llm_pricer(item):
        """
        Predict price using the specified LLM model.
        
        Args:
            item: Item object with summary text
            
        Returns:
            Predicted price (non-negative)
        """
        if client is None:
            raise ValueError("OpenRouter client not initialized. Check OPENROUTER_API_KEY.")
        
        # Create messages
        messages = messages_for(item)

        # Prepare API call parameters
        api_params = {
            "model": model_name,
            "messages": messages,
        }

        # Add any additional parameters
        api_params.update(kwargs)

        retries = 2
        for attempt in range(retries + 1):
            try:
                # Call the LLM
                completion = client.chat.completions.create(**api_params)

                # Extract response safely
                response_text = extract_response_text(completion)
                if not response_text:
                    raise ValueError("Empty response content from model")

                # Extract price from response
                price = extract_price_from_response(response_text)
                return price
            except Exception as e:
                if attempt < retries:
                    sleep_seconds = 0.5 * (2 ** attempt)
                    print(f"Error calling {model_name}: {e}. Retrying in {sleep_seconds:.1f}s...")
                    time.sleep(sleep_seconds)
                    continue
                print(f"Error calling {model_name}: {e}")
                return 0.0
    
    return llm_pricer


# Define pricer functions for different models

def gemini_2_5_flash(item):
    """Gemini 2.5 Flash pricer function."""
    pricer = create_llm_pricer("google/gemini-2.5-flash")
    return pricer(item)


def grok_4_1_fast(item):
    """Grok 4.1 Fast pricer function."""
    pricer = create_llm_pricer("x-ai/grok-4.1-fast", seed=42)
    return pricer(item)


def gpt_5_2(item):
    """GPT-5.2 pricer function."""
    pricer = create_llm_pricer("openai/gpt-5.2", reasoning_effort="low", seed=42)
    return pricer(item)


def evaluate_llm_model_parallel(pricer_func, test_items, model_name="LLM", size=200, workers=5):
    """
    Evaluate an LLM model with parallelized API calls.
    
    Args:
        pricer_func: The pricer function to evaluate
        test_items: List of Item objects for testing
        model_name: Name of the model (for display)
        size: Number of test items to evaluate
        workers: Number of parallel workers for API calls
    """
    print(f"\n{'='*50}")
    print(f"Evaluating {model_name} (parallelized with {workers} workers)")
    print(f"{'='*50}")
    
    # Limit to available test items
    test_subset = test_items[:size] if size else test_items
    
    # Parallelize LLM calls
    results = []
    errors = []
    
    def process_item(item):
        """Process a single item and return result."""
        try:
            price = pricer_func(item)
            return {
                'item': item,
                'predicted': price,
                'actual': item.price,
                'error': abs(price - item.price),
                'success': True
            }
        except Exception as e:
            return {
                'item': item,
                'predicted': 0.0,
                'actual': item.price,
                'error': item.price,  # Full error if prediction fails
                'success': False,
                'error_msg': str(e)
            }
    
    # Execute in parallel
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Submit all tasks
        future_to_item = {
            executor.submit(process_item, item): item
            for item in test_subset
        }
        
        # Process completed tasks
        completed = 0
        for future in as_completed(future_to_item):
            completed += 1
            try:
                result = future.result()
                results.append(result)
                if not result['success']:
                    errors.append(result)
            except Exception as e:
                item = future_to_item[future]
                errors.append({
                    'item': item,
                    'error_msg': str(e)
                })
            
            # Progress indicator
            if completed % 100 == 0 or completed == len(test_subset):
                print(f"  Processed {completed}/{len(test_subset)} items...", end='\r')
    
    print()  # New line after progress
    
    # Calculate metrics
    if results:
        successful = [r for r in results if r['success']]
        if successful:
            errors_list = [r['error'] for r in successful]
            mae = sum(errors_list) / len(errors_list)
            rmse = (sum(e**2 for e in errors_list) / len(errors_list)) ** 0.5
            
            print(f"  Successful predictions: {len(successful)}/{len(results)}")
            print(f"  Mean Absolute Error: ${mae:.2f}")
            print(f"  Root Mean Squared Error: ${rmse:.2f}")
            
            if errors:
                print(f"  Errors encountered: {len(errors)}")
        else:
            print("  No successful predictions!")
    else:
        print("  No results obtained!")
    
    return results


def evaluate_llm_model(pricer_func, test_items, model_name="LLM", size=200, workers=5):
    """
    Evaluate an LLM model using the custom evaluator (shows graphs).

    Args:
        pricer_func: The pricer function to evaluate
        test_items: List of Item objects for testing
        model_name: Name of the model (for display)
        size: Number of test items to evaluate
        workers: Number of parallel workers (passed to evaluator)
    """
    if evaluate is None:
        print(f"Custom evaluator not available. Skipping evaluation for {model_name}.")
        return

    print(f"\n{'='*50}")
    print(f"Evaluating {model_name}")
    print(f"{'='*50}")

    try:
        evaluate(pricer_func, test_items, size=size, workers=workers)
    except Exception as e:
        print(f"Error during evaluation: {e}")


def main(lite_mode=True, username="ed-donner", test_size=200, workers=5, max_model_workers=3):
    """
    Main function to evaluate multiple LLM models.
    
    Args:
        lite_mode: If True, use the lite dataset
        username: HuggingFace username for the dataset
        test_size: Number of test items to evaluate per model
        workers: Number of parallel workers for evaluation
    """
    if client is None:
        print("="*50)
        print("ERROR: OpenRouter client not initialized!")
        print("="*50)
        print("Please set OPENROUTER_API_KEY in your .env file or environment.")
        print("="*50)
        return
    
    print("="*50)
    print("LLM Evaluation with OpenRouter")
    print("="*50)
    print("Testing frontier models for price prediction")
    print("These models use their world knowledge without training.")
    print("="*50)
    
    # Load data
    print("\n1. Loading data...")
    train, val, test = load_data(lite_mode=lite_mode, username=username)
    
    # Define models to evaluate
    models_to_evaluate = [
        ("Gemini 2.5 Flash", gemini_2_5_flash),
        ("Grok 4.1 Fast", grok_4_1_fast),
        ("GPT-5.2", gpt_5_2),
    ]
    
    print(f"\n2. Evaluating {len(models_to_evaluate)} models...")
    print(f"Test size: {test_size} items per model")
    print(f"Workers per model: {workers}")
    print(f"Parallel models: Yes (max {max_model_workers} concurrent)")
    print("\nNote: This may take a while and may incur API costs.")
    print("You can interrupt and resume evaluation at any time.\n")
    
    # Evaluate models concurrently; each model uses the custom evaluator (graphs)
    results = {}
    print("Evaluating models concurrently...\n")
    with ThreadPoolExecutor(max_workers=max_model_workers) as executor:
        future_to_model = {
            executor.submit(
                evaluate_llm_model,
                pricer_func,
                test,
                model_name,
                test_size,
                workers
            ): model_name
            for model_name, pricer_func in models_to_evaluate
        }
        
        for future in as_completed(future_to_model):
            model_name = future_to_model[future]
            try:
                future.result()
                results[model_name] = "Completed"
            except KeyboardInterrupt:
                print(f"\nEvaluation interrupted during {model_name}")
                results[model_name] = "Interrupted"
                for f in future_to_model:
                    f.cancel()
                break
            except Exception as e:
                print(f"\nError evaluating {model_name}: {e}")
                results[model_name] = f"Error: {str(e)}"
    
    # Summary
    print("\n" + "="*50)
    print("Evaluation Summary")
    print("="*50)
    for model_name, status in results.items():
        print(f"{model_name}: {status}")
    print("="*50)
    
    return results


if __name__ == "__main__":
    # Run with lite mode by default for faster execution and lower API costs
    # Set lite_mode=False to use the full dataset
    # Adjust test_size to control how many items to evaluate per model
    
    results = main(
        lite_mode=True,      # Use lite dataset
        username="ed-donner",
        test_size=200,       # Number of test items per model (reduce for faster testing)
        workers=5,           # Number of parallel workers per model
        max_model_workers=3  # Max number of models to evaluate at once
    )
    
    # To evaluate a single model, you can do:
    # train, val, test = load_data(lite_mode=True)
    # evaluate_llm_model_parallel(gpt_5_2, test, model_name="GPT-5.2", size=50, workers=5)
