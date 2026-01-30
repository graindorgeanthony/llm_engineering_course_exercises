"""
Pydantic models for structured data in the Agentic AI Framework
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import re
import feedparser
import requests
import time

# RSS Feeds for deals
FEEDS = [
    "https://www.dealnews.com/c142/Electronics/?rss=1",
    "https://www.dealnews.com/c39/Computers/?rss=1",
    "https://www.dealnews.com/f1912/Smart-Home/?rss=1",
]


def extract_text(html_snippet: str) -> str:
    """
    Use Beautiful Soup to clean up HTML snippet and extract useful text
    """
    soup = BeautifulSoup(html_snippet, "html.parser")
    snippet_div = soup.find("div", class_="snippet summary")
    
    if snippet_div:
        description = snippet_div.get_text(strip=True)
        description = BeautifulSoup(description, "html.parser").get_text()
        description = re.sub("<[^<]+?>", "", description)
        result = description.strip()
    else:
        result = html_snippet
    return result.replace("\n", " ")


class ScrapedDeal:
    """
    A class to represent a Deal retrieved from an RSS feed
    """
    title: str
    summary: str
    url: str
    details: str
    features: str

    def __init__(self, entry: Dict[str, str]):
        """
        Populate this instance based on the provided dict
        """
        self.title = entry["title"]
        self.summary = extract_text(entry["summary"])
        self.url = entry["links"][0]["href"]
        
        try:
            stuff = requests.get(self.url, timeout=10).content
            soup = BeautifulSoup(stuff, "html.parser")
            content_div = soup.find("div", class_="content-section")
            if content_div:
                content = content_div.get_text()
                content = content.replace("\nmore", "").replace("\n", " ")
                if "Features" in content:
                    self.details, self.features = content.split("Features", 1)
                else:
                    self.details = content
                    self.features = ""
            else:
                self.details = self.summary
                self.features = ""
        except Exception as e:
            self.details = self.summary
            self.features = ""
        
        self.truncate()

    def truncate(self):
        """
        Limit the fields to a sensible length
        """
        self.title = self.title[:100]
        self.details = self.details[:500]
        self.features = self.features[:500]

    def __repr__(self):
        return f"<{self.title}>"

    def describe(self):
        """
        Return a longer string to describe this deal for use in calling a model
        """
        return f"Title: {self.title}\nDetails: {self.details.strip()}\nFeatures: {self.features.strip()}\nURL: {self.url}"

    @classmethod
    def fetch(cls, show_progress: bool = False) -> List['ScrapedDeal']:
        """
        Retrieve all deals from the selected RSS feeds
        """
        deals = []
        for feed_url in FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:10]:
                    try:
                        deals.append(cls(entry))
                        time.sleep(0.05)
                    except Exception as e:
                        continue
            except Exception as e:
                continue
        return deals


class Deal(BaseModel):
    """
    A class to represent a Deal with a summary description
    """
    product_description: str = Field(
        description="Your clearly expressed summary of the product in 3-4 sentences. Details of the item are much more important than why it's a good deal. Avoid mentioning discounts and coupons; focus on the item itself."
    )
    price: float = Field(
        description="The actual price of this product, as advertised in the deal. Be sure to give the actual price; for example, if a deal is described as $100 off the usual $300 price, you should respond with $200"
    )
    url: str = Field(description="The URL of the deal, as provided in the input")


class DealSelection(BaseModel):
    """
    A class to represent a list of Deals
    """
    deals: List[Deal] = Field(
        description="Your selection of the 5 deals that have the most detailed, high quality description and the most clear price."
    )


class Opportunity(BaseModel):
    """
    A class to represent a possible opportunity: a Deal where we estimate
    it should cost more than it's being offered
    """
    deal: Deal
    estimate: float
    discount: float


class PriceEstimate(BaseModel):
    """
    Structured output for price estimation
    """
    estimated_price: float = Field(
        description="The estimated price of the product based on similar items and market context"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Brief explanation of the price estimate"
    )
