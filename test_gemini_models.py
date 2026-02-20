
import os
import time
import json
from google import genai
from google.genai import types
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load API Key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ ERROR: GEMINI_API_KEY environment variable not set.")
    exit(1)

client = genai.Client(api_key=api_key)

models_to_test = [
    "gemini-2.0-flash",
    "gemini-1.5-pro", 
    "gemini-1.5-flash"
]

test_prompt = """
Actúa como un experto agente de viajes. Analiza el siguiente mensaje de un cliente y extrae la información en formato JSON.
El cliente dice: "Hola, quiero viajar a Miami desde Caracas el próximo viernes con mi esposa y mis dos hijos, uno de 5 años y otro de 15. Queremos regresar en dos semanas."
Asume que hoy es viernes 14 de febrero de 2025.

Devuelve un JSON con:
- origin (código IATA)
- destination (código IATA)
- departure_date (YYYY-MM-DD)
- return_date (YYYY-MM-DD)
- passengers (número total)
- adults (cantidad)
- children (cantidad)
- infants (cantidad)

Solo responde con el JSON.
"""

print(f"🚀 Iniciando prueba de modelos Gemini...\n")
print(f"📅 Fecha simulada: Viernes 14 de Febrero 2025")
print(f"📝 Prompt de prueba:\n{test_prompt}\n")
print("-" * 60)

results = []

for model_name in models_to_test:
    print(f"🔄 Probando modelo: {model_name}...")
    start_time = time.time()
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=test_prompt,
            config=types.GenerateContentConfig(
                temperature=0.1
            )
        )
        end_time = time.time()
        duration = end_time - start_time
        
        response_text = response.text.strip()
        
        # Intentar parsear JSON para validar estructura
        try:
            # Limpiar markdown si existe
            json_str = response_text.replace("```json", "").replace("```", "").strip()
            parsed_json = json.loads(json_str)
            valid_json = True
            
            # Validar lógica básica
            pax_ok = parsed_json.get('passengers') == 4
            dates_ok = parsed_json.get('departure_date') == "2025-02-21" # Próximo viernes desde 14 feb
            
            quality_score = "✅ Correcto" if (pax_ok and dates_ok) else "⚠️ Lógica cuestionable"
            
        except json.JSONDecodeError:
            valid_json = False
            quality_score = "❌ JSON Inválido"

        print(f"⏱️ Tiempo: {duration:.2f}s")
        print(f"📊 Resultado: {quality_score}")
        print(f"📄 Respuesta:\n{response_text[:200]}...") # Mostrar primeros 200 chars
        
        results.append({
            "model": model_name,
            "time": duration,
            "quality": quality_score,
            "valid_json": valid_json,
            "response_snippet": response_text
        })
        
    except Exception as e:
        print(f"❌ Error con {model_name}: {str(e)}")
        results.append({
            "model": model_name,
            "time": 0,
            "quality": "❌ Error",
            "valid_json": False,
            "error": str(e)
        })
    
    print("-" * 60)

# Resumen Final
print("\n🏆 RESUMEN DE RESULTADOS 🏆")
print(f"{'Modelo':<20} | {'Tiempo (s)':<10} | {'Calidad':<20}")
print("-" * 55)

best_model = None
best_score = -1

for r in results:
    print(f"{r['model']:<20} | {r['time']:<10.2f} | {r['quality']:<20}")
    
    # Simple scoring: Valid JSON is priority, then speed logic could apply but let's stick to correctness
    if r['quality'] == "✅ Correcto":
        # Prefer speed if correct
        if best_model is None or r['time'] < best_score:
            best_model = r['model']
            best_score = r['time']
            
print("-" * 55)

if best_model:
    print(f"\n🌟 RECOMENDACIÓN: El modelo más rápido y correcto fue: {best_model}")
else:
    print("\n⚠️ Ningún modelo pasó todas las pruebas lógicas perfectamente. Revisa los detalles.")
