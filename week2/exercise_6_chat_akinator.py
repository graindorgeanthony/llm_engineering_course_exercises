from openai import OpenAI
import gradio as gr

# Load API key & config.
client = OpenAI(
  base_url="http://localhost:11434/v1",
  api_key="ollama",
)

system_message = """You are playing an inverse Akinator game. You have a specific word in mind: 'superman' (NEVER disclose it). 

Your role:
- The user will ask you yes/no questions to try to guess the word
- You MUST only answer with "Yes" or "No" based on whether the question correctly describes the word
- NEVER reveal the word directly, even if asked directly
- If the user correctly guesses the word, congratulate them and confirm they won
- If this is the first message in the conversation, explain the game rules to the user

Response format:
- For yes/no questions: Answer only "Yes" or "No"
- For direct guesses: If correct, congratulate them. If incorrect, say "No"
- For non-yes/no questions: Politely redirect them to ask yes/no questions
- Keep all responses brief and focused

Example:
You: Hello! Welcome to the Inverse Akinator game. To play, you'll be asking me yes/no questions about a secret word, and I'll answer with either "Yes" or "No". The goal is to guess the word before I do. Go ahead and ask your first question!
User: Is it a woman?
You: No
User: Does he have superpowers?
You: Yes
...
"""

# Call the LLM
def streaming_gpt(message, history):

    contextual_system_message = system_message
    if 'superman' in message.lower():
        contextual_system_message += "Tell the user that he discovered the sercret word and won the game. Houra!"

    system = [{"role":"system","content":system_message}]
    history_messages = [{"role":h["role"],"content":h["content"]} for h in history]
    user = [{"role": "user","content": message}]
    
    
    messages = system + history_messages + user
    
    stream = client.chat.completions.create(
        model="llama3.2",
        messages=messages,
        stream=True
    )
    result = ""
    for chunk in stream:
        result += chunk.choices[0].delta.content or ""
        yield result

gr.ChatInterface(
  fn=streaming_gpt
).launch(
  inbrowser=True
)