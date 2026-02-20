import os
from dotenv import load_dotenv
from google import genai

# Limpiar variables que puedan interferir
if "GOOGLE_API_KEY" in os.environ:
    del os.environ["GOOGLE_API_KEY"]

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
model_name = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')

print(f"Testing Gemini with model: {model_name}")
print(f"Using API Key: {api_key[:10]}...")

try:
    # Forzar el uso de la API KEY específica
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_name,
        contents="Hola, ¿estás funcionando?"
    )
    print("Success!")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Failed with error: {e}")
