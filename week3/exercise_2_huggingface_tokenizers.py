from huggingface_hub import login
from transformers import AutoTokenizer

import os
from dotenv import load_dotenv

load_dotenv(override=True)

hf_token = os.getenv('HF_TOKEN')

login(hf_token, add_to_git_credential=True)

# Tokenizer for base models
tokenizer = AutoTokenizer.from_pretrained('meta-llama/Meta-Llama-3.1-8B', trust_remote_code=True)

text = "Hello, how are you?"
token_ids = tokenizer.encode(text)
tokens = tokenizer.decode(token_ids)
token_batch = tokenizer.batch_decode(token_ids)
added_vocab = tokenizer.get_added_vocab()
len_vocab = len(tokenizer.vocab)

print(f"Token IDs encoded: {tokenizer.encode(text)}")
print(f"Tokens sentence decoded: {tokenizer.decode(tokenizer.encode(text))}")
print(f"Token list decoded: {token_batch}")
print(f"Added Vocab: {added_vocab}")
print(f"Length of Vocab: {len_vocab}")

# Tokenizer for instruct/chat models
# As we will see, the tokenizer simply transform the messages into a single prompt that can be used by the model.
tokenizer = AutoTokenizer.from_pretrained('meta-llama/Meta-Llama-3.1-8B-Instruct', trust_remote_code=True)

messages = [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Tell a light-hearted joke for a room of Data Scientists"}
  ]

prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
print(f"Prompt: {prompt}")

# Other tokenizer
PHI4 = "microsoft/Phi-4-mini-instruct"
DEEPSEEK = "deepseek-ai/DeepSeek-V3.1"
QWEN_CODER = "Qwen/Qwen2.5-Coder-7B-Instruct"

phi4_tokenizer = AutoTokenizer.from_pretrained(PHI4, trust_remote_code=True)
deepseek_tokenizer = AutoTokenizer.from_pretrained(DEEPSEEK, trust_remote_code=True)
qwen_coder_tokenizer = AutoTokenizer.from_pretrained(QWEN_CODER, trust_remote_code=True)

print(f"Phi-4: {phi4_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)}")
print(f"DeepSeek: {deepseek_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)}")
print(f"Qwen-Coder: {qwen_coder_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)}")