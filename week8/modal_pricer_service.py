"""
Modal service for deploying Hugging Face pricer model (Modal 1.0 compatible)
"""
import modal

# Setup - define our infrastructure with code!
app = modal.App("agentic-pricer-service")

# Create image with required dependencies
image = modal.Image.debian_slim().pip_install(
    "huggingface_hub",
    "torch",
    "transformers",
    "bitsandbytes",
    "accelerate",
    "peft"
)

# Secrets for Hugging Face authentication
secrets = [modal.Secret.from_name("huggingface-secret")]

# Configuration
GPU = "T4"
BASE_MODEL = "meta-llama/Llama-3.2-3B"
PROJECT_NAME = "price"
HF_USER = "ed-donner"  # Replace with your HF username if you have a fine-tuned model
RUN_NAME = "2025-11-28_18.47.07"
PROJECT_RUN_NAME = f"{PROJECT_NAME}-{RUN_NAME}"
REVISION = "b19c8bfea3b6ff62237fbb0a8da9779fc12cefbd"
FINETUNED_MODEL = f"{HF_USER}/{PROJECT_RUN_NAME}"
CACHE_DIR = "/cache"

# Keep 1 container warm for faster responses
MIN_CONTAINERS = 1

PREFIX = "Price is $"
QUESTION = "What does this cost to the nearest dollar?"

# Volume for caching
hf_cache_volume = modal.Volume.from_name("hf-hub-cache", create_if_missing=True)


@app.cls(
    image=image.env({"HF_HUB_CACHE": CACHE_DIR}),
    secrets=secrets,
    gpu=GPU,
    timeout=1800,
    scaledown_window=300,  # Renamed from container_idle_timeout in Modal 1.0
    volumes={CACHE_DIR: hf_cache_volume},
)
class HuggingFacePricer:
    """
    Modal service class for price estimation using a fine-tuned Llama model
    """
    
    @modal.enter()
    def setup(self):
        """
        Load the model and tokenizer on container startup
        """
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
        from peft import PeftModel
        
        print("Loading model and tokenizer...")
        
        # Quantization config for 4-bit loading
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
        )
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = "right"
        
        # Load base model
        self.base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL,
            quantization_config=quant_config,
            device_map="auto"
        )
        
        # Load fine-tuned adapter
        self.fine_tuned_model = PeftModel.from_pretrained(
            self.base_model,
            FINETUNED_MODEL,
            revision=REVISION
        )
        
        print("Model loaded successfully!")
    
    @modal.method()
    def price(self, description: str) -> float:
        """
        Estimate the price of a product based on its description
        
        Args:
            description: Product description
            
        Returns:
            Estimated price as a float
        """
        import re
        import torch
        from transformers import set_seed
        
        set_seed(42)
        prompt = f"{QUESTION}\n\n{description}\n\n{PREFIX}"
        
        # Tokenize and generate
        inputs = self.tokenizer.encode(prompt, return_tensors="pt").to("cuda")
        with torch.no_grad():
            outputs = self.fine_tuned_model.generate(inputs, max_new_tokens=5)
        
        # Decode and extract price
        result = self.tokenizer.decode(outputs[0])
        
        # Extract price from result
        if "Price is $" in result:
            contents = result.split("Price is $")[1]
            contents = contents.replace(",", "")
            match = re.search(r"[-+]?\d*\.\d+|\d+", contents)
            return float(match.group()) if match else 0.0
        
        return 0.0


# Client class for local use (Modal 1.0 compatible)
class PricerClient:
    """
    Client to interact with the Modal pricer service using Modal 1.0 API
    Uses modal.Cls.from_name to hydrate the deployed class metadata
    """
    
    def __init__(self):
        """
        Initialize the Modal class reference
        """
        print("🔌 Initializing Modal Pricer Client (Modal 1.0)...")
        print("🔍 Connecting to deployed 'agentic-pricer-service::HuggingFacePricer'...")
        
        try:
            self.pricer_cls = modal.Cls.from_name(
                "agentic-pricer-service",
                "HuggingFacePricer",
            )
            print("✅ Modal class reference hydrated successfully!")
        except Exception as e:
            print(f"❌ Error getting class reference: {e}")
            print("💡 Make sure you've deployed with: modal deploy modal_pricer_service.py")
            raise
    
    def price(self, description: str) -> float:
        """
        Get price estimate from Modal service
        
        Args:
            description: Product description
            
        Returns:
            Estimated price
        """
        try:
            print(f"📡 Calling Modal service for pricing...")
            # Call the remote method on the hydrated class
            result = self.pricer_cls().price.remote(description)
            print(f"✅ Modal returned price: ${result:.2f}")
            return result
        except Exception as e:
            print(f"❌ Error calling Modal pricer: {e}")
            print(f"   Error details: {type(e).__name__}: {str(e)}")
            print("   Falling back to 0.0")
            return 0.0


# For local testing without Modal deployment
class MockPricerClient:
    """
    Mock pricer for testing without Modal
    """
    
    def price(self, description: str) -> float:
        """
        Return a mock price estimate
        """
        # Simple heuristic based on description length
        import random
        random.seed(hash(description) % 1000)
        return round(random.uniform(50, 800), 2)


if __name__ == "__main__":
    # Example usage
    description = "Apple MacBook Pro 16-inch with M3 Pro chip, 18GB RAM, 512GB SSD"
    
    # To deploy: modal deploy modal_pricer_service.py
    # To test locally without deployment, use MockPricerClient
    client = MockPricerClient()
    price = client.price(description)
    print(f"Estimated price: ${price:.2f}")
