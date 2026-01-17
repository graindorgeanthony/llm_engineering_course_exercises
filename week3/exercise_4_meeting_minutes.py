import os
import requests
from IPython.display import Markdown, display, update_display
from openai import OpenAI
from huggingface_hub import login
from transformers import AutoTokenizer, AutoModelForCausalLM, TextStreamer, BitsAndBytesConfig
from transformers import pipeline
import torch
from mlx_lm import load, generate
import base64
import os
from dotenv import load_dotenv

load_dotenv(override=True)

hf_token = os.getenv('HF_TOKEN')
login(hf_token, add_to_git_credential=True)

LLAMA = "meta-llama/Llama-3.2-3B-Instruct"
AUDIO_MODEL = "google/gemini-3-flash-preview"
AUDIO_FILE_NAME = "./denver_extract.mp3"

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=OPENROUTER_API_KEY,
)

# Transcribe audio using OpenAI Whisper or Google Gemini

def transcribe_audio(audio_file_path, type="opensource"):
    if type == "opensource":
        transcription_pipeline = pipeline(
            "automatic-speech-recognition",
            model="openai/whisper-medium.en",
            dtype=torch.float32,
            device='mps',
            return_timestamps="chunk", 
            chunk_length_s=30,
            stride_length_s=5,
        )
        result = transcription_pipeline(audio_file_path)
        return result
    elif type == "closedsource":
        # Note: The Gemini model CAN provide the meeting minutes directly, but for demonstration purposes, I asked it to transcribe the audio first.
        audio_file = open(audio_file_path, "rb")
        transcription = client.chat.completions.create(
            model=AUDIO_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                    {
                        "type": "text",
                        "text": "Transcribe the audio into text. Return only the text, no other text or formatting."
                    },
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": base64.b64encode(audio_file.read()).decode("utf-8"),
                            "format": "mp3"
                        }
                    }
                    ]
                }
            ]
        )
        return transcription.choices[0].message.content

transcription = transcribe_audio(AUDIO_FILE_NAME, "closedsource")


# Generate meeting minutes using LLaMA

system_message = """
You produce minutes of meetings from transcripts, with summary, key discussion points,
takeaways and action items with owners, in markdown format without code blocks.
"""

user_prompt = f"""
Below is an extract transcript of a Denver council meeting.
Please write minutes in markdown without code blocks, including:
- a summary with attendees, location and date
- discussion points
- takeaways
- action items with owners

Transcription:
{transcription}
"""

messages = [
    {"role": "system", "content": system_message},
    {"role": "user", "content": user_prompt}
]

MODEL = "meta-llama/Llama-3.2-1B-Instruct"

model, tokenizer = load(MODEL, tokenizer_config={"trust_remote_code": True}, model_config={"quantize": {"group_size": 64, "bits": 4}})

formatted_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
response = generate(model, tokenizer, prompt=formatted_text, verbose=False)

print(response)