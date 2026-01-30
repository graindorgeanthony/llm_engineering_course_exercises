"""
RAG-Prices Agent - Uses RAG with frontier model to estimate prices
"""
import re
from typing import List, Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from vector_store import VectorStore
from utils import BaseAgent, BLUE


class RAGPricerAgent(BaseAgent):
    """
    RAG-based Pricer Agent that uses vector search and frontier model
    """
    name = "RAG Pricer Agent"
    color = BLUE
    MODEL = "google/gemini-2.5-flash"  # Frontier model via OpenRouter
    
    SYSTEM_PROMPT = """You are a pricing expert that estimates product prices based on similar items.
    You will be provided with a product description and examples of similar products with their prices.
    
    Analyze the similar products and provide an accurate price estimate.
    Respond ONLY with the numeric price value (e.g., "299.99" or "1499").
    Do NOT include dollar signs, explanations, or any other text.
    """
    
    USER_PROMPT_TEMPLATE = """Estimate the price of this product:

{product_description}

Here are similar products to help you estimate:

{similar_products}

What is the estimated price? Respond with ONLY the numeric value."""
    
    def __init__(self, vector_store: VectorStore, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        """
        Initialize the RAG Pricer Agent
        
        Args:
            vector_store: VectorStore instance for similarity search
            api_key: OpenRouter API key
            base_url: OpenRouter base URL
        """
        self.log("Initializing RAG Pricer Agent")
        
        self.vector_store = vector_store
        
        # Initialize LangChain LLM with OpenRouter
        self.llm = ChatOpenAI(
            model=self.MODEL,
            api_key=api_key,
            base_url=base_url,
            temperature=0.1
        )
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("user", self.USER_PROMPT_TEMPLATE)
        ])
        
        # Create chain
        self.chain = self.prompt | self.llm
        
        self.log("RAG Pricer Agent is ready")
    
    def _format_similar_products(self, descriptions: List[str], prices: List[float]) -> str:
        """
        Format similar products for the prompt
        
        Args:
            descriptions: List of product descriptions
            prices: List of prices
            
        Returns:
            Formatted string
        """
        lines = []
        for i, (desc, price) in enumerate(zip(descriptions, prices), 1):
            lines.append(f"{i}. {desc}")
            lines.append(f"   Price: ${price:.2f}\n")
        return "\n".join(lines)
    
    def _extract_price(self, response: str) -> float:
        """
        Extract price from LLM response
        
        Args:
            response: LLM response string
            
        Returns:
            Extracted price as float
        """
        # Remove common price symbols and text
        cleaned = response.replace("$", "").replace(",", "").strip()
        
        # Extract first number found
        match = re.search(r"[-+]?\d*\.\d+|\d+", cleaned)
        if match:
            return float(match.group())
        
        return 0.0
    
    def price(self, description: str, n_similar: int = 5) -> float:
        """
        Estimate the price of a product using RAG
        
        Args:
            description: Product description
            n_similar: Number of similar products to retrieve
            
        Returns:
            Estimated price
        """
        # Ensure the full dataset is loaded before querying
        self.vector_store.ensure_full_dataset_loaded()
        self.log(f"RAG Pricer is searching for {n_similar} similar products")
        
        # Find similar products using vector search
        similar_descriptions, similar_prices = self.vector_store.search_similar(
            description, n_results=n_similar
        )
        
        if not similar_descriptions:
            self.log("No similar products found, returning default price")
            return 0.0
        
        # Format similar products
        similar_products_text = self._format_similar_products(
            similar_descriptions, similar_prices
        )
        
        self.log(f"RAG Pricer is calling {self.MODEL} with context of {len(similar_descriptions)} similar products")
        
        try:
            # Invoke chain
            response = self.chain.invoke({
                "product_description": description,
                "similar_products": similar_products_text
            })
            
            # Extract price from response
            price = self._extract_price(response.content)
            
            self.log(f"RAG Pricer completed - predicting ${price:.2f}")
            return price
            
        except Exception as e:
            self.log(f"Error in pricing: {e}")
            # Fallback to average of similar prices
            if similar_prices:
                avg_price = sum(similar_prices) / len(similar_prices)
                self.log(f"Using fallback average price: ${avg_price:.2f}")
                return avg_price
            return 0.0


class HuggingFacePricerAgent(BaseAgent):
    """
    Pricer Agent that uses Hugging Face model via Modal
    """
    name = "HF Pricer Agent"
    color = BLUE
    
    def __init__(self, use_modal: bool = True):
        """
        Initialize the Hugging Face Pricer Agent
        
        Args:
            use_modal: Whether to use Modal service (True) or mock (False)
        """
        self.log(f"Initializing HF Pricer Agent (use_modal={use_modal})")
        
        self.use_modal = use_modal
        self.using_mock = False
        
        if use_modal:
            try:
                from modal_pricer_service import PricerClient
                self.client = PricerClient()
                self.log("✅ Successfully connected to Modal service!")
            except Exception as e:
                self.log(f"❌ Failed to connect to Modal: {e}")
                self.log("⚠️  Falling back to Mock Pricer")
                from modal_pricer_service import MockPricerClient
                self.client = MockPricerClient()
                self.use_modal = False
                self.using_mock = True
        else:
            from modal_pricer_service import MockPricerClient
            self.client = MockPricerClient()
            self.using_mock = True
            self.log("ℹ️  Using Mock Pricer (use_modal=False)")
        
        self.log(f"HF Pricer Agent is ready (Modal={'enabled' if use_modal and not self.using_mock else 'disabled'})")
    
    def price(self, description: str) -> float:
        """
        Estimate the price using Hugging Face model
        
        Args:
            description: Product description
            
        Returns:
            Estimated price
        """
        if self.using_mock:
            self.log("🔧 HF Pricer is using MOCK (not calling Modal)")
        else:
            self.log("📡 HF Pricer is calling Modal deployed Hugging Face model...")
        
        try:
            price = self.client.price(description)
            source = "MOCK" if self.using_mock else "MODAL"
            self.log(f"✅ HF Pricer completed ({source}) - predicting ${price:.2f}")
            return price
        except Exception as e:
            self.log(f"❌ Error in HF pricing: {e}")
            return 0.0


class EnsemblePricerAgent(BaseAgent):
    """
    Ensemble Pricer that combines RAG and HuggingFace models
    """
    name = "Ensemble Pricer Agent"
    color = BLUE
    
    def __init__(self, rag_pricer: RAGPricerAgent, hf_pricer: HuggingFacePricerAgent):
        """
        Initialize the Ensemble Pricer
        
        Args:
            rag_pricer: RAG pricer agent
            hf_pricer: Hugging Face pricer agent
        """
        self.log("Initializing Ensemble Pricer Agent")
        self.rag_pricer = rag_pricer
        self.hf_pricer = hf_pricer
        self.log("Ensemble Pricer Agent is ready")
    
    def price(self, description: str) -> float:
        """
        Estimate price using ensemble of models
        
        Args:
            description: Product description
            
        Returns:
            Weighted ensemble price estimate
        """
        self.log("Running Ensemble Pricer - getting estimates from both models")
        
        # Get estimates from both models
        rag_price = self.rag_pricer.price(description)
        hf_price = self.hf_pricer.price(description)
        
        # Weighted combination (80% RAG, 20% HF)
        ensemble_price = rag_price * 0.8 + hf_price * 0.2
        
        self.log(f"Ensemble complete - RAG: ${rag_price:.2f}, HF: ${hf_price:.2f}, Final: ${ensemble_price:.2f}")
        
        return ensemble_price
