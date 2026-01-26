"""
Exercise 7: LLM Fine-Tuning with OpenAI

This script fine-tunes a frontier LLM (GPT-4.1-nano) using OpenAI's fine-tuning API
for price prediction. It demonstrates the complete fine-tuning workflow:

1. Prepare training data in JSONL format
2. Upload files to OpenAI
3. Create a fine-tuning job
4. Monitor the job status
5. Test and evaluate the fine-tuned model

Note: Fine-tuning costs money. OpenAI recommends 50-100 examples for fine-tuning.
This script uses 100 training examples and 50 validation examples by default.
"""

import os
import json
import re
import time
from pathlib import Path
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


# Load environment variables
load_dotenv(override=True)

# Initialize OpenAI client
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("Warning: OPENAI_API_KEY not found in environment variables.")
    print("Please set it in your .env file or environment.")
    client = None
else:
    client = OpenAI(api_key=api_key)


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
    Create messages for fine-tuning data format.
    This includes both user message and assistant response.
    
    Args:
        item: Item object with summary text and price
        
    Returns:
        List of message dictionaries with user and assistant roles
    """
    message = f"Estimate the price of this product. Respond with the price, no explanation\n\n{item.summary}"
    return [
        {"role": "user", "content": message},
        {"role": "assistant", "content": f"${item.price:.2f}"}
    ]


def test_messages_for(item):
    """
    Create messages for testing/inference (no assistant response).
    
    Args:
        item: Item object with summary text
        
    Returns:
        List of message dictionaries with user role only
    """
    message = f"Estimate the price of this product. Respond with the price, no explanation\n\n{item.summary}"
    return [
        {"role": "user", "content": message},
    ]


def make_jsonl(items):
    """
    Convert items into JSONL (JSON Lines) format for fine-tuning.
    Each line is a JSON object with a "messages" key containing the conversation.
    
    Args:
        items: List of Item objects
        
    Returns:
        String containing JSONL formatted data
    """
    result = ""
    for item in items:
        messages = messages_for(item)
        messages_str = json.dumps(messages)
        result += '{"messages": ' + messages_str + '}\n'
    return result.strip()


def write_jsonl(items, filename):
    """
    Write items to a JSONL file.
    
    Args:
        items: List of Item objects
        filename: Path to the output JSONL file
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
    
    with open(filename, "w", encoding="utf-8") as f:
        jsonl = make_jsonl(items)
        f.write(jsonl)
    
    print(f"Written {len(items)} items to {filename}")


def upload_file_to_openai(filepath, purpose="fine-tune"):
    """
    Upload a file to OpenAI for fine-tuning.
    
    Args:
        filepath: Path to the file to upload
        purpose: Purpose of the file (default: "fine-tune")
        
    Returns:
        File object from OpenAI
    """
    if client is None:
        raise ValueError("OpenAI client not initialized. Check OPENAI_API_KEY.")
    
    print(f"Uploading {filepath} to OpenAI...")
    with open(filepath, "rb") as f:
        file = client.files.create(file=f, purpose=purpose)
    
    print(f"File uploaded successfully. File ID: {file.id}")
    return file


def create_fine_tuning_job(training_file_id, validation_file_id, 
                          base_model="gpt-4.1-nano-2025-04-14",
                          n_epochs=1, batch_size=1, seed=42, suffix="pricer"):
    """
    Create a fine-tuning job on OpenAI.
    
    Args:
        training_file_id: ID of the uploaded training file
        validation_file_id: ID of the uploaded validation file
        base_model: Base model to fine-tune (default: gpt-4.1-nano-2025-04-14)
        n_epochs: Number of training epochs
        batch_size: Batch size for training
        seed: Random seed for reproducibility
        suffix: Suffix for the fine-tuned model name
        
    Returns:
        Fine-tuning job object
    """
    if client is None:
        raise ValueError("OpenAI client not initialized. Check OPENAI_API_KEY.")
    
    print(f"\nCreating fine-tuning job...")
    print(f"Base model: {base_model}")
    print(f"Hyperparameters: n_epochs={n_epochs}, batch_size={batch_size}, seed={seed}")
    print(f"Model suffix: {suffix}")
    
    job = client.fine_tuning.jobs.create(
        training_file=training_file_id,
        validation_file=validation_file_id,
        model=base_model,
        seed=seed,
        hyperparameters={"n_epochs": n_epochs, "batch_size": batch_size},
        suffix=suffix
    )
    
    print(f"Fine-tuning job created successfully!")
    print(f"Job ID: {job.id}")
    print(f"Status: {job.status}")
    
    return job


def get_latest_fine_tuning_job():
    """
    Get the most recent fine-tuning job.
    
    Returns:
        Fine-tuning job object or None
    """
    if client is None:
        raise ValueError("OpenAI client not initialized. Check OPENAI_API_KEY.")
    
    jobs = client.fine_tuning.jobs.list(limit=1)
    if jobs.data:
        return jobs.data[0]
    return None


def retrieve_fine_tuning_job(job_id):
    """
    Retrieve a fine-tuning job by ID.
    
    Args:
        job_id: ID of the fine-tuning job
        
    Returns:
        Fine-tuning job object
    """
    if client is None:
        raise ValueError("OpenAI client not initialized. Check OPENAI_API_KEY.")
    
    return client.fine_tuning.jobs.retrieve(job_id)


def list_fine_tuning_events(job_id, limit=10):
    """
    List events for a fine-tuning job.
    
    Args:
        job_id: ID of the fine-tuning job
        limit: Maximum number of events to retrieve
        
    Returns:
        List of event objects
    """
    if client is None:
        raise ValueError("OpenAI client not initialized. Check OPENAI_API_KEY.")
    
    events = client.fine_tuning.jobs.list_events(fine_tuning_job_id=job_id, limit=limit)
    return events.data


def monitor_fine_tuning_job(job_id, check_interval=30, max_wait_time=3600):
    """
    Monitor a fine-tuning job until it completes or fails.
    
    Args:
        job_id: ID of the fine-tuning job
        check_interval: Seconds between status checks
        max_wait_time: Maximum time to wait in seconds
        
    Returns:
        Fine-tuning job object with final status
    """
    print(f"\nMonitoring fine-tuning job {job_id}...")
    print("This may take several minutes. You can check status at:")
    print("https://platform.openai.com/finetune")
    
    start_time = time.time()
    
    while True:
        job = retrieve_fine_tuning_job(job_id)
        status = job.status
        
        print(f"Status: {status}")
        
        if status == "succeeded":
            print(f"\nFine-tuning completed successfully!")
            print(f"Fine-tuned model: {job.fine_tuned_model}")
            return job
        elif status == "failed":
            print(f"\nFine-tuning failed!")
            if hasattr(job, 'error'):
                print(f"Error: {job.error}")
            return job
        elif status in ["cancelled", "validating_failed"]:
            print(f"\nFine-tuning {status}!")
            return job
        
        # Check if we've exceeded max wait time
        elapsed = time.time() - start_time
        if elapsed > max_wait_time:
            print(f"\nMaximum wait time ({max_wait_time}s) exceeded.")
            print("Job may still be running. Check status manually.")
            return job
        
        # Wait before next check
        time.sleep(check_interval)


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


def create_fine_tuned_pricer(fine_tuned_model_name, max_tokens=7):
    """
    Create a pricer function using a fine-tuned model.
    
    Args:
        fine_tuned_model_name: Name of the fine-tuned model
        max_tokens: Maximum tokens for the response
        
    Returns:
        A pricer function that takes an Item and returns a predicted price
    """
    if client is None:
        raise ValueError("OpenAI client not initialized. Check OPENAI_API_KEY.")
    
    def fine_tuned_pricer(item):
        """
        Predict price using the fine-tuned model.
        
        Args:
            item: Item object with summary text
            
        Returns:
            Predicted price (non-negative)
        """
        try:
            # Create messages for inference
            messages = test_messages_for(item)
            
            # Call the fine-tuned model
            response = client.chat.completions.create(
                model=fine_tuned_model_name,
                messages=messages,
                max_tokens=max_tokens
            )
            
            # Extract response text
            response_text = response.choices[0].message.content
            
            # Extract price from response
            price = extract_price_from_response(response_text)
            
            return price
            
        except Exception as e:
            print(f"Error calling fine-tuned model: {e}")
            return 0.0
    
    return fine_tuned_pricer


def main(lite_mode=False, username="ed-donner", 
         train_size=100, val_size=50,
         base_model="gpt-4.1-nano-2025-04-14",
         n_epochs=1, batch_size=1, seed=42, suffix="pricer",
         jsonl_dir="jsonl",
         monitor_job=True, test_model=True):
    """
    Main function to run the complete fine-tuning pipeline.
    
    Args:
        lite_mode: If True, use the lite dataset
        username: HuggingFace username for the dataset
        train_size: Number of training examples (OpenAI recommends 50-100)
        val_size: Number of validation examples
        base_model: Base model to fine-tune
        n_epochs: Number of training epochs
        batch_size: Batch size for training
        seed: Random seed for reproducibility
        suffix: Suffix for the fine-tuned model name
        jsonl_dir: Directory to store JSONL files
        monitor_job: If True, monitor the job until completion
        test_model: If True, test and evaluate the fine-tuned model
        
    Returns:
        Dictionary with fine-tuning results
    """
    if client is None:
        print("="*50)
        print("ERROR: OpenAI client not initialized!")
        print("="*50)
        print("Please set OPENAI_API_KEY in your .env file or environment.")
        print("="*50)
        return None
    
    print("="*50)
    print("LLM Fine-Tuning with OpenAI")
    print("="*50)
    print("This script will fine-tune a model for price prediction.")
    print(f"Training examples: {train_size} (OpenAI recommends 50-100)")
    print(f"Validation examples: {val_size}")
    print("Note: Fine-tuning costs money. Check OpenAI pricing.")
    print("="*50)
    
    # Step 1: Load data
    print("\nStep 1: Loading data...")
    train, val, test = load_data(lite_mode=lite_mode, username=username)
    
    # Prepare fine-tuning datasets
    fine_tune_train = train[:train_size]
    fine_tune_validation = val[:val_size]
    
    print(f"\nUsing {len(fine_tune_train)} training examples and {len(fine_tune_validation)} validation examples")
    
    # Step 2: Prepare JSONL files
    print("\nStep 2: Preparing JSONL files...")
    os.makedirs(jsonl_dir, exist_ok=True)
    
    train_filepath = os.path.join(jsonl_dir, "fine_tune_train.jsonl")
    val_filepath = os.path.join(jsonl_dir, "fine_tune_validation.jsonl")
    
    write_jsonl(fine_tune_train, train_filepath)
    write_jsonl(fine_tune_validation, val_filepath)
    
    # Step 3: Upload files to OpenAI
    print("\nStep 3: Uploading files to OpenAI...")
    train_file = upload_file_to_openai(train_filepath)
    validation_file = upload_file_to_openai(val_filepath)
    
    # Step 4: Create fine-tuning job
    print("\nStep 4: Creating fine-tuning job...")
    job = create_fine_tuning_job(
        training_file_id=train_file.id,
        validation_file_id=validation_file.id,
        base_model=base_model,
        n_epochs=n_epochs,
        batch_size=batch_size,
        seed=seed,
        suffix=suffix
    )
    
    job_id = job.id
    
    # Step 5: Monitor job (optional)
    fine_tuned_model_name = None
    if monitor_job:
        print("\nStep 5: Monitoring fine-tuning job...")
        final_job = monitor_fine_tuning_job(job_id)
        
        if final_job.status == "succeeded":
            fine_tuned_model_name = final_job.fine_tuned_model
            print(f"\nFine-tuned model ready: {fine_tuned_model_name}")
        else:
            print(f"\nFine-tuning job ended with status: {final_job.status}")
            if test_model:
                print("Cannot test model - fine-tuning did not complete successfully.")
                return {"job_id": job_id, "status": final_job.status}
    else:
        print("\nStep 5: Skipping job monitoring.")
        print(f"Job ID: {job_id}")
        print("You can check status at: https://platform.openai.com/finetune")
        print("Use retrieve_fine_tuning_job(job_id) to get the model name when ready.")
        
        # Try to get the model name if job is already complete
        try:
            job_status = retrieve_fine_tuning_job(job_id)
            if job_status.status == "succeeded" and job_status.fine_tuned_model:
                fine_tuned_model_name = job_status.fine_tuned_model
                print(f"Fine-tuned model: {fine_tuned_model_name}")
        except:
            pass
    
    # Step 6: Test and evaluate model (optional)
    results = {
        "job_id": job_id,
        "fine_tuned_model": fine_tuned_model_name,
        "status": "pending" if not monitor_job else retrieve_fine_tuning_job(job_id).status
    }
    
    if test_model and fine_tuned_model_name:
        print("\nStep 6: Testing fine-tuned model...")
        
        # Create pricer function
        pricer = create_fine_tuned_pricer(fine_tuned_model_name)
        
        # Test on a single example
        print("\nTesting on a single example:")
        test_item = test[0]
        print(f"Item: {test_item.title[:50]}...")
        print(f"Actual price: ${test_item.price:.2f}")
        predicted = pricer(test_item)
        print(f"Predicted price: ${predicted:.2f}")
        
        # Evaluate on test set
        if evaluate is not None:
            print("\nEvaluating on test set...")
            evaluate(pricer, test)
        else:
            print("\nCustom evaluator not available. Skipping evaluation.")
        
        results["pricer"] = pricer
    
    print("\n" + "="*50)
    print("Fine-tuning pipeline complete!")
    print("="*50)
    
    return results


if __name__ == "__main__":
    # Configuration
    # OpenAI recommends 50-100 examples for fine-tuning
    # Using 100 training examples and 50 validation examples as in the notebook
    
    results = main(
        lite_mode=False,              # Use full dataset
        username="ed-donner",
        train_size=100,               # Number of training examples (OpenAI recommends 50-100)
        val_size=50,                  # Number of validation examples
        base_model="gpt-4.1-nano-2025-04-14",  # Base model to fine-tune
        n_epochs=1,                   # Number of epochs (1 is recommended for small datasets)
        batch_size=1,                 # Batch size
        seed=42,                      # Random seed
        suffix="pricer",              # Suffix for model name
        jsonl_dir="jsonl",           # Directory for JSONL files
        monitor_job=True,             # Monitor job until completion
        test_model=True               # Test and evaluate the model
    )
    
    # The results dictionary contains:
    # - 'job_id': The fine-tuning job ID
    # - 'fine_tuned_model': The name of the fine-tuned model (if successful)
    # - 'status': The job status
    # - 'pricer': The pricer function (if test_model=True and model is ready)
    
    # Example: To use the fine-tuned model later:
    # if results and results.get('fine_tuned_model'):
    #     pricer = create_fine_tuned_pricer(results['fine_tuned_model'])
    #     price = pricer(test_item)
