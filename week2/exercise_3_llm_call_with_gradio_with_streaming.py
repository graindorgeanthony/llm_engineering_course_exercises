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

# Call the LLM
def streaming_gpt(prompt):
  messages=[
    {"role":"system","content":[{"type":"text","text":system_message}]},
    {"role": "user","content": [{"type": "text","text": prompt}]}
  ]
  stream = client.chat.completions.create(
    model="llama3.2",
    messages=messages,
    stream=True
  )
  result = ""
  for chunk in stream:
    result += chunk.choices[0].delta.content or ""
    yield result

message_input = gr.Textbox(label="Your message:", info="Enter a message that will be sent to a llama 3.2", lines=5)
message_output = gr.Markdown(label="Response:")

gr.Interface(
  fn=streaming_gpt,
  title="Send a message to an LLM",
  inputs=[message_input],
  outputs=[message_output],
  examples=["Hello!", "Tell me a joke", "What are the secrets to happiness?"],
  flagging_mode="never"
).launch(
  inbrowser=True
)