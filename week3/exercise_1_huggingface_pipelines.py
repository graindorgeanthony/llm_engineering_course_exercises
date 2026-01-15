# Imports

import torch
from huggingface_hub import login
from transformers import pipeline
from diffusers import DiffusionPipeline
from datasets import load_dataset
import soundfile as sf
from IPython.display import Audio

import os
from dotenv import load_dotenv

load_dotenv(override=True)

hf_token = os.getenv('HF_TOKEN')

# Pipelines (use Tasks tags in HuggingFace to find the correct pipeline, example: https://huggingface.co/models?pipeline_tag=translation&sort=downloads)
simple_sentiment_analysis_pipeline      = pipeline("sentiment-analysis", device="mps")
good_sentiment_analysis_pipeline        = pipeline("sentiment-analysis", model="nlptown/bert-base-multilingual-uncased-sentiment", device="mps")
translation_pipeline                    = pipeline("translation_en_to_fr", model="Helsinki-NLP/opus-mt-en-fr", device="mps")
ner_pipeline                            = pipeline("ner", device="mps")
question_answering_pipeline             = pipeline("question-answering", device="mps")
summarization_pipeline                  = pipeline("summarization", device="mps")
classification_pipeline                 = pipeline("zero-shot-classification", device="mps")
text_generation_pipeline                = pipeline("text-generation", device="mps")
synthesis_pipeline                      = pipeline("text-to-speech", model="microsoft/speecht5_tts", device="mps")

# Sentiment Analysis
def sentiment_analysis(text):
    return simple_sentiment_analysis_pipeline(text), good_sentiment_analysis_pipeline(text)

# Translation
def translation(text):
    return translation_pipeline(text)

# Named Entity Recognition
def named_entity_recognition(text):
    return ner_pipeline(text)

# Question Answering
def question_answering(question, context):
    return question_answering_pipeline(question=question, context=context)

# Summarization
def summarization(text):
    return summarization_pipeline(text, max_length=50, min_length=25, do_sample=False)[0]['summary_text']

# Zero-Shot Classification
def zero_shot_classification(text, labels):
    return classification_pipeline(text, candidate_labels=labels)

# Text Generation
def text_generation(prompt):
    return text_generation_pipeline(prompt)[0]['generated_text']

# Text to Speech
def text_to_speech(text):
    embeddings_dataset = load_dataset("matthijs/cmu-arctic-xvectors", split="validation", trust_remote_code=True)
    speaker_embedding = torch.tensor(embeddings_dataset[7306]["xvector"]).unsqueeze(0)
    speech = synthesis_pipeline(text, forward_params={"speaker_embeddings": speaker_embedding})
    sf.write("speech.wav", speech["audio"], speech["sampling_rate"])
    return speech

#print(sentiment_analysis("I should be more excited to be on the way to LLM mastery!"))
#print(translation("I should be more excited to be on the way to LLM mastery!"))
#print(named_entity_recognition("My name is Anthony G., learning LLM engineering and building a LLM application."))
#print(question_answering("What is my name?", "Name: Anthony G.; Address: 123 Main St; City: New York; State: NY; Zip: 10001;"))
text = """
The Hugging Face transformers library is an incredibly versatile and powerful tool for natural language processing (NLP).
It allows users to perform a wide range of tasks such as text classification, named entity recognition, and question answering, among others.
It's an extremely popular library that's widely used by the open-source data science community.
It lowers the barrier to entry into the field by providing Data Scientists with a productive, convenient way to work with transformer models.
"""
#print(summarization(text))
#print(zero_shot_classification(text, labels=["technology", "math", "history", "art", "music", "literature", "philosophy", "religion", "other"]))
#print(text_generation("Once upon a time, there was a"))
#text_to_speech("Hi to an artificial intelligence engineer, on the way to mastery!")