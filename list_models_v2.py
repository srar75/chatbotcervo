import os
from dotenv import load_dotenv
from google import genai

# Prioritize GEMINI_API_KEY and don't let GOOGLE_API_KEY interfere
load_dotenv()
if "GOOGLE_API_KEY" in os.environ:
    del os.environ["GOOGLE_API_KEY"]

api_key = os.getenv('GEMINI_API_KEY')
print(f"Using API Key: {api_key[:10]}...")

try:
    client = genai.Client(api_key=api_key)
    print("Listing models...")
    for model in client.models.list():
        # The attribute name might be slightly different depending on the version
        # Try a safer way to print attributes
        attrs = [attr for attr in dir(model) if not attr.startswith('_')]
        print(f"- {model.name}")
except Exception as e:
    print(f"Failed to list models: {e}")
