from email import message
import os
from dotenv import load_dotenv

import sqlite3
import gradio as gr

from gradio.utils import tex2svg
from langchain.agents import create_agent
from langchain_core.tools import StructuredTool
#from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

load_dotenv(override=True)

# System prompt
SYSTEM_PROMPT = """You are a helpful assistant for an Airline called FlightAI.
Give short, courteous answers, no more than 1 sentence.
Always be accurate. If you don't know the answer, say so."""

# Database name
DB = "prices.db"

# Database configuration
def init_database():
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS prices (city TEXT PRIMARY KEY, price REAL)")
        cur.execute("SELECT COUNT(*) FROM prices")
        if cur.fetchone()[0] == 0:
            prices = {"london": 799, "paris": 899, "tokyo": 1420, "sydney": 2999, "berlin": 499}
            cur.executemany(
                "INSERT INTO prices (city, price) VALUES (?, ?)",
                [(k, float(v)) for k, v in prices.items()],
            )
        conn.commit()

init_database()

# Configure the LLM
#llm = ChatOllama(model="llama3.2", temperature=0)

api_key = os.getenv('OPENROUTER_API_KEY')
llm = ChatOpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1",
    model="google/gemini-2.5-flash", 
    temperature=0
)

# Get prices in the database
def get_ticket_price(destination_city: str) -> str:
    city = (destination_city or "").strip().lower()
    if not city:
        return "Please provide a destination city."

    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT price FROM prices WHERE city = ?", (city,))
        row = cur.fetchone()

    if not row:
        return f"No price data available for {destination_city}."

    price = float(row[0])
    price_str = str(int(price)) if price.is_integer() else f"{price:.2f}"
    return f"The price of a ticket to {destination_city} is ${price_str}."

# Setup the function in Langchain
ticket_price_tool = StructuredTool.from_function(
    func=get_ticket_price,
    name="get_ticket_price",
    description="Get the price of a return ticket to the destination city.",
)

# Chat function to manage LLM calls
def chat(message, history):
    history_messages = [{"role": h["role"], "content": h["content"]} for h in history]
    messages = history_messages + [{"role": "user", "content": message}]

    state = agent.invoke({"messages": messages})
    
    # Check if any tool calls were made and look for image results
    for msg in reversed(state["messages"]):
        # Check for ToolMessage with image data
        if hasattr(msg, "content") and isinstance(msg.content, str):
            if msg.content.startswith("data:image"):
                # Return image in the format Gradio expects
                return {"role": "assistant", "content": {"image": msg.content}}
    
    # Get the last message for regular text responses
    last = state["messages"][-1]

    # Works for AIMessage/HumanMessage/etc.
    if hasattr(last, "content"):
        return last.content

    # Works if some runner returns dicts
    if isinstance(last, dict):
        return last.get("content", "")

    return str(last)

# Launch the chat interface
if __name__ == "__main__":
    gr.ChatInterface(
        fn=chat,
        title="FlightAI Assistant",
        description="Ask me about ticket prices to various destinations!"
    ).launch(inbrowser=True)
