"""
Scanner Agent - Identifies promising deals from RSS feeds using LangChain
"""
from typing import List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from models import ScrapedDeal, DealSelection, Deal
from utils import BaseAgent, CYAN


class ScannerAgent(BaseAgent):
    """
    Scanner Agent identifies and summarizes the most detailed deals from RSS feeds
    """
    name = "Scanner Agent"
    color = CYAN
    MODEL = "google/gemini-2.5-flash"  # Using OpenRouter
    
    SYSTEM_PROMPT = """You identify and summarize the 5 most detailed deals from a list.
    Select deals that have:
    1. The most detailed, high quality description
    2. A clear price that is greater than 0
    
    IMPORTANT:
    - Focus on products with detailed descriptions
    - Only include deals where you're confident about the actual price
    - Be careful with "$XXX off" or "reduced by $XXX" - that's not the actual price
    - Summarize the product itself, not the terms of the deal
    - Respond strictly in the specified JSON format
    """
    
    USER_PROMPT_TEMPLATE = """Respond with the most promising 5 deals from this list.
    Select those which have the most detailed, high quality product description and a clear price > 0.
    Rephrase the description to be a summary of the product itself, not the terms of the deal.
    
    Deals:
    
    {deals}
    
    Include exactly 5 deals, no more.
    
    {format_instructions}
    """
    
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        """
        Initialize the Scanner Agent with OpenRouter
        
        Args:
            api_key: OpenRouter API key
            base_url: OpenRouter base URL
        """
        self.log("Scanner Agent is initializing")
        
        # Initialize LangChain LLM with OpenRouter
        self.llm = ChatOpenAI(
            model=self.MODEL,
            api_key=api_key,
            base_url=base_url,
            temperature=0.1
        )
        
        # Setup output parser
        self.parser = PydanticOutputParser(pydantic_object=DealSelection)
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("user", self.USER_PROMPT_TEMPLATE)
        ])
        
        # Create chain
        self.chain = self.prompt | self.llm | self.parser
        
        self.log("Scanner Agent is ready")
    
    def fetch_deals(self, memory: List) -> List[ScrapedDeal]:
        """
        Look up deals published on RSS feeds
        Return any new deals that are not already in the memory provided
        
        Args:
            memory: List of Opportunity objects already processed
            
        Returns:
            List of new ScrapedDeal objects
        """
        self.log("Scanner Agent is fetching deals from RSS feeds")
        urls = [opp.deal.url for opp in memory]
        scraped = ScrapedDeal.fetch()
        result = [scrape for scrape in scraped if scrape.url not in urls]
        self.log(f"Scanner Agent received {len(result)} deals not already processed")
        return result
    
    def scan(self, memory: List = []) -> Optional[DealSelection]:
        """
        Call LLM to provide a high potential list of deals
        
        Args:
            memory: List of URLs representing deals already raised
            
        Returns:
            DealSelection or None if there aren't any new deals
        """
        scraped = self.fetch_deals(memory)
        
        if not scraped:
            self.log("No new deals found")
            return None
        
        # Prepare deals text
        deals_text = "\n\n".join([scrape.describe() for scrape in scraped])
        
        self.log(f"Scanner Agent is calling LLM to analyze {len(scraped)} deals")
        
        try:
            # Invoke chain
            result = self.chain.invoke({
                "deals": deals_text,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            # Filter out deals with price <= 0
            result.deals = [deal for deal in result.deals if deal.price > 0]
            
            self.log(f"Scanner Agent received {len(result.deals)} selected deals with price > 0")
            return result
            
        except Exception as e:
            self.log(f"Error in scanning: {e}")
            return None
    
    def test_scan(self) -> Optional[DealSelection]:
        """
        Return a test DealSelection for testing without API calls
        """
        self.log("Using test scan data")
        test_deals = [
            Deal(
                product_description="The Hisense R6 Series 55R6030N is a 55-inch 4K UHD Roku Smart TV with stunning picture quality and 3840x2160 resolution.",
                price=178.0,
                url="https://www.dealnews.com/test/tv"
            ),
            Deal(
                product_description="The Poly Studio P21 is a 21.5-inch LED personal meeting display designed for remote work with 1080p webcam.",
                price=30.0,
                url="https://www.dealnews.com/test/display"
            ),
            Deal(
                product_description="The Lenovo IdeaPad Slim 5 laptop with AMD Ryzen 5 8645HS, 16GB RAM, 512GB SSD, and 16-inch touch display.",
                price=446.0,
                url="https://www.dealnews.com/test/laptop"
            ),
            Deal(
                product_description="The Dell G15 gaming laptop with AMD Ryzen 5 7640HS, 15.6-inch 120Hz display, 16GB RAM, 1TB SSD, and RTX 3050 GPU.",
                price=650.0,
                url="https://www.dealnews.com/test/gaming"
            ),
            Deal(
                product_description="Apple AirPods Pro 2nd generation with active noise cancellation, adaptive transparency, and USB-C charging case.",
                price=189.0,
                url="https://www.dealnews.com/test/airpods"
            )
        ]
        return DealSelection(deals=test_deals)
