import os
from dotenv import load_dotenv
from openai import OpenAI

# Load API key & config.
load_dotenv(override=True)
api_key = os.getenv('OPENROUTER_API_KEY')

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=api_key,
)

# Call the LLM
completion = client.chat.completions.create(
  model="google/gemini-2.5-flash",
  messages=[
    {
        "role":"system",
        "content":[{
            "type":"text",
            "text":"Answer in a funny way."
        }]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "You toss 2 coins. One of them is heads. What's the probability the other is tails? Answer with the probability only."
        }
      ]
    }
  ],
  reasoning_effort="high"
)

# Print the response
print(completion.choices[0].message.content)