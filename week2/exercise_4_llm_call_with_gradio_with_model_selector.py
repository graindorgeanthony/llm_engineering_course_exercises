import os
from unittest import result
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr

# Load API key & config.
load_dotenv(override=True)
api_key = os.getenv('OPENROUTER_API_KEY')

client = OpenAI(
  base_url="http://localhost:11434/v1",
  api_key="ollama",
)

system_message = "You are an helpfull assistant that responses in markdown, without code blocks."

# Function to call the LLM with streaming
def streaming_model(prompt, model):
  messages=[
    {"role":"system","content":[{"type":"text","text":system_message}]},
    {"role": "user","content": [{"type": "text","text": prompt}]}
  ]
  stream = client.chat.completions.create(
    model=model,
    messages=messages,
    stream=True
  )
  result = ""
  for chunk in stream:
    result += chunk.choices[0].delta.content or ""
    yield result

# Inputs & outputs
message_input = gr.Textbox(label="Your message:", info="Enter a message that will be sent to a llama 3.2", lines=5)
model_selector = gr.Dropdown(choices=["llama3.2", "gemma3:4b"])
message_output = gr.Markdown(label="Response:")

# Gradio interface
gr.Interface(
  fn=streaming_model,
  title="Send a message to an LLM",
  inputs=[message_input, model_selector],
  outputs=[message_output],
  examples=[
    ["Hello!", "llama3.2"],
    ["Tell me a joke", "llama3.2"],
    ["What are the secrets to happiness?", "llama3.2"],
  ],
  flagging_mode="never"
).launch(
  inbrowser=True
)