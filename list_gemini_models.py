"""  
Script para listar modelos disponibles de Gemini
"""
import os
import sys
from dotenv import load_dotenv

# Configurar UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Cargar variables de entorno
load_dotenv()

try:
    from google import genai
    
    api_key = os.getenv('GEMINI_API_KEY')
    print(f"API Key: {api_key[:20]}...")
    
    client = genai.Client(api_key=api_key)
    
    print("\n=== MODELOS DISPONIBLES ===\n")
    
    # Listar modelos
    models = client.models.list()
    
    for model in models:
        if hasattr(model, 'name'):
            print(f"✓ {model.name}")
            if hasattr(model, 'supported_generation_methods'):
                methods = model.supported_generation_methods
                if methods:
                    print(f"  Métodos: {', '.join(methods)}")
    
    print("\n=== MODELOS RECOMENDADOS PARA generateContent ===\n")
    for model in models:
        if hasattr(model, 'name') and hasattr(model, 'supported_generation_methods'):
            if 'generateContent' in (model.supported_generation_methods or []):
                print(f"✓ {model.name}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
