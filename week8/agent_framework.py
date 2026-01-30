"""
Agent Framework - Main orchestration with memory and logging
"""
import os
import json
import logging
from typing import List, Optional
from dotenv import load_dotenv
from models import Opportunity
from vector_store import VectorStore
from agents.scanner_agent import ScannerAgent
from agents.rag_pricer_agent import RAGPricerAgent, HuggingFacePricerAgent, EnsemblePricerAgent
from agents.messaging_agent import MessagingAgent
from agents.planning_agent import PlanningAgent
from utils import init_logging, BG_BLUE, WHITE, RESET

load_dotenv(override=True)


class AgentFramework:
    """
    Main Agent Framework for coordinating all agents with memory and logging
    """
    MEMORY_FILE = "agent_memory.json"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        use_modal: bool = True,
        test_mode: bool = False
    ):
        """
        Initialize the Agent Framework
        
        Args:
            api_key: OpenRouter API key (from env if not provided)
            use_modal: Whether to use Modal for HF pricer (default: True, requires deployment)
            test_mode: Whether to use test data instead of live RSS feeds
        """
        # Initialize logging
        init_logging()
        self.log("Initializing Agent Framework")
        
        # Get API key
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key not provided. Set OPENROUTER_API_KEY env variable.")
        
        self.test_mode = test_mode
        self.use_modal = use_modal
        
        # Load memory
        self.memory = self._load_memory()
        self.log(f"Loaded {len(self.memory)} items from memory")
        
        # Initialize vector store
        self.vector_store = VectorStore()
        
        # Initialize agents (lazy loading)
        self.scanner = None
        self.rag_pricer = None
        self.hf_pricer = None
        self.ensemble_pricer = None
        self.messenger = None
        self.planner = None
        
        self.log("Agent Framework initialized")
    
    def _init_agents(self):
        """
        Initialize all agents (called on first run)
        """
        if self.planner is not None:
            return  # Already initialized
        
        self.log("Initializing all agents")
        
        # Scanner Agent
        self.scanner = ScannerAgent(api_key=self.api_key)
        
        # RAG Pricer Agent
        self.rag_pricer = RAGPricerAgent(
            vector_store=self.vector_store,
            api_key=self.api_key
        )
        
        # Hugging Face Pricer Agent
        self.hf_pricer = HuggingFacePricerAgent(use_modal=self.use_modal)
        
        # Ensemble Pricer Agent
        self.ensemble_pricer = EnsemblePricerAgent(
            rag_pricer=self.rag_pricer,
            hf_pricer=self.hf_pricer
        )
        
        # Messaging Agent
        self.messenger = MessagingAgent(api_key=self.api_key)
        
        # Planning Agent
        self.planner = PlanningAgent(
            scanner=self.scanner,
            pricer=self.ensemble_pricer,
            messenger=self.messenger
        )
        
        self.log("All agents initialized successfully")
    
    def _load_memory(self) -> List[Opportunity]:
        """
        Load memory from file
        
        Returns:
            List of Opportunity objects
        """
        if os.path.exists(self.MEMORY_FILE):
            try:
                with open(self.MEMORY_FILE, "r") as f:
                    data = json.load(f)
                return [Opportunity(**item) for item in data]
            except Exception as e:
                logging.error(f"Error loading memory: {e}")
                return []
        return []
    
    def _save_memory(self):
        """
        Save memory to file
        """
        try:
            data = [opp.model_dump() for opp in self.memory]
            with open(self.MEMORY_FILE, "w") as f:
                json.dump(data, f, indent=2)
            self.log(f"Saved {len(self.memory)} items to memory")
        except Exception as e:
            logging.error(f"Error saving memory: {e}")
    
    def reset_memory(self):
        """
        Reset memory (keep only last 2 items for testing)
        """
        self.memory = self.memory[:2] if len(self.memory) > 2 else self.memory
        self._save_memory()
        self.log("Memory reset")
    
    def log(self, message: str):
        """
        Log a message with framework identification
        """
        text = BG_BLUE + WHITE + "[Agent Framework] " + message + RESET
        logging.info(text)
    
    def run(self) -> List[Opportunity]:
        """
        Run the agent framework workflow
        
        Returns:
            Updated list of opportunities
        """
        self._init_agents()
        
        self.log("Starting agent workflow")
        
        # Run planning agent
        result = self.planner.plan(memory=self.memory)
        
        # Update memory if new opportunity found
        if result:
            self.memory.append(result)
            self._save_memory()
            self.log(f"New opportunity added to memory - Total: {len(self.memory)}")
        else:
            self.log("No new opportunities above threshold")
        
        self.log("Agent workflow completed")
        
        return self.memory
    
    def load_sample_data(self, num_samples: int = 100):
        """
        Load sample product data into vector store
        
        Args:
            num_samples: Number of sample products to generate
        """
        self.log(f"Loading {num_samples} sample products into vector store")
        
        # Sample product data (in real scenario, this would come from a dataset)
        sample_products = [
            ("Apple MacBook Pro 16-inch with M3 Pro chip, 18GB RAM, 512GB SSD, Liquid Retina XDR display", 2499.0, "Electronics"),
            ("Sony WH-1000XM5 Wireless Noise Cancelling Headphones with 30-hour battery life", 399.0, "Electronics"),
            ("Samsung 55-inch 4K UHD Smart TV with HDR and Alexa built-in", 649.0, "Electronics"),
            ("Dell XPS 15 Laptop with Intel Core i7, 16GB RAM, 512GB SSD, 15.6-inch display", 1599.0, "Computers"),
            ("Logitech MX Master 3S Wireless Mouse with 8K DPI sensor", 99.0, "Accessories"),
            ("iPad Air 5th Gen with M1 chip, 64GB, Wi-Fi, 10.9-inch display", 599.0, "Electronics"),
            ("Bose SoundLink Flex Bluetooth Speaker waterproof portable", 129.0, "Electronics"),
            ("Amazon Echo Show 10 Smart Display with motion tracking", 249.0, "Smart Home"),
            ("Canon EOS R6 Mark II Mirrorless Camera body only", 2499.0, "Electronics"),
            ("Nintendo Switch OLED Model with 7-inch OLED screen", 349.0, "Electronics"),
            ("Dyson V15 Detect Cordless Vacuum with laser dust detection", 749.0, "Home"),
            ("Apple AirPods Pro 2nd generation with MagSafe charging case", 249.0, "Accessories"),
            ("Samsung Galaxy Tab S9 11-inch tablet with S Pen included", 799.0, "Electronics"),
            ("LG 27-inch 4K UHD Monitor with USB-C connectivity", 449.0, "Computers"),
            ("Kindle Paperwhite 11th Gen with 6.8-inch display and warm light", 139.0, "Electronics"),
            ("Fitbit Charge 6 Fitness Tracker with heart rate and GPS", 159.0, "Wearables"),
            ("GoPro HERO12 Black Action Camera with 5.3K60 video", 399.0, "Electronics"),
            ("Sony PlayStation 5 Console with disc drive", 499.0, "Electronics"),
            ("Microsoft Surface Pro 9 with Intel Core i5, 8GB RAM, 256GB SSD", 999.0, "Computers"),
            ("Anker PowerCore 20000mAh Portable Charger with fast charging", 49.0, "Accessories"),
        ]
        
        # Extend to requested number with variations
        descriptions = []
        prices = []
        categories = []
        
        import random
        random.seed(42)
        
        for i in range(num_samples):
            base_product = sample_products[i % len(sample_products)]
            # Add slight variation to price
            price_variation = random.uniform(0.9, 1.1)
            descriptions.append(base_product[0])
            prices.append(base_product[1] * price_variation)
            categories.append(base_product[2])
        
        # Add to vector store
        self.vector_store.add_products(descriptions, prices, categories)
        
        self.log(f"Successfully loaded {num_samples} products into vector store")
    
    def get_stats(self) -> dict:
        """
        Get framework statistics
        
        Returns:
            Dictionary with stats
        """
        return {
            "memory_items": len(self.memory),
            "vector_store_items": self.vector_store.count(),
            "best_discount": max([opp.discount for opp in self.memory], default=0.0),
            "total_savings": sum([opp.discount for opp in self.memory if opp.discount > 0]),
        }


if __name__ == "__main__":
    # Example usage (use_modal=True to call deployed Modal service)
    framework = AgentFramework(test_mode=False, use_modal=True)
    
    # Load sample data if vector store is empty
    if framework.vector_store.count() == 0:
        framework.load_sample_data(100)
    
    # Run the framework
    opportunities = framework.run()
    
    # Print stats
    stats = framework.get_stats()
    print(f"\n=== Framework Stats ===")
    print(f"Total opportunities: {stats['memory_items']}")
    print(f"Vector store items: {stats['vector_store_items']}")
    print(f"Best discount: ${stats['best_discount']:.2f}")
    print(f"Total savings: ${stats['total_savings']:.2f}")
