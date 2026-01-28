"""
Freight Rate Dataset Building + Upload to Hugging Face

This script:
1. Loads freight bookings from CSV file
2. Creates prompts and completions for supervised fine-tuning (SFT)
3. Splits data into train, validation, and test sets
4. Uploads the processed dataset to Hugging Face Hub (private)

The dataset format will have "prompt" and "completion" fields suitable for training
language models to predict freight rates.

Based on exercise_1_dataset_building.py from the pricer project.
"""

import os
from dotenv import load_dotenv
from huggingface_hub import login
from transformers import AutoTokenizer
from sklearn.model_selection import train_test_split
from tqdm import tqdm
import matplotlib.pyplot as plt
import sys
from pathlib import Path

# Add the current directory to Python path to ensure imports work
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from freight_booking import FreightBooking


# Configuration constants
LITE_MODE = False  # Set to True for lite dataset, False for full dataset
BASE_MODEL = "meta-llama/Llama-3.2-3B"  # Base model for tokenizer
CUTOFF = 110  # Maximum tokens in description (bookings with more will be truncated)
DATA_USER_UPLOAD = "Anthonygdg123"  # Your Hugging Face username

# CSV file path (relative to this script)
CSV_PATH = "shipping/pricing-extract.csv"  # Update this with your full dataset path

# Data filtering thresholds
MIN_PRICE = 100.0  # Minimum price in USD (filters out unrealistic low prices)
MAX_PRICE = None  # Maximum price (None = no limit, or set to e.g., 500000 to filter outliers)
MIN_TEU = 0.1  # Minimum TEU (filters out zero/invalid volumes)
MAX_TEU = None  # Maximum TEU (None = no limit, or set to e.g., 5000 to filter mega-shipments)


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


def load_bookings(csv_path: str, min_price: float = 100.0, max_price: float = None, 
                  min_teu: float = 0.1, max_teu: float = None):
    """
    Load and filter freight bookings from CSV file.
    
    Args:
        csv_path: Path to the CSV file containing freight booking data
        min_price: Minimum price threshold (default: $100 - filters out unrealistic low prices)
        max_price: Maximum price threshold (default: None - no upper limit)
        min_teu: Minimum TEU threshold (default: 0.1 - filters out zero/invalid volumes)
        max_teu: Maximum TEU threshold (default: None - no upper limit)
        
    Returns:
        List of FreightBooking objects
    """
    print(f"Loading bookings from: {csv_path}")
    
    # Load bookings from CSV
    all_bookings = FreightBooking.from_csv(csv_path)
    original_count = len(all_bookings)
    
    print(f"✓ Loaded {original_count:,} raw bookings")
    
    # Show raw statistics
    prices = [b.price for b in all_bookings]
    teus = [b.teu for b in all_bookings]
    
    print(f"\n📊 Raw Data Statistics:")
    print(f"  Price range: ${min(prices):.2f} - ${max(prices):,.2f}")
    print(f"  TEU range: {min(teus):.1f} - {max(teus):.1f}")
    print(f"  Mean price: ${sum(prices)/len(prices):,.2f}")
    print(f"  Median price: ${sorted(prices)[len(prices)//2]:,.2f}")
    
    # Apply filters
    print(f"\n🔧 Applying filters:")
    print(f"  Minimum price: ${min_price:,.2f}")
    print(f"  Minimum TEU: {min_teu:.1f}")
    if max_price:
        print(f"  Maximum price: ${max_price:,.2f}")
    if max_teu:
        print(f"  Maximum TEU: {max_teu:.1f}")
    
    bookings = []
    filtered_price = 0
    filtered_teu = 0
    
    for b in all_bookings:
        # Filter by price
        if b.price < min_price:
            filtered_price += 1
            continue
        if max_price and b.price > max_price:
            filtered_price += 1
            continue
        
        # Filter by TEU
        if b.teu < min_teu:
            filtered_teu += 1
            continue
        if max_teu and b.teu > max_teu:
            filtered_teu += 1
            continue
        
        bookings.append(b)
    
    # Show filtering results
    print(f"\n✅ Filtering Results:")
    print(f"  Kept: {len(bookings):,} bookings ({len(bookings)/original_count*100:.1f}%)")
    print(f"  Filtered by price: {filtered_price:,}")
    print(f"  Filtered by TEU: {filtered_teu:,}")
    print(f"  Total removed: {original_count - len(bookings):,}")
    
    # Show filtered statistics
    if bookings:
        prices = [b.price for b in bookings]
        teus = [b.teu for b in bookings]
        
        print(f"\n📊 Filtered Data Statistics:")
        print(f"  Price range: ${min(prices):.2f} - ${max(prices):,.2f}")
        print(f"  Mean price: ${sum(prices)/len(prices):,.2f}")
        print(f"  Median price: ${sorted(prices)[len(prices)//2]:,.2f}")
        print(f"  TEU range: {min(teus):.1f} - {max(teus):.1f}")
    
    return bookings


def split_data(bookings, train_ratio=0.8, val_ratio=0.1, test_ratio=0.1):
    """
    Split bookings into train, validation, and test sets.
    
    Args:
        bookings: List of FreightBooking objects
        train_ratio: Proportion for training set (default: 0.8)
        val_ratio: Proportion for validation set (default: 0.1)
        test_ratio: Proportion for test set (default: 0.1)
        
    Returns:
        Tuple of (train, val, test) lists
    """
    print("\nSplitting data into train/val/test sets...")
    
    # First split: separate out test set
    train_val, test = train_test_split(
        bookings,
        test_size=test_ratio,
        random_state=42
    )
    
    # Second split: separate train and validation
    val_size = val_ratio / (train_ratio + val_ratio)
    train, val = train_test_split(
        train_val,
        test_size=val_size,
        random_state=42
    )
    
    print(f"✓ Training set: {len(train):,} bookings ({train_ratio*100:.0f}%)")
    print(f"✓ Validation set: {len(val):,} bookings ({val_ratio*100:.0f}%)")
    print(f"✓ Test set: {len(test):,} bookings ({test_ratio*100:.0f}%)")
    
    return train, val, test


def analyze_token_distribution(bookings, tokenizer):
    """
    Analyze the distribution of tokens in booking descriptions.
    
    This helps determine an appropriate CUTOFF value for truncating long descriptions.
    
    Args:
        bookings: List of FreightBooking objects
        tokenizer: Tokenizer instance from transformers
        
    Returns:
        List of token counts for each booking's description
    """
    print("\nAnalyzing token distribution in descriptions...")
    
    # Create temporary prompts to count tokens
    for booking in tqdm(bookings[:100], desc="Sampling bookings"):  # Sample first 100
        booking.make_prompts(tokenizer, cutoff=1000, do_round=True)  # High cutoff to get full length
    
    # Count tokens in each booking's prompt
    token_counts = [booking.count_tokens(tokenizer) for booking in bookings[:100]]
    
    # Calculate statistics
    avg_tokens = sum(token_counts) / len(token_counts)
    max_tokens = max(token_counts)
    
    print(f"Average tokens per description: {avg_tokens:,.1f}")
    print(f"Maximum tokens: {max_tokens:,}")
    
    # Optional: Plot histogram of token distribution
    # Uncomment to visualize
    # plt.figure(figsize=(15, 6))
    # plt.title(f"Tokens in Description: Avg {avg_tokens:,.1f} and highest {max_tokens:,}\n")
    # plt.xlabel('Number of tokens in description')
    # plt.ylabel('Count')
    # plt.hist(token_counts, rwidth=0.7, color="skyblue", bins=range(0, 200, 10))
    # plt.show()
    
    return token_counts


def create_prompts_and_completions(train, val, test, tokenizer, cutoff: int = 110):
    """
    Create prompts and completions for all bookings.
    
    For training and validation sets, prices are rounded to nearest dollar.
    For test set, exact prices are kept for accurate evaluation.
    
    Args:
        train: List of training FreightBooking objects
        val: List of validation FreightBooking objects
        test: List of test FreightBooking objects
        tokenizer: Tokenizer instance for encoding/decoding
        cutoff: Maximum number of tokens to keep in description (longer ones are truncated)
    """
    print(f"\nCreating prompts and completions with CUTOFF={cutoff}...")
    
    # Count how many bookings will be truncated
    all_bookings = train + val + test
    
    # Create prompts for training set (round prices)
    print("Processing training set...")
    for booking in tqdm(train, desc="Train prompts"):
        booking.make_prompts(tokenizer, cutoff, do_round=True)
    
    # Create prompts for validation set (round prices)
    print("Processing validation set...")
    for booking in tqdm(val, desc="Val prompts"):
        booking.make_prompts(tokenizer, cutoff, do_round=True)
    
    # Create prompts for test set (keep exact prices for evaluation)
    print("Processing test set...")
    for booking in tqdm(test, desc="Test prompts"):
        booking.make_prompts(tokenizer, cutoff, do_round=False)
    
    print("✓ All prompts and completions created")
    
    # Show example
    if test:
        print("\nExample prompt and completion:")
        print("PROMPT:")
        print(test[0].prompt)
        print("\nCOMPLETION:")
        print(test[0].completion)


def analyze_prompt_tokens(bookings, tokenizer):
    """
    Analyze the distribution of tokens in final prompts (including completion).
    
    Args:
        bookings: List of FreightBooking objects with prompts already created
        tokenizer: Tokenizer instance
    """
    print("\nAnalyzing final prompt token distribution...")
    
    prompt_token_counts = [booking.count_prompt_tokens(tokenizer) 
                          for booking in tqdm(bookings[:100], desc="Counting prompt tokens")]
    
    avg_tokens = sum(prompt_token_counts) / len(prompt_token_counts)
    max_tokens = max(prompt_token_counts)
    
    print(f"Average tokens per prompt+completion: {avg_tokens:,.1f}")
    print(f"Maximum tokens: {max_tokens:,}")


def upload_to_huggingface(train, val, test, lite_mode: bool = False, username: str = "username"):
    """
    Upload the processed dataset to Hugging Face Hub (PRIVATE).
    
    The dataset will be uploaded with the name: {username}/freight_rates_lite or
    {username}/freight_rates_full depending on lite_mode.
    
    Args:
        train: List of training FreightBooking objects with prompts created
        val: List of validation FreightBooking objects with prompts created
        test: List of test FreightBooking objects with prompts created
        lite_mode: If True, uploads as freight_rates_lite, else freight_rates_full
        username: Hugging Face username for the dataset
    """
    # Determine dataset name
    dataset_name = f"{username}/freight_rates_lite" if lite_mode else f"{username}/freight_rates_full"
    
    print(f"\nUploading dataset to Hugging Face (PRIVATE): {dataset_name}")
    print(f"  Train: {len(train):,} bookings")
    print(f"  Validation: {len(val):,} bookings")
    print(f"  Test: {len(test):,} bookings")
    
    # Upload using the FreightBooking class method (private=True)
    FreightBooking.push_prompts_to_hub(dataset_name, train, val, test, private=True)
    
    print(f"✓ Successfully uploaded dataset to: https://huggingface.co/datasets/{dataset_name}")
    print(f"✓ Dataset is PRIVATE (only you can access it)")


def main():
    """
    Main function to orchestrate the dataset building and upload process.
    """
    print("=" * 60)
    print("Freight Rate Dataset Building + Upload to Hugging Face")
    print("=" * 60)
    
    # Step 1: Authenticate with Hugging Face
    load_environment()
    
    # Step 2: Load and filter bookings from CSV
    bookings = load_bookings(CSV_PATH, min_price=MIN_PRICE, max_price=MAX_PRICE,
                            min_teu=MIN_TEU, max_teu=MAX_TEU)
    
    # Step 3: Split into train/val/test
    train, val, test = split_data(bookings)
    
    # Step 4: Load tokenizer for the base model
    print(f"\nLoading tokenizer for {BASE_MODEL}...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    print("✓ Tokenizer loaded")
    
    # Step 5: Analyze token distribution (optional but recommended)
    analyze_token_distribution(bookings, tokenizer)
    
    # Step 6: Create prompts and completions
    create_prompts_and_completions(train, val, test, tokenizer, cutoff=CUTOFF)
    
    # Step 7: Analyze final prompt tokens (optional)
    analyze_prompt_tokens(train + val + test, tokenizer)
    
    # Step 8: Upload to Hugging Face (PRIVATE)
    upload_to_huggingface(train, val, test, lite_mode=LITE_MODE, username=DATA_USER_UPLOAD)
    
    print("\n" + "=" * 60)
    print("Dataset building and upload complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Update CSV_PATH with your full dataset (25K or 150K rows)")
    print("2. Run this script again with LITE_MODE=True for 25K dataset")
    print("3. Run exercise_2_evaluating_base_model_freight.py to test base model")
    print("4. Fine-tune using exercise_3 (Google Colab)")
    print("5. Evaluate fine-tuned model with exercise_4")


if __name__ == "__main__":
    main()
