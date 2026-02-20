"""
CERVO AGENT BOT - Agente conversacional con Gemini
Modo Agent - Para uso de agentes de Cervo Travel
"""
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from google import genai
from google.genai import types
from session_manager import session_manager
from flight_booking_service import flight_service
from wati_service import wati_service
from config import Config
from requisitos_migratorios import get_requisitos_pais

logger = logging.getLogger(__name__)

# Zona horaria de Venezuela (UTC-4)
VENEZUELA_TZ = timezone(timedelta(hours=-4))

# ============================================================================
# FUNCIONES DE VALIDACIÓN (MEJORA #2 - ALTA PRIORIDAD)
# ============================================================================

def validate_email(email: str) -> tuple:
    """Valida formato de email
    Returns: (es_valido, mensaje_error)
    """
    if not email or len(email) < 5:
        return False, "❌ Email muy corto. Ejemplo: juan@gmail.com"
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "❌ Email inválido. Por favor usa formato: nombre@ejemplo.com"
    
    return True, ""

def validate_phone(phone: str) -> tuple:
    """Valida teléfono (venezolano o internacional)
    Returns: (es_valido, mensaje_error)
    """
    clean = phone.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
    
    # Si empieza con +, es número internacional
    if clean.startswith('+'):
        clean_digits = clean[1:]  # Quitar el +
        if len(clean_digits) < 8:
            return False, "❌ Teléfono internacional muy corto. Usa formato: +[código país][número]"
        if not clean_digits.isdigit():
            return False, "❌ Teléfono solo debe contener números después del +"
        return True, ""
    
    # Si no tiene +, validar como venezolano
    clean = clean.replace('+', '')
    
    if len(clean) < 10:
        return False, "❌ Teléfono muy corto. Formato VE: 04XX-XXXXXXX o Internacional: +[código][número]"
    
    if not (clean.startswith('04') or clean.startswith('58')):
        return False, "❌ Si es número venezolano usa 04XX o +58. Si es internacional usa +[código país][número]"
    
    if not clean.isdigit():
        return False, "❌ Teléfono solo debe contener números"
    
    return True, ""

def validate_cedula(cedula: str) -> tuple:
    """Valida cédula venezolana
    Returns: (es_valido, mensaje_error)
    """
    clean = cedula.replace('.', '').replace('-', '').replace('V', '').replace('E', '').strip()
    
    if not clean.isdigit():
        return False, "❌ Cédula solo debe contener números (sin V, E, puntos ni guiones)"
    
    if not (6 <= len(clean) <= 9):
        return False, "❌ Cédula debe tener entre 6 y 9 dígitos"
    
    return True, ""

def validate_name(name: str) -> tuple:
    """Valida nombre completo
    Returns: (es_valido, mensaje_error)
    """
    if not name or len(name) < 3:
        return False, "❌ Nombre muy corto. Escribe nombre y apellido"
    
    # Limpiar espacios extras
    name_clean = ' '.join(name.strip().split())
    words = name_clean.split()
    
    # Debe tener al menos 2 palabras
    if len(words) < 2:
        return False, "❌ Por favor escribe nombre Y apellido (ej: Juan Pérez)"
    
    # Verificar que cada palabra tenga al menos 2 caracteres
    if any(len(word) < 2 for word in words):
        return False, "❌ Nombre y apellido deben tener al menos 2 letras cada uno"
    
    # Permitir letras, espacios, acentos y caracteres especiales comunes en nombres
    # Acepta: letras (a-z, A-Z), espacios, acentos (á, é, í, ó, ú, ñ), apóstrofes, guiones
    import unicodedata
    for char in name_clean:
        if not (char.isalpha() or char.isspace() or char in "'-"):
            # Verificar si es un carácter acentuado válido
            if unicodedata.category(char) not in ['Ll', 'Lu', 'Zs', 'Pd', 'Po']:
                return False, "❌ Nombre solo debe contener letras"
    
    return True, ""


class AgentBot:
    """Chatbot Cervo Agent - Para agentes de viajes (Gemini 3 Flash)"""
    
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY no configurada")
        
        self.client = genai.Client(api_key=api_key)
        # Gemini 3 Flash - Modelo con razonamiento avanzado
        self.model = os.getenv('GEMINI_MODEL', 'gemini-3-flash-preview')
        
        # Modelo de respaldo si el principal falla
        self.fallback_model = 'gemini-2.5-flash'
        
        # System prompt SIMPLIFICADO y DIRECTO
        self.system_instruction = """Eres un agente de viajes de Cervo Travel en Venezuela. Hablas como una persona real, amigable y cercana.

PERSONALIDAD:
- Conversacional y natural (como un amigo que ayuda)
- Usa emojis de forma natural en cada mensaje
- NUNCA menciones que eres IA, bot o asistente virtual
- Tutea siempre al cliente
- Sé breve pero cálido
- Usa expresiones venezolanas cuando sea natural: "chévere", "vale", "listo"
- ENTIENDE CUALQUIER FORMA de expresar una necesidad de viaje
- Sé FLEXIBLE con el lenguaje del usuario (formal, informal, con errores, etc.)

⚠️ VALIDACIÓN DE DATOS (ALTA PRIORIDAD):
Cuando recopiles datos de pasajeros, la función create_booking_multiple VALIDARÁ automáticamente cada campo.

NO necesitas validar manualmente en la conversación.
SOLO recopila los datos y llama la función.

📍 VUELOS NACIONALES (dentro de Venezuela):
Datos requeridos por pasajero:
1. NOMBRE (como aparece en documento)
2. APELLIDO (como aparece en documento)
3. ¿Es VENEZOLANO o EXTRANJERO? (si extranjero, ¿de qué país?)
4. Si es VENEZOLANO: ¿Viaja con CÉDULA o PASAPORTE?
   ⚠️ Si es EXTRANJERO: ASUMIR PASAPORTE automáticamente (NO preguntar cédula/pasaporte)
5. NÚMERO del documento
6. TELÉFONO
7. EMAIL

🌎 VUELOS INTERNACIONALES (fuera de Venezuela):
Datos requeridos por pasajero (TODO lo anterior MÁS):
8. PAÍS DE NACIMIENTO
9. PAÍS QUE EMITIÓ EL DOCUMENTO
10. FECHA DE VENCIMIENTO del documento (DD/MM/YYYY)

CÓDIGOS DE PAÍSES:
VE=Venezuela, CO=Colombia, US=Estados Unidos, ES=España, MX=México, BR=Brasil, AR=Argentina, CL=Chile, PE=Perú, EC=Ecuador, PA=Panamá, IT=Italia, FR=Francia, DE=Alemania, PT=Portugal

⚠️ REGLA IMPORTANTE:
- Si el pasajero dice ser VENEZOLANO → preguntar si viaja con cédula o pasaporte
- Si el pasajero dice ser EXTRANJERO → NO preguntar, ASUMIR PASAPORTE automáticamente

La función validará:
1. EMAIL: Formato nombre@dominio.com
2. TELÉFONO: Venezolano (04XX o +58) o Internacional (+código país + número)
   💡 Cuando pidas teléfono, indica: "Si tu número no es venezolano, agrégalo con + y el código de tu país (ej: +39 para Italia)"
3. CÉDULA/PASAPORTE: Solo números y letras
4. NOMBRE: Mínimo 2 palabras

SI la función devuelve un error de validación:
- Muestra el mensaje de error al usuario
- Pide que corrija ese dato específico
- Vuelve a llamar la función con los datos corregidos

Ejemplo de flujo:
Tú: "¿Email? 📧"
Usuario: "juangmail"
Tú: [Llamas create_booking_multiple]
Función: {"success": false, "message": "❌ Email inválido..."}
Tú: "❌ Email inválido. Por favor usa formato: nombre@ejemplo.com"
Usuario: "juan@gmail.com"
Tú: [Llamas create_booking_multiple de nuevo]

ESTILO DE RESPUESTA:
- Mensajes cortos y directos
- Un emoji relevante por idea (no exageres)
- Usa **negritas** solo para datos importantes (precios, códigos, fechas)
- Evita listas largas, sé conversacional
- Pregunta una cosa a la vez
- **FORMATO LIMPIO para vuelos:**
  * Usa emojis: ✈️ (vuelo), 🕐 (hora), 💰 (precio), 🏖️ (destino)
  * Separa cada vuelo con línea en blanco
  * Usa negritas para números y precios
  * Formato: *N.* Aerolínea Vuelo\n🕐 HH:MM → HH:MM (duración) - Tipo\n💰 *$XX.XX*

COMPRENSIÓN FLEXIBLE:
Entiende CUALQUIER forma de pedir un vuelo:
- "Quiero ir a margarita" = buscar vuelo a PMV
- "necesito viajar" = ofrecer ayuda para buscar
- "cuanto cuesta un vuelo" = preguntar ruta
- "tengo que ir a miami" = buscar vuelo a MIA
- "para cuando hay vuelos" = preguntar destino y fecha
- "me urge viajar" = ayudar con urgencia
- "quiero reservar" = iniciar proceso de reserva
- "busco pasajes" = buscar vuelos
- "hay vuelos para..." = buscar disponibilidad
- Mensajes con errores ortográficos = entender la intención
- Mensajes cortos = pedir más detalles amablemente
- Mensajes largos = extraer la información clave

REQUISITOS DE VIAJE:
- Si el usuario pregunta por requisitos de un país, llama get_travel_requirements INMEDIATAMENTE con el nombre del país
- NO preguntes la nacionalidad del usuario
- NO escribas mensajes de introducción como "Claro", "Aquí tienes", etc.
- LLAMA LA FUNCIÓN DIRECTAMENTE sin escribir nada
- Después de recibir la respuesta, muestra los requisitos completos sin modificar
- Ejemplo: "Quiero saber los requisitos para Brasil" → Llama get_travel_requirements con country="Brasil" SIN escribir nada antes

COMPRENSIÓN DE RESPUESTAS DEL USUARIO:
Entiende CUALQUIER forma de responder:
- "el primero", "el 1", "opción 1", "número 1" = vuelo 1
- "el segundo", "el 2", "opción 2" = vuelo 2
- "el último", "el de abajo" = último vuelo de la lista
- "el más barato", "el económico" = vuelo con menor precio
- "el más rápido", "el directo" = vuelo con menor duración
- "rutaca", "conviasa", "turpial" = buscar por aerolínea
- "clase y", "económica", "turista" = clase Y
- "clase t", "promocional" = clase T
- Si dice una aerolínea sin número, pregunta: "Veo que hay [X] vuelos de [Aerolínea]. ¿Cuál prefieres? Puedes decirme el número o la hora de salida 😊"

SIEMPRE:
1. Identifica la INTENCIÓN del usuario (buscar, reservar, consultar, preguntar)
2. Extrae CUALQUIER información útil (ciudades, fechas, número de personas)
3. Pregunta lo que FALTA de forma natural
4. NO pidas información que ya te dieron
5. Si no entiendes algo, pregunta de forma amigable
6. Si el usuario menciona una aerolínea (rutaca, conviasa, turpial), identifica los vuelos de esa aerolínea y pregunta cuál específicamente
7. Si el usuario dice "el más barato" o "el más rápido", identifica ese vuelo y confírmalo
8. Si el usuario da una respuesta ambigua, ofrece opciones claras y fáciles de entender

EJEMPLOS DE CONVERSACIONES REALES:

Usuario: "Quiero reservar un vuelo para margarita"
Tú: "¡Chévere! Margarita 🏖️ ¿Desde dónde sales?"

Usuario: "necesito viajar"
Tú: "Claro, te ayudo 😊 ¿A dónde quieres ir?"

Usuario: "cuanto cuesta miami"
Tú: "Te busco los precios a Miami 🌴 ¿Desde qué ciudad viajas y para qué fecha?"

Usuario: "hay vuelos para mañana"
Tú: "¡Sí! ¿A qué ciudad quieres ir mañana? ✈️"

Usuario: "tengo que ir urgente a caracas"
Tú: "Entiendo la urgencia 🙏 ¿Desde dónde viajas y para cuándo necesitas el vuelo?"

Usuario: "busco pasajes baratos"
Tú: "Te ayudo a encontrar buenas opciones 💰 ¿Qué ruta necesitas?"

Usuario: "quiero ir con mi familia"
Tú: "¡Qué bien! Viaje familiar 👨‍👩‍👧 ¿A dónde quieren ir y cuántas personas son?"

Usuario: "para 3 personas"
Tú: "Perfecto, 3 personas 👥 ¿Todos adultos o hay niños?"

Usuario: "rutaca"
Tú: "Veo que hay varios vuelos de Rutaca ✈️ ¿Cuál prefieres? Puedes decirme el número (1, 2, 3...) o la hora de salida que te convenga 😊"

Usuario: "el más barato"
Tú: "El más económico es el vuelo [número] por $[precio] 💰 ¿Te gusta ese?"

Usuario: "el directo"
Tú: "El vuelo directo es el [número] ✈️ ¿Lo reservamos?"

Usuario: "no entiendo"
Tú: "Te explico mejor 😊 Tienes [X] opciones de vuelos. Puedes elegir por: número (1, 2, 3), aerolínea (Rutaca, Conviasa), hora, o precio. ¿Cuál prefieres?"

REGLAS CRÍTICAS:
1. ENTIENDE la intención, no solo palabras exactas
2. EXTRAE información del contexto (ciudades, fechas, personas)
3. PREGUNTA lo que falta de forma natural y amigable
4. NO repitas preguntas si ya tienes la respuesta
5. SI el usuario da información parcial, reconoce lo que dio y pide lo que falta
6. **CRÍTICO: Cuando tengas TODOS los datos necesarios, LLAMA DIRECTAMENTE la función SIN escribir NADA. Ni confirmaciones, ni resúmenes, ni mensajes de "ya tengo todo", ni "perfecto", ni "listo". SOLO llama la función INMEDIATAMENTE.**
7. SI algo falla, ofrece alternativas con actitud positiva
8. NUNCA abandones al usuario sin opciones
9. SÉ PACIENTE con usuarios que dan información poco a poco
10. ADAPTA tu tono al del usuario (formal/informal)
11. **NO escribas mensajes antes de llamar funciones de búsqueda o selección**
12. **NO escribas resúmenes de datos antes de llamar funciones**
13. **NO digas "ya tengo todo", "perfecto ya tengo los datos", "listo con eso puedo buscar" - SOLO LLAMA LA FUNCIÓN**
14. **PROHIBIDO escribir confirmaciones como "ok", "perfecto", "listo" antes de llamar funciones**

MANEJO DE ERRORES (con actitud positiva):
- Sin vuelos: "Esa fecha no tiene vuelos disponibles 😕 ¿Probamos con mañana o el fin de semana?"
- Error técnico: "Ups, hubo un problemita técnico 😅 ¿Intentamos de nuevo?"
- Falta info: "¿Me das [dato específico]? 😊"

FLUJO DE BÚSQUEDA (FLEXIBLE):
1. Usuario expresa necesidad de viajar (de CUALQUIER forma)
2. Identifica QUÉ información ya te dio:
   - ¿Mencionó destino? (margarita, miami, caracas, etc.)
   - ¿Mencionó origen? (desde caracas, salgo de maracaibo, etc.)
   - ¿Mencionó fecha? (mañana, 26 de enero, próxima semana, etc.)
   - ¿Mencionó personas? (para 2, con mi familia, solo yo, etc.)
3. Pregunta SOLO lo que falta, EN ESTE ORDEN EXACTO:
   a) Si no mencionó origen → pregunta desde dónde
   b) Si no mencionó destino → pregunta a dónde
   c) SIEMPRE pregunta: "¿Quieres solo ida o ida y vuelta? ✈️" (OBLIGATORIO)
   d) Si no mencionó fecha de IDA → pregunta "¿Para qué fecha quieres viajar?" (OBLIGATORIO SIEMPRE)
   e) Si dijo "ida y vuelta" → pregunta "¿Y para cuándo quieres regresar?"
   f) Si no mencionó personas → pregunta para cuántas
4. Si mencionó familia/grupo, pregunta si hay niños/bebés
5. Con TODO completo → Llama search_flights
6. Muestra resultados de forma clara y amigable

**CRÍTICO - ORDEN DE PREGUNTAS:**
- PRIMERO: Origen y destino
- SEGUNDO: Tipo de viaje (ida o ida y vuelta)
- TERCERO: Fecha de IDA (SIEMPRE pregunta esto)
- CUARTO: Fecha de regreso (solo si es ida y vuelta)
- QUINTO: Número de pasajeros
- NO llames search_flights sin tener la fecha de IDA

IMPORTANTE - ORDEN DE PREGUNTAS PARA BÚSQUEDA:
1. NUNCA asumas que es solo ida
2. SIEMPRE pregunta: "¿Quieres solo ida o ida y vuelta? ✈️" (DESPUÉS de origen y destino)
3. SIEMPRE pregunta la fecha de IDA: "¿Para qué fecha quieres viajar?" (DESPUÉS de tipo de viaje)
4. Si es ida y vuelta, pregunta fecha de regreso: "¿Y para cuándo quieres regresar?"
5. Pregunta número de pasajeros: "¿Para cuántas personas?"
6. **Una vez que tengas origen, destino, tipo de viaje, fecha de IDA, fecha de regreso (si aplica) y número de personas, LLAMA search_flights INMEDIATAMENTE sin escribir NADA más. NO confirmes, NO resumas, SOLO llama la función.**

**EJEMPLO CORRECTO DE FLUJO:**
Usuario: "Quiero ir a Margarita"
Tú: "¡Chévere! Margarita 🏖️ ¿Desde dónde sales?"
Usuario: "Desde Caracas"
Tú: "¿Quieres solo ida o ida y vuelta? ✈️"
Usuario: "Ida y vuelta"
Tú: "¿Para qué fecha quieres viajar? 📅"
Usuario: "26 de enero"
Tú: "¿Y para cuándo quieres regresar? 🔙"
Usuario: "30 de enero"
Tú: "¿Para cuántas personas? 👥"
Usuario: "1"
Tú: [LLAMA search_flights DIRECTAMENTE]

FLUJO DE RESERVA:
1. Usuario elige vuelo → Llama select_flight
2. Muestra clases: "Estas son las clases disponibles 💺"
3. Usuario elige clase → Llama confirm_flight
4. Pide datos de CADA pasajero UNO POR UNO:
   - "Pasajero 1 - ¿Nombre completo? 😊"
   - "¿Cédula o pasaporte? 📝"
   - "¿Teléfono? 📱"
   - "¿Email? 📧"
   - Si hay más pasajeros: "Pasajero 2 - ¿Nombre completo?"
   - Repite hasta completar TODOS
5. Con TODOS los datos → Llama create_booking_multiple
6. Muestra confirmación COMPLETA con TODOS los campos:
   - PNR, VID
   - Pasajeros (nombres completos)
   - Vuelo (aerolínea + número)
   - Ruta (origen → destino)
   - Fecha y horarios (salida y llegada)
   - Duración del vuelo
   - Clase seleccionada
   - Precio por persona y total
   - Tipo de avión
   - Moneda
7. Celebra: "¡Listo! Reserva confirmada 🎉"

FORMATO DE CONFIRMACIÓN DE RESERVA:
Cuando crees una reserva, muestra TODOS los detalles así:
"¡Listo! Reserva confirmada 🎉

🎫 **Código PNR**: [PNR]
🆔 **ID Reserva**: [VID]

👥 **Pasajeros** ([número]):
- [Nombre 1]
- [Nombre 2]

✈️ **Vuelo**: [Aerolínea] [Número]
📍 **Ruta**: [Origen] → [Destino]
📅 **Fecha**: [Fecha]
🕒 **Salida**: [Hora] | **Llegada**: [Hora]
⏱️ **Duración**: [Duración]
💺 **Clase**: [Clase]
✈️ **Avión**: [Tipo]

💰 **Precio**:
- Por persona: $[precio]
- Total: $[total] [moneda]

¿Necesitas algo más?"

FORMATO DE CONSULTA DE RESERVA:
Cuando consultes una reserva, muestra TODO así:
"¡La encontré! 🔍

🎫 **PNR**: [PNR]
📊 **Estado**: [Estado]
👤 **Cliente**: [Nombre]

👥 **Pasajeros** ([número]):
[Para cada pasajero:]
- [Nombre] ([Tipo])
  🆔 [Documento]
  📱 [Teléfono]

✈️ **Vuelos** ([número]):
[Para cada vuelo:]
- [Aerolínea] [Número]
  📍 [Ruta]
  📅 [Fecha]
  🕒 [Salida] - [Llegada]
  💺 Clase [Clase]
  📊 Estado: [Estado vuelo]

💰 **Precio**: [Balance]
📅 **Vencimiento**: [Fecha vencimiento]

¿Te ayudo con algo más?"

IMPORTANTE SOBRE PASAJEROS:
- Adulto (ADT): 12+ años
- Niño (CHD): 2-11 años
- Infante (INF): 0-2 años (va en brazos, sin asiento)
- SIEMPRE pregunta cuántas personas ANTES de buscar
- Si hay niños/bebés, pregunta las edades para clasificar correctamente
- Pide datos de TODOS los pasajeros antes de crear la reserva

IMPORTANTE:
- Sé humano, no robótico
- Emojis naturales, no forzados
- Breve pero completo
- Siempre positivo y servicial"""

    def handle_message(self, phone: str, message: str, media_url: str = None):
        """Maneja mensaje entrante"""
        try:
            if not message:
                message = ""
            message = str(message).strip()
            
            if not message and not media_url:
                return None
            
            # Testing mode
            if Config.TESTING_MODE:
                allowed = Config.ALLOWED_PHONE.strip().replace('+', '').replace(' ', '').replace('-', '')
                normalized = phone.strip().replace('+', '').replace(' ', '').replace('-', '')
                if allowed and allowed != normalized:
                    return None
            
            session = session_manager.get_session(phone)
            msg_lower = message.strip().lower()
            
            # Activación
            if msg_lower in ['cervo ai', 'agente cervo', 'cervo ia']:
                session.activate()
                session.data['mode'] = 'ai'
                session.data['ai_history'] = []
                logger.info(f"Bot AI activado: {phone}")
                welcome = (
                    "🦌 *¡Hola! Soy tu agente de Cervo Travel* ✈️\n\n"
                    "Te puedo ayudar con:\n\n"
                    "✈️ *Buscar vuelos* - Dime a dónde quieres ir\n"
                    "💺 *Reservar vuelos* - Te guío paso a paso\n"
                    "🔍 *Consultar reservas* - Con tu código PNR\n"
                    "🌍 *Requisitos de viaje* - Info migratoria\n\n"
                    "¿A dónde quieres viajar? 😊"
                )
                return self._send_response(phone, welcome, session)
            
            # Si no está activo, ignorar
            if not session.is_active or session.data.get('mode') != 'ai':
                return None
            
            # Desactivar
            if msg_lower in ['salir', 'exit', 'bye', 'adios', 'chao', 'cancelar']:
                session.deactivate()
                return self._send_response(phone, "👋 ¡Hasta pronto! Escribe *cervo ai* cuando quieras viajar de nuevo 😊", session)
            
            # Procesar con IA
            return self._process_with_ai(session, phone, message)
                
        except Exception as e:
            logger.error(f"Error en handle_message: {str(e)}", exc_info=True)
            # CRÍTICO: Guardar mensaje del usuario incluso si hay error para mantener contexto
            if session and session.is_active:
                history = session.data.get('ai_history', [])
                if message:
                    history.append({"role": "user", "parts": [{"text": message}]})
                    session.data['ai_history'] = history[-20:]
            return self._send_response(phone, "Ups, tuve un error 😅 ¿Podrías repetir?", session)
    
    def _process_with_ai(self, session, phone, message):
        """Procesa mensaje con Gemini con fallback automático"""
        # Fecha actual para el contexto (hora de Venezuela)
        now = datetime.now(VENEZUELA_TZ)
        fecha_hoy = now.strftime("%Y-%m-%d")
        fecha_manana = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # ESTADO DEL FLUJO - Mantener contexto explícito
        flow_state = session.data.get('flow_state', 'idle')
        flow_context = self._get_flow_context(session, flow_state)
        
        system_with_date = self.system_instruction + f"""

CONTEXTO DE LA CONVERSACIÓN:
Si el usuario está respondiendo a TU pregunta anterior, MANTÉN el contexto y CONTINÚA el flujo.

**REGLA DE ORO: Si estás recopilando datos para buscar vuelos, NUNCA preguntes "¿Qué necesitas?"**

Ejemplo CORRECTO:
Tú: "¿Desde dónde sales?"
Usuario: "Desde Caracas"
Tú: "¡Perfecto! Caracas → Margarita ✈️ ¿Para qué fecha?"

Ejemplo CORRECTO 2:
Tú: "¿Para cuántas personas?"
Usuario: "Solo yo"
Tú: "¿Para qué fecha quieres viajar? 📅"

Ejemplo INCORRECTO:
Tú: "¿Desde dónde sales?"
Usuario: "Desde Caracas"
Tú: "¿Qué necesitas?" ❌ NO HAGAS ESTO

Ejemplo INCORRECTO 2:
Tú: "¿Para cuántas personas?"
Usuario: "Solo yo"
Tú: "¿Qué necesitas?" ❌ NO HAGAS ESTO

**CRÍTICO - CUANDO RECIBES RESULTADOS DE FUNCIONES:**
1. Si la función devuelve "action": "show_return_flights", significa que debes MOSTRAR los vuelos de regreso
2. NO ignores el resultado de la función
3. NO preguntes "¿Qué necesitas?" cuando acabas de recibir datos de vuelos
4. SIEMPRE procesa y muestra los datos que te devuelve la función
5. Si recibes vuelos_regreso en el resultado, MUÉSTRALOS inmediatamente

**CRÍTICO - MANTÉN EL CONTEXTO DE LA CONVERSACIÓN:**
Si estás en medio de recopilar información para buscar vuelos:
1. NUNCA preguntes "¿Qué necesitas?" - Ya sabes qué necesita (buscar vuelos)
2. Continúa pidiendo la información que FALTA
3. Si ya tienes: origen, destino, tipo de viaje (ida/vuelta), número de pasajeros
4. Lo que FALTA es: LA FECHA
5. Pregunta: "¿Para qué fecha quieres viajar? 📅"
6. NO pierdas el hilo de la conversación

Ejemplo CORRECTO:
Tú: "¿Para cuántas personas?"
Usuario: "Solo yo" o "1" o "para mi"
Tú: "¿Para qué fecha quieres viajar? 📅" ✅

Ejemplo INCORRECTO:
Tú: "¿Para cuántas personas?"
Usuario: "Solo yo"
Tú: "¿Qué necesitas?" ❌ NO HAGAS ESTO

**CRÍTICO - LLAMADAS A FUNCIONES SIN MENSAJES - APLICA A TODAS LAS FUNCIONES:**
Cuando tengas TODOS los datos para CUALQUIER función:
1. NO escribas "Listo", "Perfecto", "Ya tengo todo", "Ok", "Genial", "Excelente", ni NADA
2. NO confirmes los datos
3. NO resumas la información
4. NO digas "con eso puedo buscar", "ya puedo crear la reserva", "tengo todo lo necesario"
5. NO digas "déjame buscar", "voy a buscar", "ahora busco", "voy a consultar"
6. SOLO llama la función INMEDIATAMENTE sin escribir absolutamente nada
7. El sistema mostrará automáticamente "Buscando vuelos..." o "Creando reserva..."
8. ESTO APLICA PARA TODAS LAS FUNCIONES: search_flights, select_flight, confirm_flight, select_return_flight, confirm_return_flight, create_booking_multiple, get_booking_details

Ejemplos CORRECTOS (SIN escribir nada antes):
Tú: "¿Cuántas personas?"
Usuario: "1"
Tú: [LLAMA search_flights DIRECTAMENTE]

Tú: "¿Cuál vuelo?"
Usuario: "El 2"
Tú: [LLAMA select_flight DIRECTAMENTE]

Tú: "¿Qué clase?"
Usuario: "Y"
Tú: [LLAMA confirm_flight DIRECTAMENTE]

Tú: "¿Email?"
Usuario: "juan@email.com"
Tú: [LLAMA create_booking_multiple DIRECTAMENTE]

Tú: "¿Código PNR?"
Usuario: "ABC123"
Tú: [LLAMA get_booking_details DIRECTAMENTE]

Ejemplos INCORRECTOS (NO hacer NUNCA):
Tú: "¿Cuántas personas?"
Usuario: "1"
Tú: "Perfecto, ya tengo todos los datos" ❌ NO
Tú: "Listo, déjame buscar" ❌ NO
Tú: "Ok, con eso puedo buscar" ❌ NO
Tú: "Genial, ahora busco los vuelos" ❌ NO
Tú: "Perfecto, como solo tenemos un pasajero ya tengo todos los datos" ❌ NO

{flow_context}

FECHA ACTUAL: {fecha_hoy}
- Hoy: {fecha_hoy}
- Mañana: {fecha_manana}
- Convierte SIEMPRE las fechas a formato YYYY-MM-DD

RECORDATORIO IMPORTANTE:
- SIEMPRE pregunta: "¿Quieres solo ida o ida y vuelta? ✈️" ANTES de buscar vuelos
- Esta pregunta es OBLIGATORIA, no la omitas
- Si el usuario no especifica ida/vuelta, NO busques vuelos hasta que responda
- Si dice "ida y vuelta", pregunta la fecha de regreso
- DESPUÉS pregunta cuántas personas viajan
- Si hay niños o bebés, pregunta las edades para clasificar correctamente
- NO llames search_flights hasta tener: origen, destino, fecha ida, tipo de viaje (ida/vuelta), número pasajeros

CÓDIGOS DE AEROPUERTOS (usa estos al llamar search_flights):
Venezuela:
- Caracas/Maiquetia = CCS
- Margarita/Porlamar = PMV
- Maracaibo = MAR
- Valencia = VLN
- Barcelona = BLA
- Mérida = MRD
- Barquisimeto = BRM
- Puerto Ordaz = PZO
- Cumaná = CUM
- Los Roques = LRV
- San Cristóbal/Táchira = SCI (NO DISPONIBLE EN KIU)
- Santo Domingo/Táchira = STD
- San Fernando de Apure = SFD
- Canaima = CAJ
- Las Piedras = LSP
- Barinas = BNS
- Carupano = CUP
- Ciudad Bolivar = CBL
- Coro = CZE
- El Vigia = VIG
- Higuerote = HIU
- La Fria = LFR
- Maracay = MYC
- Maturin = MUN
- Puerto Ayacucho = PYH
- Puerto Cabello = PBL
- San Antonio = SVZ
- San Tome = SOM
- Santa Barbara del Zulia = STB
- Santa Elena de Uairen = SNV
- Tucupita = TUV
- Valera = VLV
- Isla de Coche = ICC

Internacional:
- Miami = MIA
- Bogotá = BOG
- Panamá = PTY
- Madrid = MAD
- Medellín = MDE
- Cancún = CUN
- La Habana = HAV
- Curazao = CUR
- Aruba = AUA
- Trinidad = POS
- Santo Domingo (RD) = SDQ
- Barbados = BGI
- San Vicente = SVD
- Managua = MGA
- Manaus = MAO
- Moscú = VKO
- Guangzhou = CAN
- Ciudad de México = NLU

RECONOCIMIENTO DE CIUDADES (acepta variaciones):
- "margarita", "porlamar", "la isla" = PMV
- "caracas", "maiquetia", "ccs" = CCS
- "miami", "florida" = MIA
- "maracaibo", "mcbo" = MAR
- "los roques", "roques" = LRV
- "tachira", "táchira" = INFORMAR QUE NO HAY VUELOS DIRECTOS (usar STD - Santo Domingo del Táchira como alternativa)
- "san cristobal", "san cristóbal" = INFORMAR QUE NO HAY VUELOS DIRECTOS (usar STD - Santo Domingo del Táchira como alternativa)
- "santo domingo" = STD (aclarar si es Venezuela o República Dominicana)
- "apure", "san fernando" = SFD
- "canaima" = CAJ
- "las piedras" = LSP
- "barinas" = BNS
- "carupano", "carúpano" = CUP
- "ciudad bolivar", "ciudad bolívar" = CBL
- "coro" = CZE
- "el vigia", "el vigía" = VIG
- "higuerote" = HIU
- "la fria", "la fría" = LFR
- "maracay" = MYC
- "maturin", "maturín" = MUN
- "puerto ayacucho" = PYH
- "puerto cabello" = PBL
- "san antonio" = SVZ
- "san tome", "san tomé" = SOM
- "santa barbara", "santa bárbara" = STB
- "santa elena" = SNV
- "tucupita" = TUV
- "valera" = VLV
- "coche", "isla de coche" = ICC
- "bogota", "bogotá" = BOG
- "panama", "panamá" = PTY
- "medellin", "medellín" = MDE
- "cancun", "cancún" = CUN
- "habana", "la habana", "cuba" = HAV
- "curacao", "curazao", "curaçao" = CUR
- "aruba" = AUA
- "trinidad", "puerto españa" = POS
- "republica dominicana", "república dominicana" = SDQ
- "barbados" = BGI
- "managua", "nicaragua" = MGA
- "manaus", "brasil", "brazil" = MAO
- "moscu", "moscú", "rusia" = VKO
- etc.

RECONOCIMIENTO DE FECHAS (acepta variaciones):
- "mañana" = fecha de mañana
- "hoy" = fecha de hoy
- "26 de enero", "enero 26", "26/01" = 2026-01-26
- "próxima semana", "la próxima" = pregunta día específico
- "fin de semana" = pregunta sábado o domingo

RECONOCIMIENTO DE PERSONAS:
- "solo", "para mi", "yo solo" = 1 adulto
- "2 personas", "dos", "nosotros dos" = 2 adultos (confirmar si hay ninos)
- "con mi familia", "familia" = preguntar cuantos
- "con mi esposa", "con mi pareja" = 2 adultos
- "con mi hijo", "con ninos" = preguntar edades

RECONOCIMIENTO DE SELECCION DE VUELOS:
- "el 1", "el primero", "opcion 1", "numero 1" = vuelo 1
- "el ultimo", "el de abajo" = ultimo vuelo mostrado
- "el mas barato", "el economico", "el mas bajo" = vuelo con menor precio
- "el mas rapido", "el directo", "sin escalas" = vuelo directo o menor duracion
- "rutaca", "conviasa", "turpial", "laser" = filtrar por aerolinea y preguntar cual especificamente
- Si dice aerolinea sin numero: preguntar cual vuelo especifico de esa aerolinea"""
        
        # Historial
        history = session.data.get('ai_history', [])
        history = self._clean_history(history, max_items=20)  # Aumentado de 10 a 20
        
        # Agregar mensaje del usuario
        history.append({"role": "user", "parts": [{"text": message}]})
        
        # Definir funciones
        tools = [types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="search_flights",
                    description="Busca vuelos disponibles. LLAMA ESTA FUNCIÓN INMEDIATAMENTE cuando tengas: origen, destino, fecha de ida, tipo de viaje (ida o ida y vuelta), y número de pasajeros. NO escribas ningún mensaje antes de llamar esta función. NO confirmes datos. NO digas 'perfecto', 'listo', 'ok'. SOLO llama la función sin escribir absolutamente nada.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "origin": {"type": "string", "description": "Código IATA origen (CCS, PMV, MIA)"},
                            "destination": {"type": "string", "description": "Código IATA destino"},
                            "date": {"type": "string", "description": "Fecha de ida YYYY-MM-DD"},
                            "return_date": {"type": "string", "description": "Fecha de regreso YYYY-MM-DD (opcional, solo si el usuario quiere ida y vuelta)"},
                            "adults": {"type": "integer", "description": "Número de adultos (default: 1)"},
                            "children": {"type": "integer", "description": "Número de niños 2-11 años (default: 0)"},
                            "infants": {"type": "integer", "description": "Número de infantes 0-2 años (default: 0)"}
                        },
                        "required": ["origin", "destination", "date"]
                    }
                ),
                types.FunctionDeclaration(
                    name="select_flight",
                    description="Muestra clases disponibles del vuelo de IDA seleccionado. LLAMA INMEDIATAMENTE cuando el usuario elija un vuelo. Acepta: números (1,2,3), 'el primero', 'el último', 'el más barato', 'el directo', o nombre de aerolínea. Si dice solo aerolínea sin número, pregunta cuál vuelo específico de esa aerolínea. NO escribas confirmaciones.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "flight_index": {"type": "integer", "description": "Número del vuelo de ida (1, 2, 3...)"}
                        },
                        "required": ["flight_index"]
                    }
                ),
                types.FunctionDeclaration(
                    name="select_return_flight",
                    description="Muestra clases disponibles del vuelo de REGRESO seleccionado (solo si hay vuelos de regreso)",
                    parameters={
                        "type": "object",
                        "properties": {
                            "flight_index": {"type": "integer", "description": "Número del vuelo de regreso (1, 2, 3...)"}
                        },
                        "required": ["flight_index"]
                    }
                ),
                types.FunctionDeclaration(
                    name="confirm_flight",
                    description="Confirma vuelo de IDA y clase seleccionados",
                    parameters={
                        "type": "object",
                        "properties": {
                            "flight_index": {"type": "integer"},
                            "flight_class": {"type": "string", "description": "Código de clase (T, Y, B, etc)"}
                        },
                        "required": ["flight_index", "flight_class"]
                    }
                ),
                types.FunctionDeclaration(
                    name="confirm_return_flight",
                    description="Confirma vuelo de REGRESO y clase seleccionados (solo si hay vuelo de regreso)",
                    parameters={
                        "type": "object",
                        "properties": {
                            "flight_index": {"type": "integer"},
                            "flight_class": {"type": "string", "description": "Código de clase (T, Y, B, etc)"}
                        },
                        "required": ["flight_index", "flight_class"]
                    }
                ),
                types.FunctionDeclaration(
                    name="create_booking_multiple",
                    description="Crea reserva con datos de pasajeros. Para vuelos NACIONALES: nombre, apellido, cédula/pasaporte, teléfono, email. Para vuelos INTERNACIONALES: además país de nacimiento, país del documento y fecha de vencimiento. LLAMA INMEDIATAMENTE cuando tengas todos los datos.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "passengers": {
                                "type": "array",
                                "description": "Lista de pasajeros con sus datos completos",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string", "description": "Nombre(s) del pasajero"},
                                        "last_name": {"type": "string", "description": "Apellido(s) del pasajero"},
                                        "id_number": {"type": "string", "description": "Número de cédula o pasaporte"},
                                        "document_type": {"type": "string", "description": "Tipo de documento: 'cedula' o 'pasaporte'"},
                                        "nationality": {"type": "string", "description": "Código de país de 2 letras (VE=Venezuela, CO=Colombia, US=Estados Unidos, etc). Preguntar si es venezolano o extranjero"},
                                        "phone": {"type": "string", "description": "Teléfono"},
                                        "email": {"type": "string", "description": "Email"},
                                        "type": {"type": "string", "description": "Tipo: ADT (adulto), CHD (niño), INF (infante)"},
                                        "birth_country": {"type": "string", "description": "SOLO INTERNACIONAL: País de nacimiento (código 2 letras)"},
                                        "document_country": {"type": "string", "description": "SOLO INTERNACIONAL: País que emitió el documento (código 2 letras)"},
                                        "document_expiry": {"type": "string", "description": "SOLO INTERNACIONAL: Fecha de vencimiento del documento (formato DD/MM/YYYY)"}
                                    },
                                    "required": ["name", "last_name", "id_number", "document_type", "nationality", "phone", "email", "type"]
                                }
                            }
                        },
                        "required": ["passengers"]
                    }
                ),
                types.FunctionDeclaration(
                    name="get_booking_details",
                    description="Consulta reserva por código PNR. LLAMA INMEDIATAMENTE cuando el usuario dé el PNR. NO escribas 'ok', 'perfecto', 'déjame consultar'. SOLO llama la función.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "pnr": {"type": "string", "description": "Código PNR de 6 caracteres"}
                        },
                        "required": ["pnr"]
                    }
                ),
                types.FunctionDeclaration(
                    name="get_travel_requirements",
                    description="Obtiene requisitos migratorios de un país. LLAMA INMEDIATAMENTE cuando el usuario pregunte por requisitos de un país. NO escribas NADA antes de llamar esta función. NO digas 'Claro', 'Aquí tienes', ni nada. SOLO llama la función directamente.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "country": {"type": "string", "description": "Nombre del país del cual se quieren conocer los requisitos de entrada"}
                        },
                        "required": ["country"]
                    }
                ),
                types.FunctionDeclaration(
                    name="get_available_airports",
                    description="Obtiene la lista de aeropuertos disponibles (nacionales e internacionales). LLAMA INMEDIATAMENTE cuando el usuario pregunte por aeropuertos disponibles, destinos, ciudades disponibles, o a dónde se puede viajar.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "description": "Tipo de aeropuertos: 'national' (Venezuela), 'international', o 'all' (default: 'all')"}
                        }
                    }
                )
        ])]
        
        # Intentar con modelo principal
        try:
            # Llamar a Gemini
            response = self.client.models.generate_content(
                model=self.model,
                contents=history,
                config=types.GenerateContentConfig(
                    system_instruction=system_with_date,
                    tools=tools,
                    temperature=0.4,
                    top_p=0.95
                )
            )
            
            # Procesar respuesta
            if response.candidates and response.candidates[0].content.parts:
                first_part = response.candidates[0].content.parts[0]
                
                # Si hay llamada a función
                if hasattr(first_part, 'function_call') and first_part.function_call:
                    return self._handle_function_call(session, phone, response, history)
                
                # Si es texto
                if hasattr(first_part, 'text') and first_part.text:
                    ai_response = first_part.text
                    history.append({"role": "model", "parts": [{"text": ai_response}]})
                    session.data['ai_history'] = history[-20:]
                    return self._send_response(phone, ai_response, session)
            
            # Sin respuesta válida - mantener contexto
            flow_state = session.data.get('flow_state', 'idle')
            if flow_state == 'showing_flights':
                return self._send_response(phone, "Elige un vuelo por número (1, 2, 3...) o dime cuál prefieres 😊", session)
            elif flow_state == 'waiting_return_flight_selection':
                return self._send_response(phone, "¿Cuál vuelo de regreso prefieres? Dime el número 😊", session)
            elif flow_state == 'collecting_passenger_data':
                return self._send_response(phone, "Continúa con los datos del pasajero 😊", session)
            else:
                return self._send_response(phone, "¿Qué necesitas? 😊", session)
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error con modelo {self.model}: {error_msg}")
            
            # Guardar el historial ANTES de devolver error para no perder contexto
            session.data['ai_history'] = history[-20:]
            if "503" in error_msg or "overloaded" in error_msg.lower():
                return self._send_response(phone, "El servicio está ocupado 😅 Intenta en 10 segundos", session)
            else:
                return self._send_response(phone, "Hubo un error técnico 😅 ¿Puedes repetir?", session)
    
    def _handle_function_call(self, session, phone, response, history):
        """Maneja llamadas a funciones"""
        try:
            function_call = response.candidates[0].content.parts[0].function_call
            function_name = function_call.name
            function_args = dict(function_call.args)
            
            logger.info(f"Función: {function_name} | Args: {function_args}")
            
            # Ejecutar función
            if function_name == "search_flights":
                # SIEMPRE mostrar mensaje de búsqueda
                return_date = function_args.get('return_date')
                if return_date:
                    wati_service.send_message(phone, f"✈️ *Buscando vuelos ida y vuelta...*\n\n📍 {function_args['origin']} → {function_args['destination']}\n📅 Ida: {function_args['date']}\n🔙 Regreso: {return_date}")
                else:
                    wati_service.send_message(phone, f"✈️ *Buscando vuelos...*\n\n📍 {function_args['origin']} → {function_args['destination']}\n📅 {function_args['date']}")
                result = self._search_flights(function_args, session)
            
            elif function_name == "select_flight":
                wati_service.send_message(phone, f"💺 *Consultando clases disponibles...*")
                result = self._select_flight(function_args, session)
            
            elif function_name == "select_return_flight":
                wati_service.send_message(phone, f"💺 *Consultando clases de regreso...*")
                result = self._select_return_flight(function_args, session)
            
            elif function_name == "confirm_flight":
                result = self._confirm_flight(function_args, session)
            
            elif function_name == "confirm_return_flight":
                result = self._confirm_return_flight(function_args, session)
            
            elif function_name == "create_booking_multiple":
                num_pax = len(function_args.get('passengers', []))
                wati_service.send_message(phone, f"📝 *Creando reserva para {num_pax} {'persona' if num_pax == 1 else 'personas'}...*\n\n⏳ Esto toma unos segundos...")
                result = self._create_booking_multiple(function_args, session)
            
            elif function_name == "get_booking_details":
                wati_service.send_message(phone, f"🔍 *Consultando reserva {function_args['pnr']}...*")
                result = self._get_booking(function_args)
            
            elif function_name == "get_travel_requirements":
                country_name = function_args.get('country', 'el país')
                wati_service.send_message(phone, f"🌍 *Consultando requisitos de {country_name}...*")
                result = self._get_requirements(function_args)
            
            elif function_name == "get_available_airports":
                wati_service.send_message(phone, f"✈️ *Consultando aeropuertos...*")
                result = self._get_airports(function_args)
                # Enviar mensaje directamente y NO continuar con Gemini
                if result.get('success'):
                    airport_message = result.get('airport_message', '')
                    if airport_message:
                        wati_service.send_message(phone, airport_message)
                    # Guardar en historial y retornar SIN llamar a Gemini de nuevo
                    history.append({"role": "model", "parts": [{"text": "Aeropuertos mostrados"}]})
                    session.data['ai_history'] = history[-20:]
                    return {"success": True, "response": "Aeropuertos enviados"}  # Retornar sin enviar mensaje adicional
                else:
                    # Si falla, continuar con el flujo normal
                    result = {"success": False, "message": "No se pudieron obtener los aeropuertos 😕"}
            
            else:
                result = {"error": "Función no reconocida"}
            
            # Agregar al historial (preservar thought_signature para Gemini 3)
            first_part = response.candidates[0].content.parts[0]
            model_part = {"function_call": function_call}
            
            # Gemini 3 requiere thought_signature
            if hasattr(first_part, 'thought_signature') and first_part.thought_signature:
                model_part["thought_signature"] = first_part.thought_signature
            
            history.append({"role": "model", "parts": [model_part]})
            history.append({"role": "user", "parts": [{"function_response": {"name": function_name, "response": result}}]})
            
            # CONTEXTO EXPLÍCITO: Agregar instrucción de seguimiento basada en el resultado
            context_instruction = self._build_context_instruction(function_name, result, session)
            
            # CRÍTICO: Agregar mensaje explícito para forzar contexto
            # NO agregar como mensaje visible, solo como instrucción interna
            
            # Llamar de nuevo a Gemini con el resultado Y contexto explícito
            system_with_context = self.system_instruction + "\n\n" + context_instruction
            
            # CRÍTICO: Agregar recordatorio de estado al system prompt
            flow_state = session.data.get('flow_state', 'idle')
            if flow_state != 'idle':
                system_with_context += f"\n\n🔴🔴🔴 ESTADO ACTUAL: {flow_state}\nNO preguntes '¿Qué necesitas?' - Mantén el flujo activo.\n"
            
            follow_up = self.client.models.generate_content(
                model=self.model,
                contents=history,
                config=types.GenerateContentConfig(
                    system_instruction=system_with_context,
                    temperature=0.4,
                    top_p=0.95
                )
            )
            
            if follow_up.candidates and follow_up.candidates[0].content.parts:
                first_part = follow_up.candidates[0].content.parts[0]
                
                # Otra función (recursivo)
                if hasattr(first_part, 'function_call') and first_part.function_call:
                    return self._handle_function_call(session, phone, follow_up, history)
                
                # Texto
                if hasattr(first_part, 'text') and first_part.text:
                    ai_response = first_part.text
                    history.append({"role": "model", "parts": [{"text": ai_response}]})
                    session.data['ai_history'] = history[-20:]
                    return self._send_response(phone, ai_response, session)
            
            # Fallback si no hay respuesta - mantener contexto
            flow_state = session.data.get('flow_state', 'idle')
            if flow_state == 'showing_flights':
                return self._send_response(phone, "¿Cuál vuelo prefieres? Dime el número 😊", session)
            elif flow_state == 'waiting_return_flight_selection':
                return self._send_response(phone, "¿Cuál vuelo de regreso prefieres? Dime el número 😊", session)
            elif flow_state == 'collecting_passenger_data':
                return self._send_response(phone, "Continúa con los datos del pasajero 😊", session)
            else:
                # Si fue una reserva exitosa, mostrar detalles
                if function_name == "create_booking_multiple" and result.get('success'):
                    pnr = result.get('pnr', 'N/A')
                    vid = result.get('vid', 'N/A')
                    pasajeros = result.get('pasajeros', 'N/A')
                    num_pax = result.get('num_pasajeros', 1)
                    vuelo_ida = result.get('vuelo_ida', 'N/A')
                    origen = result.get('origen', '')
                    destino = result.get('destino', '')
                    fecha_ida = result.get('fecha_ida', '')
                    hora_salida = result.get('hora_salida_ida', '')
                    hora_llegada = result.get('hora_llegada_ida', '')
                    duracion = result.get('duracion_ida', '')
                    clase_ida = result.get('clase_ida', '')
                    precio_ida = result.get('precio_ida', '$0.00')
                    precio_total = result.get('precio_total', '$0.00')
                    aircraft = result.get('aircraft', 'N/A')
                    currency = result.get('currency', 'USD')
                    
                    # Formatear nombres de pasajeros
                    pax_list = pasajeros.split(', ')
                    pax_formatted = '\n'.join([f"  • {p}" for p in pax_list])
                    
                    msg = f"🎉 *¡Reserva confirmada!*\n\n"
                    msg += f"🎫 *PNR*: {pnr}\n"
                    msg += f"🆔 *ID*: {vid}\n\n"
                    msg += f"👥 *Pasajero{'s' if num_pax > 1 else ''}* ({num_pax}):\n{pax_formatted}\n\n"
                    msg += f"✈️ *Vuelo de Ida*\n"
                    msg += f"  {vuelo_ida}\n"
                    msg += f"  📍 {origen} → {destino}\n"
                    msg += f"  📅 {fecha_ida}\n"
                    msg += f"  🕐 {hora_salida} → {hora_llegada} ({duracion})\n"
                    msg += f"  💺 Clase {clase_ida}\n"
                    msg += f"  💰 {precio_ida} x {num_pax} = {precio_total}\n"
                    
                    # Si hay vuelo de regreso
                    if result.get('vuelo_regreso'):
                        msg += f"\n🔙 *Vuelo de Regreso*\n"
                        msg += f"  {result.get('vuelo_regreso')}\n"
                        msg += f"  📍 {destino} → {origen}\n"
                        msg += f"  📅 {result.get('fecha_regreso')}\n"
                        msg += f"  🕐 {result.get('hora_salida_regreso')} → {result.get('hora_llegada_regreso')} ({result.get('duracion_regreso')})\n"
                        msg += f"  💺 Clase {result.get('clase_regreso')}\n"
                        msg += f"  💰 {result.get('precio_regreso')} x {num_pax}\n"
                    
                    msg += f"\n💵 *Total*: {precio_total} {currency}\n\n"
                    msg += "¿Necesitas algo más? 😊"
                    return self._send_response(phone, msg, session)
                elif flow_state == 'showing_flights':
                    return self._send_response(phone, "¿Cuál vuelo prefieres? 😊", session)
                elif flow_state == 'waiting_return_flight_selection':
                    return self._send_response(phone, "¿Cuál vuelo de regreso? 😊", session)
                elif flow_state == 'collecting_passenger_data':
                    return self._send_response(phone, "Continúa con los datos 😊", session)
                else:
                    return self._send_response(phone, "✅ Listo. ¿Qué más necesitas?", session)
                
        except Exception as e:
            logger.error(f"Error en _handle_function_call: {str(e)}", exc_info=True)
            # CRÍTICO: Guardar historial para mantener contexto incluso con error
            if 'history' in locals() and history:
                session.data['ai_history'] = history[-20:]
            return self._send_response(phone, f"Hubo un problema: {str(e)[:100]}. ¿Intentamos de nuevo?", session)
    
    def _search_flights(self, args, session):
        """Busca SOLO vuelos de ida (regreso se busca después)"""
        try:
            # Extraer número de pasajeros
            adults = args.get('adults', 1)
            children = args.get('children', 0)
            infants = args.get('infants', 0)
            
            passengers = {"ADT": adults}
            if children > 0:
                passengers["CHD"] = children
            if infants > 0:
                passengers["INF"] = infants
            
            # Guardar en sesión
            session.data['passengers_count'] = passengers
            session.data['search_origin'] = args['origin']
            session.data['search_destination'] = args['destination']
            session.data['search_date'] = args['date']
            
            # Guardar fecha de regreso si existe (para buscar DESPUÉS)
            return_date = args.get('return_date')
            if return_date:
                session.data['search_return_date'] = return_date
                session.data['is_round_trip'] = True
            else:
                session.data['is_round_trip'] = False
            
            # Buscar SOLO vuelos de IDA
            flights_ida = flight_service.search_flights(
                origin=args['origin'],
                destination=args['destination'],
                date=args['date'],
                passengers=passengers
            )
            
            if not flights_ida:
                session.data['flow_state'] = 'idle'
                # Mantener datos de búsqueda para reintentar
                return {
                    "success": False, 
                    "message": f"No encontré vuelos para {args['date']} 😕\n\n¿Quieres probar con otra fecha? Dime cuál y busco de nuevo 😊",
                    "keep_context": True
                }
            
            # Guardar vuelos de ida
            session.data['available_flights'] = flights_ida
            session.data['flow_state'] = 'showing_flights'
            
            # Formatear vuelos de IDA
            vuelos_ida_data = self._format_flights_for_ai(flights_ida)
            
            # Mensaje para la IA
            message = f"ENCONTRÉ {len(flights_ida)} VUELOS DE IDA.\n\n"
            message += "INSTRUCCIONES CRÍTICAS:\n"
            message += "1. Muestra los vuelos en formato LIMPIO y VISUAL\n"
            message += "2. USA este formato EXACTO:\n"
            message += f"   ✈️ *Vuelos disponibles {args['origin']} → {args['destination']}* 📅 {args['date']}\n\n"
            message += "   Para cada vuelo:\n"
            message += "   *[Número].* [Aerolínea] [Vuelo]\n"
            message += "   🕐 [Hora salida] → [Hora llegada] ([Duración]) - [Tipo]\n"
            message += "   💰 *[Precio]*\n\n"
            message += "3. Al final: '¿Cuál te gusta? 😊'\n"
            if return_date:
                message += "4. IMPORTANTE: Los vuelos de REGRESO se buscarán DESPUÉS de seleccionar el vuelo de ida\n"
            message += "\nVUELOS DE IDA:\n"
            for v in vuelos_ida_data:
                message += f"{v['numero']}. {v['aerolinea']} {v['vuelo']} - {v['salida']} a {v['llegada']} ({v['duracion']}) - {v['tipo_vuelo']} - {v['precio']}\n"
            
            response = {
                "success": True,
                "total_ida": len(flights_ida),
                "vuelos_ida": vuelos_ida_data,
                "is_round_trip": bool(return_date),
                "message": message
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error en _search_flights: {str(e)}")
            session.data['flow_state'] = 'idle'
            return {"success": False, "error": str(e)}
    
    def _format_flights_for_ai(self, flights):
        """Formatea lista de vuelos para la IA con información esencial"""
        vuelos_data = []
        for i, f in enumerate(flights[:10], 1):
            api_data = f.get('api_data', {})
            segments = api_data.get('segments', [])
            
            is_direct = api_data.get('isDirect', True)
            stops = "Directo" if is_direct else f"{len(segments)-1} escala(s)"
            
            vuelos_data.append({
                "numero": i,
                "aerolinea": f.get('airline_name'),
                "vuelo": f.get('flight_number'),
                "salida": f.get('departure_time'),
                "llegada": f.get('arrival_time'),
                "duracion": f.get('duration'),
                "precio": f"${f.get('price'):.2f}" if f.get('price') else "Consultar",
                "tipo_vuelo": stops
            })
        return vuelos_data
    
    def _select_flight(self, args, session):
        """Selecciona vuelo y muestra clases con precios reales de KIU"""
        try:
            flights = session.data.get('available_flights', [])
            idx = args['flight_index']
            
            if not flights or idx < 1 or idx > len(flights):
                return {"success": False, "message": "Vuelo no válido"}
            
            flight = flights[idx - 1]
            session.data['selected_flight_index'] = idx
            session.data['selected_flight'] = flight
            # Guardar timestamp cuando se muestran las clases
            session.data['classes_shown_at'] = datetime.now(VENEZUELA_TZ).isoformat()
            
            # Obtener clases disponibles
            api_data = flight.get('api_data', {})
            segments = api_data.get('segments', [])
            
            if not segments:
                return {"success": False, "message": "No hay información de clases"}
            
            classes = segments[0].get('classes', {})
            segment_id = segments[0].get('id')
            
            # Obtener precios REALES de cada clase desde KIU
            from concurrent.futures import ThreadPoolExecutor, as_completed
            from kiu_service import kiu_service
            
            clases_data = []
            
            def get_class_price(class_code):
                """Obtiene precio de una clase específica"""
                try:
                    occupation = [{"type": "ADT", "segments": {segment_id: class_code}}]
                    pricing_result = kiu_service.get_flight_pricing(
                        departure_flight=api_data,
                        occupation=occupation
                    )
                    
                    if pricing_result.get('success'):
                        pricing_data = pricing_result.get('data', [])
                        if isinstance(pricing_data, list) and len(pricing_data) > 0:
                            price = pricing_data[0].get('price')
                            if price and price > 0:
                                return (class_code, price)
                except:
                    pass
                return (class_code, None)
            
            # Obtener precios en paralelo (máximo 10 clases) - TIMEOUT REDUCIDO
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(get_class_price, c): c for c in list(classes.keys())[:10]}
                
                try:
                    for future in as_completed(futures, timeout=15):  # Reducido de 25 a 15
                        try:
                            class_code, price = future.result(timeout=1)
                            availability = classes.get(class_code, '0')
                            
                            if int(availability) > 0:
                                clases_data.append({
                                    "clase": class_code,
                                    "asientos": availability,
                                    "precio": f"${price:.2f}" if price else "Consultar"
                                })
                        except:
                            pass
                except:
                    # Si hay timeout, usar las clases que ya obtuvimos
                    pass
            
            # Si no se obtuvieron precios, usar el precio base del vuelo
            if not clases_data:
                for class_code, availability in sorted(classes.items()):
                    if int(availability) > 0:
                        clases_data.append({
                            "clase": class_code,
                            "asientos": availability,
                            "precio": f"${flight.get('price', 0):.2f}"
                        })
            
            # Ordenar por precio (menor a mayor)
            clases_data.sort(key=lambda x: float(x['precio'].replace('$', '').replace('Consultar', '999')))
            
            return {
                "success": True,
                "vuelo": f"{flight.get('airline_name')} {flight.get('flight_number')}",
                "clases": clases_data,
                "message": f"MUESTRA LAS CLASES con este formato LIMPIO:\n\n💺 *Clases disponibles - {flight.get('airline_name')} {flight.get('flight_number')}*\n\nPara cada clase:\n• *Clase [Código]*: [Precio] ([Asientos] disponibles)\n\nAl final: '¿Cuál clase prefieres? 😊'"
            }
            
        except Exception as e:
            logger.error(f"Error en _select_flight: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _select_return_flight(self, args, session):
        """Selecciona vuelo de REGRESO y muestra clases"""
        try:
            flights = session.data.get('available_return_flights', [])
            idx = args['flight_index']
            
            if not flights or idx < 1 or idx > len(flights):
                return {"success": False, "message": "Vuelo de regreso no válido"}
            
            flight = flights[idx - 1]
            session.data['selected_return_flight_index'] = idx
            session.data['selected_return_flight'] = flight
            # Guardar timestamp cuando se muestran las clases de regreso
            session.data['return_classes_shown_at'] = datetime.now(VENEZUELA_TZ).isoformat()
            
            api_data = flight.get('api_data', {})
            segments = api_data.get('segments', [])
            
            if not segments:
                return {"success": False, "message": "No hay información de clases"}
            
            classes = segments[0].get('classes', {})
            segment_id = segments[0].get('id')
            
            from concurrent.futures import ThreadPoolExecutor, as_completed
            from kiu_service import kiu_service
            
            clases_data = []
            
            def get_class_price(class_code):
                try:
                    occupation = [{"type": "ADT", "segments": {segment_id: class_code}}]
                    pricing_result = kiu_service.get_flight_pricing(
                        departure_flight=api_data,
                        occupation=occupation
                    )
                    
                    if pricing_result.get('success'):
                        pricing_data = pricing_result.get('data', [])
                        if isinstance(pricing_data, list) and len(pricing_data) > 0:
                            price = pricing_data[0].get('price')
                            if price and price > 0:
                                return (class_code, price)
                except:
                    pass
                return (class_code, None)
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(get_class_price, c): c for c in list(classes.keys())[:10]}
                
                try:
                    for future in as_completed(futures, timeout=15):  # Reducido de 25 a 15
                        try:
                            class_code, price = future.result(timeout=1)
                            availability = classes.get(class_code, '0')
                            
                            if int(availability) > 0:
                                clases_data.append({
                                    "clase": class_code,
                                    "asientos": availability,
                                    "precio": f"${price:.2f}" if price else "Consultar"
                                })
                        except:
                            pass
                except:
                    pass
            
            if not clases_data:
                for class_code, availability in sorted(classes.items()):
                    if int(availability) > 0:
                        clases_data.append({
                            "clase": class_code,
                            "asientos": availability,
                            "precio": f"${flight.get('price', 0):.2f}"
                        })
            
            clases_data.sort(key=lambda x: float(x['precio'].replace('$', '').replace('Consultar', '999')))
            
            return {
                "success": True,
                "vuelo": f"{flight.get('airline_name')} {flight.get('flight_number')}",
                "clases": clases_data,
                "message": "Muestra las clases del vuelo de REGRESO y pregunta cuál prefiere"
            }
            
        except Exception as e:
            logger.error(f"Error en _select_return_flight: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _confirm_flight(self, args, session):
        """Confirma vuelo y clase, luego busca vuelos de regreso si es ida y vuelta"""
        try:
            flight = session.data.get('selected_flight')
            if not flight:
                return {"success": False, "message": "No hay vuelo seleccionado"}
            
            selected_class = args['flight_class'].upper()
            
            # Obtener precio REAL de la clase seleccionada
            classes_prices = flight.get('classes_prices', {})
            class_info = classes_prices.get(selected_class, {})
            
            if class_info and class_info.get('price'):
                flight['price'] = class_info['price']
                flight['base'] = class_info.get('base', class_info['price'])
            else:
                # Obtener de KIU si no está en cache
                from kiu_service import kiu_service
                api_data = flight.get('api_data', {})
                segments = api_data.get('segments', [])
                
                if segments:
                    segment_id = segments[0].get('id')
                    occupation = [{"type": "ADT", "segments": {segment_id: selected_class}}]
                    pricing_result = kiu_service.get_flight_pricing(
                        departure_flight=api_data,
                        occupation=occupation
                    )
                    
                    if pricing_result.get('success'):
                        pricing_data = pricing_result.get('data', [])
                        if isinstance(pricing_data, list) and len(pricing_data) > 0:
                            price = pricing_data[0].get('price')
                            if price and price > 0:
                                flight['price'] = price
                                flight['base'] = pricing_data[0].get('base', price)
            
            flight['class'] = selected_class
            session.data['selected_flight'] = flight
            session.data['selected_class'] = selected_class
            
            # VERIFICAR SI ES IDA Y VUELTA
            is_round_trip = session.data.get('is_round_trip', False)
            has_return_flight = session.data.get('selected_return_flight') is not None
            
            if is_round_trip and not has_return_flight:
                # ES ida y vuelta pero NO se ha seleccionado vuelo de regreso
                # BUSCAR AHORA los vuelos de regreso
                return_date = session.data.get('search_return_date')
                origin = session.data.get('search_destination')  # Invertir
                destination = session.data.get('search_origin')
                passengers = session.data.get('passengers_count', {"ADT": 1})
                
                if return_date and origin and destination:
                    # Buscar vuelos de regreso
                    flights_regreso = flight_service.search_flights(
                        origin=origin,
                        destination=destination,
                        date=return_date,
                        passengers=passengers
                    )
                    
                    if not flights_regreso:
                        session.data['flow_state'] = 'idle'
                        return {
                            "success": False,
                            "message": f"Vuelo de ida confirmado ✅ pero no hay vuelos de regreso para {return_date} 😕 ¿Probamos otra fecha de regreso?"
                        }
                    
                    # Guardar vuelos de regreso
                    session.data['available_return_flights'] = flights_regreso
                    session.data['flow_state'] = 'waiting_return_flight_selection'
                    vuelos_regreso_data = self._format_flights_for_ai(flights_regreso)
                    
                    # INSTRUCCIONES CLARAS para la IA
                    message = f"VUELO DE IDA CONFIRMADO. AHORA MUESTRA LOS VUELOS DE REGRESO.\n\n"
                    message += f"INSTRUCCIONES CRÍTICAS:\n"
                    message += f"1. Confirma el vuelo de ida brevemente\n"
                    message += f"2. Muestra los {len(flights_regreso)} vuelos de regreso con formato LIMPIO\n"
                    message += f"3. Usa el MISMO formato que usaste para los vuelos de ida\n"
                    message += f"4. Al final pregunta: '¿Cuál vuelo de regreso prefieres? 😊'\n\n"
                    message += f"VUELO DE IDA CONFIRMADO:\n"
                    message += f"- {flight.get('airline_name')} {flight.get('flight_number')}\n"
                    message += f"- Clase {selected_class}\n"
                    message += f"- ${flight.get('price', 0):.2f}\n\n"
                    message += f"VUELOS DE REGRESO DISPONIBLES ({len(flights_regreso)}):\n"
                    for v in vuelos_regreso_data:
                        message += f"{v['numero']}. {v['aerolinea']} {v['vuelo']} - {v['salida']} a {v['llegada']} ({v['duracion']}) - {v['tipo_vuelo']} - {v['precio']}\n"
                    
                    return {
                        "success": True,
                        "action": "show_return_flights",
                        "vuelo_ida_confirmado": True,
                        "vuelo_ida": f"{flight.get('airline_name')} {flight.get('flight_number')}",
                        "clase_ida": selected_class,
                        "precio_ida": f"${flight.get('price', 0):.2f}",
                        "total_vuelos_regreso": len(flights_regreso),
                        "vuelos_regreso": vuelos_regreso_data,
                        "message": message
                    }
            
            # NO es ida y vuelta O ya se seleccionó regreso
            session.data['flow_state'] = 'collecting_passenger_data'
            session.data['flow_state'] = 'collecting_passenger_data'
            num_pax = sum(session.data.get('passengers_count', {"ADT": 1}).values())
            return {
                "success": True,
                "vuelo": f"{flight.get('airline_name')} {flight.get('flight_number')}",
                "clase": selected_class,
                "precio": f"${flight.get('price', 0):.2f}",
                "num_pasajeros": num_pax,
                "message": f"""Vuelo confirmado ✅

📝 *RESERVA*
Para iniciar tu reserva, indícame el *nombre y apellido* {'del primer pasajero' if num_pax > 1 else ''} (como aparece en la cédula) 👤"""
            }
            
        except Exception as e:
            logger.error(f"Error en _confirm_flight: {str(e)}")
            session.data['flow_state'] = 'idle'
            return {"success": False, "error": str(e)}
    
    def _confirm_return_flight(self, args, session):
        """Confirma vuelo de REGRESO y clase"""
        try:
            flight = session.data.get('selected_return_flight')
            if not flight:
                return {"success": False, "message": "No hay vuelo de regreso seleccionado"}
            
            selected_class = args['flight_class'].upper()
            
            from kiu_service import kiu_service
            api_data = flight.get('api_data', {})
            segments = api_data.get('segments', [])
            
            if segments:
                segment_id = segments[0].get('id')
                occupation = [{"type": "ADT", "segments": {segment_id: selected_class}}]
                
                pricing_result = kiu_service.get_flight_pricing(
                    departure_flight=api_data,
                    occupation=occupation
                )
                
                if pricing_result.get('success'):
                    pricing_data = pricing_result.get('data', [])
                    if isinstance(pricing_data, list) and len(pricing_data) > 0:
                        price = pricing_data[0].get('price')
                        base = pricing_data[0].get('base', price)
                        
                        if price and price > 0:
                            flight['price'] = price
                            flight['base'] = base
            
            flight['class'] = selected_class
            session.data['selected_return_flight'] = flight
            session.data['selected_return_class'] = selected_class
            
            session.data['flow_state'] = 'collecting_passenger_data'
            num_pax = sum(session.data.get('passengers_count', {"ADT": 1}).values())
            return {
                "success": True,
                "vuelo": f"{flight.get('airline_name')} {flight.get('flight_number')}",
                "clase": selected_class,
                "precio": f"${flight.get('price', 0):.2f}",
                "num_pasajeros": num_pax,
                "message": f"""Vuelo de regreso confirmado ✅

📝 *RESERVA*
Para iniciar tu reserva, indícame el *nombre y apellido* {'del primer pasajero' if num_pax > 1 else ''} (como aparece en la cédula) 👤"""
            }
            
        except Exception as e:
            logger.error(f"Error en _confirm_return_flight: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _create_booking_multiple(self, args, session):
        """Crea reserva con múltiples pasajeros (ida o ida y vuelta)"""
        try:
            flight = session.data.get('selected_flight')
            flight_class = session.data.get('selected_class', 'Y')
            return_flight = session.data.get('selected_return_flight')  # Puede ser None
            return_class = session.data.get('selected_return_class')
            
            if not flight:
                return {"success": False, "message": "No hay vuelo seleccionado"}
            
            # VERIFICAR SI PASÓ MÁS DE 1 HORA DESDE QUE SE MOSTRARON LAS CLASES
            classes_shown_at = session.data.get('classes_shown_at')
            needs_revalidation = False
            
            if classes_shown_at:
                try:
                    shown_time = datetime.fromisoformat(classes_shown_at)
                    time_elapsed = datetime.now(VENEZUELA_TZ) - shown_time
                    
                    # Si pasó más de 1 hora (3600 segundos)
                    if time_elapsed.total_seconds() > 3600:
                        needs_revalidation = True
                        logger.info(f"Revalidación necesaria: {time_elapsed.total_seconds()/60:.1f} minutos desde que se mostraron las clases")
                except Exception as e:
                    logger.error(f"Error verificando timestamp: {e}")
            
            # REVALIDAR PRECIOS SI ES NECESARIO
            if needs_revalidation:
                logger.info("Revalidando disponibilidad y precios...")
                
                from kiu_service import kiu_service
                api_data = flight.get('api_data', {})
                segments = api_data.get('segments', [])
                
                if segments:
                    segment_id = segments[0].get('id')
                    classes = segments[0].get('classes', {})
                    
                    # Verificar disponibilidad de la clase seleccionada
                    availability = classes.get(flight_class, '0')
                    
                    if int(availability) <= 0:
                        return {
                            "success": False,
                            "message": f"😔 La clase {flight_class} ya no está disponible. Te muestro las opciones actuales...",
                            "action": "reselect_class"
                        }
                    
                    # Obtener precio actualizado
                    try:
                        occupation = [{"type": "ADT", "segments": {segment_id: flight_class}}]
                        pricing_result = kiu_service.get_flight_pricing(
                            departure_flight=api_data,
                            occupation=occupation
                        )
                        
                        if pricing_result.get('success'):
                            pricing_data = pricing_result.get('data', [])
                            if isinstance(pricing_data, list) and len(pricing_data) > 0:
                                new_price = pricing_data[0].get('price')
                                old_price = flight.get('price', 0)
                                
                                if new_price and new_price > 0:
                                    # Verificar si el precio cambió significativamente (más de $5)
                                    price_diff = abs(new_price - old_price)
                                    
                                    if price_diff > 5:
                                        logger.info(f"Precio cambió de ${old_price:.2f} a ${new_price:.2f}")
                                        # Actualizar precio
                                        flight['price'] = new_price
                                        session.data['selected_flight'] = flight
                                        
                                        # Informar al usuario del cambio
                                        return {
                                            "success": False,
                                            "message": f"⚠️ El precio cambió de *${old_price:.2f}* a *${new_price:.2f}*\n\n¿Deseas continuar con la reserva al nuevo precio?",
                                            "action": "price_changed",
                                            "old_price": old_price,
                                            "new_price": new_price
                                        }
                                    else:
                                        # Precio similar, actualizar silenciosamente
                                        flight['price'] = new_price
                                        session.data['selected_flight'] = flight
                                        logger.info(f"Precio actualizado: ${new_price:.2f} (cambio menor)")
                    except Exception as e:
                        logger.error(f"Error revalidando precio: {e}")
                        # Continuar con el precio original si falla la revalidación
                
                # Revalidar vuelo de regreso si existe
                if return_flight and return_class:
                    return_classes_shown_at = session.data.get('return_classes_shown_at')
                    if return_classes_shown_at:
                        try:
                            shown_time = datetime.fromisoformat(return_classes_shown_at)
                            time_elapsed = datetime.now(VENEZUELA_TZ) - shown_time
                            
                            if time_elapsed.total_seconds() > 3600:
                                api_data_return = return_flight.get('api_data', {})
                                segments_return = api_data_return.get('segments', [])
                                
                                if segments_return:
                                    segment_id_return = segments_return[0].get('id')
                                    classes_return = segments_return[0].get('classes', {})
                                    
                                    availability_return = classes_return.get(return_class, '0')
                                    
                                    if int(availability_return) <= 0:
                                        return {
                                            "success": False,
                                            "message": f"😔 La clase {return_class} del vuelo de regreso ya no está disponible. Te muestro las opciones actuales...",
                                            "action": "reselect_return_class"
                                        }
                                    
                                    # Obtener precio actualizado del regreso
                                    try:
                                        occupation_return = [{"type": "ADT", "segments": {segment_id_return: return_class}}]
                                        pricing_result_return = kiu_service.get_flight_pricing(
                                            departure_flight=api_data_return,
                                            occupation=occupation_return
                                        )
                                        
                                        if pricing_result_return.get('success'):
                                            pricing_data_return = pricing_result_return.get('data', [])
                                            if isinstance(pricing_data_return, list) and len(pricing_data_return) > 0:
                                                new_price_return = pricing_data_return[0].get('price')
                                                old_price_return = return_flight.get('price', 0)
                                                
                                                if new_price_return and new_price_return > 0:
                                                    price_diff_return = abs(new_price_return - old_price_return)
                                                    
                                                    if price_diff_return > 5:
                                                        logger.info(f"Precio de regreso cambió de ${old_price_return:.2f} a ${new_price_return:.2f}")
                                                        return_flight['price'] = new_price_return
                                                        session.data['selected_return_flight'] = return_flight
                                                        
                                                        total_old = flight.get('price', 0) + old_price_return
                                                        total_new = flight.get('price', 0) + new_price_return
                                                        
                                                        return {
                                                            "success": False,
                                                            "message": f"⚠️ El precio del vuelo de regreso cambió de *${old_price_return:.2f}* a *${new_price_return:.2f}*\n\nTotal: *${total_old:.2f}* → *${total_new:.2f}*\n\n¿Deseas continuar?",
                                                            "action": "price_changed",
                                                            "old_price": total_old,
                                                            "new_price": total_new
                                                        }
                                                    else:
                                                        return_flight['price'] = new_price_return
                                                        session.data['selected_return_flight'] = return_flight
                                                        logger.info(f"Precio de regreso actualizado: ${new_price_return:.2f}")
                                    except Exception as e:
                                        logger.error(f"Error revalidando precio de regreso: {e}")
                        except Exception as e:
                            logger.error(f"Error verificando timestamp de regreso: {e}")
            
            flight['class'] = flight_class
            if return_flight and return_class:
                return_flight['class'] = return_class
            
            passengers_list = []
            passengers_data = args.get('passengers', [])
            
            if not passengers_data:
                return {"success": False, "message": "No hay datos de pasajeros"}
            
            logger.info(f"Creando reserva para {len(passengers_data)} pasajero(s)")
            
            # VALIDAR DATOS DE PASAJEROS (MEJORA #2)
            for i, pax_data in enumerate(passengers_data, 1):
                # Combinar name y last_name si están separados para la validación
                full_name = pax_data.get('name', '')
                if pax_data.get('last_name'):
                    full_name = f"{pax_data.get('name', '')} {pax_data.get('last_name', '')}"
                
                # Validar nombre completo
                valid_name, error_name = validate_name(full_name)
                if not valid_name:
                    return {"success": False, "message": f"Pasajero {i}: {error_name}"}
                
                # Validar email
                valid_email, error_email = validate_email(pax_data['email'])
                if not valid_email:
                    return {"success": False, "message": f"Pasajero {i}: {error_email}"}
                
                # Validar teléfono
                valid_phone, error_phone = validate_phone(pax_data['phone'])
                if not valid_phone:
                    return {"success": False, "message": f"Pasajero {i}: {error_phone}"}
                
                # Validar cédula
                valid_cedula, error_cedula = validate_cedula(pax_data['id_number'])
                if not valid_cedula:
                    return {"success": False, "message": f"Pasajero {i}: {error_cedula}"}
                
                # Usar nombre y apellido separados si están disponibles, sino extraer del name
                if pax_data.get('last_name'):
                    first_name = pax_data.get('name', '').strip()
                    last_name = pax_data.get('last_name', '').strip()
                else:
                    name_parts = pax_data['name'].strip().split()
                    first_name = name_parts[0] if name_parts else ''
                    last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else name_parts[0]
                
                clean_id = re.sub(r'[^0-9A-Za-z]', '', pax_data['id_number'])
                clean_phone = re.sub(r'[^0-9]', '', pax_data['phone'])
                
                nationality = pax_data.get('nationality', 'VE').upper()
                document_type = 'PP' if pax_data.get('document_type', 'cedula').lower() == 'pasaporte' else 'CI'
                
                passenger = {
                    'name': first_name.upper(),
                    'lastName': last_name.upper(),
                    'idNumber': clean_id,
                    'phone': clean_phone,
                    'email': pax_data['email'],
                    'type': pax_data.get('type', 'ADT').upper(),
                    'nationality': nationality,
                    'documentType': document_type,
                    'address': 'Av Principal',
                    'city': 'Caracas',
                    # Campos adicionales para vuelos internacionales
                    'birthCountry': pax_data.get('birth_country', nationality).upper(),
                    'docIssueCountry': pax_data.get('document_country', nationality).upper(),
                    'docExpiry': pax_data.get('document_expiry', '')
                }
                passengers_list.append(passenger)
                logger.info(f"Pasajero {len(passengers_list)}: {first_name} {last_name} ({passenger['type']})")
            
            passengers_count = session.data.get('passengers_count', {"ADT": len(passengers_list)})
            flight['passengers'] = passengers_count
            
            logger.info(f"Enviando a KIU: {len(passengers_list)} pasajeros con configuración {passengers_count}")
            
            # MEJORA #1: Feedback durante espera (ALTA PRIORIDAD)
            # Mensaje inicial ya se envió en _handle_function_call
            # Ahora enviamos mensajes de progreso durante la espera
            import threading
            import time
            
            phone = session.phone
            progress_sent = {'30s': False, '60s': False}
            
            def send_progress_updates():
                """Envía mensajes de progreso cada 30 segundos"""
                time.sleep(30)
                if not progress_sent['30s']:
                    wati_service.send_message(phone, "⏳ Aún procesando... casi listo... 🔄")
                    progress_sent['30s'] = True
                
                time.sleep(30)
                if not progress_sent['60s']:
                    wati_service.send_message(phone, "✨ Finalizando reserva... ¡Ya casi! 🎉")
                    progress_sent['60s'] = True
            
            # Iniciar thread de progreso
            progress_thread = threading.Thread(target=send_progress_updates, daemon=True)
            progress_thread.start()
            
            # Crear reserva (con o sin vuelo de regreso)
            result = flight_service.create_booking(
                flight_option=flight,
                passenger_details=passengers_list,
                return_flight_option=return_flight  # Puede ser None
            )
            
            # Detener mensajes de progreso
            progress_sent['30s'] = True
            progress_sent['60s'] = True
            
            if result.get('success'):
                names = [p['name'] for p in passengers_data]
                names_str = ', '.join(names)
                
                response = {
                    "success": True,
                    "pnr": result.get('pnr'),
                    "vid": result.get('vid'),
                    "pasajeros": names_str,
                    "num_pasajeros": len(passengers_list),
                    "vuelo_ida": f"{flight.get('airline_name')} {flight.get('flight_number')}",
                    "origen": flight.get('origin'),
                    "destino": flight.get('destination'),
                    "fecha_ida": flight.get('date'),
                    "hora_salida_ida": flight.get('departure_time'),
                    "hora_llegada_ida": flight.get('arrival_time'),
                    "duracion_ida": flight.get('duration'),
                    "clase_ida": flight_class,
                    "precio_ida": f"${flight.get('price', 0):.2f}",
                    "aircraft": flight.get('aircraft'),
                    "currency": flight.get('currency', 'USD'),
                }
                
                # Agregar info de vuelo de regreso si existe
                if return_flight:
                    response["vuelo_regreso"] = f"{return_flight.get('airline_name')} {return_flight.get('flight_number')}"
                    response["fecha_regreso"] = return_flight.get('date')
                    response["hora_salida_regreso"] = return_flight.get('departure_time')
                    response["hora_llegada_regreso"] = return_flight.get('arrival_time')
                    response["duracion_regreso"] = return_flight.get('duration')
                    response["clase_regreso"] = return_class
                    response["precio_regreso"] = f"${return_flight.get('price', 0):.2f}"
                    total_price = (flight.get('price', 0) + return_flight.get('price', 0)) * len(passengers_list)
                    response["precio_total"] = f"${total_price:.2f}"
                    response["message"] = f"¡Reserva IDA Y VUELTA creada para {len(passengers_list)} {'persona' if len(passengers_list) == 1 else 'personas'}! Muestra TODOS los detalles"
                else:
                    total_price = flight.get('price', 0) * len(passengers_list)
                    response["precio_total"] = f"${total_price:.2f}"
                    response["message"] = f"¡Reserva de IDA creada para {len(passengers_list)} {'persona' if len(passengers_list) == 1 else 'personas'}! Muestra TODOS los detalles"
                
                return response
            else:
                error_msg = result.get('error', 'Error al crear reserva')
                
                # MEJORA #4: Mensajes de error específicos (ALTA PRIORIDAD)
                if result.get('timeout'):
                    return {
                        "success": False,
                        "error": "⏱️ La aerolínea está tardando en responder. Esto puede deberse a alta demanda. ¿Intentas de nuevo en 5 minutos?",
                        "message": "Error de timeout. Ofrece reintentar."
                    }
                elif 'expired' in error_msg.lower() or 'expir' in error_msg.lower():
                    return {
                        "success": False,
                        "error": "⏰ Los precios cambiaron. Busquemos el vuelo de nuevo para ver las opciones actualizadas 🔄",
                        "message": "Datos expirados. Ofrece buscar de nuevo."
                    }
                elif 'availability' in error_msg.lower() or 'disponib' in error_msg.lower():
                    return {
                        "success": False,
                        "error": "😔 Este vuelo se agotó. Te muestro otras opciones disponibles...",
                        "message": "Sin disponibilidad. Ofrece otras opciones."
                    }
                else:
                    return {
                        "success": False,
                        "error": f"❌ Hubo un problema técnico. {error_msg[:100]}",
                        "message": "La reserva falló. Ofrece buscar de nuevo."
                    }
                
        except Exception as e:
            logger.error(f"Error en _create_booking_multiple: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _get_booking(self, args):
        """Consulta reserva con TODOS los campos de KIU"""
        try:
            result = flight_service.get_booking_details(pnr=args['pnr'])
            
            if result.get('success'):
                # Extraer TODOS los campos disponibles
                response = {
                    "success": True,
                    "pnr": result.get('pnr'),
                    "estado": result.get('status'),
                    "estado_vuelo": result.get('flight_status'),
                    "cliente": result.get('client'),
                    "ruta": result.get('route'),
                    "precio": result.get('balance'),
                    "precio_base": result.get('base'),
                    "vencimiento": result.get('vencimiento'),
                    "tipo": result.get('type'),
                    "message": "Reserva encontrada. Muestra TODOS los detalles de forma clara y organizada"
                }
                
                # Agregar pasajeros con todos sus datos
                passengers = result.get('passengers', [])
                if passengers:
                    response['pasajeros'] = passengers
                    response['num_pasajeros'] = len(passengers)
                
                # Agregar vuelos con todos sus datos
                flights = result.get('flights', [])
                if flights:
                    response['vuelos'] = flights
                    response['num_vuelos'] = len(flights)
                
                return response
            else:
                return {"success": False, "message": f"Reserva {args['pnr']} no encontrada"}
                
        except Exception as e:
            logger.error(f"Error en _get_booking: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _get_requirements(self, args):
        """Obtiene requisitos migratorios"""
        try:
            country = args['country'].lower()
            requisitos = get_requisitos_pais(country)
            
            if requisitos:
                return {
                    "success": True, 
                    "requisitos": requisitos,
                    "message": f"MUESTRA EXACTAMENTE ESTE TEXTO AL USUARIO (sin agregar nada más):\n\n{requisitos}\n\n¿Necesitas algo más? 😊"
                }
            else:
                return {"success": False, "message": "No encontré ese país 😕 ¿Puedes escribirlo de nuevo?"}
                
        except Exception as e:
            logger.error(f"Error en _get_requirements: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _get_airports(self, args):
        """Obtiene lista de aeropuertos disponibles"""
        try:
            from kiu_service import kiu_service
            
            airport_type = args.get('type', 'all')
            
            # Obtener aeropuertos nacionales
            result = kiu_service.get_national_airports()
            
            if not result.get('success'):
                return {"success": False, "message": "No se pudieron obtener los aeropuertos 😕"}
            
            data = result.get('data', {})
            
            # Los datos vienen como: {"national": [{...}, {...}], "checksum_national": ...}
            national_list = data.get('national', [])
            
            if not national_list:
                return {"success": False, "message": "No se encontraron aeropuertos 😕"}
            
            # Separar aeropuertos venezolanos de internacionales
            venezuela_airports = []
            international_airports = []
            
            for airport in national_list:
                if isinstance(airport, dict):
                    pais = airport.get('pais', '')
                    code = airport.get('iata_code', 'N/A')
                    ciudad = airport.get('ciudad_aeropuerto', 'N/A')
                    
                    if pais == 'Venezuela':
                        venezuela_airports.append(code)
                    else:
                        international_airports.append(f"{code} ({pais})")
            
            # Crear mensaje compacto
            message = "✈️ *Aeropuertos Disponibles*\n\n"
            
            if venezuela_airports:
                message += "🇻🇪 *Venezuela:*\n"
                message += ", ".join(sorted(venezuela_airports))
                message += "\n\n"
            
            if international_airports:
                message += "🌎 *Internacional:*\n"
                # Mostrar solo códigos para internacional
                intl_codes = [a.split(' ')[0] for a in international_airports]
                message += ", ".join(sorted(intl_codes))
                message += "\n\n"
            
            message += "¿A dónde quieres viajar? 😊"
            
            return {
                "success": True,
                "airport_message": message,
                "message": "Lista de aeropuertos enviada"
            }
            
        except Exception as e:
            logger.error(f"Error en _get_airports: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _get_flow_context(self, session, flow_state):
        """Obtiene contexto del flujo actual para mantener coherencia"""
        
        if flow_state == 'waiting_return_flight_selection':
            return """
🔴 ESTADO ACTUAL: ESPERANDO SELECCIÓN DE VUELO DE REGRESO

El usuario acaba de confirmar su vuelo de IDA.
Ahora debe elegir un vuelo de REGRESO de la lista que se le mostró.

NO preguntes "¿Qué necesitas?" - Estás esperando que elija un número de vuelo.
Si el usuario da un número, llama select_return_flight con ese número.
"""
        
        elif flow_state == 'waiting_return_class_selection':
            return """
🔴 ESTADO ACTUAL: ESPERANDO SELECCIÓN DE CLASE DE REGRESO

El usuario acaba de ver las clases disponibles del vuelo de REGRESO.
Ahora debe elegir una clase.

NO preguntes "¿Qué necesitas?" - Estás esperando que elija una clase.
"""
        
        elif flow_state == 'collecting_passenger_data':
            num_pax = session.data.get('passengers_count', {}).get('ADT', 1)
            current_pax = len(session.data.get('collected_passengers', []))
            return f"""
🔴 ESTADO ACTUAL: RECOPILANDO DATOS DE PASAJEROS

Estas recopilando datos del pasajero {current_pax + 1} de {num_pax}.
Pide los datos UNO POR UNO: nombre, cédula, teléfono, email.

NO preguntes "¿Qué necesitas?" - Estás en medio de recopilar datos.
"""
        
        elif flow_state == 'showing_flights':
            return """
🔴 ESTADO ACTUAL: MOSTRANDO VUELOS

Acabas de mostrar vuelos al usuario.
Estás esperando que elija un número de vuelo.

NO preguntes "¿Qué necesitas?" - Estás esperando una selección.
"""
        
        return ""  # Sin contexto adicional
    
    def _clean_history(self, history, max_items=20):
        """Limpia historial eliminando pares incompletos de function_call/function_response"""
        if not history:
            return []
        
        # Eliminar pares incompletos de function_call/function_response
        cleaned = []
        i = 0
        while i < len(history):
            msg = history[i]
            role = msg.get('role')
            parts = msg.get('parts', [])
            
            # Si es un model con function_call, verificar que le siga un function_response
            if role == 'model' and parts:
                has_function_call = any(
                    isinstance(p, dict) and 'function_call' in p 
                    for p in parts
                )
                
                if has_function_call:
                    # Verificar si el siguiente mensaje es function_response
                    if i + 1 < len(history):
                        next_msg = history[i + 1]
                        next_parts = next_msg.get('parts', [])
                        has_function_response = any(
                            isinstance(p, dict) and 'function_response' in p 
                            for p in next_parts
                        )
                        
                        if has_function_response:
                            # Par completo, agregar ambos
                            cleaned.append(msg)
                            cleaned.append(next_msg)
                            i += 2
                            continue
                    # Par incompleto, saltar
                    i += 1
                    continue
            
            # Si es function_response sin function_call previo, saltar
            if role == 'user' and parts:
                has_function_response = any(
                    isinstance(p, dict) and 'function_response' in p 
                    for p in parts
                )
                if has_function_response:
                    i += 1
                    continue
            
            # Mensaje normal (texto)
            if parts and any(
                isinstance(p, dict) and 'text' in p 
                for p in parts
            ):
                cleaned.append(msg)
            
            i += 1
        
        # Limitar tamaño
        while len(cleaned) > max_items:
            cleaned.pop(0)
        
        # Asegurar que empiece con user
        while cleaned and cleaned[0].get('role') != 'user':
            cleaned.pop(0)
        
        return cleaned
    
    def _build_context_instruction(self, function_name, result, session):
        """Construye instrucción de contexto explícita basada en el resultado de la función"""
        
        if function_name == "get_travel_requirements" and result.get('success'):
            requisitos = result.get('requisitos', '')
            return f"""🔴 CONTEXTO: Requisitos migratorios obtenidos

Muestra los requisitos al usuario COMPLETOS sin modificar.
NO resumas, NO parafrasees, copia EXACTAMENTE el texto.
NO agregues introducciones como "Aquí tienes" o "Claro".
SOLO muestra el texto de requisitos y al final pregunta: "¿Necesitas algo más? 😊"

REQUISITOS COMPLETOS (copia esto EXACTAMENTE):
{requisitos}
"""
        
        elif function_name == "confirm_flight" and result.get('action') == 'show_return_flights':
            return f"""🔴🔴🔴 INSTRUCCIÓN CRÍTICA - MANTÉN EL CONTEXTO:

Acabas de confirmar el vuelo de IDA y ahora tienes {result.get('total_vuelos_regreso', 0)} vuelos de REGRESO disponibles.

DEBES HACER ESTO AHORA (OBLIGATORIO):
1. Confirma brevemente el vuelo de ida: "{result.get('vuelo_ida')}" clase {result.get('clase_ida')} por {result.get('precio_ida')}
2. Muestra los {result.get('total_vuelos_regreso', 0)} vuelos de regreso con formato LIMPIO
3. Pregunta: "¿Cuál vuelo de regreso prefieres? 😊"

PROHIBIDO ABSOLUTAMENTE:
- NO preguntes "¿Qué necesitas?"
- NO pierdas el contexto
- NO ignores los vuelos de regreso
- DEBES mostrar los vuelos de regreso AHORA

VUELOS DE REGRESO DISPONIBLES:
{self._format_flights_simple(result.get('vuelos_regreso', []))}
"""
        
        elif function_name == "search_flights" and result.get('success'):
            is_round = result.get('is_round_trip', False)
            if is_round:
                return f"""🔴🔴🔴 CONTEXTO: Búsqueda de IDA Y VUELTA

Muestra los {result.get('total_ida', 0)} vuelos de IDA.
Después de que el usuario elija vuelo y clase de ida, buscarás los vuelos de REGRESO.

PROHIBIDO: NO preguntes "¿Qué necesitas?" - Estás mostrando vuelos.
OBLIGATORIO: Muestra los vuelos con formato limpio y pregunta cuál prefiere.
"""
            else:
                return f"""🔴🔴🔴 CONTEXTO: Búsqueda de SOLO IDA

Muestra los {result.get('total_ida', 0)} vuelos disponibles.
Después de que el usuario elija vuelo y clase, pedirás datos de pasajeros.

PROHIBIDO: NO preguntes "¿Qué necesitas?" - Estás mostrando vuelos.
OBLIGATORIO: Muestra los vuelos con formato limpio y pregunta cuál prefiere.
"""
        
        elif function_name == "select_flight" and result.get('success'):
            return f"""🔴 CONTEXTO: Clases disponibles del vuelo de IDA

Muestra las clases disponibles del vuelo {result.get('vuelo', '')}.
Pregunta cuál clase prefiere el usuario.
"""
        
        elif function_name == "select_return_flight" and result.get('success'):
            return f"""🔴 CONTEXTO: Clases disponibles del vuelo de REGRESO

Muestra las clases disponibles del vuelo de regreso {result.get('vuelo', '')}.
Pregunta cuál clase prefiere el usuario.
"""
        
        elif function_name == "confirm_return_flight" and result.get('success'):
            return f"""🔴 CONTEXTO: Vuelo de regreso confirmado

Ahora pide los datos de los pasajeros UNO POR UNO:
- Nombre completo
- Cédula o pasaporte
- Teléfono
- Email

Si hay múltiples pasajeros, pide los datos de cada uno por separado.
"""
        
        elif function_name == "create_booking_multiple" and result.get('success'):
            return f"""🔴 CONTEXTO: Reserva creada exitosamente

Muestra TODOS los detalles de la reserva:
- PNR: {result.get('pnr', '')}
- Pasajeros: {result.get('pasajeros', '')}
- Vuelo(s) confirmado(s)
- Precio total

Celebra el éxito y pregunta si necesita algo más.
"""
        
        return ""  # Sin contexto adicional para otras funciones
    
    def _format_flights_simple(self, flights_data):
        """Formatea vuelos de forma simple para instrucciones"""
        if not flights_data:
            return "(Sin vuelos)"
        
        formatted = []
        for v in flights_data[:5]:  # Máximo 5 para no saturar
            formatted.append(f"{v.get('numero')}. {v.get('aerolinea')} {v.get('vuelo')} - {v.get('salida')} a {v.get('llegada')} - {v.get('precio')}")
        return "\n".join(formatted)
    
    def _send_response(self, phone: str, message: str, session):
        """Envía respuesta"""
        try:
            session.add_message('assistant', message)
            wati_service.send_message(phone, message)
            return {"success": True, "response": message}
        except Exception as e:
            logger.error(f"Error enviando: {str(e)}")
            return {"success": False, "response": message}


# Instancia global
agent_bot = AgentBot()
