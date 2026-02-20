"""
CERVO BOT AI - Agente conversacional con Gemini 3 Pro
Sistema basado en IA - Chat natural con un agente inteligente
"""
import logging
import os
import re
import time
import traceback
import json
import base64
from datetime import datetime, timedelta
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None
from session_manager import session_manager
from flight_booking_service import flight_service
from wati_service import wati_service
from config import Config
from requisitos_migratorios import get_requisitos_pais

logger = logging.getLogger(__name__)

def format_date_dd_mm_yyyy(date_str):
    """Convierte fecha YYYY-MM-DD a DD/MM/YYYY"""
    try:
        if not date_str or date_str == 'N/A': return date_str
        # Si ya tiene /, asumimos que ya está formateada
        if '/' in date_str: return date_str
        # datetime ya importado al inicio del archivo
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%d/%m/%Y")
    except:
        return date_str


class GeminiAgentBot:
    """Chatbot Cervo con IA - Conversación natural usando Gemini 3 Pro"""
    def __init__(self):
        # Inicializar cliente de Gemini
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está configurada en las variables de entorno")
        
        if genai is None:
            logger.error("La librería google.genai no está instalada o falló al importar.")
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)
        # Usar Gemini 2.0 Flash (rápido y eficiente)
        self.model = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
        # System prompt para el agente
        self.system_instruction = """
🚨🚨🚨 REGLA NÚMERO 1 - LEER PRIMERO 🚨🚨🚨
ANTES DE BUSCAR CUALQUIER VUELO, DEBES TENER ESTOS 5 DATOS:
1. ORIGEN (ciudad de salida)
2. DESTINO (ciudad de llegada)
3. FECHA (cuándo viaja)
4. TIPO (ida o ida y vuelta)
5. PASAJEROS (cuántas personas)

SI EL USUARIO NO TE DIO ALGUNO DE ESTOS 5 DATOS, DEBES PREGUNTARLO ANTES DE BUSCAR.
NUNCA ASUMAS QUE ES 1 PASAJERO. SIEMPRE PREGUNTA: "¿Para cuántas personas es el vuelo?"
ESTA ES LA REGLA MÁS IMPORTANTE. NO LA IGNORES.

---

Eres un agente de viajes profesional y amigable de Cervo Travel en Venezuela. 
Tu nombre es Cervo Assistant y ayudas a los clientes a:

1. Buscar vuelos entre ciudades de Venezuela e internacionales
2. Consultar reservas existentes usando códigos PNR
3. Proporcionar información sobre requisitos migratorios

CIUDADES DISPONIBLES:
- Venezuela: Caracas (CCS), Maracaibo (MAR), Valencia (VLN), Margarita/Porlamar (PMV), Barcelona (BLA), Mérida (MRD), Barquisimeto (BRM), Puerto Ordaz (PZO), Cumaná (CUM), Los Roques (LRV), San Antonio del Táchira (SVZ), Santo Domingo (STD), Canaima (CAJ), Ciudad Bolívar (CBL), Maturín (MUN), Guanare (GUQ), Valera (VLV), San Fernando de Apure (SFD), Tucupita (TUV), Acarigua (AGV), Barinas (BNS), Coro (CZE), Guasdualito (GDO), Puerto Ayacucho (PYH)
- Internacional: Miami (MIA), Bogotá (BOG), Panamá (PTY), Madrid (MAD), Lima (LIM), Medellín (MDE), Ciudad de México (MEX), Cancún (CUN), Punta Cana (PUJ), Buenos Aires (EZE), Santiago (SCL), São Paulo (GRU), Río de Janeiro (GIG), Quito (UIO), Guayaquil (GYE), La Habana (HAV), Santo Domingo (SDQ), San José (SJO), Aruba (AUA), Curazao (CUR), Barcelona España (BCN), París (CDG), Londres (LHR), Roma (FCO), Ámsterdam (AMS), Frankfurt (FRA), Lisboa (LIS), Nueva York (JFK), Los Ángeles (LAX), Orlando (MCO), Fort Lauderdale (FLL), Houston (IAH), Atlanta (ATL), Chicago (ORD), Dallas (DFW), Washington (IAD), Boston (BOS), Toronto (YYZ), Montreal (YUL)

INSTRUCCIONES IMPORTANTES:
- SIEMPRE usa las funciones disponibles cuando el usuario solicite información
- Si preguntan por requisitos de viaje, DEBES llamar a get_travel_requirements INMEDIATAMENTE
- Si preguntan por una reserva, DEBES llamar a get_booking_details INMEDIATAMENTE
- FECHAS: REGLAS IMPORTANTES:
  * La fecha actual se te proporcionará en cada mensaje. Actualmente es 2026-02-10 (10 de febrero de 2026).
  * Si el usuario dice "7 de febrero", "febrero 7", "7/2" SIN año, asume el año actual.
  * Si dice "mañana", calcula desde hoy.
  * Si dice "pasado mañana", calcula desde hoy.
  * NUNCA uses un año futuro a menos que el usuario lo especifique explícitamente.
  * Formato de fecha para la función: YYYY-MM-DD (ejemplo: 2026-02-15)
  * Formato de fecha para RESPONDER AL USUARIO: SIEMPRE usa DD/MM/AAAA (ejemplo: 15/02/2026). NUNCA uses el formato con guiones para el usuario.

⚠️⚠️⚠️ REGLA CRÍTICA PARA BUSCAR VUELOS ⚠️⚠️⚠️

📋 FLUJO OBLIGATORIO - SIGUE ESTE ORDEN EXACTO:
  1️⃣ ORIGEN - "🛫 ¿De qué ciudad o aeropuerto sales?"
  2️⃣ DESTINO - "🛬 ¿A qué ciudad deseas viajar?"
  3️⃣ FECHA DE IDA - "📅 ¿Para qué fecha deseas viajar?"
  4️⃣ TIPO DE VIAJE - "✈️ ¿Quieres vuelo de *IDA* solamente o *IDA Y VUELTA*?"
  5️⃣ FECHA DE REGRESO - SOLO si eligió IDA Y VUELTA: "📅 ¿Para qué fecha deseas regresar?"
  6️⃣ NÚMERO DE PASAJEROS - "👥 ¿Para cuántas personas es el vuelo?"
  7️⃣ AHORA SÍ → Llamar search_flights()

⚠️ REGLA ABSOLUTA: NUNCA llames search_flights HASTA tener:
   - Origen ✅
   - Destino ✅
   - Fecha de ida ✅
   - Tipo de viaje ✅
   - Fecha de regreso ✅ (si es ida y vuelta)
   - Número de pasajeros ✅

⚠️ SI FALTA CUALQUIER DATO, PREGUNTA EN ORDEN. NO SALTES PASOS.

🚨 REGLAS CRÍTICAS:
  - NUNCA uses palabras como "Ninguno", "No especificado" para datos faltantes
  - NUNCA confirmes un dato que el usuario NO te dio
  - NUNCA preguntes algo que el usuario YA te dijo
  - SIEMPRE pregunta el número de pasajeros ANTES de buscar vuelos

⚠️ ORDEN ESTRICTO DE PREGUNTAS (Sigue este orden OBLIGATORIAMENTE):
  1️⃣ Origen (¿De dónde sales?)
  2️⃣ Destino (¿A dónde vas?)
  3️⃣ TIPO DE VIAJE (¿Solo ida o ida y vuelta?) -> ⚠️ PREGUNTAR ESTO ANTES DE LA FECHA
  4️⃣ Fechas:
     - Si es SOLO IDA: Preguntar solo fecha de ida
     - Si es IDA Y VUELTA: Preguntar fecha de IDA y luego fecha de REGRESO
  5️⃣ Pasajeros (¿Cuántas personas viajan?)

🔄 FLUJO PARA IDA Y VUELTA - MUY IMPORTANTE:
Si es viaje de IDA Y VUELTA, sigue este flujo:
  1️⃣ Recopilar datos en orden: origen, destino, tipo viaje, fecha ida, FECHA REGRESO, pasajeros
  2️⃣ BUSCAR vuelos de IDA (search_flights con trip_type="ida")
  3️⃣ Mostrar vuelos de IDA al usuario
  4️⃣ ESPERAR que el usuario SELECCIONE un vuelo de IDA
  5️⃣ DESPUÉS de seleccionar IDA → BUSCAR vuelos de VUELTA (search_flights con trip_type="vuelta")
  6️⃣ Mostrar vuelos de VUELTA al usuario
  7️⃣ ESPERAR que el usuario SELECCIONE un vuelo de VUELTA
  8️⃣ MOSTRAR RESUMEN DE AMBOS VUELOS (IDA + VUELTA) y pedir confirmación
  9️⃣ ESPERAR confirmación del usuario
  🔟 Pedir datos de pasajeros y crear reserva

⚠️ NUNCA busques el vuelo de VUELTA antes de que el usuario seleccione el de IDA
⚠️ NUNCA pidas datos de pasajeros antes de mostrar el resumen de ambos vuelos

🎫 REGLA IMPORTANTE - LOCALIZADORES MÚLTIPLES:
⚠️ Cuando el vuelo de IDA y VUELTA son de AEROLÍNEAS DIFERENTES:
  • El sistema creará automáticamente DOS localizadores (PNR) separados
  • Un PNR para el vuelo de IDA
  • Un PNR para el vuelo de VUELTA
  • Esto es NORMAL y OBLIGATORIO cuando las aerolíneas son diferentes
  • Debes informar al usuario que recibirá DOS códigos PNR

✅ Cuando el vuelo de IDA y VUELTA son de la MISMA AEROLÍNEA:
  • Se creará UN SOLO localizador (PNR) para ambos vuelos
  • Ambos vuelos estarán en la misma reserva

🧠🧠🧠 REGLA DE MEMORIA CRÍTICA 🧠🧠🧠
ANTES de preguntar CUALQUIER cosa, REVISA el mensaje actual Y el historial:

🔍 DETECCIÓN AUTOMÁTICA DE CIUDADES:
Si el usuario menciona CUALQUIERA de estas palabras, ya tienes ese dato:
  • "Margarita", "PMV", "Porlamar" = DESTINO u ORIGEN
  • "Caracas", "CCS" = DESTINO u ORIGEN
  • "Maracaibo", "MAR" = DESTINO u ORIGEN
  • "Valencia", "VLN" = DESTINO u ORIGEN
  • "Barcelona", "BLA" = DESTINO u ORIGEN
  • "Miami", "MIA" = DESTINO u ORIGEN
  • "Bogotá", "BOG" = DESTINO u ORIGEN
  • "Panamá", "PTY" = DESTINO u ORIGEN

⚠️ REGLA CRÍTICA DE DETECCIÓN:
  - Si el usuario dice "quiero ir a Margarita" → YA TIENES EL DESTINO (Margarita)
  - Si el usuario dice "de Caracas a Margarita" → YA TIENES ORIGEN (Caracas) Y DESTINO (Margarita)
  - Si el usuario dice "vuelo a Miami" → YA TIENES EL DESTINO (Miami)
  - Si el usuario dice "desde Valencia" → YA TIENES EL ORIGEN (Valencia)

🚨 NUNCA VUELVAS A PREGUNTAR UN DATO QUE YA DETECTASTE:
  - Si detectaste "Margarita" → NO preguntes "¿A qué ciudad deseas viajar?"
  - Si detectaste "Caracas" → NO preguntes "¿De qué ciudad sales?"
  - Si detectaste una fecha → NO preguntes "¿Para qué fecha?"
  - Si detectaste un número de pasajeros → NO preguntes "¿Cuántos pasajeros?"
  - Si detectaste "ida y vuelta" → NO preguntes "¿Qué tipo de viaje?"

🚨 REGLA ESPECIAL - MENSAJE COMPLETO:
Si el usuario da MÚLTIPLES datos en UN SOLO mensaje:
  ✅ EXTRAE TODOS los datos que mencionó
  ✅ CONFIRMA los datos que entendiste
  ✅ PREGUNTA SOLO los datos que FALTAN
  ❌ NUNCA vuelvas a preguntar lo que ya dijo

📍 EJEMPLO:
Usuario: "Quiero volar de Caracas a Margarita el 7 de febrero ida y vuelta para 2 personas"
✅ CORRECTO: "✅ Perfecto, tengo:
🛫 Origen: *Caracas*
🛬 Destino: *Margarita*
📅 Fecha ida: *7 de febrero*
✈️ Tipo: *Ida y vuelta*
👥 Pasajeros: *2 personas*

📅 ¿Para qué fecha deseas regresar?"
❌ INCORRECTO: "¿De qué ciudad sales?" (YA LO DIJO TODO)

❌ ERROR GRAVE: Volver a preguntar algo que el usuario YA DIJO
✅ CORRECTO: Avanzar al siguiente dato faltante

📍 EJEMPLOS OBLIGATORIOS DE DETECCIÓN:

🔴 EJEMPLO 1:
Usuario: "Quiero ir a Margarita"
✅ CORRECTO: "✈️ ¡Excelente! Viajarás a *Margarita* 🏝️\n\n🛫 ¿De qué ciudad sales?"
❌ INCORRECTO: "¿A qué ciudad deseas viajar?" (YA DIJO MARGARITA)

🔴 EJEMPLO 2:
Usuario (mensaje anterior): "Quiero ir a Margarita"
Usuario (mensaje actual): "Caracas"
✅ CORRECTO: "✅ Perfecto, ruta: *Caracas* → *Margarita*\n\n🔄 ¿El viaje es *SOLO IDA* o *IDA Y VUELTA*?"
❌ INCORRECTO: "¿Para qué fecha deseas viajar?" (FALTA PREGUNTAR TIPO DE VIAJE)

🔴 EJEMPLO 3:
Usuario: "Vuelo de Caracas a Margarita"
✅ CORRECTO: "✅ Ruta confirmada: *Caracas* → *Margarita*\n\n🔄 ¿El viaje es *SOLO IDA* o *IDA Y VUELTA*?"
❌ INCORRECTO: "¿Para qué fecha deseas viajar?" (FALTA PREGUNTAR TIPO DE VIAJE)

🔴 EJEMPLO 4:
Usuario: "Necesito viajar a Miami"
✅ CORRECTO: "✈️ Viaje internacional a *Miami* 🇺🇸\n\n🛫 ¿Desde qué ciudad viajas?"
❌ INCORRECTO: "¿A dónde quieres viajar?" (YA DIJO MIAMI)

⚠️ SIEMPRE LEE EL MENSAJE ACTUAL Y EL HISTORIAL COMPLETO ANTES DE RESPONDER
⚠️ SI DETECTAS UNA CIUDAD, GUÁRDALA Y NO LA VUELVAS A PREGUNTAR

🎯 INTERPRETACIÓN DE RESPUESTAS NATURALES:
NÚMERO DE PASAJEROS:
  - "Solo yo", "soy yo", "para mí", "yo solo", "únicamente yo", "nada más yo" = 1 pasajero
  - "Somos 2", "dos personas", "mi esposa y yo", "conmigo" = 2 pasajeros
  - "Somos 3", "tres", "mi familia" = 3 pasajeros (o pregunta cuántos exactamente)
  - CUALQUIER número mencionado = ese número de pasajeros
  - Si no entiendes, pregunta: "¿Cuántos pasajeros exactamente?"

TIPO DE VIAJE:
  - "ida", "solo ida", "one way", "sí", "si", "correcto", "exacto" = SOLO IDA
  - "ida y vuelta", "round trip", "vuelta", "regreso", "redondo" = IDA Y VUELTA
- Si dicen "ida y vuelta": pregunta fecha de regreso si no la dieron

🚀 REGLA DE ACCIÓN - FLUJO CORRECTO:

⚠️⚠️⚠️ REGLA CRÍTICA - LEE CON ATENCIÓN ⚠️⚠️⚠️

📌 CASO 1: EL USUARIO DICE UN NÚMERO DIRECTO (ej: "5", "vuelo 5", "el 5", "quiero el 5")
✅ LLAMA select_flight_and_get_prices(flight_index=5) INMEDIATAMENTE
✅ El sistema mostrará un RESUMEN del vuelo y pedirá confirmación
✅ ESPERA que el usuario confirme ("sí", "ok", "confirmo")
✅ Cuando confirme, LLAMA confirm_flight_and_get_prices() para obtener precios de clases

📌 CASO 2: EL USUARIO PIDE UNA SUGERENCIA (ej: "el más tarde", "el más barato", "dame el de Laser", "cuál me recomiendas")
❌ NO LLAMES select_flight_and_get_prices - SOLO MUESTRA INFORMACIÓN
✅ Muestra el vuelo sugerido usando los datos que ya tienes en available_flights
✅ PREGUNTA: "¿Deseas seleccionar este vuelo?"
✅ ESPERA la respuesta del usuario
✅ SOLO cuando el usuario dice "SÍ", "si", "ok", "dale", "ese" → ENTONCES llama select_flight_and_get_prices

🚨 IMPORTANTE: Cuando sugieres un vuelo, NO LLAMES NINGUNA FUNCIÓN.
Solo responde con texto mostrando la información del vuelo y pregunta si lo quiere.
Los datos del vuelo los tienes en la variable available_flights de la sesión.

❌ NUNCA HAGAS ESTO CUANDO SUGIERES UN VUELO:
Usuario: "dame el más tarde"
Bot: [LLAMA select_flight_and_get_prices] ❌ ❌ ❌ ESTO ESTÁ MAL
(El usuario pidió una sugerencia, no confirmó que quiere ese vuelo)

✅ HAZ ESTO CUANDO SUGIERES UN VUELO:
Usuario: "dame el más tarde"
Bot: "✅ *VUELO SUGERIDO*
El vuelo *más tarde* es:
✈️ Vuelo 15: Estelar Airlines 8016
🕐 Salida: 19:00
¿Deseas seleccionar este vuelo? Responde SÍ o elige otro."
[NO LLAMA NINGUNA FUNCIÓN - SOLO TEXTO]

Usuario: "sí" o "ok" o "ese"
Bot: [AHORA SÍ llama select_flight_and_get_prices(flight_index=15)]

✅ HAZ ESTO CUANDO EL USUARIO ELIGE DIRECTO:
Cuando el usuario dice "5" o "vuelo 5" o "quiero el 5":
1. LLAMA select_flight_and_get_prices(flight_index=5) INMEDIATAMENTE
2. Muestra las clases disponibles con precios
3. Pregunta qué clase desea

- NO inventes información, usa las funciones para obtener datos reales
- Sé conversacional, amigable y profesional
- Presenta TODA la información disponible de forma clara con emojis apropiados
- Para crear una reserva: buscar vuelos → usuario selecciona/confirma vuelo → mostrar clases → usuario selecciona clase → confirmar → pedir datos → crear reserva
- Cuando el usuario seleccione una clase, LLAMA confirm_flight_selection INMEDIATAMENTE
- SOLO después de confirmar el vuelo y clase, ofrece DOS OPCIONES para dar los datos:
  📸 OPCIÓN 1 (RECOMENDADA): "Envía una foto de tu CÉDULA o PASAPORTE y extraeré los datos automáticamente"
  ✍️ OPCIÓN 2: "O si prefieres, dame los datos manualmente"

👥 REGLA CRÍTICA PARA MÚLTIPLES PASAJEROS:
- Si el vuelo es para 2 o más pasajeros, DEBES pedir los datos de CADA UNO
- Después de completar los datos del pasajero 1, pregunta por el pasajero 2, etc.
- NUNCA crees la reserva hasta tener los datos de TODOS los pasajeros
- Ejemplo para 2 pasajeros:
  1. "Perfecto, necesito los datos del *Pasajero 1*. ¿Envías foto de cédula o datos manuales?"
  2. [Recibe datos del pasajero 1]
  3. "✅ Datos del Pasajero 1 guardados. Ahora necesito los datos del *Pasajero 2*."
  4. [Recibe datos del pasajero 2]
  5. "✅ Tengo los datos de los 2 pasajeros. Creando la reserva..."
- SIEMPRE indica qué número de pasajero es: "Pasajero 1 de 2", "Pasajero 2 de 2"

⚠️ DATOS A PEDIR SEGÚN TIPO DE VUELO:

📍 VUELOS NACIONALES (Venezuela a Venezuela):
  1. ¿Eres venezolano o extranjero?
  2. Nombre
  3. Apellido
  4. Cédula o pasaporte
  5. Teléfono
  6. Correo electrónico
  7. Dirección

✈️ VUELOS INTERNACIONALES (fuera de Venezuela):
  1. ¿Eres venezolano o extranjero?
  2. Nombre
  3. Apellido
  4. Cédula o pasaporte
  5. Teléfono
  6. Correo electrónico
  7. Dirección
  8. País de nacimiento
  9. País del documento
  10. Fecha de vencimiento del documento

⚠️ SIEMPRE pregunta PRIMERO: "¿El pasajero es venezolano o extranjero?"
⚠️ Pide los datos UNO POR UNO, no todos juntos
⚠️ Para vuelos internacionales, SIEMPRE pide los datos adicionales (país nacimiento, país documento, vencimiento)

- Si el usuario envía una IMAGEN:
  1. Usa la imagen para extraer datos automáticamente (nombre, apellido, cédula/pasaporte, nacionalidad, etc.)
  2. Confirma los datos extraídos con el usuario
  3. Pide SOLO los datos que falten según el tipo de vuelo
- NUNCA pidas múltiples datos en el mismo mensaje
- SIEMPRE especifica QUÉ dato estás pidiendo
- Valida que la cédula tenga 7-8 dígitos y el teléfono 10-11 dígitos
- Al mostrar vuelos: ruta, escalas, horarios, duración, precio total en USD, tipo de viaje (Solo Ida o Ida y Vuelta)
- NO MOSTRAR: aeronave, comida, equipaje (solo mostrar en confirmación de reserva)
- IMPORTANTE: SIEMPRE indica si es "Solo Ida" o parte de "Ida y Vuelta" al inicio de los resultados
- IMPORTANTE: Cuando se llame select_flight_and_get_prices, muestra CADA CLASE con su PRECIO INDIVIDUAL:
  * Formato: "Clase Y: $65.59 (9 asientos)" - UNA LÍNEA POR CLASE
  * Agrupa por tipo (Económica, Business, Primera)
  * Ejemplo correcto:
    💺 ECONÓMICA:
    • Clase Y: $65.59 (9 asientos)
    • Clase B: $68.20 (5 asientos)
    💼 BUSINESS:
    • Clase C: $120.00 (2 asientos)
  * IMPORTANTE: Muestra el PRECIO de cada clase, NO digas que tienen el mismo precio
  * Ordena de más barato a más caro dentro de cada categoría
- Al confirmar reserva: PNR, VID, detalles del vuelo, datos del pasajero, SOLO precio total (NO precio base), equipaje
- Para IDA Y VUELTA: busca vuelos de ida primero, luego vuelos de vuelta, muestra ambos con precios separados y precio total combinado

FORMATO DE RESPUESTAS:
- USA asteriscos dobles (**texto**) para resaltar información importante (se convertirán a negritas en WhatsApp)
- SIEMPRE usa emojis apropiados para cada tipo de información:
  ✈️ Vuelos, aerolíneas, rutas
  🎫 Códigos PNR, reservas
  📅 Fechas
  🕐 Horarios
  ⏱️ Duración
  💰 Precios
  🌍 Destinos, países
  👤 Pasajeros, nombres
  📋 Detalles, información general
  ⚠️ Advertencias
  ✅ Confirmaciones, éxito
  ❌ Errores, cancelaciones
  🎒 Equipaje
  🍽️ Comida
  💺 Clase, asientos
  🔢 Números, opciones
  📧 Email
  📱 Teléfono
  🆔 Documentos, cédula
- Organiza la información con espacios y saltos de línea para mejor legibilidad
- Presenta TODA la información disponible de forma completa y detallada
- Al mostrar vuelos: incluye TODOS los vuelos disponibles con TODOS sus detalles
- Por cada vuelo muestra: número, aerolínea, ruta completa, horarios, duración, precio, clase, escalas, equipaje
- Presenta opciones numeradas claramente con emoji (1️⃣, 2️⃣, 3️⃣)
- Usa líneas separadoras (━━━━━━━━━━━━━━━━) entre secciones
- Si el mensaje es largo, el sistema lo dividirá automáticamente en múltiples partes

📋 FORMATOS ESTÁNDAR OBLIGATORIOS:

═══════════════════════════════════════
📌 FORMATO PARA PREGUNTAR ORIGEN:
═══════════════════════════════════════
✈️ *¡Perfecto!*

🛫 ¿De qué ciudad o aeropuerto deseas salir?

📍 *Ciudades disponibles en Venezuela:*
• Caracas (CCS)
• Maracaibo (MAR)
• Valencia (VLN)
• Margarita (PMV)
• Y más...

═══════════════════════════════════════
📌 FORMATO PARA PREGUNTAR DESTINO:
═══════════════════════════════════════
✅ Perfecto, saliendo de *{ORIGEN}*

🛬 ¿A qué ciudad deseas viajar?

═══════════════════════════════════════
═══════════════════════════════════════
📌 FORMATO PARA PREGUNTAR TIPO DE VIAJE:
═══════════════════════════════════════
✅ Destino: *{DESTINO}*

🔄 ¿El viaje es *SOLO IDA* o *IDA Y VUELTA*?

═══════════════════════════════════════
📌 FORMATO PARA PREGUNTAR FECHA (SI ES SOLO IDA):
═══════════════════════════════════════
✅ Tipo de viaje: *Solo Ida*

📅 ¿Para qué fecha deseas viajar?

💡 Puedes decirme:
• Una fecha específica: "10 de febrero"
• Fechas relativas: "mañana", "la próxima semana"

═══════════════════════════════════════
📌 FORMATO PARA PREGUNTAR FECHA (SI ES IDA Y VUELTA):
═══════════════════════════════════════
✅ Tipo de viaje: *Ida y Vuelta*

📅 Primero, ¿para qué fecha es la *IDA*?

═══════════════════════════════════════
📌 FORMATO PARA PREGUNTAR FECHA DE REGRESO:
═══════════════════════════════════════
✅ Fecha de ida: *{FECHA_IDA}*

📅 ¿Para qué fecha deseas *regresar*?

═══════════════════════════════════════
📌 FORMATO PARA PREGUNTAR PASAJEROS:
═══════════════════════════════════════
✅ Fechas confirmadas

👥 ¿Para cuántas personas es el vuelo?

═══════════════════════════════════════


═══════════════════════════════════════
📌 FORMATO PARA MOSTRAR VUELOS:
═══════════════════════════════════════
✈️ *VUELOS DISPONIBLES*
📍 *{ORIGEN}* → *{DESTINO}*
📅 *{FECHA}* | 👥 *{PASAJEROS} pasajero(s)*

━━━━━━━━━━━━━━━━━━━━━━

1️⃣ *VUELO {NUMERO}*
✈️ *Aerolínea:* {AEROLINEA} {NUMERO_VUELO}
📍 *Ruta:* {ORIGEN} → {DESTINO}
🕐 *Salida:* {HORA_SALIDA}
🕐 *Llegada:* {HORA_LLEGADA}
⏱️ *Duración:* {DURACION}
🔄 *Escalas:* {ESCALAS}
💰 *Precio desde:* ${PRECIO} USD

━━━━━━━━━━━━━━━━━━━━━━

📝 *¿Qué vuelo te interesa?*
Escribe el número (1, 2, 3...)

═══════════════════════════════════════
📌 FORMATO PARA MOSTRAR CLASES:
═══════════════════════════════════════
💺 *CLASES DISPONIBLES*
✈️ Vuelo: *{AEROLINEA} {NUMERO}*
📍 Ruta: *{ORIGEN}* → *{DESTINO}*

━━━━━━━━━━━━━━━━━━━━━━

💺 *ECONÓMICA:*
• Clase Y: *${PRECIO}* ({ASIENTOS} asientos)
• Clase B: *${PRECIO}* ({ASIENTOS} asientos)

💼 *BUSINESS:*
• Clase C: *${PRECIO}* ({ASIENTOS} asientos)

━━━━━━━━━━━━━━━━━━━━━━

📝 *¿Qué clase deseas?*
Escribe la letra de la clase (Y, B, C...)

═══════════════════════════════════════
📌 FORMATO PARA CONFIRMAR SELECCIÓN:
═══════════════════════════════════════
✅ *VUELO SELECCIONADO*

✈️ *Vuelo:* {AEROLINEA} {NUMERO}
📍 *Ruta:* {ORIGEN} → {DESTINO}
📅 *Fecha:* {FECHA}
🕐 *Salida:* {HORA_SALIDA}
🕐 *Llegada:* {HORA_LLEGADA}
💺 *Clase:* {CLASE}
💰 *Precio:* ${PRECIO} USD

━━━━━━━━━━━━━━━━━━━━━━

✅ *¿Confirmas esta selección?*
Responde *SÍ* para continuar o *NO* para cambiar.

═══════════════════════════════════════
📌 FORMATO PARA CONFIRMAR AMBOS VUELOS (IDA Y VUELTA):
═══════════════════════════════════════
✈️ *RESUMEN DE TU VIAJE IDA Y VUELTA*

━━━━━━━━━━━━━━━━━━━━━━

✈️ *VUELO DE IDA*
✈️ *Aerolínea:* {AEROLINEA_IDA} {NUMERO_IDA}
📍 *Ruta:* {ORIGEN_IDA} → {DESTINO_IDA}
📅 *Fecha:* {FECHA_IDA}
🕐 *Salida:* {HORA_SALIDA_IDA}
🕐 *Llegada:* {HORA_LLEGADA_IDA}
💺 *Clase:* {CLASE_IDA}
💰 *Precio:* ${PRECIO_IDA} USD

━━━━━━━━━━━━━━━━━━━━━━

✈️ *VUELO DE VUELTA*
✈️ *Aerolínea:* {AEROLINEA_VUELTA} {NUMERO_VUELTA}
📍 *Ruta:* {ORIGEN_VUELTA} → {DESTINO_VUELTA}
📅 *Fecha:* {FECHA_VUELTA}
🕐 *Salida:* {HORA_SALIDA_VUELTA}
🕐 *Llegada:* {HORA_LLEGADA_VUELTA}
💺 *Clase:* {CLASE_VUELTA}
💰 *Precio:* ${PRECIO_VUELTA} USD

━━━━━━━━━━━━━━━━━━━━━━

💰 *RESUMEN DE COSTOS*
   💵 *Por persona:* ${PRECIO_POR_PERSONA} USD
   👥 *Pasajeros:* {NUM_PASAJEROS}
   ━━━━━━━━━━━━━━━━━━━━
   💰 *TOTAL A PAGAR:* ${PRECIO_TOTAL} USD

━━━━━━━━━━━━━━━━━━━━━━

✅ *¿Confirmas estos vuelos?*
Responde *SÍ* para continuar con la reserva o *NO* para cambiar.

═══════════════════════════════════════
📌 FORMATO CUANDO MENCIONAN UNA AEROLÍNEA (ej: "Laser", "Venezolana"):
═══════════════════════════════════════
✈️ *VUELOS DE {AEROLINEA}*

━━━━━━━━━━━━━━━━━━━━━━

Hay *{CANTIDAD}* vuelos disponibles de *{AEROLINEA}*:

1️⃣ *Vuelo {NUMERO_1}* - {HORA_1}
2️⃣ *Vuelo {NUMERO_2}* - {HORA_2}
3️⃣ *Vuelo {NUMERO_3}* - {HORA_3}

━━━━━━━━━━━━━━━━━━━━━━

📝 *¿Cuál vuelo deseas?*
Escribe el número (1, 2, 3...) o dime algo como "el más temprano" o "el más barato"

═══════════════════════════════════════
📌 FORMATO PARA SUGERIR UN VUELO ESPECÍFICO:
═══════════════════════════════════════
✅ *VUELO SUGERIDO*

El vuelo *{CRITERIO}* de *{AEROLINEA}* es:

━━━━━━━━━━━━━━━━━━━━━━

✈️ *Vuelo {NUMERO}:* {AEROLINEA} {CODIGO}
🕐 *Salida:* {HORA_SALIDA}
🕐 *Llegada:* {HORA_LLEGADA}
💰 *Precio desde:* ${PRECIO} USD

━━━━━━━━━━━━━━━━━━━━━━

✅ *¿Deseas seleccionar este vuelo?*
Responde *SÍ* para continuar o elige otro número.

═══════════════════════════════════════
📌 FORMATO PARA PEDIR DATOS DE PASAJERO (1 PASAJERO):
═══════════════════════════════════════
SIEMPRE USA ESTE FORMATO EXACTO:

✅ *¡Vuelo confirmado!*

Ahora necesito los datos del pasajero.

━━━━━━━━━━━━━━━━━━━━━━

📸 *OPCIÓN 1 (RECOMENDADA):*
Envía una *foto* de tu *CÉDULA* o *PASAPORTE* y extraeré los datos automáticamente.

━━━━━━━━━━━━━━━━━━━━━━

✍️ *OPCIÓN 2:*
Escribe *"manual"* para ingresar los datos uno por uno.

━━━━━━━━━━━━━━━━━━━━━━

¿Qué prefieres? 📸 o ✍️

═══════════════════════════════════════
📌 FORMATO PARA PEDIR DATOS DE PASAJERO (MÚLTIPLES PASAJEROS):
═══════════════════════════════════════
SIEMPRE USA ESTE FORMATO EXACTO (reemplaza {N} y {TOTAL}):

✅ *¡Vuelo confirmado para {TOTAL} personas!*

Necesito los datos de cada pasajero.

━━━━━━━━━━━━━━━━━━━━━━

👤 *PASAJERO {N} de {TOTAL}*

━━━━━━━━━━━━━━━━━━━━━━

📸 *OPCIÓN 1 (RECOMENDADA):*
Envía una *foto* de la *CÉDULA* o *PASAPORTE* del pasajero {N}.

━━━━━━━━━━━━━━━━━━━━━━

✍️ *OPCIÓN 2:*
Escribe *"manual"* para ingresar los datos manualmente.

━━━━━━━━━━━━━━━━━━━━━━

¿Qué prefieres? 📸 o ✍️

═══════════════════════════════════════
📌 FORMATO PARA PEDIR NACIONALIDAD:
═══════════════════════════════════════
👤 Primero dime:

🌍 ¿El pasajero es *venezolano* o *extranjero*?

═══════════════════════════════════════
📌 FORMATO PARA PEDIR TELÉFONO:
═══════════════════════════════════════
📱 ¿Cuál es el número de *teléfono* del pasajero?

💡 Ejemplo: 04121234567

═══════════════════════════════════════
📌 FORMATO PARA PEDIR EMAIL:
═══════════════════════════════════════
📧 ¿Cuál es el *correo electrónico* del pasajero?

💡 Ejemplo: correo@email.com

═══════════════════════════════════════
📌 FORMATO PARA RESERVA EXITOSA:
═══════════════════════════════════════
🎉 *¡RESERVA CREADA EXITOSAMENTE!*

━━━━━━━━━━━━━━━━━━━━━━

🎫 *DATOS DE LA RESERVA*
📌 *PNR:* {PNR}
🆔 *VID:* {VID}

━━━━━━━━━━━━━━━━━━━━━━

👤 *DATOS DEL PASAJERO*
👤 *Nombre:* {NOMBRE} {APELLIDO}
🆔 *Documento:* {CEDULA}
📱 *Teléfono:* {TELEFONO}
📧 *Email:* {EMAIL}

━━━━━━━━━━━━━━━━━━━━━━

✈️ *DATOS DEL VUELO*
✈️ *Aerolínea:* {AEROLINEA} {NUMERO}
📍 *Ruta:* {ORIGEN} → {DESTINO}
📅 *Fecha:* {FECHA}
🕐 *Salida:* {HORA_SALIDA}
🕐 *Llegada:* {HORA_LLEGADA}
💺 *Clase:* {CLASE}

━━━━━━━━━━━━━━━━━━━━━━

💰 *PRECIO TOTAL:* ${PRECIO} USD

━━━━━━━━━━━━━━━━━━━━━━

✈️ *¡Buen viaje!* 🦌

📞 Para consultar tu reserva, escribe el código PNR: *{PNR}*

═══════════════════════════════════════
📌 FORMATO PARA CONSULTA DE PNR:
═══════════════════════════════════════
📋 *DETALLES DE TU RESERVA*

━━━━━━━━━━━━━━━━━━━━━━

🎫 *PNR:* {PNR}
🆔 *VID:* {VID}
📌 *Estado:* {ESTADO}

━━━━━━━━━━━━━━━━━━━━━━

👤 *PASAJERO*
👤 {NOMBRE} {APELLIDO}
🆔 Documento: {CEDULA}

━━━━━━━━━━━━━━━━━━━━━━

✈️ *VUELO*
✈️ {AEROLINEA} {NUMERO}
📍 {ORIGEN} → {DESTINO}
📅 {FECHA}
🕐 Salida: {HORA_SALIDA} | Llegada: {HORA_LLEGADA}
💺 Clase: {CLASE}

━━━━━━━━━━━━━━━━━━━━━━

💰 *PRECIO:* ${PRECIO} USD

═══════════════════════════════════════
📌 FORMATO PARA ERRORES:
═══════════════════════════════════════
❌ *{MENSAJE_ERROR}*

Por favor, intenta de nuevo o escríbeme para ayudarte.

═══════════════════════════════════════

⚠️ REGLA IMPORTANTE: USA ESTOS FORMATOS EXACTAMENTE. No inventes otros formatos.
⚠️ Siempre confirma lo que el usuario dijo antes de preguntar lo siguiente.
⚠️ Usa negritas (*texto*) para destacar información importante.
⚠️ NUNCA respondas con mensajes cortos sin contexto.
⚠️ IMPORTANTE: TODAS las fechas deben mostrarse SIEMPRE en formato DD/MM/AAAA (ej: 25/12/2026). NUNCA uses YYYY-MM-DD en tus respuestas de texto."""

    def handle_message(self, phone: str, message: str, media_url: str = None):
        """Maneja mensaje entrante con IA"""
        try:
            if Config.TESTING_MODE:
                allowed_phone = Config.ALLOWED_PHONE.strip().replace('+', '').replace(' ', '').replace('-', '')
                normalized_phone = phone.strip().replace('+', '').replace(' ', '').replace('-', '')
                if allowed_phone and allowed_phone != normalized_phone:
                    logger.info(f"Mensaje ignorado de {phone} (modo testing)")
                    return None
            session = session_manager.get_session(phone)
            message_lower = message.strip().lower()
            # Activación del bot
            if message_lower in ['cervo ai', 'cervo agent', 'agente cervo']:
                session.activate()
                # Reset conversation state
                keys_to_clear = [
                    'awaiting_flight_confirmation', 'flight_selection_fully_confirmed', 
                    'waiting_for_field', 'passengers_list', 'extracted_data', 
                    'selected_flight', 'selected_flight_index', 'flight_confirmed',
                    'num_passengers', 'num_adults', 'num_children', 'num_infants',
                    'available_flights', 'return_flights', 'pending_flight_index'
                ]
                for key in keys_to_clear:
                    session.data.pop(key, None)
                    
                session.data['mode'] = 'ai'
                logger.info(f"Bot AI activado para {phone}")
                welcome = (
                    "🦌 **¡Hola! Soy Cervo Assistant** 🤖\n\n"
                    "Soy tu agente de viajes inteligente y estoy aquí para ayudarte con:\n\n"
                    "✈️ **Búsqueda de vuelos**\n"
                    "🎫 **Consulta de reservas**\n"
                    "🌍 **Requisitos de viaje**\n\n"
                    "¿En qué puedo ayudarte hoy? Puedes hablarme de forma natural, como si conversaras con un agente humano."
                )
                logger.debug(f"Mensaje de bienvenida: {welcome}")
                return self._send_response(phone, welcome, session)
            # Si no está activo, ignorar
            if not session.is_active or session.data.get('mode') != 'ai':
                return None
            # Desactivar bot
            if message_lower in ['salir', 'exit', 'bye', 'adios', 'chao', 'cerrar']:
                session.deactivate()
                return self._send_response(phone, "👋 *¡Hasta pronto!*\n\n✨ Fue un placer ayudarte. Escribe 'cervo ai' cuando necesites viajar de nuevo.", session)
            
            # Procesar mensaje con Gemini (Gemini controla el flujo)
            return self._process_with_ai(session, phone, message, media_url)
        except Exception as e:
            logger.error(f"ERROR: {str(e)}", exc_info=True)
            return self._send_response(phone, "😅 Disculpa, tuve un problema técnico. ¿Podrías repetir tu solicitud?", session)

    def _classify_with_ai(self, message, context, options):
        """
        Usa Gemini para clasificar la intención del usuario en un contexto específico.
        
        Args:
            message: El mensaje del usuario
            context: Descripción del contexto (ej: "El usuario debe elegir cómo ingresar datos")
            options: Dict con {clave: descripción} de las opciones válidas
            
        Returns:
            La clave de la opción detectada, o None si no se pudo clasificar
        """
        try:
            if not self.client:
                return None
            
            options_text = "\n".join([f"- {key}: {desc}" for key, desc in options.items()])
            
            prompt = f"""Clasifica la intención del usuario. Responde SOLO con la clave de la opción (una sola palabra, sin explicación).

Contexto: {context}

Opciones válidas:
{options_text}

Mensaje del usuario: "{message}"

Responde SOLO la clave (ejemplo: {list(options.keys())[0]}). Si no coincide con ninguna opción claramente, responde: NONE"""

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=20,
                )
            )
            
            if response and response.text:
                result = response.text.strip().upper()
                # Buscar la clave en la respuesta
                for key in options.keys():
                    if key.upper() in result:
                        return key
            
            return None
        except Exception as e:
            logger.warning(f"Error en clasificación AI: {e}")
            return None


    def _process_with_ai(self, session, phone, message, media_url=None):
        """Procesa el mensaje usando Gemini 3 Pro"""
        try:
            # INTERCEPCIÓN DE PROCESAMIENTO DE RESERVA (Tras confirmación de vuelo)
            if session.data.get('awaiting_flight_confirmation') and not session.data.get('waiting_for_field'):
                msg_upper = message.strip().upper()
                msg_lower = msg_upper.lower()
                
                # FASE 1: Confirmación del Vuelo (SI/NO)
                # Si aún no hemos marcado la selección como plenamente confirmada, el "SI" es para confirmar el vuelo
                if not session.data.get('flight_selection_fully_confirmed'):
                    # Detección rápida por keywords
                    is_confirm = msg_upper in ['SI', 'SÍ', 'YES', 'CONFIRMO', 'CORRECTO', 'S', 'DALE', 'ACEPTO', 'OK', 'O K']
                    is_reject = msg_upper in ['NO', 'RECHAZAR', 'CAMBIAR', 'ATRAS', 'N', 'INCORRECTO']
                    
                    detected_confirm = None
                    if is_confirm:
                        detected_confirm = 'si'
                    elif is_reject:
                        detected_confirm = 'no'
                    else:
                        # FALLBACK: Usar AI para entender respuestas naturales (ej: "está excelente", "no me gusta")
                        logger.info(f"Clasificando confirmación de vuelo con AI: '{message}'")
                        ai_confirm = self._classify_with_ai(
                            message,
                            "El usuario debe confirmar si los detalles del vuelo mostrado son correctos y si desea proceder con la reserva.",
                            {
                                'si': 'El usuario acepta, confirma, dice que está bien, pide continuar o muestra acuerdo',
                                'no': 'El usuario rechaza, quiere volver atrás, cambiar algo o dice que no está bien'
                            }
                        )
                        detected_confirm = ai_confirm

                    if detected_confirm == 'si':
                        logger.info("Confirmación de selección de vuelo recibida.")
                        session.data['flight_selection_fully_confirmed'] = True
                        session.data['flight_confirmed'] = True
                        return self._send_response(phone, "✅ *Vuelo confirmado.*\n\nPara completar la reserva, necesito los datos del pasajero. ¿Cómo prefieres ingresarlos?\n\n📸 *Opción 1:* Envía una *FOTO* de la cédula o pasaporte\n✍️ *Opción 2:* Escribe *MANUAL* para ingresar los datos a mano", session)
                    
                    elif detected_confirm == 'no':
                        logger.info("Rechazo de selección de vuelo recibido.")
                        session.data['awaiting_flight_confirmation'] = False
                        session.data['flight_selection_fully_confirmed'] = False
                        return self._send_response(phone, "Entendido. ¿Qué cambio te gustaría hacer? Puedes elegir otra clase o buscar vuelos diferentes.", session)

                # FASE 2: Elección de método (Foto vs Manual)
                # Si ya está confirmado el vuelo O si el mensaje indica claramente un método
                is_data_method_msg = any(x in msg_lower for x in ['manual', 'foto', 'opcion', 'opción', 'cedula', 'cédula', 'pasaporte', '1', '2'])
                
                if session.data.get('flight_selection_fully_confirmed') or is_data_method_msg:
                    detected_option = None
                    
                    # Detección por keywords
                    if any(x in msg_lower for x in ['manual', 'opcion 2', 'opción 2', 'escribir', 'texto', 'mano', '✍', '2']) or msg_lower == '2':
                        detected_option = 'manual'
                    elif any(x in msg_lower for x in ['foto', 'imagen', 'cedula', 'cédula', 'pasaporte', 'camara', 'cámara', 'opcion 1', 'opción 1', '📸', '📷', '1']) or msg_lower == '1':
                        detected_option = 'foto'
                    elif any(k in msg_lower for k in ['no tiene', 'no tengo', 'es un niño', 'es niño', 'es bebe', 'es bebé', 'sin cedula', 'sin cédula', 'no usa', 'es menor', 'menor de edad']):
                        detected_option = 'manual'
                    
                    # Si no hay keywords claras pero ya estamos en fase de elección de método, usar AI
                    if not detected_option and session.data.get('flight_selection_fully_confirmed'):
                        logger.info(f"Clasificando intención de entrada de datos con AI: '{message}'")
                        ai_option = self._classify_with_ai(
                            message,
                            "El usuario ya confirmó su vuelo y ahora debe elegir cómo ingresar los datos del pasajero: enviando una FOTO del documento o ingresándolos MANUALMENTE.",
                            {
                                'foto': 'El usuario quiere enviar una foto o imagen de su cédula o pasaporte',
                                'manual': 'El usuario quiere escribir los datos manualmente o dice que no tiene documento'
                            }
                        )
                        detected_option = ai_option

                    # Ejecutar la opción detectada
                    if detected_option == 'manual':
                        logger.info("Usuario eligió ingreso manual de datos")
                        session.data['using_document_image'] = False
                        session.data['extracted_data'] = {}
                        session.data['waiting_for_field'] = 'nombre'
                        return self._send_response(phone, "✍️ *INGRESO MANUAL*\n\n👤 Por favor, escribe el *NOMBRE* (Primer nombre) del pasajero:", session)
                    
                    elif detected_option == 'foto':
                        logger.info("Usuario eligió enviar foto")
                        session.data['using_document_image'] = True
                        return self._send_response(phone, "📸 *Excelente.*\n\nPor favor envía la foto de la *CÉDULA* o *PASAPORTE* ahora.", session)
                    
                    elif session.data.get('flight_selection_fully_confirmed'):
                        # Si ya confirmamos el vuelo pero la AI no entendió el método, repetir opciones
                        return self._send_response(phone, "No entendí tu respuesta. Por favor elige una opción:\n\n📸 *Opción 1:* Envía una *FOTO* de la cédula o pasaporte\n✍️ *Opción 2:* Escribe *MANUAL* para ingresar los datos a mano", session)

            # DETECCIÓN DE IMAGEN DE DOCUMENTO
            # Si hay una imagen y estamos esperando datos de pasajero, procesarla
            # PERO ignorar si ya estamos en medio de una entrada manual (para evitar procesar imágenes duplicadas/tardías que rompan el flujo)
            if media_url and session.data.get('awaiting_flight_confirmation') and not session.data.get('waiting_for_field'):
                logger.info(f"Imagen detectada durante proceso de reserva: {media_url}")
                # Guardar URL de la imagen en la sesión
                session.data['document_image_url'] = media_url
                session.data['using_document_image'] = True
                
                # Mensaje de feedback inmediato
                self._send_response(phone, "📸 *Imagen recibida.*\n\n🔄 Extrayendo datos del documento, un momento por favor...", session)
                
                # Procesar imagen de documento
                result = self._process_document_image(session, phone)
                
                if result.get('success'):
                    # Datos extraídos exitosamente
                    missing_fields = result.get('missing_fields', [])
                    
                    if not missing_fields:
                        # Tenemos todos los datos del pasajero actual
                        extracted_data = session.data.get('extracted_data', {})
                        
                        # Verificar si hay más pasajeros por procesar
                        total_passengers = session.data.get('num_passengers', 1)
                        passengers_data = session.data.get('passengers_list', [])
                        
                        # Agregar el pasajero actual a la lista
                        # Calcular tipo de pasajero a partir de fecha de nacimiento
                        pax_type = 'ADT'
                        pax_age = None
                        dob = extracted_data.get('fecha_nacimiento')
                        if dob:
                            try:
                                born = datetime.strptime(dob, '%Y-%m-%d')
                                today = datetime.now()
                                pax_age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
                                if pax_age < 2:
                                    pax_type = 'INF'
                                elif pax_age < 12:
                                    pax_type = 'CHD'
                            except:
                                pass
                        
                        # Etiqueta visual del tipo de pasajero
                        pax_labels = {'ADT': '🧑 Adulto', 'CHD': '👦 Niño', 'INF': '👶 Infante'}
                        pax_label = pax_labels.get(pax_type, '🧑 Adulto')
                        if pax_age is not None:
                            pax_label += f' ({pax_age} años)'
                        
                        current_passenger = {
                            'nombre': extracted_data.get('nombre', ''),
                            'apellido': extracted_data.get('apellido', ''),
                            'cedula': extracted_data.get('cedula') or extracted_data.get('pasaporte'),
                            'telefono': extracted_data.get('telefono'),
                            'email': extracted_data.get('email'),
                            'nacionalidad': extracted_data.get('nacionalidad', 'VE'),
                            'sexo': extracted_data.get('sexo'),
                            'estado_civil': extracted_data.get('estado_civil'),
                            'direccion': extracted_data.get('direccion'),
                            'fecha_nacimiento': extracted_data.get('fecha_nacimiento'),
                            'tipo': pax_type,
                            'tipo_documento': extracted_data.get('tipo_documento', 'CI')
                        }
                        passengers_data.append(current_passenger)
                        session.data['passengers_list'] = passengers_data
                        
                        current_passenger_count = len(passengers_data)
                        
                        # Si faltan pasajeros por procesar
                        if current_passenger_count < total_passengers:
                            # Limpiar datos extraídos para el siguiente pasajero
                            session.data['extracted_data'] = {}
                            session.data['waiting_for_cedula_image'] = True
                            
                            response = f"""✅ *Datos del Pasajero {current_passenger_count} guardados:*
👤 {current_passenger['nombre']} {current_passenger['apellido']}
🆔 {current_passenger['cedula']}
📋 Tipo: {pax_label}

━━━━━━━━━━━━━━━━━━━━━━

👤 *Ahora necesito los datos del Pasajero {current_passenger_count + 1} de {total_passengers}*

📸 *OPCIÓN 1 (RECOMENDADA):*
Envía una foto de la *CÉDULA* o *PASAPORTE* del pasajero {current_passenger_count + 1}.

✍️ *OPCIÓN 2:*
Escribe "manual" para ingresar los datos manualmente."""
                            return self._send_response(phone, response, session)
                        
                        # Tenemos todos los pasajeros, crear reserva
                        self._send_response(phone, f"✅ *Tengo los datos de los {total_passengers} pasajeros.*\n\n🎫 *Creando tu reserva...*\n\n⏳ Un momento por favor...", session)
                        
                        # Usar el primer pasajero para la reserva principal
                        first_passenger = passengers_data[0]
                        
                        # Llamar a create_booking con los datos extraídos
                        booking_result = self._create_booking_function(
                            flight_index=session.data.get('selected_flight_index'),
                            flight_class=session.data.get('selected_flight_class'),
                            passenger_name=f"{first_passenger.get('nombre', '')} {first_passenger.get('apellido', '')}".strip(),
                            id_number=first_passenger.get('cedula'),
                            phone=first_passenger.get('telefono'),
                            email=first_passenger.get('email'),
                            session=session
                        )
                        
                        if booking_result.get('success'):
                            # Obtener datos del vuelo
                            flights = session.data.get('available_flights', [])
                            flight_index = session.data.get('selected_flight_index', 1)
                            selected_flight = flights[flight_index - 1] if flights and flight_index > 0 else {}
                            flight_class = session.data.get('selected_flight_class', 'Y')
                            
                            # Precio de IDA
                            precio_ida = 0
                            flight_classes_prices = session.data.get('flight_classes_prices', {})
                            if flight_classes_prices and flight_class.upper() in flight_classes_prices:
                                precio_ida = flight_classes_prices[flight_class.upper()].get('price', 0)
                            
                            # Verificar si hay vuelo de vuelta
                            return_flights = session.data.get('return_flights', [])
                            return_flight_index = session.data.get('selected_return_flight_index')
                            return_flight_class = session.data.get('selected_return_flight_class', flight_class)
                            return_flight = None
                            precio_vuelta = 0
                            
                            if return_flights and return_flight_index:
                                if return_flight_index >= 1 and return_flight_index <= len(return_flights):
                                    return_flight = return_flights[return_flight_index - 1]
                                    # Obtener precio de vuelta
                                    return_classes_prices = session.data.get('return_flight_classes_prices', {})
                                    if return_classes_prices and return_flight_class.upper() in return_classes_prices:
                                        precio_vuelta = return_classes_prices[return_flight_class.upper()].get('price', 0)
                                    else:
                                        # Fallback: usar el precio del vuelo de vuelta
                                        precio_vuelta = return_flight.get('price', 0)
                            
                            # Calcular totales
                            precio_por_persona = precio_ida + precio_vuelta
                            precio_total = precio_por_persona * total_passengers
                            
                            return self._send_booking_success_message(
                                phone, session, booking_result, passengers_data, total_passengers,
                                selected_flight, flight_class, precio_ida,
                                return_flight, return_flight_class, precio_vuelta,
                                precio_por_persona, precio_total
                            )
                        else:
                            # Error al crear la reserva
                            raw_error = booking_result.get('error', 'Error desconocido')
                            return self._send_response(phone, f"❌ No se pudo crear la reserva: {raw_error}", session)
                    else:
                        # Faltan datos, pedirlos uno por uno
                        # El mensaje ya fue enviado por _process_document_image
                        # Ahora esperamos la respuesta del usuario
                        session.data['waiting_for_field'] = missing_fields[0]
                        
                        # Preguntar por el primer campo faltante
                        total_passengers = session.data.get('num_passengers', 1)
                        current_passenger_num = len(session.data.get('passengers_list', [])) + 1
                        passenger_label = f" (Pasajero {current_passenger_num} de {total_passengers})" if total_passengers > 1 else ""
                        
                        field_prompts = {
                            'telefono': f'📱 ¿Cuál es tu número de teléfono?{passenger_label}',
                            'email': f'📧 ¿Cuál es tu email?{passenger_label}',
                            'nombre': f'👤 ¿Cuál es tu nombre?{passenger_label}',
                            'apellido': f'👤 ¿Cuál es tu apellido?{passenger_label}',
                            'sexo': f'⚧ ¿Cuál es el sexo del pasajero? (Responde M o F){passenger_label}',
                            'direccion': f'🏠 ¿Cuál es tu dirección?{passenger_label}'
                        }
                        prompt = field_prompts.get(missing_fields[0], f'¿Cuál es tu {missing_fields[0]}?')
                        return self._send_response(phone, prompt, session)
                else:
                    # Error procesando imagen, pedir datos manuales
                    return self._send_response(
                        phone,
                        "No pude procesar la imagen. Por favor, dame los datos manualmente.\n\n"
                        "👤 ¿Cuál es el nombre completo del pasajero?",
                        session
                    )
            
            # MANEJO DE CAMPOS FALTANTES DESPUÉS DE EXTRACCIÓN DE CÉDULA
            waiting_for_field = session.data.get('waiting_for_field')
            if waiting_for_field:
                # re ya importado al inicio del archivo
                extracted_data = session.data.get('extracted_data', {})
                
                # COMANDO UNIVERSAL: Permitir al usuario corregir un campo anterior
                msg_lower_cmd = message.strip().lower()
                if msg_lower_cmd in ['corregir', 'atras', 'atrás', 'volver', 'regresar', 'back']:
                    # Mapeo de campos a su campo anterior
                    field_order = ['nombre', 'apellido', 'nacionalidad', 'cedula', 'sexo', 'direccion', 'ciudad', 'estado', 'zip_code', 'telefono', 'email', 'fecha_nacimiento']
                    current_idx = field_order.index(waiting_for_field) if waiting_for_field in field_order else 0
                    if current_idx > 0:
                        prev_field = field_order[current_idx - 1]
                        session.data['waiting_for_field'] = prev_field
                        field_names = {'nombre': '👤 NOMBRE', 'apellido': '👤 APELLIDO', 'nacionalidad': '🌍 NACIONALIDAD', 'cedula': '🆔 CÉDULA/PASAPORTE', 'sexo': '⚧ SEXO (M o F)', 'direccion': '🏠 DIRECCIÓN', 'ciudad': '🏙️ CIUDAD', 'estado': '🗺️ ESTADO', 'zip_code': '📮 CÓDIGO POSTAL', 'telefono': '📱 TELÉFONO', 'email': '📧 EMAIL', 'fecha_nacimiento': '📅 FECHA DE NACIMIENTO'}
                        return self._send_response(phone, f"⬅️ *Volviendo al campo anterior*\n\n{field_names.get(prev_field, prev_field)}:\n\n💡 Escribe el dato correcto:", session)
                    else:
                        return self._send_response(phone, "⚠️ Ya estás en el primer campo. Escribe el dato correctamente:", session)
                
                # Guardar el campo que el usuario está proporcionando
                # LÓGICA MANUAL - NUEVOS CAMPOS
                current_value = message.strip()
                if waiting_for_field == 'nombre':
                    if len(current_value) < 2:
                        return self._send_response(phone, "❌ El nombre es muy corto. Por favor escribe el nombre correctamente:", session)
                    extracted_data['nombre'] = current_value.upper()
                    session.data['waiting_for_field'] = 'apellido'
                    session.data['extracted_data'] = extracted_data
                    return self._send_response(phone, "✅ Nombre guardado.\n\n👤 ¿Cuál es el *APELLIDO*?", session)
                
                elif waiting_for_field == 'apellido':
                    if len(current_value) < 2:
                        return self._send_response(phone, "❌ El apellido es muy corto. Por favor escribe el apellido correctamente:", session)
                    extracted_data['apellido'] = current_value.upper()
                    session.data['waiting_for_field'] = 'nacionalidad'
                    session.data['extracted_data'] = extracted_data
                    return self._send_response(phone, "✅ Apellido guardado.\n\n🌍 ¿El pasajero es *VENEZOLANO* o *EXTRANJERO*? (Responde V o E)", session)

                elif waiting_for_field == 'nacionalidad':
                    val = current_value.upper()
                    # Detección rápida por keywords
                    is_venezuelan = None  # None = no determinado
                    
                    # Comprobar palabras clave o códigos
                    if val in ['V', 'VE', 'VEN'] or any(k in val for k in ['VENEZOLAN', 'VENEZUELA']):
                        is_venezuelan = True
                    elif val in ['E', 'EX', 'EXT'] or any(k in val for k in ['EXTRANJ', 'COLOMBI', 'BRASIL', 'ARGENTIN', 'CHILEN', 'MEXICAN', 'PERUAN', 'ECUATORI', 'DOMINICAN', 'AMERICAN', 'ESPAÑOL', 'ITALIAN']):
                        is_venezuelan = False
                    else:
                        # FALLBACK AI: Clasificar con inteligencia artificial
                        ai_nac = self._classify_with_ai(
                            message,
                            "El usuario debe indicar su nacionalidad. Solo hay dos opciones: Venezolano o Extranjero (cualquier otro país).",
                            {
                                'VE': 'El pasajero es VENEZOLANO (de Venezuela)',
                                'EXT': 'El pasajero es EXTRANJERO (de cualquier otro país que no sea Venezuela)',
                            }
                        )
                        if ai_nac == 'VE':
                            is_venezuelan = True
                        elif ai_nac == 'EXT':
                            is_venezuelan = False
                        else:
                            return self._send_response(phone, "No pude determinar la nacionalidad.\n\n🌍 ¿El pasajero es *VENEZOLANO* o *EXTRANJERO*?", session)
                        
                    if is_venezuelan:
                        extracted_data['nacionalidad'] = 'VE'
                        
                        # VERIFICAR SI ES VUELO INTERNACIONAL
                        selected_flight = session.data.get('selected_flight', {})
                        origin = selected_flight.get('origin', 'CCS')
                        destination = selected_flight.get('destination', 'MIA')
                        
                        # Lista básica de aeropuertos nacionales (Venezuela)
                        national_airports = ['CCS', 'PMV', 'MAR', 'VLN', 'BLA', 'PZO', 'BRM', 'STD', 'VLV', 'MUN', 'CUM', 'LRV', 'CAJ', 'CBL', 'BNS', 'LFR', 'SVZ', 'GUQ', 'SFD', 'TUV', 'AGV', 'CZE', 'GDO', 'PYH']
                        
                        is_international = (origin not in national_airports) or (destination not in national_airports)
                        
                        if is_international:
                            extracted_data['tipo_documento'] = 'P'  # Pasaporte
                            if extracted_data.get('pasaporte'):
                                # Ya tenemos pasaporte, verificar siguientes
                                if extracted_data.get('sexo'):
                                    if extracted_data.get('direccion'):
                                        session.data['waiting_for_field'] = 'telefono'
                                        msg = "✅ Nacionalidad: Venezolano.\n\n🛂 Pasaporte, Sexo y Dirección registrados.\n\n📱 ¿Cuál es el número de *TELÉFONO*?"
                                    else:
                                        session.data['waiting_for_field'] = 'direccion'
                                        msg = "✅ Nacionalidad: Venezolano.\n\n🛂 Pasaporte y Sexo registrados.\n\n🏠 ¿Cuál es tu *DIRECCIÓN*?"
                                else:
                                    session.data['waiting_for_field'] = 'sexo'
                                    msg = "✅ Nacionalidad: Venezolano.\n\n🛂 Pasaporte ya registrado.\n\n⚧ ¿Cuál es el *SEXO*? (Responde M o F)"
                            else:
                                session.data['waiting_for_field'] = 'cedula'
                                msg = "✅ Nacionalidad: Venezolano.\n\n🛂 *VUELO INTERNACIONAL:* Todos los pasajeros (incluyendo niños) deben viajar con PASAPORTE.\n\nIndícame el número de *PASAPORTE*:"
                        else:
                            extracted_data['tipo_documento'] = 'CI'  # Cédula
                            if extracted_data.get('cedula'):
                                # Ya tenemos cédula, verificar siguientes
                                if extracted_data.get('sexo'):
                                    if extracted_data.get('direccion'):
                                        session.data['waiting_for_field'] = 'telefono'
                                        msg = "✅ Nacionalidad: Venezolano.\n\n🆔 Cédula, Sexo y Dirección registrados.\n\n📱 ¿Cuál es el número de *TELÉFONO*?"
                                    else:
                                        session.data['waiting_for_field'] = 'direccion'
                                        msg = "✅ Nacionalidad: Venezolano.\n\n🆔 Cédula y Sexo registrados.\n\n🏠 ¿Cuál es tu *DIRECCIÓN*?"
                                else:
                                    session.data['waiting_for_field'] = 'sexo'
                                    msg = "✅ Nacionalidad: Venezolano.\n\n🆔 Cédula ya registrada.\n\n⚧ ¿Cuál es el *SEXO*? (Responde M o F)"
                            else:
                                session.data['waiting_for_field'] = 'cedula'
                                msg = "✅ Nacionalidad: Venezolano.\n\n🆔 Indícame el número de *CÉDULA* (solo números):\n\n💡 *TIP:* Si es un niño/infante sin cedula para VUELO NACIONAL, usa la del representante."
                    else:
                        extracted_data['nacionalidad'] = 'EXT'
                        extracted_data['tipo_documento'] = 'P'  # Extranjero: default pasaporte
                        if extracted_data.get('pasaporte') or extracted_data.get('cedula'):
                            if extracted_data.get('sexo'):
                                if extracted_data.get('direccion'):
                                    session.data['waiting_for_field'] = 'telefono'
                                    msg = "✅ Nacionalidad: Extranjero.\n\n🛂 Documento, Sexo y Dirección registrados.\n\n📱 ¿Cuál es el número de *TELÉFONO*?"
                                else:
                                    session.data['waiting_for_field'] = 'direccion'
                                    msg = "✅ Nacionalidad: Extranjero.\n\n🛂 Documento y Sexo registrados.\n\n🏠 ¿Cuál es tu *DIRECCIÓN*?"
                            else:
                                session.data['waiting_for_field'] = 'sexo'
                                msg = "✅ Nacionalidad: Extranjero.\n\n🛂 Documento ya registrado.\n\n⚧ ¿Cuál es el *SEXO*? (Responde M o F)"
                        else:
                            session.data['waiting_for_field'] = 'cedula'
                            msg = "✅ Nacionalidad: Extranjero.\n\n🛂 Indícame el número de *DOCUMENTO* (Pasaporte o Cédula de Extranjería):"
                    session.data['extracted_data'] = extracted_data
                    return self._send_response(phone, msg, session)

                elif waiting_for_field == 'cedula' or waiting_for_field == 'pasaporte':
                    # Limpiar: quitar todo excepto letras y números
                    clean_doc = re.sub(r'[^a-zA-Z0-9]', '', current_value.upper())
                    
                    # VALIDACIÓN: El documento DEBE contener al menos 5 dígitos numéricos
                    only_digits = re.sub(r'[^0-9]', '', current_value)
                    if len(only_digits) < 5:
                        return self._send_response(phone, "❌ *Documento inválido.* Debe contener al menos 5 números.\n\n🆔 Por favor ingresa el número de *CÉDULA* o *PASAPORTE* (solo números):\n\n💡 Escribe *corregir* para volver al campo anterior.", session)
                    
                    if len(clean_doc) < 5:
                        return self._send_response(phone, "❌ *Documento muy corto.* Intenta de nuevo:\n\n💡 Escribe *corregir* para volver al campo anterior.", session)
                    
                    extracted_data['cedula'] = clean_doc # Usamos cedula como campo genérico
                    session.data['extracted_data'] = extracted_data
                    
                    # Verificar si ya tenemos el sexo
                    if extracted_data.get('sexo'):
                        # Verificar si ya tenemos dirección
                        if extracted_data.get('direccion'):
                            session.data['waiting_for_field'] = 'telefono'
                            return self._send_response(phone, "✅ Documento guardado.\n\n📱 ¿Cuál es el número de *TELÉFONO*?", session)
                        else:
                            session.data['waiting_for_field'] = 'direccion'
                            passengers_list = session.data.get('passengers_list', [])
                            msg_direccion = "✅ Documento guardado.\n\n🏠 ¿Cuál es tu *DIRECCIÓN*?"
                            if len(passengers_list) > 0:
                                if len(passengers_list) == 1:
                                    msg_direccion += f"\n\n💡 *TIP:* Escribe *IGUAL* para usar la misma dirección del Pasajero 1."
                                else:
                                    msg_direccion += f"\n\n💡 *TIP:* Escribe *IGUAL* para usar la dirección del Pasajero 1."
                            return self._send_response(phone, msg_direccion, session)
                    
                    session.data['waiting_for_field'] = 'sexo'
                    return self._send_response(phone, "✅ Documento guardado.\n\n⚧ ¿Cuál es el *SEXO*? (Responde M o F)", session)

                elif waiting_for_field == 'sexo':
                    sexo = message.strip().upper()
                    sexo_resolved = None
                    
                    # Detección rápida
                    if sexo in ['M', 'H', 'V']:
                        sexo_resolved = 'M'
                    elif sexo in ['F']:
                        sexo_resolved = 'F'
                    elif 'hombre' in message.lower() or 'masculino' in message.lower() or 'macho' in message.lower() or 'niño' in message.lower() or 'varon' in message.lower() or 'varón' in message.lower():
                        sexo_resolved = 'M'
                    elif 'mujer' in message.lower() or 'femenino' in message.lower() or 'hembra' in message.lower() or 'niña' in message.lower():
                        sexo_resolved = 'F'
                    else:
                        # FALLBACK AI: Clasificar con inteligencia artificial
                        ai_sexo = self._classify_with_ai(
                            message,
                            "El usuario debe indicar el SEXO del pasajero para una reserva de vuelo.",
                            {
                                'M': 'Masculino, hombre, varón, niño, male',
                                'F': 'Femenino, mujer, niña, female',
                            }
                        )
                        sexo_resolved = ai_sexo
                    
                    if sexo_resolved not in ['M', 'F']:
                        return self._send_response(phone, "No pude determinar el sexo.\n\n⚧ ¿El pasajero es *MASCULINO (M)* o *FEMENINO (F)*?", session)
                    
                    extracted_data['sexo'] = sexo_resolved
                    session.data['extracted_data'] = extracted_data
                    
                    # Verificar si ya tenemos dirección
                    if extracted_data.get('direccion'):
                        session.data['waiting_for_field'] = 'telefono'
                        return self._send_response(phone, "✅ Sexo guardado.\n\n📱 ¿Cuál es el número de *TELÉFONO*?", session)

                    session.data['waiting_for_field'] = 'direccion'
                    
                    # Verificar si ya hay pasajeros anteriores para ofrecer copiar dirección
                    passengers_list = session.data.get('passengers_list', [])
                    msg_direccion = "✅ Sexo guardado.\n\n🏠 ¿Cuál es tu *DIRECCIÓN*?"
                    
                    if len(passengers_list) > 0:
                        if len(passengers_list) == 1:
                            prev_pax = passengers_list[0]
                            prev_addr = prev_pax.get('direccion', '...')
                            msg_direccion += f"\n\n💡 *TIP:* Escribe *IGUAL* para usar la misma dirección del Pasajero 1."
                        else:
                            msg_direccion += f"\n\n💡 *TIP:* Escribe *IGUAL* para usar la dirección del Pasajero 1, o *IGUAL 2* para la del Pasajero 2."
                    
                    return self._send_response(phone, msg_direccion, session)

                elif waiting_for_field == 'direccion':
                    # Inicializar variable para evitar UnboundLocalError
                    msg_lower_dir = message.strip().lower()
                    
                    # Detectar si el usuario quiere copiar la dirección de otro pasajero
                    passengers_list = session.data.get('passengers_list', [])
                    target_pax_idx = 0  # Por defecto copiar del primero
                    is_copy_command = False
                    
                    if len(passengers_list) > 0:
                        # Palabras clave explícitas
                        if any(k in msg_lower_dir for k in ['igual', 'mismo', 'misma', 'copiar', 'anterior']):
                            is_copy_command = True
                        
                        # Si no es explícito, usar AI para interpretar
                        elif len(msg_lower_dir.split()) > 1: # Si tiene más de una palabra para valer la pena consultar
                            ai_copy = self._classify_with_ai(
                                message,
                                f"El usuario está ingresando la DIRECCIÓN del pasajero. Ya hay {len(passengers_list)} pasajero(s) anterior(es) con dirección guardada. ¿El usuario quiere COPIAR la dirección de un pasajero anterior, o está escribiendo una DIRECCIÓN NUEVA?",
                                {
                                    'copiar': 'El usuario quiere usar/copiar la misma dirección de otro pasajero anterior',
                                    'nueva': 'El usuario está escribiendo una dirección nueva diferente (una dirección real como calle, avenida, etc)',
                                }
                            )
                            if ai_copy == 'copiar':
                                is_copy_command = True
                        
                        if is_copy_command:
                            # Intentar extraer número de pasajero del mensaje
                            # re ya importado al inicio del archivo
                            pax_num_match = re.search(r'(?:pasajero|pax|del)\s*(\d+)', msg_lower_dir)
                            if not pax_num_match:
                                pax_num_match = re.search(r'igual\s+(\d+)', msg_lower_dir)
                            if not pax_num_match:
                                pax_num_match = re.search(r'misma?\s+(\d+)', msg_lower_dir)
                            
                            if pax_num_match:
                                idx = int(pax_num_match.group(1)) - 1
                                if 0 <= idx < len(passengers_list):
                                    target_pax_idx = idx
                        
                        if is_copy_command:
                            target_pax = passengers_list[target_pax_idx]
                            # Verificar que el pasajero objetivo tenga dirección
                            if target_pax.get('direccion'):
                                extracted_data['direccion'] = target_pax.get('direccion')
                                extracted_data['ciudad'] = target_pax.get('ciudad', 'Caracas') 
                                extracted_data['estado'] = target_pax.get('estado', 'Distrito Capital')
                                extracted_data['zipCode'] = target_pax.get('zipCode', '1010')
                                
                                session.data['extracted_data'] = extracted_data
                                session.data['waiting_for_field'] = 'telefono' # Saltar preguntas
                                
                                msg_confirm = f"✅ Dirección copiada: {target_pax.get('direccion')}\n\n📱 ¿Cuál es el número de *TELÉFONO*?"
                                return self._send_response(phone, msg_confirm, session)
                    
                    if len(message.strip()) < 5:
                        return self._send_response(phone, "❌ La dirección es muy corta. Por favor sé más específico (Av, Calle, Casa...):", session)
                    
                    extracted_data['direccion'] = message.strip()
                    session.data['extracted_data'] = extracted_data
                    # Flujo normal: pedir ciudad
                    session.data['waiting_for_field'] = 'ciudad'
                    return self._send_response(phone, "✅ Dirección guardada.\n\n🏙️ ¿En qué *CIUDAD* resides?", session)

                elif waiting_for_field == 'ciudad':
                    if len(message.strip()) < 3:
                        return self._send_response(phone, "❌ El nombre de la ciudad es muy corto:", session)
                    
                    extracted_data['ciudad'] = message.strip()
                    session.data['extracted_data'] = extracted_data
                    session.data['waiting_for_field'] = 'estado'
                    return self._send_response(phone, "✅ Ciudad guardada.\n\n🗺️ ¿En qué *ESTADO* (o Provincia)?", session)
                
                elif waiting_for_field == 'estado':
                    if len(message.strip()) < 3:
                         return self._send_response(phone, "❌ El nombre del estado es muy corto:", session)

                    extracted_data['estado'] = message.strip()
                    session.data['extracted_data'] = extracted_data
                    session.data['waiting_for_field'] = 'zip_code'
                    return self._send_response(phone, "✅ Estado guardado.\n\n📮 ¿Cuál es tu *CÓDIGO POSTAL* (Zip Code)?", session)

                elif waiting_for_field == 'zip_code':
                    # re ya importado al inicio del archivo
                    zip_code = re.sub(r'[^a-zA-Z0-9]', '', message.strip())
                    if len(zip_code) < 3:
                         return self._send_response(phone, "❌ Código postal inválido. Intenta de nuevo:", session)

                    extracted_data['zipCode'] = zip_code
                    session.data['extracted_data'] = extracted_data
                    session.data['waiting_for_field'] = 'telefono'
                    return self._send_response(phone, "✅ Código Postal guardado.\n\n📱 ¿Cuál es el número de *TELÉFONO*?", session)

                elif waiting_for_field == 'telefono':
                    # Extraer números del mensaje (teléfono)
                    phone_digits = re.sub(r'\D', '', message)
                    if len(phone_digits) >= 10:
                        extracted_data['telefono'] = phone_digits
                        session.data['extracted_data'] = extracted_data
                        
                        # Ahora pedir email
                        session.data['waiting_for_field'] = 'email'
                        return self._send_response(phone, "✅ Teléfono guardado.\n\n📧 ¿Cuál es tu correo electrónico?", session)
                    else:
                        return self._send_response(phone, "❌ El teléfono debe tener al menos 10 dígitos.\n\n📱 Por favor, ingresa un número de teléfono válido:", session)
                
                elif waiting_for_field == 'email':
                    # Validar email
                    email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', message)
                    if email_match:
                        extracted_data['email'] = email_match.group(1)
                        session.data['extracted_data'] = extracted_data
                        
                        # VERIFICAR SI YA TENEMOS FECHA DE NACIMIENTO (extraída de imagen)
                        if extracted_data.get('fecha_nacimiento'):
                            # Ya tenemos la fecha de nacimiento de la imagen, saltar pregunta
                            logger.info(f"Fecha de nacimiento ya extraída de imagen: {extracted_data['fecha_nacimiento']}")
                            session.data['waiting_for_field'] = None
                            
                            # CALCULAR TIPO DE PASAJERO
                            dob_iso = extracted_data['fecha_nacimiento']
                            today = datetime.now()
                            try:
                                born = datetime.strptime(dob_iso, '%Y-%m-%d')
                                age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
                            except:
                                age = 30  # Default adulto
                            
                            pax_type = 'ADT'
                            if age < 2:
                                pax_type = 'INF'
                            elif age < 12:
                                pax_type = 'CHD'
                            
                            extracted_data['tipo'] = pax_type
                            
                            # Etiqueta visual del tipo de pasajero
                            pax_labels = {'ADT': '🧑 Adulto', 'CHD': '👦 Niño', 'INF': '👶 Infante'}
                            pax_label = pax_labels.get(pax_type, '🧑 Adulto') + f' ({age} años)'
                            
                            # Agregar pasajero a la lista
                            total_passengers = session.data.get('num_passengers', 1)
                            passengers_data = session.data.get('passengers_list', [])
                            
                            current_passenger = {
                                'nombre': extracted_data.get('nombre', ''),
                                'apellido': extracted_data.get('apellido', ''),
                                'cedula': extracted_data.get('cedula') or extracted_data.get('pasaporte'),
                                'telefono': extracted_data.get('telefono'),
                                'email': extracted_data.get('email'),
                                'nacionalidad': extracted_data.get('nacionalidad', 'VE'),
                                'sexo': extracted_data.get('sexo', 'M'),
                                'direccion': extracted_data.get('direccion'),
                                'ciudad': extracted_data.get('ciudad'),
                                'estado': extracted_data.get('estado'),
                                'zipCode': extracted_data.get('zipCode'),
                                'fecha_nacimiento': extracted_data.get('fecha_nacimiento'),
                                'tipo': pax_type,
                                'tipo_documento': extracted_data.get('tipo_documento', 'CI')
                            }
                            passengers_data.append(current_passenger)
                            session.data['passengers_list'] = passengers_data
                            
                            current_passenger_count = len(passengers_data)
                            
                            if current_passenger_count < total_passengers:
                                session.data['extracted_data'] = {}
                                session.data['waiting_for_cedula_image'] = True
                                
                                response = f"""✅ *Datos del Pasajero {current_passenger_count} guardados*
👤 {current_passenger['nombre']} {current_passenger['apellido']}
🆔 {current_passenger['cedula']}
📋 Tipo: {pax_label}

━━━━━━━━━━━━━━━━━━━━━━

👤 *Ahora necesito los datos del Pasajero {current_passenger_count + 1} de {total_passengers}*

📸 *OPCIÓN 1 (RECOMENDADA):*
Envía una foto de la *CÉDULA* o *PASAPORTE* del pasajero {current_passenger_count + 1}.

✍️ *OPCIÓN 2:*
Escribe "manual" para ingresar los datos manualmente."""
                                return self._send_response(phone, response, session)
                            
                            # Tenemos todos los pasajeros, crear reserva
                            wati_service.send_message(phone, f"✅ Email guardado. {pax_label}\n\n✅ *Tengo los datos de los {total_passengers} pasajeros.*\n\n🎫 *Creando tu reserva...*\n\n⏳ Un momento por favor...")
                            
                            first_passenger = passengers_data[0]
                            
                            booking_result = self._create_booking_function(
                                flight_index=session.data.get('selected_flight_index'),
                                flight_class=session.data.get('selected_flight_class'),
                                passenger_name=f"{first_passenger.get('nombre', '')} {first_passenger.get('apellido', '')}".strip(),
                                id_number=first_passenger.get('cedula'),
                                phone=first_passenger.get('telefono'),
                                email=first_passenger.get('email'),
                                session=session
                            )
                            
                            if booking_result.get('success'):
                                flight_class = session.data.get('selected_flight_class', 'Y')
                                precio_ida = 0
                                flight_classes_prices = session.data.get('flight_classes_prices', {})
                                if flight_classes_prices and flight_class.upper() in flight_classes_prices:
                                    precio_ida = flight_classes_prices[flight_class.upper()].get('price', 0)
                                
                                flights = session.data.get('available_flights', [])
                                flight_index = session.data.get('selected_flight_index', 1)
                                selected_flight = flights[flight_index - 1] if flights and flight_index > 0 else {}
                                
                                return_flights = session.data.get('return_flights', [])
                                return_flight_index = session.data.get('selected_return_flight_index')
                                return_flight_class = session.data.get('selected_return_flight_class', flight_class)
                                return_flight = None
                                precio_vuelta = 0
                                
                                if return_flights and return_flight_index:
                                    if return_flight_index >= 1 and return_flight_index <= len(return_flights):
                                        return_flight = return_flights[return_flight_index - 1]
                                        return_classes_prices = session.data.get('return_flight_classes_prices', {})
                                        if return_classes_prices and return_flight_class.upper() in return_classes_prices:
                                            precio_vuelta = return_classes_prices[return_flight_class.upper()].get('price', 0)
                                        else:
                                            precio_vuelta = return_flight.get('price', 0)
                                
                                precio_por_persona = precio_ida + precio_vuelta
                                precio_total = precio_por_persona * total_passengers
                                
                                return self._send_booking_success_message(
                                    phone, session, booking_result, passengers_data, total_passengers,
                                    selected_flight, flight_class, precio_ida,
                                    return_flight, return_flight_class, precio_vuelta,
                                    precio_por_persona, precio_total
                                )
                            else:
                                # Error en la reserva
                                raw_error = booking_result.get('error', 'Error desconocido')
                                return self._send_response(phone, f"❌ No se pudo crear la reserva: {raw_error}", session)
                        else:
                            # NO tenemos fecha de nacimiento (flujo manual), preguntar
                            session.data['waiting_for_field'] = 'fecha_nacimiento'
                            return self._send_response(phone, "✅ Email guardado.\n\n📅 ¿Cuál es tu *FECHA DE NACIMIENTO*? (Ejemplo: 25/12/1990)", session)
                    else:
                        return self._send_response(phone, "❌ No parece ser un email válido.\n\n📧 Por favor, ingresa un correo electrónico válido (ejemplo: correo@email.com):", session)

                elif waiting_for_field == 'fecha_nacimiento':
                    # Validar fecha (re y datetime ya importados al inicio del archivo)
                    
                    dob_raw = message.strip()
                    # Intentar formatos
                    dob_iso = None
                    try:
                        # Soportar DD/MM/YYYY o DD-MM-YYYY o DD.MM.YYYY
                        clean_date = re.sub(r'[.-]', '/', dob_raw)
                        dt = datetime.strptime(clean_date, '%d/%m/%Y')
                        dob_iso = dt.strftime('%Y-%m-%d')
                    except:
                        return self._send_response(phone, "❌ Fecha inválida.\n\n📅 Por favor usa el formato DÍA/MES/AÑO (Ejemplo: 25/12/1990):", session)
                    
                    extracted_data['fecha_nacimiento'] = dob_iso
                    session.data['extracted_data'] = extracted_data
                    session.data['waiting_for_field'] = None

                    # CALCULAR TIPO DE PASAJERO
                    today = datetime.now()
                    born = datetime.strptime(dob_iso, '%Y-%m-%d')
                    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
                    
                    pax_type = 'ADT'
                    if age < 2:
                        pax_type = 'INF' # Infante
                    elif age < 12:
                        pax_type = 'CHD' # Niño
                    
                    extracted_data['tipo'] = pax_type
                    
                    # Etiqueta visual del tipo de pasajero
                    pax_labels = {'ADT': '🧑 Adulto', 'CHD': '👦 Niño', 'INF': '👶 Infante'}
                    pax_label = pax_labels.get(pax_type, '🧑 Adulto') + f' ({age} años)'
                        
                    # Verificar si hay más pasajeros por procesar
                    total_passengers = session.data.get('num_passengers', 1)
                    passengers_data = session.data.get('passengers_list', [])
                    
                    # Agregar el pasajero actual a la lista
                    current_passenger = {
                        'nombre': extracted_data.get('nombre', ''),
                        'apellido': extracted_data.get('apellido', ''),
                        'cedula': extracted_data.get('cedula') or extracted_data.get('pasaporte'),
                        'telefono': extracted_data.get('telefono'),
                        'email': extracted_data.get('email'),
                        'nacionalidad': extracted_data.get('nacionalidad', 'VE'),
                        'sexo': extracted_data.get('sexo', 'M'),
                        'direccion': extracted_data.get('direccion'),
                        'ciudad': extracted_data.get('ciudad'),
                        'estado': extracted_data.get('estado'),
                        'zipCode': extracted_data.get('zipCode'),
                        'fecha_nacimiento': extracted_data.get('fecha_nacimiento'),
                        'tipo': extracted_data.get('tipo', 'ADT'),
                        'tipo_documento': extracted_data.get('tipo_documento', 'CI')
                    }
                    passengers_data.append(current_passenger)
                    session.data['passengers_list'] = passengers_data
                    
                    current_passenger_count = len(passengers_data)
                    
                    # Si faltan pasajeros por procesar
                    if current_passenger_count < total_passengers:
                        # Limpiar datos extraídos para el siguiente pasajero
                        session.data['extracted_data'] = {}
                        session.data['waiting_for_cedula_image'] = True
                        
                        response = f"""✅ *Datos del Pasajero {current_passenger_count} guardados*
👤 {current_passenger['nombre']} {current_passenger['apellido']}
🆔 {current_passenger['cedula']}
📋 Tipo: {pax_label}

━━━━━━━━━━━━━━━━━━━━━━

👤 *Ahora necesito los datos del Pasajero {current_passenger_count + 1} de {total_passengers}*

📸 *OPCIÓN 1 (RECOMENDADA):*
Envía una foto de la *CÉDULA* o *PASAPORTE* del pasajero {current_passenger_count + 1}.

✍️ *OPCIÓN 2:*
Escribe "manual" para ingresar los datos manualmente."""
                        return self._send_response(phone, response, session)
                    
                    # Tenemos todos los pasajeros, crear reserva
                    self._send_response(phone, f"✅ Fecha guardada. {pax_label}\n\n✅ *Tengo los datos de los {total_passengers} pasajeros.*\n\n🎫 *Creando tu reserva...*\n\n⏳ Un momento por favor...", session)
                    
                    # Usar el primer pasajero para la reserva principal
                    first_passenger = passengers_data[0]
                    
                    booking_result = self._create_booking_function(
                        flight_index=session.data.get('selected_flight_index'),
                        flight_class=session.data.get('selected_flight_class'),
                        passenger_name=f"{first_passenger.get('nombre', '')} {first_passenger.get('apellido', '')}".strip(),
                        id_number=first_passenger.get('cedula'),
                        phone=first_passenger.get('telefono'),
                        email=first_passenger.get('email'),
                        session=session
                    )
                        
                    if booking_result.get('success'):
                        # Obtener precio de IDA
                        flight_class = session.data.get('selected_flight_class', 'Y')
                        precio_ida = 0
                        flight_classes_prices = session.data.get('flight_classes_prices', {})
                        if flight_classes_prices and flight_class.upper() in flight_classes_prices:
                            precio_ida = flight_classes_prices[flight_class.upper()].get('price', 0)
                        
                        # Obtener datos del vuelo seleccionado
                        flights = session.data.get('available_flights', [])
                        flight_index = session.data.get('selected_flight_index', 1)
                        selected_flight = flights[flight_index - 1] if flights and flight_index > 0 else {}
                        
                        # Obtener lista de pasajeros
                        all_passengers = session.data.get('passengers_list', [])
                        total_passengers = len(all_passengers)
                        
                        # Verificar si hay vuelo de vuelta
                        return_flights = session.data.get('return_flights', [])
                        return_flight_index = session.data.get('selected_return_flight_index')
                        return_flight_class = session.data.get('selected_return_flight_class', flight_class)
                        return_flight = None
                        precio_vuelta = 0
                        
                        if return_flights and return_flight_index:
                            if return_flight_index >= 1 and return_flight_index <= len(return_flights):
                                return_flight = return_flights[return_flight_index - 1]
                                # Obtener precio de vuelta
                                return_classes_prices = session.data.get('return_flight_classes_prices', {})
                                if return_classes_prices and return_flight_class.upper() in return_classes_prices:
                                    precio_vuelta = return_classes_prices[return_flight_class.upper()].get('price', 0)
                                else:
                                    precio_vuelta = return_flight.get('price', 0)
                        
                        # Calcular totales
                        precio_por_persona = precio_ida + precio_vuelta
                        precio_total = precio_por_persona * total_passengers if total_passengers > 0 else precio_por_persona
                        
                        return self._send_booking_success_message(
                            phone, session, booking_result, passengers_data, total_passengers,
                            selected_flight, flight_class, precio_ida,
                            return_flight, return_flight_class, precio_vuelta,
                            precio_por_persona, precio_total
                        )
                    else:
                        # Traducir error técnico a mensaje amigable
                        raw_error = booking_result.get('error', 'Error desconocido')
                        error_lower = raw_error.lower()
                        
                        user_msg = f"❌ No se pudo crear la reserva: {raw_error}" # Default
                        
                        if "disponible" in error_lower or "availability" in error_lower or "no seats" in error_lower:
                            user_msg = f"❌ *Vuelo no disponible.*\n\n{raw_error}"
                        elif ("time limit" in error_lower or "expired" in error_lower) and "ticket" not in error_lower:
                            user_msg = "⏱️ *Tiempo agotado.*\n\nLa sesión de reserva expiró. Por favor realiza la búsqueda nuevamente."
                        elif "availability" in error_lower or "no seats" in error_lower or "waitlist" in error_lower:
                            user_msg = "❌ *Vuelo lleno.*\n\nYa no quedan asientos disponibles en esta clase. Por favor intenta con otra fecha o clase."
                        elif "duplicate" in error_lower:
                            user_msg = "⚠️ *Reserva duplicada.*\n\nYa existe una reserva activa para este pasajero en este vuelo."
                        elif "invalid" in error_lower:
                            user_msg = "✍️ *Datos inválidos.*\n\nPor favor verifica que el número de cédula/pasaporte y nombres sean correctos."
                        elif "restricted" in error_lower or "not allowed" in error_lower:
                            user_msg = "🚫 *No permitido.*\n\nLa aerolínea bloqueó la reserva. Puede ser por restricciones de tarifa o tiempo."

                        return self._send_response(phone, user_msg, session)
            
            # DETECCIÓN DE "MANUAL" PARA INGRESO DE DATOS
            message_clean = message.lower().strip()
            if message_clean == 'manual' and session.data.get('awaiting_flight_confirmation'):
                # Iniciar flujo manual
                session.data['extracted_data'] = {}  # Limpiar datos previos
                # Iniciar lista de pasajeros si no existe
                if not session.data.get('passengers_list'):
                    session.data['passengers_list'] = []
                
                # Determinar qué pasajero estamos procesando
                current_count = len(session.data['passengers_list'])
                total_passengers = session.data.get('num_passengers', 1)
                
                if current_count < total_passengers:
                    # Empezar a pedir datos comenzando por el Nombre
                    session.data['waiting_for_field'] = 'nombre'
                    passenger_label = f" (Pasajero {current_count + 1} de {total_passengers})" if total_passengers > 1 else ""
                    return self._send_response(phone, f"📝 Entendido, ingresaremos los datos manualmente.\n\n👤 ¿Cuál es el *NOMBRE* (sin apellidos) del pasajero?{passenger_label}", session)

            # DETECCIÓN DE SELECCIÓN DE CLASE (Interceptando a Gemini)
            # Solo si estamos esperando selección de clase
            # Verificar en qué etapa estamos:
            # 1. Ida: flight_classes_prices existe Y NO flight_confirmed
            # 2. Vuelta: return_flight_classes_prices existe Y flight_confirmed
            
            flight_prices = session.data.get('flight_classes_prices')
            return_prices = session.data.get('return_flight_classes_prices')
            flight_confirmed = session.data.get('flight_confirmed', False)
            
            waiting_for_class_ida = bool(flight_prices) and not flight_confirmed
            waiting_for_class_vuelta = bool(return_prices) and flight_confirmed
            
            if waiting_for_class_ida or waiting_for_class_vuelta:
                # re ya importado al inicio del archivo
                msg_upper = message.upper().strip()
                
                # Buscar patrón fuerte: "Clase X", "Opción X", "La X", o solo "X" si es muy corto
                class_match = re.search(r'^(?:CLASE|OPCI[ÓO]N|LA|EL)?\s*([A-Z])$', msg_upper)
                
                # O si dice explícitamente "quiero la clase X"
                if not class_match:
                    class_match = re.search(r'QUIERO.*CLASE\s+([A-Z])', msg_upper)
                
                if class_match:
                    selected_class = class_match.group(1)
                    
                    # Determinar contexto (Ida o Vuelta)
                    is_return_flow = waiting_for_class_vuelta
                    prices_dict = return_prices if is_return_flow else flight_prices
                    
                    # Validar existencia de la clase
                    if prices_dict and selected_class in prices_dict:
                        logger.info(f"⚡ Interceptando selección de clase manual: {selected_class} (Return Flow: {is_return_flow})")
                        
                        # Obtener índice correcto
                        idx = session.data.get('selected_return_flight_index') if is_return_flow else session.data.get('selected_flight_index')
                        
                        if idx:
                            # Mensaje de feedback inmediato
                            wati_service.send_message(phone, f"✅ Clase {selected_class} seleccionada.\n\n🔄 Preparando resumen de confirmación...")
                            
                            # Llamar a la función interna
                            result = self._confirm_flight_selection_function(idx, selected_class, session, is_return=is_return_flow)
                            
                            if result.get('success'):
                                if result.get('is_round_trip_summary'):
                                    # ES EL RESUMEN FINAL (Ya confirmó vuelta, ahora confirma TODO)
                                    response_text = f"""✈️ *RESUMEN FINAL DE TU VIAJE IDA Y VUELTA*

━━━━━━━━━━━━━━━━━━━━

🛫 *IDA*
✈️ {result.get('ida_aerolinea')} {result.get('ida_vuelo')}
📍 {result.get('ida_ruta')}
📅 {result.get('ida_fecha')}
🕐 {result.get('ida_salida')} → {result.get('ida_llegada')}
💺 Clase: {result.get('ida_clase')} (${result.get('ida_precio')})

━━━━━━━━━━━━━━━━━━━━

🛬 *VUELTA*
✈️ {result.get('vuelta_aerolinea')} {result.get('vuelta_vuelo')}
📍 {result.get('vuelta_ruta')}
📅 {result.get('vuelta_fecha')}
🕐 {result.get('vuelta_salida')} → {result.get('vuelta_llegada')}
💺 Clase: {result.get('vuelta_clase')} (${result.get('vuelta_precio')})

━━━━━━━━━━━━━━━━━━━━

💰 *COSTO TOTAL*
💵 Por persona: ${result.get('precio_por_persona')}
👥 Pasajeros: {result.get('num_passengers')}
💰 *TOTAL:* {result.get('precio_total')} {result.get('moneda')}

━━━━━━━━━━━━━━━━━━━━

✅ *¿Confirmas esta reserva?*
Responde *SÍ* para continuar con los datos de pasajeros o *NO* para cambiar."""
                                else:
                                    # ES LA CONFIRMACIÓN DE UN SOLO VUELO (Ida o Vuelta)
                                    header_msg = "✅ *VUELO DE REGRESO SELECCIONADO*" if result.get('is_return_flight') else "✅ *CLASE SELECCIONADA*"
                                    response_text = f"""{header_msg}

✈️ *Vuelo:* {result.get('aerolinea')} {result.get('vuelo')}
📍 *Ruta:* {result.get('ruta')}
📅 *Fecha:* {format_date_dd_mm_yyyy(result.get('fecha'))}
🕐 *Salida:* {result.get('salida')}
🕐 *Llegada:* {result.get('llegada')}
💺 *Clase:* {result.get('clase_seleccionada')}
💰 *Precio:* ${result.get('precio')} {result.get('moneda')}

━━━━━━━━━━━━━━━━━━━━

✅ *¿Confirmas esta selección?*
Responde *SÍ* para continuar."""

                                # IMPORTANTE: Agregar al historial de Gemini para que sepa que ya pidió confirmación
                                history = session.data.get('ai_history', [])
                                history.append({"role": "user", "parts": [{"text": message}]})
                                history.append({"role": "model", "parts": [{"text": response_text}]})
                                session.data['ai_history'] = history
                                
                                return self._send_response(phone, response_text, session)
                                
            # INTERCEPCIÓN DE "SI" PARA CONFIRMAR VUELO DE VUELTA Y MOSTRAR RESUMEN FINAL
            # Si estamos esperando confirmación de vuelo y es un vuelo de REGRESO que aún no está "fully confirmed"
            if session.data.get('awaiting_flight_confirmation') and session.data.get('selected_return_flight_index') and not session.data.get('return_flight_fully_confirmed'):
                msg_upper = message.strip().upper()
                if msg_upper in ['SI', 'SÍ', 'YES', 'CONFIRMO', 'CORRECTO']:
                    logger.info("Interceptando confirmación de vuelo de regreso - mostrando resumen final")
                    
                    # Marcar como confirmado completamente
                    session.data['return_flight_fully_confirmed'] = True
                    
                    # Llamar a la función de confirmación para generar el resumen final
                    idx = session.data.get('selected_return_flight_index')
                    cls_code = session.data.get('selected_return_flight_class')
                    if idx and cls_code:
                        result = self._confirm_flight_selection_function(idx, cls_code, session, is_return=True)
                        if result.get('success') and result.get('is_round_trip_summary'):
                            response_text = f"""✈️ *RESUMEN FINAL DE TU VIAJE IDA Y VUELTA*

━━━━━━━━━━━━━━━━━━━━

🛫 *IDA*
✈️ {result.get('ida_aerolinea')} {result.get('ida_vuelo')}
📍 {result.get('ida_ruta')}
📅 {format_date_dd_mm_yyyy(result.get('ida_fecha'))}
🕐 {result.get('ida_salida')} → {result.get('ida_llegada')}
💺 Clase: {result.get('ida_clase')} (${result.get('ida_precio')})

━━━━━━━━━━━━━━━━━━━━

🛬 *VUELTA*
✈️ {result.get('vuelta_aerolinea')} {result.get('vuelta_vuelo')}
📍 {result.get('vuelta_ruta')}
📅 {format_date_dd_mm_yyyy(result.get('vuelta_fecha'))}
🕐 {result.get('vuelta_salida')} → {result.get('vuelta_llegada')}
💺 Clase: {result.get('vuelta_clase')} (${result.get('vuelta_precio')})

━━━━━━━━━━━━━━━━━━━━

💰 *COSTO TOTAL*
💵 Por persona: ${result.get('precio_por_persona')}
👥 Pasajeros: {result.get('num_passengers')}
💰 *TOTAL:* {result.get('precio_total')} {result.get('moneda')}

━━━━━━━━━━━━━━━━━━━━

✅ *¿Confirmas esta reserva?*
Responde *SÍ* para continuar con los datos de pasajeros o *NO* para cambiar."""
                            
                            # Actualizar historial
                            history = session.data.get('ai_history', [])
                            history.append({"role": "user", "parts": [{"text": message}]})
                            history.append({"role": "model", "parts": [{"text": response_text}]})
                            session.data['ai_history'] = history
                            
                            return self._send_response(phone, response_text, session)

            # DETECCIÓN AUTOMÁTICA DE CÓDIGO PNR (6 caracteres alfanuméricos)
            # re ya importado al inicio del archivo
            potential_pnr = message.strip().upper()
            pnr_match = re.match(r'^[A-Z0-9]{6}$', potential_pnr)
            
            # Lista de palabras comunes que NO son PNR
            palabras_excluidas = [
                # Saludos y respuestas comunes
                'BUENOS', 'BUENAS', 'HOLA', 'ADIOS', 'CHAO',
                'GRACIAS', 'THANKS', 'PLEASE', 'PORFA',
                # Palabras de vuelos
                'VUELOS', 'VUELTA', 'AVION', 'AVIONES',
                # Ciudades y lugares
                'BOGOTA', 'MADRID', 'PANAMA', 'MEXICO', 'ITALIA',
                'MERIDA', 'CUMANA', 'MARGARITA',
                # Meses
                'ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO',
                'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE',
                # Días
                'LUNES', 'MARTES', 'JUEVES', 'VIERNES', 'SABADO', 'DOMINGO',
                # Respuestas comunes
                'QUIERO', 'BUSCAR', 'RESERVA', 'RESERVAR', 'COMPRAR',
                'SALIR', 'VIAJAR', 'FECHAS', 'PRECIO', 'PRECIOS',
                'PAGAR', 'TARJETA', 'EFECTIVO', 'CANCELAR',
                'AYUDA', 'MANUAL', 'IMAGEN', 'CEDULA',
                # Nacionalidades
                'VENEZOLANO', 'COLOMBIANO', 'PERUANO', 'CHILENO', 'ARGENTINO',
                # Otros
                'CORREO', 'CORRECTO', 'EXACTO', 'PERFECTO',
                'NUMERO', 'PASAJERO', 'PASAJERA', 'SI', 'NO', 'CONFIRMO',
                # Clases
                'ECONOMICA', 'BUSINESS', 'PRIMERA', 'CLASE',
            ]
            
            # Un PNR válido debe:
            # 1. Tener exactamente 6 caracteres alfanuméricos
            # 2. NO ser una palabra común
            # 3. Preferiblemente tener al menos un número (los PNR reales suelen tener números)
            es_palabra_comun = potential_pnr in palabras_excluidas
            tiene_numero = any(c.isdigit() for c in potential_pnr)
            
            # Solo considerar como PNR si:
            # - Tiene al menos un número, O
            # - No es una palabra común (para PNR como "ABCDEF" que son raros pero existen)
            es_pnr_valido = pnr_match and (tiene_numero or not es_palabra_comun)
            
            if es_pnr_valido:
                pnr_code = potential_pnr
                logger.info(f"Código PNR detectado automáticamente: {pnr_code}")
                
                # Enviar mensaje de "consultando"
                wati_service.send_message(phone, f"🔍 Consultando reserva {pnr_code}...")
                
                # Consultar directamente sin pasar por Gemini
                result = self._get_booking_function(pnr_code)
                if result.get('success'):
                    # Usar el mensaje formateado de la función
                    response = result.get('message')
                    # Agregar al historial
                    history = session.data.get('ai_history', [])
                    history.append({"role": "user", "parts": [{"text": message}]})
                    history.append({"role": "model", "parts": [{"text": response}]})
                    session.data['ai_history'] = history
                    return self._send_response(phone, response, session)
                else:
                    error_response = f"❌ **Reserva no encontrada**\n\n🎫 PNR: **{pnr_code}**\n\n🔍 Verifica el código e intenta de nuevo."
                    # Agregar al historial
                    history = session.data.get('ai_history', [])
                    history.append({"role": "user", "parts": [{"text": message}]})
                    history.append({"role": "model", "parts": [{"text": error_response}]})
                    session.data['ai_history'] = history
                    return self._send_response(phone, error_response, session)
            # Si no es un PNR, continuar con el flujo normal de Gemini
            # Obtener fecha actual
            fecha_hoy = datetime.now().strftime("%Y-%m-%d")
            fecha_manana = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            # System instruction con fecha actual
            system_with_date = self.system_instruction + f"\n\n**FECHA ACTUAL: {fecha_hoy}**\nCuando el usuario diga 'hoy' usa: {fecha_hoy}\nCuando el usuario diga 'mañana' usa: {fecha_manana}"
            # Obtener historial de conversación
            history = session.data.get('ai_history', [])
            # Agregar mensaje del usuario
            history.append({
                "role": "user",
                "parts": [{"text": message}]
            })
            # Definir herramientas disponibles
            tools = [
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name="search_flights",
                            description="Busca vuelos de IDA disponibles entre dos ciudades en una fecha específica. Para vuelos de ida y vuelta, llama esta función dos veces (ida y vuelta por separado). IMPORTANTE: Debes llamar esta función INMEDIATAMENTE cuando tengas toda la información necesaria (origen, destino, fecha, pasajeros). NO confirmes los datos con texto, llama directamente.",
                            parameters={
                                "type": "object",
                                "properties": {
                                    "origin": {
                                        "type": "string",
                                        "description": "Código IATA de la ciudad de origen (ej: CCS, PMV, MIA)"
                                    },
                                    "destination": {
                                        "type": "string",
                                        "description": "Código IATA de la ciudad de destino"
                                    },
                                    "date": {
                                        "type": "string",
                                        "description": "Fecha del vuelo en formato YYYY-MM-DD"
                                    },
                                    "trip_type": {
                                        "type": "string",
                                        "description": "Tipo de viaje: 'ida' o 'vuelta'. OBLIGATORIO.",
                                        "enum": ["ida", "vuelta"]
                                    },
                                    "num_passengers": {
                                        "type": "integer",
                                        "description": "Número TOTAL de pasajeros. OBLIGATORIO."
                                    },
                                    "adults": {
                                        "type": "integer",
                                        "description": "Número de adultos (12+ años). Opcional, por defecto num_passengers."
                                    },
                                    "children": {
                                        "type": "integer",
                                        "description": "Número de niños (2-11 años). Opcional, por defecto 0."
                                    },
                                    "infants": {
                                        "type": "integer",
                                        "description": "Número de infantes (0-2 años). Opcional, por defecto 0."
                                    }
                                },
                                "required": ["origin", "destination", "date", "trip_type", "num_passengers"]
                            }
                        ),
                        types.FunctionDeclaration(
                            name="get_booking_details",
                            description="Consulta los detalles de una reserva usando el código PNR",
                            parameters={
                                "type": "object",
                                "properties": {
                                    "pnr": {
                                        "type": "string",
                                        "description": "Código PNR de 6 caracteres de la reserva"
                                    }
                                },
                                "required": ["pnr"]
                            }
                        ),
                        types.FunctionDeclaration(
                            name="get_travel_requirements",
                            description="OBLIGATORIO: Llama a esta función cuando el usuario pregunte sobre requisitos migratorios, documentos necesarios, o qué se necesita para viajar a un país. Obtiene los requisitos migratorios completos.",
                            parameters={
                                "type": "object",
                                "properties": {
                                    "country": {
                                        "type": "string",
                                        "description": "Nombre del país en minúsculas (ej: cuba, mexico, venezuela, bolivia, brasil)"
                                    }
                                },
                                "required": ["country"]
                            }
                        ),
                        types.FunctionDeclaration(
                            name="select_flight_and_get_prices",
                            description="OBLIGATORIO: Llama esta función cuando el usuario seleccione un vuelo (ejemplo: 'opción 1', 'vuelo 2', 'el primero'). Esta función muestra el resumen del vuelo y pide confirmación. Para vuelos de REGRESO, usa is_return=true.",
                            parameters={
                                "type": "object",
                                "properties": {
                                    "flight_index": {
                                        "type": "integer",
                                        "description": "Número del vuelo seleccionado (1, 2, 3, etc.)"
                                    },
                                    "is_return": {
                                        "type": "boolean",
                                        "description": "True si es vuelo de REGRESO/VUELTA, False si es vuelo de IDA. Por defecto es False."
                                    }
                                },
                                "required": ["flight_index"]
                            }
                        ),
                        types.FunctionDeclaration(
                            name="confirm_flight_and_get_prices",
                            description="Llama esta función cuando el usuario CONFIRME el vuelo mostrado (dice 'sí', 'confirmo', 'ok', 'dale'). Obtiene los precios de todas las clases disponibles.",
                            parameters={
                                "type": "object",
                                "properties": {
                                    "is_return": {
                                        "type": "boolean",
                                        "description": "True si es vuelo de REGRESO/VUELTA, False si es vuelo de IDA. Por defecto es False."
                                    }
                                },
                                "required": []
                            }
                        ),
                        types.FunctionDeclaration(
                            name="confirm_flight_selection",
                            description="Muestra los detalles del vuelo seleccionado con la clase elegida y pide confirmación al usuario ANTES de proceder con la reserva. SOLO llama esta función DESPUÉS de que el usuario haya elegido una clase de las opciones mostradas. Para vuelos de IDA Y VUELTA, después de seleccionar la clase del vuelo de VUELTA, esta función mostrará el resumen de AMBOS vuelos.",
                            parameters={
                                "type": "object",
                                "properties": {
                                    "flight_index": {
                                        "type": "integer",
                                        "description": "Número del vuelo seleccionado (1, 2, 3, etc.)"
                                    },
                                    "flight_class": {
                                        "type": "string",
                                        "description": "Código de la clase seleccionada (ej: Y, B, C, D). Debe ser una de las clases disponibles mostradas al usuario."
                                    },
                                    "is_return": {
                                        "type": "boolean",
                                        "description": "True si es vuelo de REGRESO/VUELTA, False si es vuelo de IDA. Por defecto es False."
                                    }
                                },
                                "required": ["flight_index", "flight_class"]
                            }
                        ),

                        types.FunctionDeclaration(
                            name="create_booking",
                            description="Crea una reserva de vuelo con los datos del pasajero y la clase seleccionada. Pide los datos necesarios antes de llamar esta función.",
                            parameters={
                                "type": "object",
                                "properties": {
                                    "flight_index": {
                                        "type": "integer",
                                        "description": "Número del vuelo seleccionado de la lista (1, 2, 3, etc.)"
                                    },
                                    "flight_class": {
                                        "type": "string",
                                        "description": "Código de la clase seleccionada (ej: Y, B, C, D)"
                                    },
                                    "passenger_name": {
                                        "type": "string",
                                        "description": "Nombre completo del pasajero (ej: Juan Perez)"
                                    },
                                    "id_number": {
                                        "type": "string",
                                        "description": "Número de cédula del pasajero (7-8 dígitos, sin V- ni E-)"
                                    },
                                    "phone": {
                                        "type": "string",
                                        "description": "Número de teléfono del pasajero (10-11 dígitos, ejemplo: 04121234567)"
                                    },
                                    "email": {
                                        "type": "string",
                                        "description": "Email del pasajero"
                                    },
                                    "city": {
                                        "type": "string",
                                        "description": "Ciudad del pasajero (opcional, por defecto: Caracas)"
                                    },
                                    "address": {
                                        "type": "string",
                                        "description": "Dirección del pasajero (opcional, por defecto: Av Principal)"
                                    }
                                },
                                "required": ["flight_index", "flight_class", "passenger_name", "id_number", "phone", "email"]
                            }
                        )
                    ]
                )
            ]
            # Llamar a Gemini con herramientas (con reintentos para error 503)
            if not self.client:
                logger.error("Cliente Gemini no inicializado")
                return self._send_response(phone, "⚠️ Error de configuración: El servicio de IA no está disponible.", session)
            
            max_retries = 3
            retry_delay = 2
            response = None
            for attempt in range(max_retries):
                try:
                    response = self.client.models.generate_content(
                        model=self.model,
                        contents=history,
                        config=types.GenerateContentConfig(
                            system_instruction=system_with_date,
                            tools=tools,
                            temperature=0.4
                        )
                    )
                    break
                except Exception as api_error:
                    error_str = str(api_error)
                    if '503' in error_str or 'overloaded' in error_str.lower() or 'UNAVAILABLE' in error_str:
                        if attempt < max_retries - 1:
                            logger.warning(f"Gemini sobrecargado, reintentando en {retry_delay}s (intento {attempt + 1}/{max_retries})")
                            # time ya importado al inicio del archivo
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        else:
                            logger.error(f"Gemini no disponible después de {max_retries} intentos")
                            return self._send_response(phone, "⚠️ El servicio de IA está temporalmente sobrecargado. Por favor, intenta de nuevo en unos segundos.", session)
                    else:
                        raise
            if not response:
                return self._send_response(phone, "⚠️ No se pudo conectar con el servicio de IA. Intenta de nuevo.", session)
            
            # Procesar respuesta con reintentos si viene vacía
            max_empty_retries = 2
            for empty_attempt in range(max_empty_retries + 1):
                try:
                    # Verificar si hay candidatos válidos
                    if not response.candidates:
                        logger.warning(f"Respuesta sin candidatos (intento {empty_attempt + 1})")
                        if empty_attempt < max_empty_retries:
                            # time ya importado al inicio del archivo
                            time.sleep(1)
                            response = self.client.models.generate_content(
                                model=self.model,
                                contents=history,
                                config=types.GenerateContentConfig(
                                    system_instruction=system_with_date,
                                    tools=tools,
                                    temperature=0.5 + (empty_attempt * 0.2)
                                )
                            )
                            continue
                        break
                    
                    candidate = response.candidates[0]
                    
                    # Log del finish_reason para diagnóstico
                    finish_reason = getattr(candidate, 'finish_reason', 'UNKNOWN')
                    logger.info(f"Gemini finish_reason: {finish_reason}")
                    
                    # Verificar si fue bloqueado por seguridad
                    if str(finish_reason) in ['SAFETY', 'BLOCKED', 'RECITATION']:
                        logger.warning(f"Respuesta bloqueada por: {finish_reason}")
                        return self._send_response(phone, "No pude procesar esa solicitud. ¿Podrías reformularla?", session)
                    
                    if candidate.content and candidate.content.parts:
                        # Primero buscar si hay alguna llamada a función en las partes
                        function_call_part = next((p for p in candidate.content.parts if hasattr(p, 'function_call') and p.function_call), None)
                        
                        if function_call_part:
                            # Si hay texto antes de la función, enviarlo primero pero guardarlo en historial
                            for part in candidate.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    self._send_response(phone, part.text, session)
                                    history.append({"role": "model", "parts": [{"text": part.text}]})
                            
                            # Luego manejar la llamada a función
                            return self._handle_function_call(session, phone, response, history)
                        
                        # Si no hay función, procesar texto normal
                        ai_response = ""
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                ai_response += part.text
                        
                        if ai_response:
                            # Agregar respuesta al historial
                            history.append({
                                "role": "model",
                                "parts": [{"text": ai_response}]
                            })
                            session.data['ai_history'] = history
                            return self._send_response(phone, ai_response, session)
                    
                    # Si llegamos aquí, la respuesta está vacía
                    logger.warning(f"Respuesta vacía de Gemini (intento {empty_attempt + 1}/{max_empty_retries + 1})")
                    
                    if empty_attempt < max_empty_retries:
                        # time ya importado al inicio del archivo
                        time.sleep(1)
                        response = self.client.models.generate_content(
                            model=self.model,
                            contents=history,
                            config=types.GenerateContentConfig(
                                system_instruction=system_with_date,
                                tools=tools,
                                temperature=0.5 + (empty_attempt * 0.2)
                            )
                        )
                        continue
                    
                except Exception as parse_error:
                    logger.error(f"Error parseando respuesta (intento {empty_attempt + 1}): {parse_error}")
                    if empty_attempt < max_empty_retries:
                        # time ya importado al inicio del archivo
                        time.sleep(1)
                        response = self.client.models.generate_content(
                            model=self.model,
                            contents=history,
                            config=types.GenerateContentConfig(
                                system_instruction=system_with_date,
                                tools=tools,
                                temperature=0.5 + (empty_attempt * 0.2)
                            )
                        )
                        continue
                    break
            
            # Si después de todos los reintentos no hay respuesta útil
            logger.error("No se pudo obtener respuesta útil de Gemini después de múltiples intentos")
            return self._send_response(phone, "⚠️ Tuve un problema procesando tu mensaje. ¿Podrías intentar de nuevo?", session)
        except Exception as e:
            error_str = str(e)
            error_type = type(e).__name__
            logger.error(f"Error procesando con AI: {error_type}: {error_str}", exc_info=True)
            if '503' in error_str or 'overloaded' in error_str.lower() or 'UNAVAILABLE' in error_str:
                return self._send_response(phone, "⚠️ El servicio de IA está temporalmente sobrecargado. Por favor, intenta de nuevo en unos segundos.", session)
            elif '429' in error_str or 'quota' in error_str.lower():
                return self._send_response(phone, "⚠️ Se ha alcanzado el límite de solicitudes. Por favor, intenta de nuevo en un momento.", session)
            else:
                # DEBUG: Mostrar error real para diagnosticar
                error_detail = f"{error_type}: {error_str[:200]}"
                return self._send_response(phone, f"😅 Tuve un problema procesando tu solicitud. ¿Podrías intentar de nuevo?\n\n🔧 DEBUG: {error_detail}", session)
    def _handle_function_call(self, session, phone, response, history):
        """Maneja las llamadas a funciones"""
        try:
            # Calcular fecha actual para el follow-up
            fecha_hoy = datetime.now().strftime("%Y-%m-%d")
            fecha_manana = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            system_with_date = self.system_instruction + f"\n\n**FECHA ACTUAL: {fecha_hoy}**\nCuando el usuario diga 'hoy' usa: {fecha_hoy}\nCuando el usuario diga 'mañana' usa: {fecha_manana}"
            # Encontrar el part que contiene la llamada a función
            function_call = next((p.function_call for p in response.candidates[0].content.parts if hasattr(p, 'function_call') and p.function_call), None)
            if not function_call:
                return self._send_response(phone, "No pude procesar la función solicitada.", session)
                
            function_name = function_call.name
            function_args = dict(function_call.args)
            logger.info(f"Llamando función: {function_name} con args: {function_args}")
            # Ejecutar la función correspondiente
            if function_name == "search_flights":
                # Enviar mensaje de "buscando" ANTES de ejecutar la búsqueda
                origin = function_args.get('origin')
                destination = function_args.get('destination')
                date = function_args.get('date')
                trip_type = function_args.get('trip_type', 'ida')
                # Nuevos campos detallados - Conversión segura de tipos
                safe_int = lambda x, default: int(float(x)) if x is not None and str(x).replace('.', '', 1).isdigit() else default
                
                # Asegurar que num_passengers tenga un valor válido
                raw_num_passengers = function_args.get('num_passengers')
                num_passengers = safe_int(raw_num_passengers, 1)
                
                # Extraer y convertir desglose de pasajeros
                adults = safe_int(function_args.get('adults'), num_passengers)
                children = safe_int(function_args.get('children'), 0)
                infants = safe_int(function_args.get('infants'), 0)
                
                # Si adults=0 pero hay niños/infantes, o si adults no se pasó, recalcular
                if adults == 0 and (children > 0 or infants > 0):
                    # Asumir que num_passengers es el total
                    remaining = num_passengers - children - infants
                    adults = max(1, remaining)
                
                # Si no se pasó num_passengers explícito pero sí desglose
                if num_passengers <= 1 and (children > 0 or infants > 0):
                    num_passengers = adults + children + infants
                
                session.data['num_passengers'] = num_passengers
                session.data['num_adults'] = adults
                session.data['num_children'] = children
                session.data['num_infants'] = infants
                session.data['passengers_list'] = []  # Inicializar lista de pasajeros
                
                # Determinar tipo de viaje para el mensaje
                tipo_viaje = "✈️ Solo Ida" if trip_type == 'ida' else "🔄 Vuelta"
                
                pasajeros_texto = []
                if adults > 0: pasajeros_texto.append(f"{adults} Adulto(s)")
                if children > 0: pasajeros_texto.append(f"{children} Niño(s)")
                if infants > 0: pasajeros_texto.append(f"{infants} Infante(s)")
                if not pasajeros_texto: # Si por alguna razón está vacío
                    pasajeros_texto.append(f"{num_passengers} Pasajero(s)")
                pax_str = ", ".join(pasajeros_texto)
                
                self._send_response(phone, f"✈️ *Buscando los mejores vuelos para ti...*\n\n📍 Ruta: {origin} → {destination}\n📅 Fecha: {format_date_dd_mm_yyyy(date)}\n{tipo_viaje}\n👥 {pax_str}\n\n🔍 Estoy revisando todas las opciones disponibles...", session)
                result = self._search_flights_function(
                    origin,
                    destination,
                    date,
                    session,
                    trip_type,
                    adults=adults,
                    children=children,
                    infants=infants
                )
            elif function_name == "get_booking_details":
                pnr = function_args.get('pnr')
                self._send_response(phone, f"🔍 Consultando reserva {pnr}...", session)
                result = self._get_booking_function(pnr)
            elif function_name == "get_travel_requirements":
                result = self._get_requirements_function(function_args.get('country'))
            elif function_name == "select_flight_and_get_prices":
                # Nueva función: seleccionar vuelo y mostrar resumen
                is_return = function_args.get('is_return', False)
                flight_type = "REGRESO" if is_return else "IDA"
                
                self._send_response(phone, f"✈️ *Seleccionando vuelo de {flight_type}...*", session)
                
                result = self._select_flight_and_get_prices_function(
                    function_args.get('flight_index'),
                    session,
                    is_return
                )
            elif function_name == "confirm_flight_and_get_prices":
                # Confirmar vuelo y obtener precios de clases
                is_return = function_args.get('is_return', False)
                flight_type = "REGRESO" if is_return else "IDA"
                
                # Marcar como confirmado
                if is_return:
                    session.data['return_flight_confirmed'] = True
                    flight_index = session.data.get('pending_return_flight_index')
                else:
                    session.data['flight_confirmed'] = True
                    flight_index = session.data.get('pending_flight_index')
                
                if not flight_index:
                    result = {"success": False, "message": "No hay vuelo pendiente de confirmación."}
                else:
                    self._send_response(phone, f"💰 *Consultando precios de todas las clases disponibles para vuelo de {flight_type}...*\n\n⏳ Un momento por favor...", session)
                    result = self._select_flight_and_get_prices_function(
                        flight_index,
                        session,
                        is_return
                    )
            elif function_name == "confirm_flight_selection":
                is_return = function_args.get('is_return', False)
                
                self._send_response(phone, "📝 *Preparando confirmación de vuelo...*", session)
                
                result = self._confirm_flight_selection_function(
                    function_args.get('flight_index'),
                    function_args.get('flight_class'),
                    session,
                    is_return
                )

            elif function_name == "create_booking":
                passenger_name = function_args.get('passenger_name', 'pasajero')
                self._send_response(phone, f"🎫 *Creando tu reserva...*\n\n👤 Pasajero: {passenger_name}\n\n⏳ Un momento por favor, estoy procesando tu solicitud...", session)
                result = self._create_booking_function(
                    function_args.get('flight_index'),
                    function_args.get('flight_class'),
                    passenger_name,
                    function_args.get('id_number'),
                    function_args.get('phone'),
                    function_args.get('email'),
                    session,
                    function_args.get('city'),
                    function_args.get('address')
                )
            else:
                result = {"error": "Función no reconocida"}
            # MANEJO MANUAL DE RESPUESTAS ESTRUCTURADAS
            # Si la función devuelve un mensaje formateado (ej: confirmaciones, tablas),
            # lo enviamos directamente para evitar que la AI lo modifique o alucine.
            structured_message = result.get('message')
            if structured_message and isinstance(structured_message, str):
                # Solo enviar directo si parece un mensaje final formateado (empieza con emojis o tiene estructura)
                if any(start in structured_message for start in ['✅', '✈️', '💰', '📋', '❌', '📝']):
                    logger.info("Enviando mensaje estructurado directamente (bypass AI generation)")
                    self._send_response(phone, structured_message, session)
                    
                    # Agregar al historial como si la AI lo hubiera generado
                    # ...
                    return None
            
            # Si no es un mensaje estructurado, flujo normal
            # Agregar la llamada a función y el resultado al historial
            history.append({
                "role": "model",
                "parts": [{"function_call": function_call}]
            })
            history.append({
                "role": "function",
                "parts": [{"function_response": {
                    "name": function_name,
                    "response": result
                }}]
            })
            # Llamar de nuevo a Gemini con el resultado (con reintentos)
            max_follow_up_retries = 3
            ai_response = None
            
            for attempt in range(max_follow_up_retries):
                try:
                    follow_up = self.client.models.generate_content(
                        model=self.model,
                        contents=history,
                        config=types.GenerateContentConfig(
                            system_instruction=system_with_date,
                            temperature=1.0
                        )
                    )
                    
                    # Validar respuesta
                    if follow_up and follow_up.candidates and len(follow_up.candidates) > 0:
                        candidate = follow_up.candidates[0]
                        if candidate.content and candidate.content.parts and len(candidate.content.parts) > 0:
                            first_part = candidate.content.parts[0]
                            if hasattr(first_part, 'text') and first_part.text:
                                ai_response = first_part.text
                                break
                    
                    # Si no hay respuesta válida, reintentar
                    if attempt < max_follow_up_retries - 1:
                        logger.warning(f"Respuesta vacía de Gemini en intento {attempt + 1}, reintentando...")
                        # time ya importado al inicio del archivo
                        time.sleep(1)
                        continue
                        
                except Exception as retry_error:
                    logger.warning(f"Error en follow-up intento {attempt + 1}: {str(retry_error)}")
                    if attempt < max_follow_up_retries - 1:
                        # time ya importado al inicio del archivo
                        time.sleep(2)
                        continue
                    else:
                        raise
            
            if ai_response:
                # Agregar respuesta final al historial
                history.append({
                    "role": "model",
                    "parts": [{"text": ai_response}]
                })
                session.data['ai_history'] = history
                return self._send_response(phone, ai_response, session)
            else:
                # Si no hay respuesta después de reintentos, enviar mensaje por defecto
                logger.warning("No se obtuvo respuesta de Gemini después de reintentos")
                return self._send_response(phone, "✅ He procesado tu solicitud. ¿En qué más puedo ayudarte?", session)
        except Exception as e:
            # traceback ya importado al inicio del archivo
            error_details = traceback.format_exc()
            error_str = str(e).lower()
            error_type = type(e).__name__
            logger.error(f"Error manejando función: {str(e)}\nTraceback:\n{error_details}")
            
            # DEBUG: Incluir error real en el mensaje
            debug_info = f"\n\n🔧 DEBUG: {error_type}: {str(e)[:200]}"
            
            # Mensajes de error más específicos según el tipo de problema
            if 'timeout' in error_str or 'timed out' in error_str or 'connection' in error_str:
                return self._send_response(phone, f"⏱️ *La búsqueda tardó demasiado*\n\nEl servidor está tardando en responder. Por favor intenta de nuevo en unos segundos.{debug_info}", session)
            elif '503' in error_str or 'unavailable' in error_str or 'overloaded' in error_str:
                return self._send_response(phone, f"⚠️ *Servidor temporalmente ocupado*\n\nHay mucha demanda en este momento. Por favor intenta de nuevo en 30 segundos.{debug_info}", session)
            elif '429' in error_str or 'quota' in error_str or 'rate limit' in error_str:
                return self._send_response(phone, f"⏳ *Límite de solicitudes alcanzado*\n\nPor favor espera 1 minuto e intenta de nuevo.{debug_info}", session)
            elif 'invalid' in error_str or 'argument' in error_str:
                return self._send_response(phone, f"❌ *Datos incorrectos*\n\nParece que hay un problema con los datos ingresados. Por favor verifica la información e intenta de nuevo.{debug_info}", session)
            else:
                return self._send_response(phone, f"😅 *Hubo un problema con la búsqueda*\n\nPor favor intenta de nuevo. Si el problema persiste, intenta con otra fecha o ruta.{debug_info}", session)
    def _search_flights_function(self, origin, destination, date, session, trip_type='ida', adults=1, children=0, infants=0):
        """Busca vuelos usando el servicio"""
        try:
            # MAPEO DE CIUDADES A CÓDIGOS IATA
            iata_codes = {
                'CARACAS': 'CCS', 'MAIQUETIA': 'CCS', 'LA GUAIRA': 'CCS',
                'MARGARITA': 'PMV', 'PORLAMAR': 'PMV', 
                'MARACAIBO': 'MAR', 'ZULIA': 'MAR',
                'VALENCIA': 'VLN', 'CARABOBO': 'VLN',
                'PUERTO ORDAZ': 'PZO', 'GUAYANA': 'PZO', 'CIUDAD GUAYANA': 'PZO',
                'BARCELONA': 'BLA', 'ANZOATEGUI': 'BLA',
                'MERIDA': 'MRD', # MRD is Alberto Carnevalli (city), VIG is El Vigia (usually used for Merida)
                'EL VIGIA': 'VIG', 'VIGIA': 'VIG', 'ALBERTO ADRIANI': 'VIG',
                'BARQUISIMETO': 'BRM', 'LARA': 'BRM',
                'CUMANA': 'CUM', 'SUCRE': 'CUM',
                'MATURIN': 'MUN', 'MONAGAS': 'MUN',
                'SANTO DOMINGO': 'STD', 'TACHIRA': 'STD',
                'SAN CRISTOBAL': 'STD', # Serves San Cristobal
                'LA FRIA': 'LFR', 'GARCIA DE HEVIA': 'LFR',
                'SAN ANTONIO': 'SVZ', 'SAN ANTONIO DEL TACHIRA': 'SVZ',
                'VALERA': 'VLV', 'TRUJILLO': 'VLV',
                'CORO': 'CZE', 'FALCON': 'CZE',
                'LAS PIEDRAS': 'LSP', 'PUNTO FIJO': 'LSP', 'PARAGUANA': 'LSP',
                'CIUDAD BOLIVAR': 'CBL',
                'CANAIMA': 'CAJ',
                'LOS ROQUES': 'LRV',
                'PORLAMAR': 'PMV',
                'PUERTO AYACUCHO': 'PYH', 'AMAZONAS': 'PYH',
                'SAN FERNANDO': 'SFD', 'APURE': 'SFD',
                'ACARIGUA': 'AGV', 'PORTUGUESA': 'AGV',
                'GUASDUALITO': 'GDO',
                'TUCUPITA': 'TUV', 'DELTA AMACURO': 'TUV',
                
                # INTERNACIONALES
                'MIAMI': 'MIA',
                'PANAMA': 'PTY', 'TOCUMEN': 'PTY',
                'BOGOTA': 'BOG', 'EL DORADO': 'BOG',
                'MEDELLIN': 'MDE', 'RIO NEGRO': 'MDE',
                'MADRID': 'MAD', 'BARAJAS': 'MAD',
                'SANTO DOMINGO RD': 'SDQ', 'REPUBLICA DOMINICANA': 'SDQ',
                'PUNTA CANA': 'PUJ',
                'CANCUN': 'CUN', 'MEXICO': 'MEX',
                'LIMA': 'LIM', 'PERU': 'LIM',
                'SANTIAGO': 'SCL', 'CHILE': 'SCL',
                'BUENOS AIRES': 'EZE', 'ARGENTINA': 'EZE',
                'SAO PAULO': 'GRU', 'BRASIL': 'GRU',
                'LISBOA': 'LIS', 'PORTUGAL': 'LIS',
                'TENERIFE': 'TFN',
                'CURAZAO': 'CUR', 'WILLEMSTAD': 'CUR',
                'ARUBA': 'AUA',
                'BONAIRE': 'BON',
                'TRINIDAD': 'POS', 'PUERTO ESPAÑA': 'POS'
            }
            
            # Normalizar origen
            origin_upper = origin.upper().strip()
            if len(origin_upper) > 3:
                # Intentar mapear nombre de ciudad a código
                for city, code in iata_codes.items():
                    if city in origin_upper:
                        origin = code
                        break
            
            # Normalizar destino
            dest_upper = destination.upper().strip()
            if len(dest_upper) > 3:
                # Intentar mapear nombre de ciudad a código
                for city, code in iata_codes.items():
                    if city in dest_upper:
                        destination = code
                        break
            
            logger.info(f"Buscando vuelos normalizado: {origin} -> {destination}")

            # Construir diccionario de pasajeros para la BÚSQUEDA
            # IMPORTANTE: La API de búsqueda KIU puede no soportar CHD/INF
            # correctamente, así que buscamos con el total de pasajeros como ADT
            # Los tipos reales (ADT/CHD/INF) se usan al momento del BOOKING
            total_pax = adults + children + infants
            if total_pax < 1:
                total_pax = 1
            passengers = {"ADT": total_pax}
            
            logger.info(f"Pasajeros para búsqueda: {passengers} (real: ADT={adults}, CHD={children}, INF={infants})")

            # Intentar búsqueda con reintentos agresivos en caso de timeout
            max_retries = 5
            flights = None
            last_error = None
            for attempt in range(max_retries):
                try:
                    flights = flight_service.search_flights(
                        origin=origin,
                        destination=destination,
                        date=date,
                        passengers=passengers
                    )
                    break
                except Exception as search_error:
                    last_error = str(search_error)
                    error_lower = last_error.lower()
                    if 'timeout' in error_lower or 'tardó demasiado' in error_lower or 'timed out' in error_lower or 'connection' in error_lower:
                        if attempt < max_retries - 1:
                            logger.warning(f"Error en búsqueda (intento {attempt + 1}/{max_retries}): {last_error}")
                            # time ya importado al inicio del archivo
                            wait_time = 5 + (attempt * 2)
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"Todos los intentos fallaron: {last_error}")
                    else:
                        raise

            if not flights:
                # Mensaje mejorado con información sobre reintentos
                logger.error(f"flights es None o vacío: {flights}")
                error_msg = f"No se encontraron vuelos disponibles para la ruta {origin} → {destination} en la fecha {date}."
                if last_error:
                    error_lower = last_error.lower()
                    if 'timeout' in error_lower or 'tardó demasiado' in error_lower or 'timed out' in error_lower:
                        error_msg += f"\n\nLa API no respondió después de {max_retries} intentos automáticos. Esto puede deberse a:\n\n1. Alta demanda en el sistema\n2. Problemas de conectividad\n3. La ruta no tiene vuelos disponibles\n\nPor favor intenta:\n• Buscar en otra fecha\n• Intentar de nuevo en 1 minuto\n• Verificar que la ruta sea correcta"
                    else:
                        error_msg += f"\n\nEsto puede deberse a que:\n1. No hay vuelos operando en esa fecha\n2. Los vuelos están agotados\n3. La ruta no es válida\n\nPor favor intenta con otra fecha o ruta."
                return {
                    "success": False, 
                    "message": error_msg
                }
            # Guardar vuelos en la sesión según el tipo de viaje
            if trip_type == 'vuelta':
                session.data['return_flights'] = flights
            else:
                session.data['available_flights'] = flights
            # Formatear vuelos para la IA con TODOS los campos
            flights_data = []
            for i, flight in enumerate(flights, 1):  # TODOS los vuelos
                api_data = flight.get('api_data', {})
                segments = api_data.get('segments', [])
                segment = segments[0] if segments else {}
                # Construir ruta completa si hay múltiples segmentos
                if len(segments) > 1:
                    route_parts = []
                    for seg in segments:
                        if not route_parts:
                            route_parts.append(seg.get('departureCode', ''))
                        route_parts.append(seg.get('arrivalCode', ''))
                    ruta_completa = ' → '.join(route_parts)
                    escalas = len(segments) - 1
                else:
                    ruta_completa = f"{flight.get('origin')} → {flight.get('destination')}"
                    escalas = 0
                currency_symbol = "$"
                # Extraer y clasificar clases disponibles
                clases_disponibles = segment.get('classes', {})
                economy_classes = []
                business_classes = []
                first_classes = []
                # Validar que clases_disponibles sea un diccionario
                if isinstance(clases_disponibles, dict):
                    for clase_code, asientos in clases_disponibles.items():
                        if clase_code in ['Y', 'B', 'M', 'H', 'Q', 'V', 'W', 'S', 'T', 'L', 'K', 'G', 'U', 'E', 'N', 'R', 'O']:
                            economy_classes.append({"codigo": clase_code, "asientos": asientos})
                        elif clase_code in ['J', 'C', 'D', 'I', 'Z']:
                            business_classes.append({"codigo": clase_code, "asientos": asientos})
                        elif clase_code in ['F', 'A', 'P']:
                            first_classes.append({"codigo": clase_code, "asientos": asientos})
                        else:
                            economy_classes.append({"codigo": clase_code, "asientos": asientos})
                flight_info = {
                    "numero": i,
                    "aerolinea": flight.get('airline_name'),
                    "vuelo": flight.get('flight_number'),
                    "ruta": ruta_completa,
                    "escalas": escalas,
                    "salida": flight.get('departure_time'),
                    "llegada": flight.get('arrival_time'),
                    "duracion": flight.get('duration'),
                    "precio_total": f"{currency_symbol}{flight.get('price'):.2f}" if flight.get('price') else "Consultar",
                    "moneda": flight.get('currency', 'USD'),
                    "clases_economica": economy_classes,
                    "clases_business": business_classes,
                    "clases_primera": first_classes,
                    "internacional": api_data.get('international', False),
                    "directo": api_data.get('isDirect', True)
                }
                flights_data.append(flight_info)
            return {
                "success": True,
                "total": len(flights),
                "vuelos": flights_data,
                "ruta": f"{origin} → {destination}",
                "fecha": format_date_dd_mm_yyyy(date),
                "tipo_viaje": "Solo Ida" if trip_type == 'ida' else "Vuelta"
            }
        except Exception as e:
            logger.error(f"Error buscando vuelos: {str(e)}")
            return {"success": False, "error": str(e)}
    def _get_booking_function(self, pnr):
        """Consulta una reserva con TODOS los detalles posibles de KIU"""
        try:
            result = flight_service.get_booking_details(pnr=pnr)
            
            # DEBUG: Ver respuesta completa
            logger.info(f"=== RESPUESTA COMPLETA DE KIU ===")
            logger.info(f"Success: {result.get('success')}")
            logger.info(f"Flights: {result.get('flights')}")
            logger.info(f"Passengers: {result.get('passengers')}")
            
            if not result.get('success'):
                return {"success": False, "message": "Reserva no encontrada"}
            
            # Obtener datos
            pasajeros = result.get('passengers', [])
            vuelos = result.get('flights', [])
            precio_total = result.get('balance', 'N/A')
            estado = result.get('status', 'N/A')
            vencimiento = result.get('vencimiento', '')
            vid = result.get('vid', '')
            base = result.get('base', '')
            ruta = result.get('route', '')
            flight_status = result.get('flight_status', '')
            
            # Determinar tipo de viaje
            num_vuelos = len(vuelos)
            tipo_viaje = "🔄 IDA Y VUELTA" if num_vuelos >= 2 else "✈️ SOLO IDA"
            
            # Formatear mensaje
            mensaje = f"""🎉 *DETALLES DE TU RESERVA*

━━━━━━━━━━━━━━━━━━━━━━

🎫 *DATOS DE LA RESERVA*
📌 *PNR:* {result.get('pnr', pnr)}"""

            if vid:
                mensaje += f"""
🆔 *VID:* {vid}"""
            
            mensaje += f"""
🎫 *Tipo:* {tipo_viaje}
📊 *Estado:* {estado}"""

            if vencimiento:
                mensaje += f"""
⏰ *Vencimiento:* {vencimiento}"""
            
            if ruta:
                mensaje += f"""
📍 *Ruta:* {ruta}"""

            # Pasajeros
            mensaje += f"""

━━━━━━━━━━━━━━━━━━━━━━

👥 *PASAJEROS ({len(pasajeros)})*"""

            for i, pax in enumerate(pasajeros, 1):
                nombre = pax.get('nombre', 'N/A')
                documento = pax.get('documento', 'N/A')
                tipo = pax.get('tipo', '')
                telefono = pax.get('telefono', '')
                
                mensaje += f"""

👤 *Pasajero {i}:*
   👤 {nombre}
   🆔 {documento}"""
                
                if tipo:
                    mensaje += f"""
   🏷️ Tipo: {tipo}"""
                if telefono:
                    mensaje += f"""
   📱 Tel: {telefono}"""

            # Vuelos
            if vuelos and len(vuelos) > 0:
                for i, vuelo in enumerate(vuelos, 1):
                    tipo_vuelo = "IDA" if i == 1 else "VUELTA" if i == 2 else f"VUELO {i}"
                    
                    # Construir ruta completa (si tiene escalas, mostrarlas)
                    ruta = vuelo.get('ruta', 'N/A')
                    if '-' in ruta and '→' not in ruta:
                        ruta = ' → '.join(ruta.split('-'))
                    
                    mensaje += f"""

━━━━━━━━━━━━━━━━━━━━━━

✈️ *VUELO DE {tipo_vuelo}*
✈️ *Aerolínea:* {vuelo.get('aerolinea', 'N/A')}
🎫 *Vuelo:* {vuelo.get('vuelo', 'N/A')}
📍 *Ruta:* {ruta}
📅 *Fecha:* {format_date_dd_mm_yyyy(vuelo.get('fecha', 'N/A'))}
🕐 *Salida:* {vuelo.get('hora_salida', 'N/A')}
🕐 *Llegada:* {vuelo.get('hora_llegada', 'N/A')}
💺 *Clase:* {vuelo.get('clase', 'N/A')}
📊 *Estado:* {vuelo.get('estado', 'N/A')}"""
                    
                    if vuelo.get('precio'):
                        mensaje += f"""
💰 *Precio:* {vuelo.get('precio')}"""
            elif ruta:
                # Si no hay vuelos pero hay ruta, mostrar la ruta
                mensaje += f"""

━━━━━━━━━━━━━━━━━━━━━━

✈️ *VUELO*
📍 *Ruta:* {ruta.replace('-', ' → ')}
📊 *Estado:* {estado}"""

            # Costos
            mensaje += f"""

━━━━━━━━━━━━━━━━━━━━━━

💰 *RESUMEN DE COSTOS*"""
            
            try:
                # re ya importado al inicio del archivo
                precio_limpio = re.sub(r'[^\d.]', '', str(precio_total))
                if precio_limpio and len(pasajeros) > 0:
                    precio_float = float(precio_limpio)
                    precio_unitario = precio_float / len(pasajeros)
                    mensaje += f"""
   💵 *Por persona:* ${precio_unitario:.2f} USD
   👥 *Pasajeros:* {len(pasajeros)}
   ━━━━━━━━━━━━━━━━━━━━"""
            except:
                pass

            mensaje += f"""
   💰 *TOTAL:* {precio_total}"""
            
            mensaje += f"""

━━━━━━━━━━━━━━━━━━━━━━

✈️ *¡Buen viaje!* 🦌

💡 Código PNR: *{result.get('pnr', pnr)}*"""

            return {
                "success": True,
                "message": mensaje,
                "pnr": result.get('pnr'),
                "estado": estado,
                "pasajeros_count": len(pasajeros),
                "vuelos_count": num_vuelos,
                "precio_total": precio_total,
                "pasajeros": pasajeros,
                "vuelos": vuelos
            }
        except Exception as e:
            logger.error(f"Error consultando reserva: {str(e)}")
            return {"success": False, "error": str(e)}
    def _get_requirements_function(self, country):
        """Obtiene requisitos migratorios"""
        try:
            requisitos = get_requisitos_pais(country.lower())
            if requisitos:
                return {"success": True, "requisitos": requisitos}
            else:
                return {"success": False, "message": "País no encontrado en la base de datos"}
        except Exception as e:
            logger.error(f"Error obteniendo requisitos: {str(e)}")
            return {"success": False, "error": str(e)}
    def _select_flight_and_get_prices_function(self, flight_index, session, is_return=False):
        """Selecciona un vuelo, muestra resumen y pide confirmación antes de obtener precios"""
        try:
            # Seleccionar la lista correcta según si es vuelo de ida o vuelta
            if is_return:
                flights = session.data.get('return_flights', [])
                flight_type = "REGRESO"
            else:
                flights = session.data.get('available_flights', [])
                flight_type = "IDA"
            
            if not flights:
                return {"success": False, "message": f"No hay vuelos de {flight_type} disponibles. Primero debes buscar vuelos."}
            if flight_index < 1 or flight_index > len(flights):
                return {"success": False, "message": f"Número de vuelo inválido. Debe ser entre 1 y {len(flights)}"}
            
            selected_flight = flights[flight_index - 1]
            
            # Verificar si ya confirmó este vuelo
            if is_return:
                already_confirmed = session.data.get('return_flight_confirmed', False)
            else:
                already_confirmed = session.data.get('flight_confirmed', False)
            
            # Si NO ha confirmado, mostrar resumen y pedir confirmación
            if not already_confirmed:
                airline = selected_flight.get('airline_name', 'N/A')
                flight_num = selected_flight.get('flight_number', 'N/A')
                origin = selected_flight.get('origin', 'N/A')
                destination = selected_flight.get('destination', 'N/A')
                date = selected_flight.get('date', 'N/A')
                departure = selected_flight.get('departure_time', 'N/A')
                arrival = selected_flight.get('arrival_time', 'N/A')
                duration = selected_flight.get('duration', 'N/A')
                price = selected_flight.get('price', 0)
                
                # Guardar índice en sesión para cuando confirme
                if is_return:
                    session.data['pending_return_flight_index'] = flight_index
                else:
                    session.data['pending_flight_index'] = flight_index
            
            # ACTIVAR MODO CONFIRMACIÓN
            # Esto es CRÍTICO para que _process_with_ai intercepte el "SI" y no la AI
            session.data['awaiting_flight_confirmation'] = True
            session.data['flight_selection_fully_confirmed'] = False
                
                return {
                    "success": True,
                    "needs_confirmation": True,
                    "flight_index": flight_index,
                    "aerolinea": airline,
                    "vuelo": flight_num,
                    # Construir ruta completa con escalas
                    "ruta": f"{selected_flight.get('origin')} → {' → '.join([s.get('arrivalCode') for s in selected_flight.get('api_data', {}).get('segments', [])])}" if len(selected_flight.get('api_data', {}).get('segments', [])) > 1 else f"{origin} → {destination}",
                    "fecha": format_date_dd_mm_yyyy(date),
                    "salida": departure,
                    "llegada": arrival,
                    "duracion": duration,
                    "precio_desde": f"{price:.2f}" if price else "Consultar",
                    "moneda": "USD",
                    "message": f"""✅ *VUELO SELECCIONADO*

✈️ *Vuelo:* {airline} {flight_num}
📍 *Ruta:* {f"{selected_flight.get('origin')} → {' → '.join([s.get('arrivalCode') for s in selected_flight.get('api_data', {}).get('segments', [])])}" if len(selected_flight.get('api_data', {}).get('segments', [])) > 1 else f"{origin} → {destination}"}
📅 *Fecha:* {format_date_dd_mm_yyyy(date)}
🕐 *Salida:* {departure}
🕐 *Llegada:* {arrival}
💰 *Precio:* ${price:.2f} USD

━━━━━━━━━━━━━━━━━━━━━━

✅ *¿Confirmas esta selección?*
Responde *SÍ* para continuar con la selección de CLASE o *NO* para cambiar."""
                }
            
            # Si YA confirmó, obtener precios de clases
            airline = selected_flight.get('airline_name', 'N/A')
            flight_num = selected_flight.get('flight_number', 'N/A')
            logger.info(f"=== OBTENIENDO PRECIOS PARA VUELO DE {flight_type} {flight_index}: {airline} {flight_num} ===")
            
            # Guardar vuelo seleccionado en sesión
            if is_return:
                session.data['selected_return_flight_index'] = flight_index
                session.data['selected_return_flight'] = selected_flight
            else:
                session.data['selected_flight_index'] = flight_index
                session.data['selected_flight'] = selected_flight
            
            # Obtener precios de todas las clases
            pricing_result = flight_service.get_all_class_prices(selected_flight)
            if not pricing_result.get('success'):
                return {
                    "success": False,
                    "message": "No se pudieron obtener los precios de las clases. Por favor intenta de nuevo."
                }
            
            classes_prices = pricing_result.get('classes_prices', {})
            if not classes_prices:
                return {
                    "success": False,
                    "message": "No se encontraron precios disponibles para este vuelo."
                }
            
            # Guardar precios en sesión
            if is_return:
                session.data['return_flight_classes_prices'] = classes_prices
            else:
                session.data['flight_classes_prices'] = classes_prices
            
            # Clasificar clases por tipo
            economy_classes = []
            business_classes = []
            first_classes = []
            economy_codes = ['Y', 'B', 'M', 'H', 'Q', 'V', 'W', 'S', 'T', 'L', 'K', 'G', 'U', 'E', 'N', 'R', 'O']
            business_codes = ['J', 'C', 'D', 'I', 'Z']
            first_codes = ['F', 'A', 'P']
            
            for class_code, class_data in classes_prices.items():
                class_info = {
                    "codigo": class_code,
                    "precio": class_data['price'],
                    "asientos": class_data['availability']
                }
                if class_code in economy_codes:
                    economy_classes.append(class_info)
                elif class_code in business_codes:
                    business_classes.append(class_info)
                elif class_code in first_codes:
                    first_classes.append(class_info)
                else:
                    economy_classes.append(class_info)
            
            # Ordenar por precio
            economy_classes.sort(key=lambda x: x['precio'])
            business_classes.sort(key=lambda x: x['precio'])
            first_classes.sort(key=lambda x: x['precio'])
            
            return {
                "success": True,
                "flight_index": flight_index,
                "aerolinea": selected_flight.get('airline_name'),
                "vuelo": selected_flight.get('flight_number'),
                "ruta": f"{selected_flight.get('origin')} → {' → '.join([s.get('arrivalCode') for s in selected_flight.get('api_data', {}).get('segments', [])])}" if len(selected_flight.get('api_data', {}).get('segments', [])) > 1 else f"{selected_flight.get('origin')} → {selected_flight.get('destination')}",
                "fecha": format_date_dd_mm_yyyy(selected_flight.get('date')),
                "salida": selected_flight.get('departure_time'),
                "llegada": selected_flight.get('arrival_time'),
                "duracion": selected_flight.get('duration'),
                "economy_classes": economy_classes,
                "business_classes": business_classes,
                "first_classes": first_classes,
                "total_classes": len(classes_prices),
                "message": f"Vuelo confirmado. Aquí están los precios de todas las clases disponibles."
            }
        except Exception as e:
            logger.error(f"Error obteniendo precios de clases: {str(e)}")
            return {"success": False, "error": str(e)}
    def _confirm_flight_selection_function(self, flight_index, flight_class, session, is_return=False):
        """Muestra detalles del vuelo seleccionado con la clase elegida y pide confirmación. Para IDA Y VUELTA, muestra resumen de ambos vuelos."""
        try:
            # Seleccionar la lista correcta según si es vuelo de ida o vuelta
            if is_return:
                flights = session.data.get('return_flights', [])
                flight_type = "REGRESO"
            else:
                flights = session.data.get('available_flights', [])
                flight_type = "IDA"
            
            if not flights:
                return {"success": False, "message": f"No hay vuelos de {flight_type} disponibles. Primero debes buscar vuelos."}
            
            # Validar parámetros
            if flight_index is None:
                flight_index = session.data.get('selected_flight_index', 1)
            if flight_class is None:
                return {"success": False, "message": "Por favor selecciona una clase de vuelo."}
            
            if flight_index < 1 or flight_index > len(flights):
                return {"success": False, "message": f"Número de vuelo inválido. Debe ser entre 1 y {len(flights)}"}
            selected_flight = flights[flight_index - 1]
            # Validar que la clase existe en el vuelo
            api_data = selected_flight.get('api_data', {})
            segments = api_data.get('segments', [])
            if segments:
                available_classes = segments[0].get('classes', {})
                if flight_class.upper() not in available_classes:
                    return {"success": False, "message": f"La clase {flight_class} no está disponible en este vuelo. Clases disponibles: {', '.join(available_classes.keys())}"}
            # Guardar vuelo y clase seleccionados en sesión (diferenciando ida y vuelta)
            if is_return:
                session.data['selected_return_flight_index'] = flight_index
                session.data['selected_return_flight_class'] = flight_class.upper()
            else:
                session.data['selected_flight_index'] = flight_index
                session.data['selected_flight_class'] = flight_class.upper()
            session.data['awaiting_flight_confirmation'] = True
            
            # SI ES VUELO DE VUELTA
            if is_return:
                # Determinar si ya confirmó este vuelo de vuelta y solo quiere el resumen final
                already_confirmed_return = session.data.get('return_flight_fully_confirmed', False)
                
                # Si NO ha confirmado explícitamente el vuelo de vuelta, mostramos solo ese vuelo
                if not already_confirmed_return:
                    asientos_disponibles = available_classes.get(flight_class.upper(), 'N/A') if segments else 'N/A'
                    
                    # Obtener precio correcto de la clase
                    precio_clase = selected_flight.get('price')
                    vuelta_classes_prices = session.data.get('return_flight_classes_prices', {})
                    if vuelta_classes_prices and flight_class.upper() in vuelta_classes_prices:
                        precio_clase = vuelta_classes_prices[flight_class.upper()].get('price', precio_clase)
                    
                    return {
                        "success": True,
                        "is_round_trip_summary": False, # Aún no es el resumen final
                        "is_return_flight": True,
                        "aerolinea": selected_flight.get('airline_name'),
                        "vuelo": selected_flight.get('flight_number'),
                        "ruta": f"{selected_flight.get('origin')} → {' → '.join([s.get('arrivalCode') for s in selected_flight.get('api_data', {}).get('segments', [])])}" if len(selected_flight.get('api_data', {}).get('segments', [])) > 1 else f"{selected_flight.get('origin')} → {selected_flight.get('destination')}",
                        "fecha": format_date_dd_mm_yyyy(selected_flight.get('date')),
                        "salida": selected_flight.get('departure_time'),
                        "llegada": selected_flight.get('arrival_time'),
                        "duracion": selected_flight.get('duration'),
                        "clase_seleccionada": flight_class.upper(),
                        "precio": f"{precio_clase:.2f}" if precio_clase else "Consultar",
                        "moneda": "USD", 
                        "message": f"""✅ *VUELO DE REGRESO SELECCIONADO*

✈️ *Vuelo:* {selected_flight.get('airline_name')} {selected_flight.get('flight_number')}
📍 *Ruta:* {f"{selected_flight.get('origin')} → {' → '.join([s.get('arrivalCode') for s in selected_flight.get('api_data', {}).get('segments', [])])}" if len(selected_flight.get('api_data', {}).get('segments', [])) > 1 else f"{selected_flight.get('origin')} → {selected_flight.get('destination')}"}
📅 *Fecha:* {format_date_dd_mm_yyyy(selected_flight.get('date'))}
🕐 *Salida:* {selected_flight.get('departure_time')}
🕐 *Llegada:* {selected_flight.get('arrival_time')}
💺 *Clase:* {flight_class.upper()} ({asientos_disponibles} as.)
💰 *Precio:* ${precio_clase:.2f} USD

━━━━━━━━━━━━━━━━━━━━━━

✅ *¿Confirmas esta selección?*
Responde *SÍ* para continuar o *NO* para cambiar."""
                    }

                # Si ya confirmó, mostramos el resumen completo IDA + VUELTA
                # Obtener datos del vuelo de IDA
                # Obtener datos del vuelo de IDA
                ida_flights = session.data.get('available_flights', [])
                ida_index = session.data.get('selected_flight_index', 1)
                ida_class = session.data.get('selected_flight_class', 'Y')
                
                if ida_flights and ida_index >= 1 and ida_index <= len(ida_flights):
                    ida_flight = ida_flights[ida_index - 1]
                    
                    # Obtener precios
                    ida_classes_prices = session.data.get('flight_classes_prices', {})
                    vuelta_classes_prices = session.data.get('return_flight_classes_prices', {})
                    
                    precio_ida = ida_flight.get('price', 0)
                    if ida_classes_prices and ida_class.upper() in ida_classes_prices:
                        precio_ida = ida_classes_prices[ida_class.upper()].get('price', precio_ida)
                    
                    precio_vuelta = selected_flight.get('price', 0)
                    if vuelta_classes_prices and flight_class.upper() in vuelta_classes_prices:
                        precio_vuelta = vuelta_classes_prices[flight_class.upper()].get('price', precio_vuelta)
                    
                    # Calcular total
                    num_passengers = session.data.get('num_passengers', 1)
                    precio_por_persona = precio_ida + precio_vuelta
                    precio_total = precio_por_persona * num_passengers
                    
                    return {
                        "success": True,
                        "is_round_trip_summary": True,
                        "num_passengers": num_passengers,
                        # Vuelo de IDA
                        "ida_aerolinea": ida_flight.get('airline_name'),
                        "ida_vuelo": ida_flight.get('flight_number'),
                        "ida_ruta": f"{ida_flight.get('origin')} → {ida_flight.get('destination')}",
                        "ida_fecha": ida_flight.get('date'),
                        "ida_salida": ida_flight.get('departure_time'),
                        "ida_llegada": ida_flight.get('arrival_time'),
                        "ida_clase": ida_class.upper(),
                        "ida_precio": f"{precio_ida:.2f}",
                        # Vuelo de VUELTA
                        "vuelta_aerolinea": selected_flight.get('airline_name'),
                        "vuelta_vuelo": selected_flight.get('flight_number'),
                        "vuelta_ruta": f"{selected_flight.get('origin')} → {selected_flight.get('destination')}",
                        "vuelta_fecha": selected_flight.get('date'),
                        "vuelta_salida": selected_flight.get('departure_time'),
                        "vuelta_llegada": selected_flight.get('arrival_time'),
                        "vuelta_clase": flight_class.upper(),
                        "vuelta_precio": f"{precio_vuelta:.2f}",
                        # Totales
                        "precio_por_persona": f"{precio_por_persona:.2f}",
                        "precio_total": f"{precio_total:.2f}",
                        "moneda": "USD",
                        "message": f"""✈️ *RESUMEN DE TU VIAJE IDA Y VUELTA*

━━━━━━━━━━━━━━━━━━━━━━

✈️ *VUELO DE IDA*
✈️ *Aerolínea:* {ida_flight.get('airline_name')} {ida_flight.get('flight_number')}
📍 *Ruta:* {ida_flight.get('origin')} → {ida_flight.get('destination')}
📅 *Fecha:* {format_date_dd_mm_yyyy(ida_flight.get('date'))}
🕐 *Salida:* {ida_flight.get('departure_time')}
🕐 *Llegada:* {ida_flight.get('arrival_time')}
💺 *Clase:* {ida_class.upper()}
💰 *Precio:* ${precio_ida:.2f} USD

━━━━━━━━━━━━━━━━━━━━━━

✈️ *VUELO DE VUELTA*
✈️ *Aerolínea:* {selected_flight.get('airline_name')} {selected_flight.get('flight_number')}
📍 *Ruta:* {selected_flight.get('origin')} → {selected_flight.get('destination')}
📅 *Fecha:* {format_date_dd_mm_yyyy(selected_flight.get('date'))}
🕐 *Salida:* {selected_flight.get('departure_time')}
🕐 *Llegada:* {selected_flight.get('arrival_time')}
💺 *Clase:* {flight_class.upper()}
💰 *Precio:* ${precio_vuelta:.2f} USD

━━━━━━━━━━━━━━━━━━━━━━

💰 *RESUMEN DE COSTOS*
   💵 *Por persona:* ${precio_por_persona:.2f} USD
   👥 *Pasajeros:* {num_passengers}
   ━━━━━━━━━━━━━━━━━━━━
   💰 *TOTAL A PAGAR:* ${precio_total:.2f} USD

━━━━━━━━━━━━━━━━━━━━━━

✅ *¿Confirmas estos vuelos?*
Responde *SÍ* para continuar con la reserva o *NO* para cambiar."""
                    }
                else:
                    return {"success": False, "message": "No se encontró información del vuelo de IDA seleccionado."}
            
            # SI ES SOLO IDA, MOSTRAR CONFIRMACIÓN NORMAL
            # Extraer detalles del vuelo
            api_data = selected_flight.get('api_data', {})
            segments = api_data.get('segments', [])
            # Construir ruta completa
            if len(segments) > 1:
                route_parts = []
                for seg in segments:
                    if not route_parts:
                        route_parts.append(seg.get('departureCode', ''))
                    route_parts.append(seg.get('arrivalCode', ''))
                ruta = ' → '.join(route_parts)
                escalas = len(segments) - 1
            else:
                ruta = f"{selected_flight.get('origin')} → {selected_flight.get('destination')}"
                escalas = 0
            # Obtener asientos disponibles para la clase seleccionada
            asientos_disponibles = "N/A"
            if segments:
                available_classes = segments[0].get('classes', {})
                asientos_disponibles = available_classes.get(flight_class.upper(), "N/A")
            # Obtener el precio de la clase específica seleccionada
            precio_clase = selected_flight.get('price')  # Precio por defecto
            # Intentar obtener el precio específico de la clase desde la sesión
            # Usar los precios correctos según sea ida o vuelta
            if is_return:
                flight_classes_prices = session.data.get('return_flight_classes_prices', {})
            else:
                flight_classes_prices = session.data.get('flight_classes_prices', {})
            
            if flight_classes_prices and flight_class.upper() in flight_classes_prices:
                precio_clase = flight_classes_prices[flight_class.upper()].get('price', precio_clase)
            
            return {
                "success": True,
                "is_round_trip_summary": False,
                "flight_index": flight_index,
                "aerolinea": selected_flight.get('airline_name'),
                "vuelo": selected_flight.get('flight_number'),
                "ruta": ruta,
                "fecha": format_date_dd_mm_yyyy(selected_flight.get('date')),
                "salida": selected_flight.get('departure_time'),
                "llegada": selected_flight.get('arrival_time'),
                "duracion": selected_flight.get('duration'),
                "precio": f"{precio_clase:.2f}" if precio_clase else "Consultar",
                "moneda": selected_flight.get('currency', 'USD'),
                "clase_seleccionada": flight_class.upper(),
                "asientos_disponibles": asientos_disponibles,
                "escalas": escalas,
                "equipaje": api_data.get('baggage', []),
                "message": f"""✅ *CLASE SELECCIONADA*

✈️ *Vuelo:* {selected_flight.get('airline_name')} {selected_flight.get('flight_number')}
📍 *Ruta:* {ruta}
📅 *Fecha:* {format_date_dd_mm_yyyy(selected_flight.get('date'))}
🕐 *Salida:* {selected_flight.get('departure_time')}
🕐 *Llegada:* {selected_flight.get('arrival_time')}
💺 *Clase:* {flight_class.upper()} ({asientos_disponibles} as.)
💰 *Precio:* ${precio_clase:.2f} USD

━━━━━━━━━━━━━━━━━━━━━━

✅ *¿Confirmas esta selección?*
Responde *SÍ* para continuar o *NO* para cambiar."""
            }
        except Exception as e:
            logger.error(f"Error confirmando selección: {str(e)}")
            return {"success": False, "error": str(e)}
    def _extract_cedula_data(self, image_url):
        """Extrae nombre, apellido y cédula de la imagen usando Gemini Vision"""
        try:
            import requests
            # base64, json, re ya importados al inicio del archivo
            logger.info(f"Descargando imagen de cédula: {image_url}")
            # Descargar imagen
            response = requests.get(image_url, timeout=15)
            if response.status_code != 200:
                logger.error(f"Error descargando imagen: {response.status_code}")
                return {"success": False, "error": "No se pudo descargar la imagen"}
            logger.info(f"Imagen descargada: {len(response.content)} bytes")
            # Convertir a base64
            image_data = base64.b64encode(response.content).decode('utf-8')
            # Prompt mejorado para Gemini Vision
            prompt = """Analiza esta imagen de cédula de identidad venezolana y extrae:

1. NOMBRE: El primer nombre de la persona (solo el primero)
2. APELLIDO: Todos los apellidos juntos
3. CEDULA: El número de cédula (solo dígitos, sin V-, E-, puntos ni guiones)

IMPORTANTE: Responde SOLO con un objeto JSON válido, sin texto adicional. NO extraigas el sexo/género.

{
  "nombre": "PRIMER_NOMBRE",
  "apellido": "APELLIDOS",
  "cedula": "12345678"
}

Si no puedes leer algún dato, usa "NO_LEGIBLE" como valor."""
            logger.info("Llamando a Gemini Vision para extraer datos...")
            # Llamar a Gemini Vision
            vision_response = self.client.models.generate_content(
                model=self.model,
                contents=[{
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_data
                        }}
                    ]
                }],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    top_p=0.95
                )
            )
            # Extraer respuesta
            if not vision_response.candidates or not vision_response.candidates[0].content.parts:
                logger.error("Gemini no retornó respuesta válida")
                return {"success": False, "error": "No se obtuvo respuesta de la IA"}
            text_response = vision_response.candidates[0].content.parts[0].text.strip()
            logger.info(f"Respuesta de Gemini: {text_response[:200]}...")
            # Limpiar respuesta (remover markdown)
            text_response = re.sub(r'```json\s*', '', text_response)
            text_response = re.sub(r'```\s*', '', text_response)
            text_response = text_response.strip()
            # Intentar parsear JSON
            try:
                data = json.loads(text_response)
            except json.JSONDecodeError as je:
                logger.error(f"Error parseando JSON: {je}")
                logger.error(f"Texto recibido: {text_response}")
                return {"success": False, "error": "Respuesta inválida de la IA"}
            # Validar datos extraídos
            nombre = data.get('nombre', '').strip().upper()
            apellido = data.get('apellido', '').strip().upper()
            cedula = re.sub(r'[^0-9]', '', str(data.get('cedula', '')))
            logger.info(f"Datos extraídos - Nombre: {nombre}, Apellido: {apellido}, Cédula: {cedula}")
            # Verificar que los datos sean válidos
            if nombre and apellido and cedula and nombre != "NO_LEGIBLE" and apellido != "NO_LEGIBLE" and cedula != "NO_LEGIBLE":
                if len(cedula) >= 6:  # Cédula debe tener al menos 6 dígitos
                    return {
                        "success": True,
                        "nombre": nombre,
                        "apellido": apellido,
                        "cedula": cedula
                    }
                else:
                    logger.error(f"Cédula muy corta: {cedula}")
            else:
                logger.error(f"Datos incompletos o no legibles")
            return {"success": False, "error": "No se pudieron extraer todos los datos"}
        except Exception as e:
            logger.error(f"Excepción extrayendo datos de cédula: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
    def _extract_contact_info(self, message):
        """Extrae teléfono y correo del mensaje"""
        try:
            # re ya importado al inicio del archivo
            # Buscar teléfono (números de 10-11 dígitos)
            phone_match = re.search(r'(\d{10,11})', message)
            # Buscar email
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', message)
            if phone_match and email_match:
                return {
                    "success": True,
                    "telefono": phone_match.group(1),
                    "email": email_match.group(1)
                }
            return {"success": False}
        except Exception as e:
            logger.error(f"Error extrayendo contacto: {str(e)}")
            return {"success": False}
    def _get_full_route(self, flight):
        """Obtiene la ruta completa del vuelo incluyendo escalas"""
        try:
            api_data = flight.get('api_data', {})
            segments = api_data.get('segments', [])
            
            if len(segments) > 1:
                # Vuelo con escalas - construir ruta completa
                route = [segments[0].get('departureCode', '')]
                for seg in segments:
                    route.append(seg.get('arrivalCode', ''))
                return ' → '.join(route)
            else:
                # Vuelo directo
                return f"{flight.get('origin', 'N/A')} → {flight.get('destination', 'N/A')}"
        except:
            return f"{flight.get('origin', 'N/A')} → {flight.get('destination', 'N/A')}"

    def _send_booking_success_message(self, phone, session, booking_result, passengers_data, total_passengers, selected_flight, flight_class, precio_ida, return_flight=None, return_flight_class=None, precio_vuelta=0, precio_por_persona=0, precio_total=0):
        """Envía el mensaje de éxito de la reserva"""
        try:
            # Construir tipo de viaje
            tipo_viaje = "🔄 IDA Y VUELTA" if return_flight else "✈️ SOLO IDA"
            
            # Verificar si hay múltiples PNR
            multiple_pnr = booking_result.get('multiple_pnr', False)
            
            if multiple_pnr:
                response = f"""🎉 *¡RESERVAS CREADAS EXITOSAMENTE!*

⚠️ *NOTA IMPORTANTE:* Las aerolíneas de ida y vuelta son diferentes, por lo que se generaron DOS localizadores separados.

━━━━━━━━━━━━━━━━━━━━━━

🎫 *LOCALIZADORES*
📌 *PNR IDA ({booking_result.get('airline_ida', 'N/A')}):* {booking_result.get('pnr_ida')}
📌 *PNR VUELTA ({booking_result.get('airline_vuelta', 'N/A')}):* {booking_result.get('pnr_vuelta')}
🎫 *Tipo:* {tipo_viaje}

━━━━━━━━━━━━━━━━━━━━━━

👥 *PASAJEROS ({total_passengers})*"""
            else:
                response = f"""🎉 *¡RESERVA CREADA EXITOSAMENTE!*

━━━━━━━━━━━━━━━━━━━━━━

🎫 *DATOS DE LA RESERVA*
📌 *PNR:* {booking_result.get('pnr')}
🆔 *VID:* {booking_result.get('vid')}
🎫 *Tipo:* {tipo_viaje}

━━━━━━━━━━━━━━━━━━━━━━

👥 *PASAJEROS ({total_passengers})*"""

            # Agregar pasajeros
            for idx, pax in enumerate(passengers_data, 1):
                pax_type_label = {'ADT': '🧑 Adulto', 'CHD': '👦 Niño', 'INF': '👶 Infante'}.get(pax.get('tipo', 'ADT'), '🧑 Adulto')
                response += f"""

👤 *Pasajero {idx}:*
   👤 {pax.get('nombre', '')} {pax.get('apellido', '')}
   🆔 {pax.get('cedula', '')}
   📋 Tipo: {pax_type_label}"""

            response += f"""

━━━━━━━━━━━━━━━━━━━━━━

✈️ *VUELO DE IDA*
✈️ *Aerolínea:* {selected_flight.get('airline_name', 'N/A')} 
🎫 *Vuelo:* {selected_flight.get('flight_number', 'N/A')}
📍 *Ruta:* {self._get_full_route(selected_flight)}
📅 *Fecha:* {format_date_dd_mm_yyyy(selected_flight.get('date', 'N/A'))}
🕐 *Salida:* {selected_flight.get('departure_time', 'N/A')}
🕐 *Llegada:* {selected_flight.get('arrival_time', 'N/A')}
💺 *Clase:* {flight_class.upper()}
💰 *Precio:* ${precio_ida:.2f} USD"""

            if return_flight:
                response += f"""

━━━━━━━━━━━━━━━━━━━━━━

✈️ *VUELO DE VUELTA*
✈️ *Aerolínea:* {return_flight.get('airline_name', 'N/A')} 
🎫 *Vuelo:* {return_flight.get('flight_number', 'N/A')}
📍 *Ruta:* {self._get_full_route(return_flight)}
📅 *Fecha:* {format_date_dd_mm_yyyy(return_flight.get('date', 'N/A'))}
🕐 *Salida:* {return_flight.get('departure_time', 'N/A')}
🕐 *Llegada:* {return_flight.get('arrival_time', 'N/A')}
💺 *Clase:* {return_flight_class.upper()}
💰 *Precio:* ${precio_vuelta:.2f} USD"""

            response += f"""

━━━━━━━━━━━━━━━━━━━━━━

💰 *RESUMEN DE COSTOS*"""

            if return_flight:
                response += f"""
   ✈️ Vuelo IDA: ${precio_ida:.2f} USD
   ✈️ Vuelo VUELTA: ${precio_vuelta:.2f} USD
   ━━━━━━━━━━━━━━━━━━━━
   💵 *Por persona:* ${precio_por_persona:.2f} USD
   👥 *Pasajeros:* {total_passengers}
   ━━━━━━━━━━━━━━━━━━━━
   💰 *TOTAL A PAGAR:* ${precio_total:.2f} USD"""
            else:
                response += f"""
   💵 *Por persona:* ${precio_ida:.2f} USD
   👥 *Pasajeros:* {total_passengers}
   ━━━━━━━━━━━━━━━━━━━━
   💰 *TOTAL A PAGAR:* ${precio_total:.2f} USD"""

            response += f"""

━━━━━━━━━━━━━━━━━━━━━━

✈️ *¡Buen viaje!* 🦌

"""
            if multiple_pnr:
                response += f"""💡 Para consultar tus reservas:
   🎫 IDA: *{booking_result.get('pnr_ida')}*
   🎫 VUELTA: *{booking_result.get('pnr_vuelta')}*"""
            else:
                response += f"""💡 Para consultar tu reserva en el futuro, escribe el código *PNR: {booking_result.get('pnr')}*"""
            
            # Limpiar datos de sesión
            session.data['extracted_data'] = {}
            session.data['waiting_for_field'] = None
            session.data['awaiting_flight_confirmation'] = False
            session.data['passengers_list'] = []  # Clear list after booking

            return self._send_response(phone, response, session)
        except Exception as e:
            logger.error(f"Error enviando mensaje de éxito: {e}")
            return self._send_response(phone, "✅ Reserva creada, pero hubo un error generando el mensaje de confirmación.", session)

    def _request_cedula_image_function(self, passenger_name, session):
        """Solicita imagen de cédula al usuario"""
        try:
            session.data['waiting_for_cedula_image'] = True
            session.data['current_passenger_name'] = passenger_name
            return {
                "success": True,
                "message": f"Para completar la reserva, necesito que envíes una foto CLARA de la cédula del pasajero. La IA extraerá automáticamente el nombre, apellido y número de cédula."
            }
        except Exception as e:
            logger.error(f"Error solicitando imagen: {str(e)}")
            return {"success": False, "error": str(e)}

    def _process_document_image(self, session, phone):
        """Procesa imagen de documento y extrae datos"""
        try:
            from document_extractor import document_extractor
            image_url = session.data.get('document_image_url')
            if not image_url:
                return {"success": False, "error": "No hay imagen de documento"}
            logger.info(f"Procesando imagen de documento: {image_url}")
            # Extraer datos del documento
            result = document_extractor.extract_from_image(image_url)
            if not result.get('success'):
                error_msg = result.get('error', 'No se pudieron extraer los datos')
                self._send_response(
                    phone,
                    f"❌ No pude extraer los datos del documento: {error_msg}\n\nPor favor, envía una foto más clara o proporciona los datos manualmente.",
                    session
                )
                return {"success": False, "error": error_msg}
            # Obtener datos extraídos
            data = result.get('data', {})
            missing_fields = result.get('missing_fields', [])
            document_type = result.get('document_type', 'unknown')
            # Guardar datos extraídos en sesión
            session.data['extracted_data'] = data
            session.data['missing_fields'] = missing_fields
            session.data['document_type'] = document_type
            # Construir mensaje de confirmación
            msg = "✅ Datos extraídos exitosamente:\n\n"
            if data.get('nombre'):
                msg += f"👤 Nombre: {data['nombre']}\n"
            if data.get('apellido'):
                msg += f"👤 Apellido: {data['apellido']}\n"
            if data.get('cedula'):
                msg += f"🆔 Cédula: {data['cedula']}\n"
            if data.get('pasaporte'):
                msg += f"🛂 Pasaporte: {data['pasaporte']}\n"
            if data.get('nacionalidad'):
                msg += f"🌍 Nacionalidad: {data['nacionalidad']}\n"
            if data.get('fecha_nacimiento'):
                msg += f"📅 Fecha de nacimiento: {format_date_dd_mm_yyyy(data['fecha_nacimiento'])}\n"
            if data.get('sexo'):
                msg += f"⚧ Sexo: {data['sexo']}\n"
            if missing_fields:
                msg += "\n\n⚠️ Datos faltantes que necesito:\n"
                for field in missing_fields:
                    field_names = {
                        'telefono': '📱 Teléfono',
                        'email': '📧 Email',
                        'nombre': '👤 Nombre',
                        'apellido': '👤 Apellido',
                        'cedula': '🆔 Cédula',
                        'pasaporte': '🛂 Pasaporte',
                        'nacionalidad': '🌍 Nacionalidad',
                        'sexo': '⚧ Sexo',
                        'direccion': '🏠 Dirección'
                    }
                    msg += f"• {field_names.get(field, field)}\n"
            wati_service.send_message(phone, msg)
            return {
                "success": True,
                "data": data,
                "missing_fields": missing_fields,
                "document_type": document_type
            }
        except Exception as e:
            logger.error(f"Error procesando imagen de documento: {str(e)}", exc_info=True)
            wati_service.send_message(
                phone,
                f"❌ Error procesando la imagen: {str(e)}\n\nPor favor, intenta con otra foto o proporciona los datos manualmente."
            )
            return {"success": False, "error": str(e)}
    def _create_booking_function(self, flight_index, flight_class, passenger_name, id_number, phone, email, session, city=None, address=None):
        """Crea una reserva de vuelo con los datos de TODOS los pasajeros y la clase seleccionada"""
        try:
            # Vuelo de IDA
            flights = session.data.get('available_flights', [])
            if not flights:
                return {"success": False, "message": "No hay vuelos disponibles. Primero debes buscar vuelos."}
            if flight_index < 1 or flight_index > len(flights):
                return {"success": False, "message": f"Número de vuelo inválido. Debe ser entre 1 y {len(flights)}"}
            selected_flight = flights[flight_index - 1]
            
            # Modificar la clase del vuelo de IDA
            if 'api_data' in selected_flight and 'segments' in selected_flight['api_data']:
                for segment in selected_flight['api_data']['segments']:
                    segment['class'] = flight_class.upper()
            selected_flight['class'] = flight_class.upper()
            
            # Vuelo de VUELTA (si existe)
            return_flight = None
            return_flights = session.data.get('return_flights', [])
            return_flight_index = session.data.get('selected_return_flight_index')
            return_flight_class = session.data.get('selected_return_flight_class', flight_class.upper())
            
            # DEBUG: Verificar datos de vuelta
            logger.info(f"=== VERIFICANDO VUELO DE VUELTA ===")
            logger.info(f"return_flights existe: {len(return_flights) if return_flights else 0} vuelos")
            logger.info(f"return_flight_index: {return_flight_index}")
            logger.info(f"return_flight_class: {return_flight_class}")
            
            if return_flights and return_flight_index:
                if return_flight_index >= 1 and return_flight_index <= len(return_flights):
                    return_flight = return_flights[return_flight_index - 1]
                    # Modificar la clase del vuelo de VUELTA
                    if 'api_data' in return_flight and 'segments' in return_flight['api_data']:
                        for segment in return_flight['api_data']['segments']:
                            segment['class'] = return_flight_class.upper()
                    return_flight['class'] = return_flight_class.upper()
                    logger.info(f"✅ Incluyendo vuelo de VUELTA: {return_flight.get('flight_number')} clase {return_flight_class}")
                else:
                    logger.warning(f"❌ return_flight_index {return_flight_index} fuera de rango (1-{len(return_flights)})")
            else:
                logger.warning(f"❌ No se encontró vuelo de vuelta - return_flights: {bool(return_flights)}, return_flight_index: {return_flight_index}")
            
            # re ya importado al inicio del archivo
            
            # Obtener TODOS los pasajeros de la lista
            passengers_list = session.data.get('passengers_list', [])
            expected_passengers = session.data.get('num_passengers', 1)
            all_passengers = []
            
            # VALIDACIÓN CRÍTICA: Verificar que tenemos todos los pasajeros
            if passengers_list and len(passengers_list) < expected_passengers:
                logger.error(f"❌ CRÍTICO: Faltan pasajeros - Esperados: {expected_passengers}, Recibidos: {len(passengers_list)}")
                return {
                    "success": False,
                    "error": f"Faltan datos de {expected_passengers - len(passengers_list)} pasajero(s). Por favor proporciona los datos de todos los pasajeros."
                }
            
            if passengers_list and len(passengers_list) > 0:
                # Usar los pasajeros de la lista
                for pax in passengers_list:
                    # Obtener nombre y apellido
                    first_name = pax.get('nombre', '').strip()
                    last_name = pax.get('apellido', '').strip()
                    pax_id = pax.get('cedula', '')
                    pax_phone = pax.get('telefono', phone)
                    pax_email = pax.get('email', email)
                    
                    # DETERMINAR TIPO DE PASAJERO (ADT/CHD/INF)
                    pax_type = pax.get('tipo', 'ADT')
                    
                    # Safety: recalcular tipo si tiene fecha de nacimiento y tipo no fue seteado
                    if pax_type == 'ADT' and pax.get('fecha_nacimiento'):
                        try:
                            born = datetime.strptime(pax['fecha_nacimiento'], '%Y-%m-%d')
                            today = datetime.now()
                            age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
                            if age < 2:
                                pax_type = 'INF'
                            elif age < 12:
                                pax_type = 'CHD'
                            logger.info(f"Tipo de pasajero recalculado: {first_name} {last_name} -> {pax_type} (edad {age})")
                        except:
                            pass
                    
                    # Limpiar datos
                    clean_phone = re.sub(r'[^0-9]', '', str(pax_phone))
                    
                    # DETERMINAR TIPO DE DOCUMENTO usando tipo_documento guardado
                    # Prefijos KIU: VCI (venezolano+cédula), VP (venezolano+pasaporte), 
                    #               ECI (extranjero+cédula), EP (extranjero+pasaporte)
                    tipo_doc = pax.get('tipo_documento', 'CI')  # 'CI' o 'P'
                    nacionalidad = pax.get('nacionalidad', 'VE')
                    
                    if tipo_doc == 'P':
                        # Pasaporte: permitir letras y números
                        clean_id = re.sub(r'[^a-zA-Z0-9]', '', str(pax_id))
                        doc_type_for_kiu = 'P'
                    else:
                        # Cédula: solo números
                        clean_id = re.sub(r'[^0-9]', '', str(pax_id))
                        if nacionalidad in ['VE', 'V']:
                            doc_type_for_kiu = 'V'  # Genera IDVCI
                        else:
                            doc_type_for_kiu = 'E'  # Genera IDECI
                    
                    passenger = {
                        'name': first_name.upper(),
                        'lastName': last_name.upper(),
                        'idNumber': clean_id,
                        'phone': clean_phone,
                        'email': pax_email.strip() if pax_email else email.strip(),
                        'type': pax_type,  # USAR TIPO REAL (ADT/CHD/INF)
                        'nationality': nacionalidad,
                        'documentType': doc_type_for_kiu,
                        'birthDate': pax.get('fecha_nacimiento', '1990-01-01'),
                        'gender': pax.get('sexo', 'M'),
                        'phoneCode': '58',
                        'address': pax.get('direccion') or address or 'Av Principal',
                        'city': pax.get('ciudad') or city or 'Caracas',
                        'zipCode': pax.get('zipCode') or '1010',
                        'state': pax.get('estado') or 'Distrito Capital',
                        'country': 'Venezuela'
                    }

                    all_passengers.append(passenger)
                    logger.info(f"Pasajero agregado: {first_name} {last_name} tipo={pax_type} doc={doc_type_for_kiu}")
            else:
                # Fallback: usar los parámetros individuales (1 solo pasajero)
                name_parts = passenger_name.strip().split()
                first_name = name_parts[0] if name_parts else ''
                last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else name_parts[0]
                clean_id = re.sub(r'[^0-9]', '', id_number)
                clean_phone = re.sub(r'[^0-9]', '', phone)
                
                passenger = {
                    'name': first_name.upper(),
                    'lastName': last_name.upper(),
                    'idNumber': clean_id,
                    'phone': clean_phone,
                    'email': email.strip(),
                    'type': 'ADT',
                    'nationality': 'VE',
                    'documentType': 'V',
                    'birthDate': '1990-01-01',
                    'gender': 'M',
                    'phoneCode': '58',
                    'address': address,
                    'city': city,
                    'zipCode': '1010',
                    'state': 'Distrito Capital',
                    'country': 'Venezuela'
                }
                all_passengers.append(passenger)
            
            # Crear reserva con TODOS los pasajeros
            is_round_trip = return_flight is not None
            trip_type_log = "IDA Y VUELTA" if is_round_trip else "SOLO IDA"
            logger.info(f"Creando reserva {trip_type_log} para {len(all_passengers)} pasajero(s)")
            
            result = flight_service.create_booking(
                flight_option=selected_flight,
                passenger_details=all_passengers,
                return_flight_option=return_flight  # Incluir vuelo de vuelta si existe
            )
            if result.get('success'):
                response_data = {
                    "success": True,
                    "pnr": result.get('pnr'),
                    "vid": result.get('vid'),
                    "multiple_pnr": result.get('multiple_pnr', False),
                    "pnr_ida": result.get('pnr_ida'),
                    "pnr_vuelta": result.get('pnr_vuelta'),
                    "airline_ida": result.get('airline_ida'),
                    "airline_vuelta": result.get('airline_vuelta'),
                    "vuelo_ida": f"{selected_flight.get('airline_name')} {selected_flight.get('flight_number')}",
                    "ruta_ida": f"{selected_flight.get('origin')} → {selected_flight.get('destination')}",
                    "fecha_ida": selected_flight.get('date'),
                    "horario_salida_ida": selected_flight.get('departure_time'),
                    "horario_llegada_ida": selected_flight.get('arrival_time'),
                    "clase_ida": flight_class.upper(),
                    "precio_total": f"${selected_flight.get('price'):.2f} {selected_flight.get('currency', 'USD')}",
                    "num_passengers": len(all_passengers),
                    "pasajero": passenger_name,
                    "cedula": all_passengers[0]['idNumber'] if all_passengers else '',
                    "telefono": all_passengers[0]['phone'] if all_passengers else '',
                    "email": all_passengers[0]['email'] if all_passengers else '',
                    "es_ida_vuelta": is_round_trip
                }
                
                # Agregar datos del vuelo de vuelta si existe
                if return_flight:
                    response_data["vuelo_vuelta"] = f"{return_flight.get('airline_name')} {return_flight.get('flight_number')}"
                    response_data["ruta_vuelta"] = f"{return_flight.get('origin')} → {return_flight.get('destination')}"
                    response_data["fecha_vuelta"] = return_flight.get('date')
                    response_data["horario_salida_vuelta"] = return_flight.get('departure_time')
                    response_data["horario_llegada_vuelta"] = return_flight.get('arrival_time')
                    response_data["clase_vuelta"] = return_flight_class.upper()
                
                return response_data
            else:
                return {"success": False, "error": result.get('error', 'Error desconocido')}
        except Exception as e:
            logger.error(f"Error creando reserva: {str(e)}")
            return {"success": False, "error": str(e)}
    def _send_response(self, phone: str, message: str, session):
        """Envía respuesta con control de duplicados"""
        try:
            session.add_message('assistant', message)
            wati_service.send_message(phone, message)
            return {'response': message, 'success': True}
        except Exception as e:
            logger.error(f"Error enviando: {str(e)}")
            return {'response': f"Error enviando mensaje: {str(e)}", 'success': False}


# Instancia global
gemini_agent_bot = GeminiAgentBot()
