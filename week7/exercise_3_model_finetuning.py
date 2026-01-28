"""
Fine-Tuning a Model + Upload on Hugging Face

This script:
1. Loads the base Llama 3.2-3B model with QLoRA (Quantized LoRA)
2. Loads the training dataset from Hugging Face
3. Configures LoRA parameters for efficient fine-tuning
4. Trains the model using Supervised Fine-Tuning (SFT)
5. Uploads the fine-tuned model to Hugging Face Hub

QLoRA combines quantization (4-bit) with LoRA adapters, allowing efficient
fine-tuning of large models on consumer hardware.
"""

import os
from dotenv import load_dotenv
from huggingface_hub import login
import torch
import transformers
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    set_seed
)
from datasets import load_dataset
from peft import LoraConfig
from trl import SFTTrainer, SFTConfig
from datetime import datetime
import sys
from pathlib import Path

# Optional: Weights & Biases for experiment tracking
try:
    import wandb
    WANDB_AVAILABLE = True
except ImportError:
    WANDB_AVAILABLE = False
    print("Warning: wandb not available. Set LOG_TO_WANDB=False or install with: pip install wandb")

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

# Model Configuration
BASE_MODEL = "meta-llama/Llama-3.2-3B"  # Base model to fine-tune
PROJECT_NAME = "price"  # Project name for organizing runs
HF_USER = "Anthonygdg123"  # Your Hugging Face username

# Dataset Configuration
LITE_MODE = True  # True: use lite dataset (faster, less data), False: use full dataset
DATA_USER = "Anthonygdg123"  # Hugging Face username for dataset

# Run Configuration
RUN_NAME = f"{datetime.now():%Y-%m-%d_%H.%M.%S}"  # Unique run identifier with timestamp
if LITE_MODE:
    RUN_NAME += "-lite"  # Append "-lite" suffix for lite mode runs
PROJECT_RUN_NAME = f"{PROJECT_NAME}-{RUN_NAME}"  # Full project run name
HUB_MODEL_NAME = f"{HF_USER}/{PROJECT_RUN_NAME}"  # Hugging Face Hub model identifier

# ============================================================================
# HYPERPARAMETERS - Overall Training
# ============================================================================

EPOCHS = 1 if LITE_MODE else 3  # Number of complete passes through the training dataset
BATCH_SIZE = 32 if LITE_MODE else 256  # Number of examples processed per batch (larger = faster but more memory)
MAX_SEQUENCE_LENGTH = 128  # Maximum number of tokens in input sequences (truncates longer sequences)
GRADIENT_ACCUMULATION_STEPS = 1  # Number of batches to accumulate before updating weights (simulates larger batch size)

# ============================================================================
# HYPERPARAMETERS - QLoRA (Quantized LoRA)
# ============================================================================

QUANT_4_BIT = True  # Use 4-bit quantization (True) or 8-bit (False) - 4-bit saves more memory
LORA_R = 32 if LITE_MODE else 256  # Rank of LoRA matrices (higher = more parameters, more capacity but slower)
LORA_ALPHA = LORA_R * 2  # LoRA alpha scaling factor (controls adapter strength, typically 2x rank)
ATTENTION_LAYERS = ["q_proj", "v_proj", "k_proj", "o_proj"]  # Attention layers to apply LoRA adapters
MLP_LAYERS = ["gate_proj", "up_proj", "down_proj"]  # MLP layers to apply LoRA adapters
TARGET_MODULES = ATTENTION_LAYERS if LITE_MODE else ATTENTION_LAYERS + MLP_LAYERS  # Which layers get LoRA adapters
LORA_DROPOUT = 0.1  # Dropout rate for LoRA adapters (prevents overfitting, 0.1 = 10% dropout)

# ============================================================================
# HYPERPARAMETERS - Training
# ============================================================================

LEARNING_RATE = 1e-4  # Step size for weight updates (0.0001, higher = faster learning but less stable)
WARMUP_RATIO = 0.01  # Fraction of training steps for learning rate warmup (gradual increase from 0)
LR_SCHEDULER_TYPE = 'cosine'  # Learning rate schedule (cosine = smooth decrease, linear = constant decrease)
WEIGHT_DECAY = 0.001  # L2 regularization strength (penalizes large weights to prevent overfitting)
OPTIMIZER = "paged_adamw_32bit"  # Optimizer algorithm (paged_adamw_32bit = memory-efficient AdamW)

# ============================================================================
# HYPERPARAMETERS - Tracking & Logging
# ============================================================================

VAL_SIZE = 500 if LITE_MODE else 1000  # Number of validation examples to use for evaluation
LOG_STEPS = 5 if LITE_MODE else 10  # Frequency of logging metrics (every N steps)
SAVE_STEPS = 100 if LITE_MODE else 200  # Frequency of saving checkpoints (every N steps)
LOG_TO_WANDB = True  # Enable Weights & Biases logging for experiment tracking


def load_environment():
    """
    Load environment variables and authenticate with Hugging Face and W&B.
    
    Requires HF_TOKEN environment variable to be set.
    Optionally requires WANDB_API_KEY if LOG_TO_WANDB is True.
    """
    # Load environment variables from .env file if it exists
    load_dotenv(override=True)
    
    # Authenticate with Hugging Face
    hf_token = os.environ.get('HF_TOKEN')
    if not hf_token:
        raise ValueError(
            "HF_TOKEN not found. Please set it as an environment variable or in a .env file.\n"
            "You can get a token from: https://huggingface.co/settings/tokens"
        )
    
    login(hf_token, add_to_git_credential=True)
    print("✓ Successfully logged in to Hugging Face")
    
    # Authenticate with Weights & Biases if enabled
    if LOG_TO_WANDB:
        if not WANDB_AVAILABLE:
            print("Warning: wandb not available. Disabling W&B logging.")
            return hf_token
        
        wandb_api_key = os.environ.get('WANDB_API_KEY')
        if wandb_api_key:
            os.environ["WANDB_API_KEY"] = wandb_api_key
            wandb.login()
            os.environ["WANDB_PROJECT"] = PROJECT_NAME
            os.environ["WANDB_LOG_MODEL"] = "false"  # Don't log full model to W&B (too large)
            os.environ["WANDB_WATCH"] = "false"  # Don't watch gradients (reduces overhead)
            print("✓ Successfully logged in to Weights & Biases")
        else:
            print("Warning: WANDB_API_KEY not found. Disabling W&B logging.")
    
    return hf_token


def load_dataset_from_hub(lite_mode: bool = True, username: str = "ed-donner", val_size: int = 500):
    """
    Load the prompts dataset from Hugging Face Hub.
    
    Args:
        lite_mode: If True, loads items_prompts_lite, else loads items_prompts_full
        username: Hugging Face username for the dataset
        val_size: Number of validation examples to use
        
    Returns:
        Tuple of (train, val, test) datasets
    """
    # Determine which dataset to load
    dataset_name = f"{username}/items_prompts_lite" if lite_mode else f"{username}/items_prompts_full"
    
    print(f"Loading dataset: {dataset_name}")
    
    # Load dataset from Hugging Face Hub
    dataset = load_dataset(dataset_name)
    train = dataset['train']
    val = dataset['val'].select(range(val_size))  # Select subset for faster evaluation
    test = dataset['test']
    
    print(f"✓ Loaded {len(train):,} training examples")
    print(f"✓ Loaded {len(val):,} validation examples")
    print(f"✓ Loaded {len(test):,} test examples")
    
    return train, val, test


def detect_compute_dtype():
    """
    Detect the best compute dtype based on GPU capabilities.
    
    bfloat16 is preferred for A100/H100 GPUs (compute capability >= 8.0)
    float16 is used for older GPUs (T4, V100, etc.)
    
    Returns:
        Tuple of (use_bf16 boolean, compute_dtype)
    """
    if torch.cuda.is_available():
        capability = torch.cuda.get_device_capability()
        use_bf16 = capability[0] >= 8  # A100/H100 and newer
        compute_dtype = torch.bfloat16 if use_bf16 else torch.float16
        print(f"GPU capability: {capability}, using {'bfloat16' if use_bf16 else 'float16'}")
    else:
        use_bf16 = False
        compute_dtype = torch.float16
        print("CUDA not available, using float16")
    
    return use_bf16, compute_dtype


def create_quantization_config(use_4bit: bool = True, compute_dtype=torch.bfloat16):
    """
    Create quantization configuration for QLoRA.
    
    QLoRA uses 4-bit quantization to reduce memory usage while maintaining
    model quality through careful quantization techniques.
    
    Args:
        use_4bit: If True, use 4-bit quantization, else use 8-bit
        compute_dtype: Data type for computations (bfloat16 or float16)
        
    Returns:
        BitsAndBytesConfig object
    """
    if use_4bit:
        print("Using 4-bit quantization (NF4 with double quantization)")
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,  # Enable 4-bit quantization
            bnb_4bit_use_double_quant=True,  # Double quantization for better compression
            bnb_4bit_compute_dtype=compute_dtype,  # Compute dtype for 4-bit base
            bnb_4bit_quant_type="nf4"  # Normal Float 4-bit quantization (better than standard 4-bit)
        )
    else:
        print("Using 8-bit quantization")
        quant_config = BitsAndBytesConfig(
            load_in_8bit=True,
            bnb_8bit_compute_dtype=compute_dtype
        )
    
    return quant_config


def load_base_model(base_model_name: str, quant_config: BitsAndBytesConfig):
    """
    Load the base model with quantization and configure tokenizer.
    
    Args:
        base_model_name: Name of the model on Hugging Face Hub
        quant_config: Quantization configuration
        
    Returns:
        Tuple of (tokenizer, model)
    """
    print(f"\nLoading tokenizer for {base_model_name}...")
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
    
    # Set padding token (required for batch processing)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Set padding side to right (standard for causal LMs)
    tokenizer.padding_side = "right"
    
    print("✓ Tokenizer loaded")
    
    print(f"\nLoading model {base_model_name} with quantization...")
    print("This may take a few minutes...")
    
    # Load model with quantization
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        quantization_config=quant_config,
        device_map="auto",  # Automatically distribute model across available GPUs/CPU
    )
    
    # Set pad token ID in generation config
    base_model.generation_config.pad_token_id = tokenizer.pad_token_id
    
    # Print memory footprint
    memory_mb = base_model.get_memory_footprint() / 1e6
    print(f"✓ Model loaded")
    print(f"  Memory footprint: {memory_mb:.1f} MB")
    
    return tokenizer, base_model


def create_lora_config(
    r: int = 32,
    alpha: int = 64,
    dropout: float = 0.1,
    target_modules: list = None,
    task_type: str = "CAUSAL_LM"
):
    """
    Create LoRA (Low-Rank Adaptation) configuration.
    
    LoRA adds trainable low-rank matrices to specific layers, allowing
    efficient fine-tuning with minimal additional parameters.
    
    Args:
        r: Rank of LoRA matrices (lower = fewer parameters, faster training)
        alpha: LoRA alpha scaling factor (typically 2x rank, controls adapter strength)
        dropout: Dropout rate for LoRA adapters (prevents overfitting)
        target_modules: List of layer names to apply LoRA adapters
        task_type: Type of task (CAUSAL_LM for language modeling)
        
    Returns:
        LoraConfig object
    """
    if target_modules is None:
        target_modules = ["q_proj", "v_proj", "k_proj", "o_proj"]
    
    print(f"\nConfiguring LoRA:")
    print(f"  Rank (r): {r}")
    print(f"  Alpha: {alpha}")
    print(f"  Dropout: {dropout}")
    print(f"  Target modules: {target_modules}")
    
    lora_config = LoraConfig(
        lora_alpha=alpha,  # Scaling factor for LoRA weights
        lora_dropout=dropout,  # Dropout probability for LoRA layers
        r=r,  # Rank of LoRA matrices (number of trainable parameters)
        bias="none",  # Don't train bias terms (none = no bias, all = all biases, lora_only = only LoRA biases)
        task_type=task_type,  # Task type for PEFT
        target_modules=target_modules,  # Which layers to apply LoRA adapters
    )
    
    return lora_config


def create_training_config(
    output_dir: str,
    num_epochs: int,
    batch_size: int,
    learning_rate: float,
    warmup_ratio: float,
    lr_scheduler_type: str,
    weight_decay: float,
    optimizer: str,
    max_sequence_length: int,
    gradient_accumulation_steps: int,
    save_steps: int,
    logging_steps: int,
    use_bf16: bool,
    hub_model_id: str,
    run_name: str,
    log_to_wandb: bool = False
):
    """
    Create Supervised Fine-Tuning (SFT) configuration.
    
    SFTConfig contains all training hyperparameters and settings for the
    SFTTrainer, which handles the fine-tuning process.
    
    Args:
        output_dir: Directory to save checkpoints
        num_epochs: Number of training epochs
        batch_size: Batch size per device
        learning_rate: Initial learning rate
        warmup_ratio: Fraction of steps for warmup
        lr_scheduler_type: Learning rate scheduler type
        weight_decay: Weight decay for regularization
        optimizer: Optimizer name
        max_sequence_length: Maximum sequence length
        gradient_accumulation_steps: Steps to accumulate gradients
        save_steps: Frequency of saving checkpoints
        logging_steps: Frequency of logging metrics
        use_bf16: Whether to use bfloat16 precision
        hub_model_id: Hugging Face Hub model ID
        run_name: Name for this training run
        log_to_wandb: Whether to log to Weights & Biases
        
    Returns:
        SFTConfig object
    """
    print(f"\nConfiguring training:")
    print(f"  Epochs: {num_epochs}")
    print(f"  Batch size: {batch_size}")
    print(f"  Learning rate: {learning_rate}")
    print(f"  Max sequence length: {max_sequence_length}")
    print(f"  Precision: {'bfloat16' if use_bf16 else 'float16'}")
    
    train_config = SFTConfig(
        # Output and saving
        output_dir=output_dir,  # Directory to save model checkpoints
        save_steps=save_steps,  # Save checkpoint every N steps
        save_total_limit=10,  # Maximum number of checkpoints to keep (deletes oldest)
        save_strategy="steps",  # Save based on steps (alternative: "epoch")
        
        # Training parameters
        num_train_epochs=num_epochs,  # Number of complete passes through training data
        per_device_train_batch_size=batch_size,  # Batch size per GPU/device
        per_device_eval_batch_size=1,  # Batch size for evaluation (smaller for memory efficiency)
        gradient_accumulation_steps=gradient_accumulation_steps,  # Accumulate gradients over N batches
        max_steps=-1,  # Maximum training steps (-1 = use epochs instead)
        
        # Optimization
        learning_rate=learning_rate,  # Initial learning rate
        warmup_ratio=warmup_ratio,  # Fraction of training for warmup (gradual LR increase)
        lr_scheduler_type=lr_scheduler_type,  # Learning rate schedule (cosine, linear, etc.)
        weight_decay=weight_decay,  # L2 regularization strength
        optim=optimizer,  # Optimizer algorithm (paged_adamw_32bit = memory-efficient)
        max_grad_norm=0.3,  # Gradient clipping threshold (prevents exploding gradients)
        
        # Precision and performance
        fp16=not use_bf16,  # Use float16 precision (if not using bfloat16)
        bf16=use_bf16,  # Use bfloat16 precision (better for A100/H100 GPUs)
        group_by_length=True,  # Group similar-length sequences together (faster training)
        
        # Sequence handling
        max_length=max_sequence_length,  # Maximum sequence length (truncates longer sequences)
        
        # Evaluation
        eval_strategy="steps",  # Evaluate based on steps (alternative: "epoch", "no")
        eval_steps=save_steps,  # Evaluate every N steps (same as save_steps)
        
        # Logging
        logging_steps=logging_steps,  # Log metrics every N steps
        report_to="wandb" if log_to_wandb else None,  # Logging backend (wandb, tensorboard, None)
        run_name=run_name,  # Name for this training run
        
        # Hugging Face Hub
        hub_strategy="every_save",  # Push to hub every time we save (alternative: "checkpoint", "end")
        push_to_hub=True,  # Automatically push model to Hugging Face Hub
        hub_model_id=hub_model_id,  # Model identifier on Hugging Face Hub
        hub_private_repo=True,  # Make repository private (False = public)
    )
    
    return train_config


def create_trainer(model, tokenizer, train_dataset, eval_dataset, lora_config, train_config):
    """
    Create SFTTrainer for supervised fine-tuning.
    
    SFTTrainer handles the training loop, applying LoRA adapters and
    managing the fine-tuning process.
    
    Args:
        model: Base model with quantization
        tokenizer: Tokenizer instance
        train_dataset: Training dataset
        eval_dataset: Validation dataset
        lora_config: LoRA configuration
        train_config: Training configuration
        
    Returns:
        SFTTrainer object
    """
    print("\nCreating SFTTrainer...")
    
    trainer = SFTTrainer(
        model=model,  # Base model to fine-tune
        train_dataset=train_dataset,  # Training dataset
        eval_dataset=eval_dataset,  # Validation dataset for evaluation
        peft_config=lora_config,  # LoRA/PEFT configuration
        args=train_config,  # Training arguments and hyperparameters
    )
    
    print("✓ Trainer created")
    
    return trainer


def train_model(trainer, hub_model_name: str):
    """
    Train the model and push to Hugging Face Hub.
    
    Args:
        trainer: SFTTrainer instance
        hub_model_name: Hugging Face Hub model name
    """
    print("\n" + "=" * 60)
    print("Starting Training")
    print("=" * 60)
    print("This may take a while depending on your hardware and dataset size...")
    print("The model will be automatically saved to Hugging Face Hub during training.")
    print()
    
    # Start training
    trainer.train()
    
    print("\n" + "=" * 60)
    print("Training Complete!")
    print("=" * 60)
    
    # Push final model to hub
    print(f"\nPushing final model to Hugging Face Hub: {hub_model_name}")
    trainer.model.push_to_hub(hub_model_name, private=True)
    print(f"✓ Model saved to: https://huggingface.co/{hub_model_name}")


def main():
    """
    Main function to orchestrate the fine-tuning process.
    """
    print("=" * 60)
    print("Fine-Tuning Model with QLoRA")
    print("=" * 60)
    print(f"Model: {BASE_MODEL}")
    print(f"Mode: {'LITE' if LITE_MODE else 'FULL'}")
    print(f"Run name: {RUN_NAME}")
    print(f"Hub model: {HUB_MODEL_NAME}")
    print("=" * 60)
    
    # Step 1: Authenticate with Hugging Face and W&B
    load_environment()
    
    # Step 2: Initialize W&B if enabled
    if LOG_TO_WANDB and WANDB_AVAILABLE:
        wandb.init(project=PROJECT_NAME, name=RUN_NAME)
        print("✓ Weights & Biases initialized")
    
    # Step 3: Load dataset
    train, val, test = load_dataset_from_hub(
        lite_mode=LITE_MODE,
        username=DATA_USER,
        val_size=VAL_SIZE
    )
    
    # Step 4: Detect compute dtype based on GPU capabilities
    use_bf16, compute_dtype = detect_compute_dtype()
    
    # Step 5: Create quantization configuration
    quant_config = create_quantization_config(
        use_4bit=QUANT_4_BIT,
        compute_dtype=compute_dtype
    )
    
    # Step 6: Load base model with quantization
    tokenizer, base_model = load_base_model(BASE_MODEL, quant_config)
    
    # Step 7: Create LoRA configuration
    lora_config = create_lora_config(
        r=LORA_R,
        alpha=LORA_ALPHA,
        dropout=LORA_DROPOUT,
        target_modules=TARGET_MODULES,
        task_type="CAUSAL_LM"
    )
    
    # Step 8: Create training configuration
    train_config = create_training_config(
        output_dir=PROJECT_RUN_NAME,
        num_epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        learning_rate=LEARNING_RATE,
        warmup_ratio=WARMUP_RATIO,
        lr_scheduler_type=LR_SCHEDULER_TYPE,
        weight_decay=WEIGHT_DECAY,
        optimizer=OPTIMIZER,
        max_sequence_length=MAX_SEQUENCE_LENGTH,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        save_steps=SAVE_STEPS,
        logging_steps=LOG_STEPS,
        use_bf16=use_bf16,
        hub_model_id=HUB_MODEL_NAME,
        run_name=RUN_NAME,
        log_to_wandb=LOG_TO_WANDB and WANDB_AVAILABLE
    )
    
    # Step 9: Create trainer
    trainer = create_trainer(
        model=base_model,
        tokenizer=tokenizer,
        train_dataset=train,
        eval_dataset=val,
        lora_config=lora_config,
        train_config=train_config
    )
    
    # Step 10: Train model
    train_model(trainer, HUB_MODEL_NAME)
    
    # Step 11: Finish W&B run
    if LOG_TO_WANDB and WANDB_AVAILABLE:
        wandb.finish()
        print("✓ Weights & Biases run finished")
    
    print("\n" + "=" * 60)
    print("Fine-tuning complete!")
    print(f"Model available at: https://huggingface.co/{HUB_MODEL_NAME}")
    print("=" * 60)


if __name__ == "__main__":
    # Set random seed for reproducibility
    set_seed(42)
    
    main()
