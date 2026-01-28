"""
Dataset Building + Upload on Hugging Face

This script:
1. Loads items from an existing Hugging Face dataset (items_lite or items_full)
2. Creates prompts and completions for supervised fine-tuning (SFT)
3. Splits data into train, validation, and test sets
4. Uploads the processed dataset to Hugging Face Hub

The dataset format will have "prompt" and "completion" fields suitable for training
language models to predict product prices.
"""

import os
from dotenv import load_dotenv
from huggingface_hub import login
from transformers import AutoTokenizer
from tqdm import tqdm
import matplotlib.pyplot as plt

# Import the Item class from the pricer module
# The script assumes it's run from the week7 directory where pricer/ is located
import sys
from pathlib import Path

# Add the current directory to Python path to ensure imports work
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from pricer.items import Item


# Configuration constants
LITE_MODE = True  # Set to True for lite dataset, False for full dataset
BASE_MODEL = "meta-llama/Llama-3.2-3B"  # Base model for tokenizer
CUTOFF = 110  # Maximum tokens in summary (items with more will be truncated)
DATA_USER_DOWNLOAD = "ed-donner"  # Hugging Face username for source dataset
DATA_USER_UPLOAD = "Anthonygdg123"  # Hugging Face username for uploaded dataset


def load_environment():
    """
    Load environment variables and authenticate with Hugging Face.
    
    Requires HF_TOKEN environment variable to be set.
    You can set this via:
    - .env file with load_dotenv()
    - Environment variable: export HF_TOKEN=your_token_here
    - Or pass directly in the script
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


def load_items(lite_mode: bool = False, username: str = "ed-donner"):
    """
    Load items from Hugging Face Hub.
    
    Args:
        lite_mode: If True, loads items_lite dataset, else loads items_full
        username: Hugging Face username for the dataset
        
    Returns:
        Tuple of (train_items, val_items, test_items, all_items)
    """
    # Determine which dataset to load
    dataset_name = f"{username}/items_lite" if lite_mode else f"{username}/items_full"
    
    print(f"Loading dataset: {dataset_name}")
    
    # Load items from Hugging Face Hub
    train, val, test = Item.from_hub(dataset_name)
    items = train + val + test
    
    print(f"✓ Loaded {len(train):,} training items")
    print(f"✓ Loaded {len(val):,} validation items")
    print(f"✓ Loaded {len(test):,} test items")
    print(f"✓ Total: {len(items):,} items")
    
    return train, val, test, items


def analyze_token_distribution(items, tokenizer):
    """
    Analyze the distribution of tokens in item summaries.
    
    This helps determine an appropriate CUTOFF value for truncating long summaries.
    
    Args:
        items: List of Item objects
        tokenizer: Tokenizer instance from transformers
        
    Returns:
        List of token counts for each item's summary
    """
    print("\nAnalyzing token distribution in summaries...")
    
    # Count tokens in each item's summary
    token_counts = [item.count_tokens(tokenizer) for item in tqdm(items, desc="Counting tokens")]
    
    # Calculate statistics
    avg_tokens = sum(token_counts) / len(token_counts)
    max_tokens = max(token_counts)
    
    print(f"Average tokens per summary: {avg_tokens:,.1f}")
    print(f"Maximum tokens: {max_tokens:,}")
    
    # Optional: Plot histogram of token distribution
    # Uncomment the following lines to visualize the distribution
    # plt.figure(figsize=(15, 6))
    # plt.title(f"Tokens in Summary: Avg {avg_tokens:,.1f} and highest {max_tokens:,}\n")
    # plt.xlabel('Number of tokens in summary')
    # plt.ylabel('Count')
    # plt.hist(token_counts, rwidth=0.7, color="skyblue", bins=range(0, 200, 10))
    # plt.show()
    
    return token_counts


def create_prompts_and_completions(train, val, test, tokenizer, cutoff: int = 110):
    """
    Create prompts and completions for all items.
    
    For training and validation sets, prices are rounded to nearest dollar.
    For test set, exact prices are kept for accurate evaluation.
    
    Args:
        train: List of training Item objects
        val: List of validation Item objects
        test: List of test Item objects
        tokenizer: Tokenizer instance for encoding/decoding
        cutoff: Maximum number of tokens to keep in summary (longer summaries are truncated)
    """
    print(f"\nCreating prompts and completions with CUTOFF={cutoff}...")
    
    # Count how many items will be truncated
    all_items = train + val + test
    token_counts = [item.count_tokens(tokenizer) for item in all_items]
    truncated_count = len([count for count in token_counts if count > cutoff])
    truncation_pct = (truncated_count / len(all_items)) * 100
    
    print(f"Items that will be truncated: {truncated_count:,} ({truncation_pct:.1f}%)")
    
    # Create prompts for training set (round prices)
    print("Processing training set...")
    for item in tqdm(train, desc="Train prompts"):
        item.make_prompts(tokenizer, cutoff, do_round=True)
    
    # Create prompts for validation set (round prices)
    print("Processing validation set...")
    for item in tqdm(val, desc="Val prompts"):
        item.make_prompts(tokenizer, cutoff, do_round=True)
    
    # Create prompts for test set (keep exact prices for evaluation)
    print("Processing test set...")
    for item in tqdm(test, desc="Test prompts"):
        item.make_prompts(tokenizer, cutoff, do_round=False)
    
    print("✓ All prompts and completions created")
    
    # Show example
    if test:
        print("\nExample prompt and completion:")
        print("PROMPT:")
        print(test[0].prompt)
        print("\nCOMPLETION:")
        print(test[0].completion)


def analyze_prompt_tokens(items, tokenizer):
    """
    Analyze the distribution of tokens in final prompts (including completion).
    
    Args:
        items: List of Item objects with prompts already created
        tokenizer: Tokenizer instance
    """
    print("\nAnalyzing final prompt token distribution...")
    
    prompt_token_counts = [item.count_prompt_tokens(tokenizer) for item in tqdm(items, desc="Counting prompt tokens")]
    
    avg_tokens = sum(prompt_token_counts) / len(prompt_token_counts)
    max_tokens = max(prompt_token_counts)
    
    print(f"Average tokens per prompt+completion: {avg_tokens:,.1f}")
    print(f"Maximum tokens: {max_tokens:,}")
    
    # Optional: Plot histogram
    # plt.figure(figsize=(15, 6))
    # plt.title(f"Tokens: Avg {avg_tokens:,.1f} and highest {max_tokens:,}\n")
    # plt.xlabel('Number of tokens in prompt and the completion')
    # plt.ylabel('Count')
    # plt.hist(prompt_token_counts, rwidth=0.7, color="gold", bins=range(0, 200, 10))
    # plt.show()


def upload_to_huggingface(train, val, test, lite_mode: bool = False, username: str = "ed-donner"):
    """
    Upload the processed dataset to Hugging Face Hub.
    
    The dataset will be uploaded with the name: {username}/items_prompts_lite or
    {username}/items_prompts_full depending on lite_mode.
    
    Args:
        train: List of training Item objects with prompts created
        val: List of validation Item objects with prompts created
        test: List of test Item objects with prompts created
        lite_mode: If True, uploads as items_prompts_lite, else items_prompts_full
        username: Hugging Face username for the dataset
    """
    # Determine dataset name
    dataset_name = f"{username}/items_prompts_lite" if lite_mode else f"{username}/items_prompts_full"
    
    print(f"\nUploading dataset to Hugging Face: {dataset_name}")
    print(f"  Train: {len(train):,} items")
    print(f"  Validation: {len(val):,} items")
    print(f"  Test: {len(test):,} items")
    
    # Upload using the Item class method
    # This creates a DatasetDict with "prompt" and "completion" fields
    Item.push_prompts_to_hub(dataset_name, train, val, test)
    
    print(f"✓ Successfully uploaded dataset to: https://huggingface.co/datasets/{dataset_name}")


def main():
    """
    Main function to orchestrate the dataset building and upload process.
    """
    print("=" * 60)
    print("Dataset Building + Upload on Hugging Face")
    print("=" * 60)
    
    # Step 1: Authenticate with Hugging Face
    load_environment()
    
    # Step 2: Load items from existing dataset
    train, val, test, items = load_items(lite_mode=LITE_MODE, username=DATA_USER_DOWNLOAD)
    
    # Step 3: Load tokenizer for the base model
    print(f"\nLoading tokenizer for {BASE_MODEL}...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    print("✓ Tokenizer loaded")
    
    # Step 4: Analyze token distribution (optional but recommended)
    token_counts = analyze_token_distribution(items, tokenizer)
    
    # Step 5: Create prompts and completions
    create_prompts_and_completions(train, val, test, tokenizer, cutoff=CUTOFF)
    
    # Step 6: Analyze final prompt tokens (optional)
    analyze_prompt_tokens(items, tokenizer)
    
    # Step 7: Upload to Hugging Face
    upload_to_huggingface(train, val, test, lite_mode=LITE_MODE, username=DATA_USER_UPLOAD)
    
    print("\n" + "=" * 60)
    print("Dataset building and upload complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
