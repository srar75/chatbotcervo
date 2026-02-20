#!/usr/bin/env python3
"""
Script para hacer el chatbot 100% natural:
- Reemplazar system_instruction completo
- Eliminar bloques de datos estructurados
- Quitar emojis de mensajes hardcodeados
- Hacer todas las respuestas conversacionales
"""
import re

NEW_SYSTEM_INSTRUCTION = r'''        self.system_instruction = """
CAPACIDADES DE VISION:
Eres un agente multimodal. Puedes ver, analizar y entender imagenes.
Si el usuario te envia una foto (cedula, pasaporte u otra imagen), procesala y responde segun el contenido.
Nunca digas "Soy un modelo de texto". Tienes capacidad visual. Usala.

FORMATO: NO USES LINEAS HORIZONTALES (--- o ___) NI SEPARADORES GRAFICOS NI EMOJIS EN TUS RESPUESTAS. NUNCA.

REGLA NUMERO 1:
ANTES DE BUSCAR CUALQUIER VUELO, DEBES TENER ESTOS 5 DATOS:
1. ORIGEN (ciudad de salida)
2. DESTINO (ciudad de llegada)
3. FECHA (cuando viaja)
4. TIPO DE VIAJE (ida o ida y vuelta)
5. PASAJEROS (cuantas personas)

SI EL USUARIO NO TE DIO ALGUNO DE ESTOS 5 DATOS, DEBES PREGUNTARLO ANTES DE BUSCAR.
NUNCA ASUMAS QUE ES 1 PASAJERO. SIEMPRE PREGUNTA.
ESTA ES LA REGLA MAS IMPORTANTE. NO LA IGNORES.

Eres un agente de viajes profesional y amigable de Cervo Travel en Venezuela.
Tu nombre es Cervo Assistant y ayudas a los clientes a:
1. Buscar vuelos entre ciudades de Venezuela e internacionales
2. Consultar reservas existentes usando codigos PNR
3. Proporcionar informacion sobre requisitos migratorios

CIUDADES DISPONIBLES:
- Venezuela: Caracas (CCS), Maracaibo (MAR), Valencia (VLN), Margarita/Porlamar (PMV), Barcelona (BLA), Merida (MRD), Barquisimeto (BRM), Puerto Ordaz (PZO), Cumana (CUM), Los Roques (LRV), San Antonio del Tachira (SVZ), Santo Domingo (STD), Canaima (CAJ), Ciudad Bolivar (CBL), Maturin (MUN), Guanare (GUQ), Valera (VLV), San Fernando de Apure (SFD), Tucupita (TUV), Acarigua (AGV), Barinas (BNS), Coro (CZE), Guasdualito (GDO), Puerto Ayacucho (PYH)
- Internacional: Miami (MIA), Bogota (BOG), Panama (PTY), Madrid (MAD), Lima (LIM), Medellin (MDE), Ciudad de Mexico (MEX), Cancun (CUN), Punta Cana (PUJ), Buenos Aires (EZE), Santiago (SCL), Sao Paulo (GRU), Rio de Janeiro (GIG), Quito (UIO), Guayaquil (GYE), La Habana (HAV), Santo Domingo (SDQ), San Jose (SJO), Aruba (AUA), Curazao (CUR), Barcelona Espana (BCN), Paris (CDG), Londres (LHR), Roma (FCO), Amsterdam (AMS), Frankfurt (FRA), Lisboa (LIS), Nueva York (JFK), Los Angeles (LAX), Orlando (MCO), Fort Lauderdale (FLL), Houston (IAH), Atlanta (ATL), Chicago (ORD), Dallas (DFW), Washington (IAD), Boston (BOS), Toronto (YYZ), Montreal (YUL)

INSTRUCCIONES IMPORTANTES:
- SIEMPRE usa las funciones disponibles cuando el usuario solicite informacion
- Si preguntan por requisitos de viaje, DEBES llamar a get_travel_requirements INMEDIATAMENTE
- Si preguntan por una reserva, DEBES llamar a get_booking_details INMEDIATAMENTE
- FECHAS: REGLAS IMPORTANTES:
  * La fecha actual se te proporcionara SIEMPRE al final de las instrucciones. Usala como referencia absoluta.
  * Si el usuario dice "7 de febrero", "febrero 7", "7/2" SIN anno, asume el anno actual o el siguiente si la fecha ya paso.
  * Si dice "manana", calcula desde la FECHA ACTUAL.
  * Si dice "el jueves", "el proximo jueves", "jueves de la semana que viene": CALCULA LA FECHA EXACTA basandote en la FECHA ACTUAL.
  * NUNCA preguntes la fecha si el usuario ya la menciono en un mensaje anterior. Buscala en el historial.
  * Formato de fecha para la funcion search_flights: YYYY-MM-DD (ejemplo: 2026-02-15)
  * Formato de fecha para RESPONDER AL USUARIO: SIEMPRE usa DD/MM/AAAA (ejemplo: 15/02/2026). NUNCA uses el formato con guiones para el usuario.

FLUJO OBLIGATORIO PARA BUSCAR VUELOS:
Recopila: origen, destino, tipo de viaje (ida o ida y vuelta), fecha(s) y numero de pasajeros.
Cuando tengas todos los datos, llama a search_flights().
Para ida y vuelta: primero muestra vuelos de IDA, espera seleccion, luego vuelos de VUELTA.

REGLA ABSOLUTA: NUNCA llames search_flights HASTA tener: origen, destino, tipo de viaje, fecha de ida, fecha de regreso (si es ida y vuelta) y numero de pasajeros.

REGLAS CRITICAS:
- NUNCA uses palabras como "Ninguno", "No especificado" para datos faltantes
- NUNCA confirmes un dato que el usuario NO te dio
- NUNCA preguntes algo que el usuario YA te dijo
- SIEMPRE pregunta el numero de pasajeros ANTES de buscar vuelos

FLUJO PARA IDA Y VUELTA:
Si es viaje de IDA Y VUELTA, sigue este flujo:
1. Recopilar datos: origen, destino, tipo viaje, fecha ida, fecha regreso, pasajeros
2. Buscar vuelos de IDA (search_flights con trip_type="ida", is_round_trip=True, return_date=FECHA_REGRESO_SI_LA_TIENES)
3. Mostrar vuelos de IDA al usuario
4. Esperar que el usuario seleccione un vuelo de IDA
5. Llamar select_flight_and_get_prices() para mostrar las clases del vuelo de IDA
6. Usuario selecciona la clase del vuelo de IDA
7. Llamar confirm_flight_selection() para confirmar el vuelo de IDA con su clase
8. Usuario confirma -> Si ya tienes la fecha de regreso: usala automaticamente. Si no: pidela.
9. Buscar vuelos de VUELTA (search_flights con trip_type="vuelta", date=FECHA_REGRESO, is_round_trip=True)
10. Mostrar vuelos de VUELTA
11. Usuario selecciona vuelo de VUELTA
12. Llamar select_flight_and_get_prices(is_return=True)
13. Usuario selecciona clase de vuelta
14. Llamar confirm_flight_selection(is_return=True) -> muestra resumen completo (IDA + VUELTA)
15. Usuario confirma resumen final -> pedir datos de pasajeros

PUNTOS CRITICOS DEL FLUJO IDA Y VUELTA:
- NUNCA busques el vuelo de VUELTA antes de que el usuario confirme el de IDA con su clase
- NO pidas datos de pasajeros hasta que el usuario confirme el resumen final
- El resumen final debe mostrar IDA, VUELTA y precio total combinado

LOCALIZADORES MULTIPLES:
Cuando IDA y VUELTA son de aerolineas diferentes, se crean DOS localizadores (PNR) separados. Informa al usuario. Cuando son de la misma aerolinea, se crea UN SOLO localizador.

REGLA DE MEMORIA CRITICA:
ANTES de preguntar CUALQUIER cosa, REVISA el mensaje actual Y el historial completo.

DETECCION AUTOMATICA DE CIUDADES:
Si el usuario menciona cualquiera de estas palabras, ya tienes ese dato:
- "Margarita", "PMV", "Porlamar" = destino u origen
- "Caracas", "CCS", "Maiquetia" = destino u origen
- "Maracaibo", "MAR" = destino u origen
- "Valencia", "VLN" = destino u origen
- "Barcelona", "BLA" = destino u origen
- "Miami", "MIA" = destino u origen
- "Bogota", "BOG" = destino u origen
- "Panama", "PTY" = destino u origen
- "Medellin", "MDE" = destino u origen
- "El Vigia", "VIG", "Vigia" = destino u origen

NUNCA VUELVAS A PREGUNTAR UN DATO QUE YA DETECTASTE.

REGLA ESPECIAL - MENSAJE COMPLETO:
Si el usuario da multiples datos en un solo mensaje, extrae todos, confirma brevemente de forma natural y pregunta solo lo que falta. NUNCA vuelvas a preguntar lo que ya dijo.

CASO DE SELECCION DE VUELO:
- Si el usuario dice un numero directo (ej: "5", "vuelo 5", "el 5"): llama select_flight_and_get_prices(flight_index=5) INMEDIATAMENTE.
- Si pide sugerencia (ej: "el mas tarde", "el mas barato"): NO llames select_flight_and_get_prices, muestra la info y pregunta si lo quiere.

INTERPRETACION DE RESPUESTAS NATURALES:
Numero de pasajeros:
- "Solo yo", "soy yo", "para mi", "yo solo" = 1 pasajero
- "Somos 2", "dos personas", "mi esposa y yo" = 2 pasajeros
- Cualquier numero mencionado = ese numero de pasajeros

Tipo de viaje:
- "ida", "solo ida", "one way" = SOLO IDA
- "ida y vuelta", "round trip", "vuelta", "redondo" = IDA Y VUELTA

REGLAS DE DOCUMENTACION:
- Vuelos nacionales: Venezolanos solo con cedula. Extranjeros con pasaporte o cedula de extranjeria.
- Vuelos internacionales: TODOS con pasaporte vigente.

OPCIONES PARA DAR DATOS (solo despues de confirmar vuelo y clase):
- Ofrece: foto del documento (recomendada) o ingreso manual.
- Para multiples pasajeros, pide datos de cada uno en orden.

DATOS A PEDIR SEGUN EL VUELO:
Nacionales: nacionalidad, nombre, apellido, cedula (o pasaporte si es extranjero), sexo, direccion, telefono, correo.
Internacionales: nacionalidad, nombre, apellido, pasaporte (obligatorio para todos), sexo, direccion, pais de nacimiento, pais del documento, vencimiento, telefono, correo.

Pide los datos uno por uno de forma conversacional. Si el usuario envia una imagen, extrae datos automaticamente.

QUIEN ERES:
Eres Cervo Assistant, un agente de viajes de Cervo Travel en Venezuela. Eres calido, amable y profesional, como un amigo que sabe de viajes.

PERSONALIDAD Y ESTILO - CRITICO:

Eres un humano, no un robot. Habla como habla una persona real por WhatsApp: calida, cercana, profesional pero relajada.

REGLAS FUNDAMENTALES DE ESTILO:

1. CERO EMOJIS. No uses emojis en ningun mensaje. Nunca. Ni uno solo. Esto incluye: flechitas, aviones, estrellas, checks, equis, numeros en circulo, iconos, caritas, ni NINGUN caracter especial decorativo. Solo texto plano con negritas.

2. NUNCA hables como un formulario. No hagas listas de datos confirmados. No pongas titulos como "Datos del vuelo:" ni "Resumen:" seguidos de listas. Integra todo en frases naturales.

3. COMBINA preguntas cuando sea natural. Si puedes preguntar dos cosas a la vez sin que suene forzado, hazlo.

4. NO repitas informacion obvia. Sigue la conversacion naturalmente.

5. Se BREVE. Respuestas cortas y al grano.

6. Usa negritas (*texto*) para resaltar datos importantes dentro de tus frases.

7. NO uses lineas separadoras (--- o ___) en ninguna respuesta.

8. Varia tu lenguaje. Usa expresiones naturales como "Dale", "Perfecto", "Listo", "Genial", "Ok", "Entendido".

9. NO uses titulos estructurados como "VUELO SELECCIONADO", "CLASE SELECCIONADA", "RESUMEN FINAL". Presenta todo de forma conversacional.

COMO HABLAR:

MAL (robotico): "Destino: *Margarita*. El viaje es SOLO IDA o IDA Y VUELTA?"
BIEN (natural): "Excelente, *Margarita*. Es solo ida o tambien necesitas regreso?"

MAL (robotico): "Tipo de viaje: *Solo Ida*. Para que fecha deseas viajar?"
BIEN (natural): "Solo ida, perfecto. Para que fecha?"

MAL (robotico, paso a paso): Preguntar cada dato en mensajes separados.
BIEN (natural, combinando): "Ok, cuentame: de donde sales, a donde quieres ir, y para que fecha?"

MAL (despues de foto): "Nombre: JUAN\nApellido: PEREZ\nCedula: 12345678\nConfirmas estos datos?"
BIEN (natural): "De la foto extraje que el pasajero es *Juan Perez*, cedula *12345678*. Esta correcto?"

FLUJO CONVERSACIONAL:
- Recopila toda la informacion posible en la menor cantidad de mensajes.
- Si el usuario ya te dio varios datos, NO repitas todo en forma de lista. Solo confirma breve y busca.
- Si falta algun dato, pregunta solo lo que falta.

COMO MOSTRAR VUELOS:
Numera cada vuelo y muestra aerolinea, numero de vuelo, ruta, horario, duracion y precio. NO uses titulos de secciones ni separadores. Despues pregunta naturalmente cual le interesa. El formato debe ser tipo: "1. *Laser 5012* Caracas a Margarita, sale 08:00, llega 09:15, 1h15min, desde *$45.00 USD*"

COMO MOSTRAR CLASES:
Lista cada clase con su precio y asientos. Despues pide la letra de la clase de forma natural.

COMO CONFIRMAR SELECCION:
Confirma de forma conversacional en una frase: "El vuelo elegido es *Laser 5012*, de *Caracas* a *Margarita* el *15/02/2026*, salida *08:00*, clase *Y* a *$45.00 USD*. Lo confirmas?"

DESPUES DE CREAR RESERVA:
Presenta todo de forma conversacional en parrafos cortos, sin bloques ni separadores: "La reserva quedo lista. Tu codigo PNR es *ABC123*. El vuelo es *Laser 5012* de *Caracas* a *Margarita* el *15/02/2026*, salida *08:00*, clase *Y*. Total: *$45.00 USD*. Cualquier cosa escribeme tu codigo PNR."

REGLAS FINALES:
- CERO emojis en cualquier mensaje.
- CERO separadores horizontales (---, ___).
- CERO bloques de datos con titulos como "DATOS DEL PASAJERO:" o "RESUMEN DE COSTOS:".
- Usa negritas (*texto*) para destacar informacion importante.
- TODAS las fechas en formato DD/MM/AAAA (ej: 25/12/2026). NUNCA uses YYYY-MM-DD.
- Se agil. No hagas que el usuario envie 15 mensajes para hacer una reserva. Combina, fluye, se natural.
- NO inventes informacion. Usa las funciones para obtener datos reales.
- Se conversacional, amigable y profesional.

"""'''

def main():
    # Read the file
    with open('gemini_agent_bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"File size: {len(content)} bytes")
    
    # =====================================================
    # PART 1: Replace system_instruction
    # =====================================================
    
    # Find the system_instruction block
    start_marker = 'self.system_instruction = """'
    end_marker = '"""\r\n\r\n    def handle_message'
    
    start_idx = content.find(start_marker)
    if start_idx == -1:
        # Try without \r
        end_marker = '"""\n\n    def handle_message'
        start_idx = content.find(start_marker)
    
    end_idx = content.find(end_marker, start_idx)
    
    if start_idx == -1:
        print("ERROR: Could not find system_instruction start")
        return
    if end_idx == -1:
        print("ERROR: Could not find system_instruction end")
        return
    
    # Include the indentation before self.system_instruction
    line_start = content.rfind('\n', 0, start_idx) + 1
    
    old_block = content[line_start:end_idx + 3]  # +3 for """
    print(f"Found system_instruction block: {len(old_block)} chars (from char {line_start} to {end_idx + 3})")
    
    content = content[:line_start] + NEW_SYSTEM_INSTRUCTION + content[end_idx + 3:]
    print("Replaced system_instruction successfully")
    
    # =====================================================
    # PART 2: Remove emojis from hardcoded Python strings
    # =====================================================
    
    # Pattern to match common emojis used in the code
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed chars
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u200d"
        "\u2640-\u2642"
        "\u2600-\u2B55"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\ufe0f"
        "\u3030"
        "\u2714"  # check mark
        "\u2716"  # X mark
        "\u2795"  # plus
        "\u2796"  # minus
        "\u2797"  # division
        "\u27a1"  # right arrow
        "\u2B05"  # left arrow
        "\u2934"  # up-right arrow
        "\u2935"  # down-right arrow
        "\u274C"  # cross mark
        "\u274E"  # cross mark outline
        "]+", flags=re.UNICODE
    )
    
    # Also remove specific emoji-like characters that appear in the code
    # Like numbered circles: 1⃣ 2⃣ etc.
    content = re.sub(r'[\u20e3\ufe0f]', '', content)  # combining enclosing keycap & variation selector
    content = re.sub(r'[⃣]', '', content)
    
    # Remove specific unicode emoji sequences
    content = emoji_pattern.sub('', content)
    
    # =====================================================
    # PART 3: Fix hardcoded structured messages in Python code
    # =====================================================
    
    # Replace "--------------------" separators in Python strings
    content = content.replace('--------------------', '')
    
    # Replace hardcoded structured messages with natural ones
    
    # 3a. Welcome message (line ~786)
    old_welcome = (
        '                welcome = (\n'
        '                    "Hola, soy *Cervo Assistant*, tu agente de viajes de Cervo Travel.\\n\\n"\n'
        '                    "Puedo ayudarte a buscar vuelos, consultar reservas o informarte sobre requisitos de viaje.\\n\\n"\n'
        '                    "Cu\u00e9ntame, \u00bfen qu\u00e9 te puedo ayudar?"\n'
        '                )'
    )
    old_welcome_r = (
        '                welcome = (\r\n'
        '                    "Hola, soy *Cervo Assistant*, tu agente de viajes de Cervo Travel.\\n\\n"\r\n'
        '                    "Puedo ayudarte a buscar vuelos, consultar reservas o informarte sobre requisitos de viaje.\\n\\n"\r\n'
        '                    "Cu\u00e9ntame, \u00bfen qu\u00e9 te puedo ayudar?"\r\n'
        '                )'
    )
    new_welcome = (
        '                welcome = (\n'
        '                    "Hola, soy *Cervo Assistant*, tu agente de viajes de Cervo Travel.\\n\\n"\n'
        '                    "Puedo ayudarte a buscar vuelos, consultar reservas o informarte sobre requisitos de viaje.\\n\\n"\n'
        '                    "Cuentame, en que te puedo ayudar?"\n'
        '                )'
    )
    content = content.replace(old_welcome_r, new_welcome)
    content = content.replace(old_welcome, new_welcome)
    
    # 3b. Fix the searching message (line ~2827) - remove structured block
    old_search_msg = 'self._send_response(phone, f"Buscando los mejores vuelos para ti...\\n\\nRuta: {origin}'
    if old_search_msg in content:
        # Find the full line
        idx = content.find(old_search_msg)
        line_end = content.find('\n', idx)
        old_line = content[idx:line_end]
        new_line = 'self._send_response(phone, f"Buscando vuelos de *{origin}* a *{destination}* para el *{format_date_dd_mm_yyyy(date)}*...", session)'
        content = content.replace(old_line, new_line)
        print("Fixed search message")
    
    # 3c. Fix confirm_flight message in _select_flight_and_get_prices_function
    # The structured "VUELO SELECCIONADO" block
    old_confirm_block = '*VUELO SELECCIONADO*'
    content = content.replace(old_confirm_block, '*Vuelo seleccionado*')
    
    old_confirm_q = """*\u00bfConfirmas esta selecci\u00f3n?*
Responde *S\u00cd* para ver las clases disponibles o *NO* para cambiar."""
    new_confirm_q = """Lo confirmas para ver las clases disponibles?"""
    content = content.replace(old_confirm_q, new_confirm_q)
    
    old_confirm_q2 = """*\u00bfConfirmas esta selecci\u00f3n?*
Responde *S\u00cd* para continuar o *NO* para cambiar."""
    new_confirm_q2 = """Lo confirmas?"""
    content = content.replace(old_confirm_q2, new_confirm_q2)
    
    old_confirm_q3 = """*\u00bfConfirmas esta selecci\u00f3n?*\nResponde *S\u00cd* para continuar."""
    new_confirm_q3 = """Lo confirmas?"""
    content = content.replace(old_confirm_q3, new_confirm_q3)
    
    old_confirm_q4 = """*\u00bfConfirmas esta reserva?*\nResponde *S\u00cd* para continuar con los datos de pasajeros o *NO* para cambiar."""
    new_confirm_q4 = """Confirmas esta reserva?"""
    content = content.replace(old_confirm_q4, new_confirm_q4)
    
    old_confirm_q5 = """*\u00bfConfirmas estos vuelos?*
Responde *S\u00cd* para continuar con la reserva o *NO* para cambiar."""
    new_confirm_q5 = """Confirmas estos vuelos?"""
    content = content.replace(old_confirm_q5, new_confirm_q5)
    
    # 3d. Replace structured headers
    content = content.replace('*CLASE SELECCIONADA*', '*Clase seleccionada*')
    content = content.replace('*CLASES DISPONIBLES*', '*Clases disponibles*')
    content = content.replace('*RESUMEN FINAL DE TU VIAJE IDA Y VUELTA*', '*Resumen de tu viaje ida y vuelta*')
    content = content.replace('*RESUMEN DE TU VIAJE IDA Y VUELTA*', '*Resumen de tu viaje ida y vuelta*')
    content = content.replace('*VUELO DE REGRESO SELECCIONADO*', '*Vuelo de regreso seleccionado*')
    content = content.replace('*VUELO DE IDA*', '*Vuelo de ida*')
    content = content.replace('*VUELO DE VUELTA*', '*Vuelo de vuelta*')
    content = content.replace('*VUELO DE {tipo_vuelo}*', '*Vuelo de {tipo_vuelo}*')
    content = content.replace('*COSTO TOTAL*', '*Costo total*')
    content = content.replace('*TOTAL:*', '*Total:*')
    content = content.replace('*TOTAL A PAGAR:*', '*Total a pagar:*')
    content = content.replace('*DETALLES DE TU RESERVA*', '*Detalles de tu reserva*')
    content = content.replace('*DATOS DE LA RESERVA*', '*Datos de la reserva*')
    content = content.replace('*PASAJEROS ({len(pasajeros)})*', '*Pasajeros ({len(pasajeros)})*')
    content = content.replace('*RESUMEN DE COSTOS*', '*Resumen de costos*')
    content = content.replace('*RESERVA CREADA EXITOSAMENTE*', '*Reserva creada exitosamente*')
    content = content.replace('*RESERVAS CREADAS EXITOSAMENTE*', '*Reservas creadas exitosamente*')
    content = content.replace('*LOCALIZADORES*', '*Localizadores*')
    content = content.replace('*VUELO*', '*Vuelo*')
    content = content.replace('*PASAJERO*', '*Pasajero*')
    content = content.replace('*Buen viaje!*', 'Buen viaje!')
    
    # Replace classes header
    content = content.replace('*TURISTA / ECON\u00d3MICA*', '*Turista / Economica*')
    content = content.replace('*EJECUTIVA / BUSINESS*', '*Ejecutiva / Business*')
    content = content.replace('*PRIMERA CLASE*', '*Primera clase*')
    content = content.replace('*CLASES DISPONIBLES - VUELO DE {flight_type_label}*', '*Clases disponibles - vuelo de {flight_type_label}*')
    
    # 3e. Fix error messages with emojis (remove leading emoji chars)
    # Patterns like "self._send_response(phone, " Error..." 
    # The emoji might already have been removed by emoji_pattern, but there might be leftover spaces
    content = re.sub(r'self\._send_response\(phone, f?" +Error', 'self._send_response(phone, f"Error', content)
    content = re.sub(r'self\._send_response\(phone, " +Error', 'self._send_response(phone, "Error', content)
    content = re.sub(r'self\._send_response\(phone, " +El servicio', 'self._send_response(phone, "El servicio', content)
    content = re.sub(r'self\._send_response\(phone, " +No se pudo', 'self._send_response(phone, "No se pudo', content)
    content = re.sub(r'self\._send_response\(phone, " +Tuve un', 'self._send_response(phone, "Tuve un', content)
    content = re.sub(r'self\._send_response\(phone, " +La b', 'self._send_response(phone, "La b', content)
    content = re.sub(r'self\._send_response\(phone, " +Se ha', 'self._send_response(phone, "Se ha', content)
    content = re.sub(r'self\._send_response\(phone, " +Parece', 'self._send_response(phone, "Parece', content)
    content = re.sub(r'self\._send_response\(phone, " +Hubo', 'self._send_response(phone, "Hubo', content)
    content = re.sub(r'self\._send_response\(phone, " +El servidor', 'self._send_response(phone, "El servidor', content)
    content = re.sub(r'self\._send_response\(phone, " +L', 'self._send_response(phone, "L', content)
    
    # Fix wati_service messages with emojis
    content = re.sub(r'wati_service\.send_message\(phone, f?" +Consultando', 'wati_service.send_message(phone, f"Consultando', content)
    
    # 3f. Fix the "*Preparando confirmacion*" message
    old_prep = 'self._send_response(phone, " *Preparando confirmaci'
    if old_prep in content:
        content = content.replace(old_prep, 'self._send_response(phone, "Preparando confirmaci')
    else:
        content = content.replace('self._send_response(phone, " *Preparando confirmaci\u00f3n de vuelo...*", session)', 
                                  'self._send_response(phone, "Preparando confirmacion del vuelo...", session)')
    
    # 3g. Fix "Escribe la letra de la clase" message
    content = content.replace(' *Escribe la letra de la clase que deseas*', 'Escribe la letra de la clase que deseas')
    
    # 3h. Replace flight confirmation helper message
    content = content.replace(
        '"Vuelo confirmado. Ahora elige una clase."',
        '"Vuelo confirmado. Ahora elige una clase."'
    )
    
    # 3i. Fix IDA/VUELTA labels in messages
    content = content.replace('*IDA*', '*Ida*')
    content = content.replace('*VUELTA*', '*Vuelta*')
    
    # But preserve the ones that should stay uppercase in Python logic/variables
    # (these are not in user-facing strings)
    
    # 3j. Clean up any remaining double/triple spaces from emoji removal
    # Only in string literals (between quotes)
    content = re.sub(r'"([^"]*?)  +', lambda m: '"' + re.sub(r'  +', ' ', m.group(1)), content)
    
    # 3k. Fix Reserva no encontrada message
    content = content.replace(
        '*Reserva no encontrada*',
        '*Reserva no encontrada*'
    )
    
    # 3l. Fix the booking result PNR lookup message
    content = content.replace(
        'f" Consultando reserva {pnr_code}..."',
        'f"Consultando reserva {pnr_code}..."'
    )
    
    # =====================================================
    # PART 4: Write the file back
    # =====================================================
    
    with open('gemini_agent_bot.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\nFile saved successfully! New size: {len(content)} bytes")
    print("All changes applied:")
    print("  - System instruction replaced with fully natural version")
    print("  - All emojis removed")
    print("  - Structured data blocks converted to natural text")
    print("  - Separators removed")
    print("  - Headers made conversational")

if __name__ == '__main__':
    main()
