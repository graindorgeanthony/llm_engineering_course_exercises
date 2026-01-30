"""
Messaging Agent - Sends push notifications about deals
"""
import os
import requests
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from models import Opportunity
from utils import BaseAgent, MAGENTA


class MessagingAgent(BaseAgent):
    """
    Messaging Agent sends push notifications via Pushover
    """
    name = "Messaging Agent"
    color = MAGENTA
    MODEL = "google/gemini-2.5-flash"  # Using Claude via OpenRouter for message crafting
    
    PUSHOVER_URL = "https://api.pushover.net/1/messages.json"
    
    MESSAGE_PROMPT = """You are crafting an exciting push notification about a great deal.
    
Product: {description}
Deal Price: ${deal_price:.2f}
Estimated Value: ${estimated_value:.2f}
Savings: ${savings:.2f}

Create a concise, exciting 2-3 sentence push notification that:
1. Highlights the product
2. Emphasizes the savings
3. Creates urgency

Keep it under 150 characters. Be enthusiastic but professional."""
    
    def __init__(
        self,
        api_key: str,
        pushover_user: Optional[str] = None,
        pushover_token: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1"
    ):
        """
        Initialize the Messaging Agent
        
        Args:
            api_key: OpenRouter API key
            pushover_user: Pushover user key (from env if not provided)
            pushover_token: Pushover app token (from env if not provided)
            base_url: OpenRouter base URL
        """
        self.log("Messaging Agent is initializing")
        
        # Get Pushover credentials
        self.pushover_user = pushover_user or os.getenv("PUSHOVER_USER", "")
        self.pushover_token = pushover_token or os.getenv("PUSHOVER_TOKEN", "")
        
        # Check if Pushover is configured
        self.pushover_enabled = bool(self.pushover_user and self.pushover_token)
        
        if not self.pushover_enabled:
            self.log("WARNING: Pushover not configured - notifications will be logged only")
        
        # Initialize LangChain LLM for message crafting
        self.llm = ChatOpenAI(
            model=self.MODEL,
            api_key=api_key,
            base_url=base_url,
            temperature=0.7  # Higher temperature for creative messages
        )
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("user", self.MESSAGE_PROMPT)
        ])
        
        # Create chain
        self.chain = self.prompt | self.llm
        
        self.log("Messaging Agent initialized")
    
    def _send_push(self, text: str, url: Optional[str] = None):
        """
        Send a push notification using Pushover API
        
        Args:
            text: Message text
            url: Optional URL to include
        """
        if not self.pushover_enabled:
            self.log(f"[MOCK PUSH] {text}")
            if url:
                self.log(f"[MOCK URL] {url}")
            return
        
        self.log("Sending push notification via Pushover")
        
        payload = {
            "user": self.pushover_user,
            "token": self.pushover_token,
            "message": text,
            "sound": "cashregister",
        }
        
        if url:
            payload["url"] = url
            payload["url_title"] = "View Deal"
        
        try:
            response = requests.post(self.PUSHOVER_URL, data=payload, timeout=10)
            if response.status_code == 200:
                self.log("Push notification sent successfully")
            else:
                self.log(f"Push notification failed: {response.status_code}")
        except Exception as e:
            self.log(f"Error sending push notification: {e}")
    
    def craft_message(
        self,
        description: str,
        deal_price: float,
        estimated_value: float
    ) -> str:
        """
        Use LLM to craft an exciting message about the deal
        
        Args:
            description: Product description
            deal_price: Actual deal price
            estimated_value: Estimated true value
            
        Returns:
            Crafted message text
        """
        self.log("Crafting message using Claude")
        
        savings = estimated_value - deal_price
        
        try:
            response = self.chain.invoke({
                "description": description,
                "deal_price": deal_price,
                "estimated_value": estimated_value,
                "savings": savings
            })
            
            message = response.content.strip()
            self.log("Message crafted successfully")
            return message
            
        except Exception as e:
            self.log(f"Error crafting message: {e}")
            # Fallback to simple message
            return f"🔥 Great Deal! ${savings:.2f} off - {description[:50]}..."
    
    def alert(self, opportunity: Opportunity):
        """
        Send an alert about an opportunity
        
        Args:
            opportunity: The deal opportunity
        """
        self.log(f"Creating alert for deal with ${opportunity.discount:.2f} discount")
        
        # Craft the message
        message = self.craft_message(
            opportunity.deal.product_description,
            opportunity.deal.price,
            opportunity.estimate
        )
        
        # Add pricing summary
        full_message = f"{message}\n\n"
        full_message += f"💰 Price: ${opportunity.deal.price:.2f}\n"
        full_message += f"📊 Value: ${opportunity.estimate:.2f}\n"
        full_message += f"💵 Save: ${opportunity.discount:.2f}"
        
        # Send push notification
        self._send_push(full_message, opportunity.deal.url)
        
        self.log("Messaging Agent completed")
    
    def notify(
        self,
        description: str,
        deal_price: float,
        estimated_value: float,
        url: str
    ):
        """
        Send a notification about specific details
        
        Args:
            description: Product description
            deal_price: Deal price
            estimated_value: Estimated value
            url: Deal URL
        """
        self.log("Creating notification")
        
        # Craft the message
        message = self.craft_message(description, deal_price, estimated_value)
        
        # Truncate and add URL
        truncated_message = message[:200]
        if len(message) > 200:
            truncated_message += "..."
        
        # Send push notification
        self._send_push(truncated_message, url)
        
        self.log("Messaging Agent completed")
