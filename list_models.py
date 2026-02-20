import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
print(f"Using API Key: {api_key[:10]}...")

try:
    client = genai.Client(api_key=api_key)
    print("Listing models...")
    for model in client.models.list():
        print(f"- {model.name} (Supported: {model.supported_methods})")
except Exception as e:
    print(f"Failed to list models: {e}")
