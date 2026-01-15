import os
from dotenv import load_dotenv

import sqlite3
import gradio as gr

from langchain.agents import create_agent
from langchain_core.tools import StructuredTool
#from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from openai import OpenAI

import base64
from io import BytesIO
from PIL import Image
from elevenlabs import ElevenLabs

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
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)

# Configure ElevenLabs for TTS
elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)

# Function to get the price of a ticket to a destination city
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

# Global variable to store the last generated image
last_generated_image = None

# Function to generate an image of a city in pop-art style
def generate_image(city):
    """Generate an actual PIL Image for a city"""
    response = client.chat.completions.create(
        model="google/gemini-2.5-flash-image",
        messages=[{"role":"user", "content":f"An image representing a vacation in {city}, showing tourist spots and everything unique about {city}, in a vibrant pop-art style"}],
        extra_body={"modalities":["image","text"]}
    )
    response = response.choices[0].message
    if response.images:
        for image in response.images:
            image_url = image['image_url']['url'] 
            image_data = base64.b64decode(image_url.split(",")[-1])
            return Image.open(BytesIO(image_data))
    return None

# Function the agent uses to generate the image
def artist(city: str) -> str:
    """Artist tool for the agent - actually generates the image"""
    global last_generated_image
    try:
        # Actually call generate_image to create the image
        last_generated_image = generate_image(city)
        if last_generated_image:
            return f"Generated a vibrant pop-art style image representing a vacation in {city}."
        else:
            return f"Failed to generate image for {city}."
    except Exception as e:
        return f"Error generating image for {city}: {str(e)}"

# Function to generate voice/audio from text using TTS
def talker(message: str):
    """Generate audio from text using ElevenLabs TTS"""
    try:
        audio = elevenlabs_client.text_to_speech.convert(
            text=message,
            voice_id="EXAVITQu4vr4xnSDxMaL",  # Rachel voice ID
            model_id="eleven_multilingual_v2"
        )
        # Convert generator to bytes
        audio_bytes = b"".join(audio)
        return audio_bytes
    except Exception as e:
        print(f"Error generating audio: {str(e)}")
        return None

# Tools for the agent
ticket_price_tool = StructuredTool.from_function(
    func=get_ticket_price,
    name="get_ticket_price",
    description="Get the price of a return ticket to the destination city.",
)

artist_tool = StructuredTool.from_function(
    func=artist,
    name="artist",
    description="Generate an image of a vacation for any city to help the user visualize their destination. Use this to show customers what their vacation destination looks like.",
)

# Create the agent
agent = create_agent(
    model=llm,
    tools=[ticket_price_tool, artist_tool],
    system_prompt=SYSTEM_PROMPT,
)

# Helper function to add user message to chatbot
def put_message_in_chatbot(message, history):
    return "", history + [{"role": "user", "content": message}]

# Chat function to manage LLM calls
def chat(history):
    global last_generated_image
    history_messages = [{"role": h["role"], "content": h["content"]} for h in history]
    
    state = agent.invoke({"messages": history_messages})
    
    # Get the last message for the response
    last = state["messages"][-1]
    reply = ""
    
    # Extract content from the message
    if hasattr(last, "content"):
        reply = last.content
    elif isinstance(last, dict):
        reply = last.get("content", "")
    else:
        reply = str(last)
    
    # Add assistant reply to history
    history += [{"role": "assistant", "content": reply}]
    
    # Generate voice/audio from the reply
    voice = talker(reply)
    
    # Use the image generated by the artist function (if any)
    image = last_generated_image
    
    return history, voice, image

# Launch the chat interface
if __name__ == "__main__":
    with gr.Blocks() as ui:
        gr.Markdown("# FlightAI Assistant")
        gr.Markdown("Ask me about ticket prices to various destinations!")
        
        with gr.Row():
            chatbot = gr.Chatbot(height=500)
            image_output = gr.Image(height=500, interactive=False)
        
        with gr.Row():
            audio_output = gr.Audio(autoplay=True)
        
        with gr.Row():
            message = gr.Textbox(label="Chat with our AI Assistant:", placeholder="Type your message here...")
        
        # Hooking up events to callbacks
        message.submit(
            put_message_in_chatbot, 
            inputs=[message, chatbot], 
            outputs=[message, chatbot]
        ).then(
            chat, 
            inputs=chatbot, 
            outputs=[chatbot, audio_output, image_output]
        )
    
    ui.launch(inbrowser=True)
