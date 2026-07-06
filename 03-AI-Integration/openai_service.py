import os
from dotenv import load_dotenv
from google import genai
from openai import OpenAI

load_dotenv()

gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

openrouter_client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY")
)
