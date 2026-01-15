"""
Quick test script to verify LangChain tool call structure
Run this to check if the tool calling works before testing the full UI
"""
import os
from dotenv import load_dotenv
import sqlite3
from langchain.agents import create_agent
from langchain_core.tools import StructuredTool
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

# Configure the LLM
api_key = os.getenv('OPENROUTER_API_KEY')
llm = ChatOpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1",
    model="google/gemini-2.5-flash", 
    temperature=0
)

def artist(city: str) -> str:
    """Artist tool for the agent - returns a string message"""
    return f"Generated a vibrant pop-art style image representing a vacation in {city}."

ticket_price_tool = StructuredTool.from_function(
    func=get_ticket_price,
    name="get_ticket_price",
    description="Get the price of a return ticket to the destination city.",
)

artist_tool = StructuredTool.from_function(
    func=artist,
    name="artist",
    description="Generate an image of a vacation for any city to help the user visualize their destination.",
)

agent = create_agent(
    model=llm,
    tools=[ticket_price_tool, artist_tool],
    system_prompt=SYSTEM_PROMPT,
)

# Test the agent
print("Testing agent with tool calls...\n")
test_message = "What's the price to Paris? Can you show me what it looks like?"
print(f"User: {test_message}\n")

state = agent.invoke({"messages": [{"role": "user", "content": test_message}]})

print("=" * 60)
print("ANALYZING MESSAGE STRUCTURE")
print("=" * 60)

price_cities = []
image_cities = []
for i, msg in enumerate(state["messages"]):
    print(f"\n--- Message {i}: {type(msg).__name__} ---")
    
    if hasattr(msg, "content"):
        print(f"Content: {msg.content[:100] if msg.content else 'None'}...")
    
    if hasattr(msg, "tool_calls") and msg.tool_calls:
        print(f"Has tool_calls: True")
        print(f"tool_calls type: {type(msg.tool_calls)}")
        print(f"Number of tool calls: {len(msg.tool_calls)}")
        
        for j, tool_call in enumerate(msg.tool_calls):
            print(f"\n  Tool Call {j}:")
            print(f"    Type: {type(tool_call)}")
            print(f"    Is dict: {isinstance(tool_call, dict)}")
            
            # Try to extract name
            if isinstance(tool_call, dict):
                tool_name = tool_call.get("name")
                args = tool_call.get("args", {})
            else:
                tool_name = getattr(tool_call, "name", None)
                args = getattr(tool_call, "args", {})
            
            print(f"    Name: {tool_name}")
            print(f"    Args: {args}")
            
            if tool_name == "get_ticket_price" and isinstance(args, dict) and "destination_city" in args:
                city = args["destination_city"]
                price_cities.append(city)
                print(f"    ✓ Extracted city for price: {city}")
            
            if tool_name == "artist" and isinstance(args, dict) and "city" in args:
                city = args["city"]
                image_cities.append(city)
                print(f"    ✓ Extracted city for image: {city}")

print("\n" + "=" * 60)
print("RESULTS:")
print(f"  Price tool cities: {price_cities}")
print(f"  Artist tool cities: {image_cities}")
print("=" * 60)

# Print final response
last_msg = state["messages"][-1]
if hasattr(last_msg, "content"):
    print(f"\nAssistant: {last_msg.content}")
