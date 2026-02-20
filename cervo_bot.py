"""
CHATBOT CERVO - Bot de reservaciones de vuelos para Venezuela
Sistema basado en COMANDOS - Menús y palabras clave
"""
import logging
import re
from datetime import datetime, timedelta, timezone
from session_manager import session_manager
from flight_booking_service import flight_service
from wati_service import wati_service
from config import Config
from requisitos_migratorios import get_requisitos_menu, get_requisitos_pais
# from glm_service import glm_service  # IA desactivada

logger = logging.getLogger(__name__)

# Zona horaria de Venezuela (UTC-4)
VENEZUELA_TZ = timezone(timedelta(hours=-4))


class CervoBot:
    """Chatbot Cervo - Basado en comandos"""
    
    def __init__(self):
        self.welcome_message = """🦌 *¡Bienvenido a Cervo Bot!* ✈️

━━━━━━━━━━━━━━━━━━━━

_Tu asistente de vuelos para Venezuela_ 🇻🇪

*¿Qué deseas hacer hoy?*

✈️ *1* → Buscar vuelos
📋 *2* → Consultar reserva
🌍 *3* → Requisitos de viaje

━━━━━━━━━━━━━━━━━━━━

💬 _Escribe el número de tu opción_"""

    def handle_message(self, phone: str, message: str, media_url: str = None):
        """Maneja mensaje entrante"""
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
            if message_lower in ['cervo bot', 'cervobot']:
                session.activate()
                logger.info(f"Bot activado para {phone}")
                return self._send_response(phone, self.welcome_message, session)
            
            # Si no está activo, ignorar
            if not session.is_active:
                return None
            
            # Desactivar bot
            if message_lower in ['salir', 'exit', 'bye', 'adios', 'chao']:
                session.deactivate()
                return self._send_response(phone, "👋 *¡Hasta pronto!*\n\n━━━━━━━━━━━━━━━━━━━━\n\n✨ _Fue un placer ayudarte_\n\n💬 Escribe *cervo bot* cuando necesites viajar de nuevo\n\n✈️ ¡Buen viaje!", session)
            
            # Comando menú
            if message_lower in ['menu', 'inicio', 'empezar', '0']:
                session.reset()
                return self._send_response(phone, self.welcome_message, session)
            
            # Saludos
            if message_lower in ['hola', 'hi', 'hello', 'hey', 'buenos dias', 'buenas tardes', 'buenas noches']:
                return self._send_response(phone, self.welcome_message, session)
            
            # Opciones del menú principal (si no está en un flujo)
            if not session.current_flow:
                if message_lower in ['1', 'buscar', 'vuelos', 'buscar vuelos'] or any(word in message_lower for word in ['barato', 'economico', 'económico']):
                    session.current_flow = 'buscar_origen'
                    # Marcar si pidió barato desde el inicio
                    if any(word in message_lower for word in ['barato', 'economico', 'económico']):
                        session.data['prefer_cheapest'] = True
                    return self._send_response(phone, "✈️ *BUSCAR VUELOS*\n\n\n\n📍 *¿Desde qué ciudad viajas?*\n\n🇻🇪 *Venezuela:*\nCaracas, Maracaibo, Valencia, Margarita, Barcelona, Mérida, Barquisimeto\n\n🌎 *Internacional:*\nMiami, Bogotá, Panamá\n\n\n📝 _Escribe la ciudad o código (ej: CCS)_", session)
                
                elif message_lower in ['2', 'consultar', 'reserva', 'consultar reserva']:
                    session.current_flow = 'consultar_pnr'
                    return self._send_response(phone, "📋 *CONSULTAR RESERVA*\n\n\n\n🎫 *Escribe tu código de reserva (PNR)*\n\n📝 _Ejemplo: ABC123_\n\n", session)
                
                elif message_lower in ['3', 'requisitos', 'requisitos de viaje']:
                    session.current_flow = 'requisitos'
                    return self._send_response(phone, get_requisitos_menu(), session)
            
            # FLUJOS ACTIVOS
            if session.current_flow == 'buscar_origen':
                return self._handle_origin(session, phone, message)
            
            if session.current_flow == 'buscar_destino':
                return self._handle_destination(session, phone, message)
            
            if session.current_flow == 'buscar_fecha':
                return self._handle_date(session, phone, message)
            
            if session.current_flow == 'tipo_viaje':
                return self._handle_trip_type(session, phone, message)
            
            if session.current_flow == 'fecha_vuelta':
                return self._handle_return_date(session, phone, message)
            
            if session.current_flow == 'seleccionar_vuelo':
                return self._handle_flight_selection(session, phone, message)
            
            if session.current_flow == 'seleccionar_clase':
                return self._handle_class_selection(session, phone, message)
            
            if session.current_flow == 'confirmar_vuelo':
                return self._handle_flight_confirmation(session, phone, message)
            
            if session.current_flow == 'recopilar_datos':
                return self._process_passenger_data(session, phone, message)
            
            if session.current_flow == 'consultar_pnr':
                return self._check_status(session, phone, message)
            
            if session.current_flow == 'requisitos':
                return self._handle_requisitos(session, phone, message)
            
            if session.current_flow == 'reintento_busqueda':
                return self._handle_retry_search(session, phone, message)
            
            # Detectar código PNR directo (6 caracteres)
            pnr_match = re.match(r'^[A-Za-z0-9]{6}$', message.strip())
            if pnr_match:
                session.current_flow = 'consultar_pnr'
                return self._check_status(session, phone, message)
            
            # No entendió
            return self._send_response(phone, "❓ *No entendí ese comando*\n\n━━━━━━━━━━━━━━━━━━━━\n\n💬 *Comandos disponibles:*\n\n✈️ *1* → Buscar vuelos\n📋 *2* → Consultar reserva\n🌍 *3* → Requisitos de viaje\n🏠 *menu* → Menú principal\n\n━━━━━━━━━━━━━━━━━━━━", session)
                
        except Exception as e:
            logger.error(f"ERROR: {str(e)}", exc_info=True)
            return self._send_response(phone, "😅 *¡Ups! Algo salió mal*\n\n━━━━━━━━━━━━━━━━━━━━\n\n🔄 Escribe *menu* para reintentar\n\n📞 Si el problema persiste, contáctanos", session)
    

    def _handle_origin(self, session, phone, message):
        """Maneja la selección de ciudad de origen"""
        airport_code = self._parse_airport(message)
        if not airport_code:
            return self._send_response(phone, "❌ *No reconozco esa ciudad*\n\n━━━━━━━━━━━━━━━━━━━━\n\n📍 *Ciudades disponibles:*\n\n🇻🇪 *Venezuela:*\nCaracas, Maracaibo, Valencia, Margarita, Barcelona, Mérida, Barquisimeto, Puerto Ordaz, Cumaná\n\n🌎 *Internacional:*\nMiami, Bogotá, Panamá\n\n━━━━━━━━━━━━━━━━━━━━\n\n📝 _Escribe el nombre de la ciudad:_", session)
        
        session.data['origin'] = airport_code
        session.current_flow = 'buscar_destino'
        return self._send_response(phone, f"✅ *Origen seleccionado:* {airport_code}\n\n━━━━━━━━━━━━━━━━━━━━\n\n📍 *¿A dónde viajas?*\n\n🇻🇪 *Venezuela:*\nMargarita, Maracaibo, Valencia, Barcelona\n\n🌎 *Internacional:*\nMiami, Bogotá, Panamá\n\n━━━━━━━━━━━━━━━━━━━━\n\n📝 _Escribe la ciudad o código (ej: PMV)_", session)
    
    def _handle_destination(self, session, phone, message):
        """Maneja la selección de ciudad de destino"""
        airport_code = self._parse_airport(message)
        if not airport_code:
            return self._send_response(phone, "❌ *No reconozco esa ciudad*\n\n━━━━━━━━━━━━━━━━━━━━\n\n📍 *Ciudades disponibles:*\n\n🇻🇪 *Venezuela:*\nCaracas, Maracaibo, Valencia, Margarita, Barcelona, Mérida, Barquisimeto, Puerto Ordaz, Cumaná\n\n🌎 *Internacional:*\nMiami, Bogotá, Panamá\n\n━━━━━━━━━━━━━━━━━━━━\n\n📝 _Escribe el nombre de la ciudad:_", session)
        
        origin = session.data.get('origin')
        if airport_code == origin:
            return self._send_response(phone, f"❌ *Origen y destino no pueden ser iguales*\n\n━━━━━━━━━━━━━━━━━━━━\n\n📍 Origen actual: *{origin}*\n\n📝 _Escribe una ciudad diferente:_", session)
        
        session.data['destination'] = airport_code
        session.current_flow = 'tipo_viaje'
        return self._send_response(phone, f"✅ *Destino seleccionado:* {airport_code}\n\n━━━━━━━━━━━━━━━━━━━━\n\n🔄 *¿Tipo de viaje?*\n\n*1* - Solo IDA ✈️\n*2* - IDA Y VUELTA ✈️↩️\n\n📝 _Escribe 1 o 2:_", session)
    
    def _handle_date(self, session, phone, message):
        """Maneja la selección de fecha de ida"""
        date = self._parse_date(message)
        if not date:
            return self._send_response(phone, "❌ *Fecha inválida*\n\n━━━━━━━━━━━━━━━━━━━━\n\n📅 *Formatos aceptados:*\n\n• 25/12/2025\n• 25-12-2025\n• hoy\n• mañana\n\n━━━━━━━━━━━━━━━━━━━━\n\n📝 _Escribe la fecha de tu viaje:_", session)
        
        session.data['date'] = date
        
        # Verificar tipo de viaje (previamente seleccionado)
        trip_type = session.data.get('trip_type', 'one_way')
        
        if trip_type == 'round_trip':
            session.current_flow = 'fecha_vuelta'
            return self._send_response(phone, f"✅ *Fecha de ida:* {date}\n\n━━━━━━━━━━━━━━━━━━━━\n\n📅 *¿Qué día regresarás?*\n\n📝 *Ejemplos:*\n• 25/12/2025\n• 15-01-2026\n\n━━━━━━━━━━━━━━━━━━━━\n\n📝 _Escribe la fecha de regreso:_", session)
        else:
            # Es solo ida, buscar de una vez
            session.data['trip_type'] = 'one_way' # asegurar
            session.data['return_date'] = None
            return self._search_flights_with_data(session, phone)
    
    def _handle_trip_type(self, session, phone, message):
        """Maneja la selección de tipo de viaje"""
        msg = message.strip().lower()
        
        if msg in ['1', 'ida', 'solo ida', 'one way']:
            session.data['trip_type'] = 'one_way'
            session.data['return_date'] = None
            session.current_flow = 'buscar_fecha'
            return self._send_response(phone, f"✅ *Tipo de viaje:* Solo Ida\n\n━━━━━━━━━━━━━━━━━━━━\n\n📅 *¿Qué día viajas?*\n\n📝 *Ejemplos:*\n• 25/12/2025\n• hoy\n• mañana\n• 15-01-2026\n\n━━━━━━━━━━━━━━━━━━━━\n\n📝 _Escribe la fecha de ida:_", session)
        elif msg in ['2', 'ida y vuelta', 'round trip', 'vuelta', 'ida y vuelta']:
            session.data['trip_type'] = 'round_trip'
            session.current_flow = 'buscar_fecha'
            return self._send_response(phone, f"✅ *Tipo de viaje:* Ida y Vuelta\n\n━━━━━━━━━━━━━━━━━━━━\n\n📅 *¿Qué día sales (IDA)?*\n\n📝 *Ejemplos:*\n• 25/12/2025\n• hoy\n• mañana\n• 15-01-2026\n\n━━━━━━━━━━━━━━━━━━━━\n\n📝 _Escribe la fecha de ida:_", session)
        else:
            return self._send_response(phone, "❓ *No entendí*\n\n━━━━━━━━━━━━━━━━━━━━\n\n*1* - Solo IDA ✈️\n*2* - IDA Y VUELTA ✈️↩️\n\n📝 _Escribe 1 o 2:_", session)
    
    def _handle_return_date(self, session, phone, message):
        """Maneja la selección de fecha de vuelta"""
        date = self._parse_date(message)
        if not date:
            return self._send_response(phone, "❌ *Fecha inválida*\n\n━━━━━━━━━━━━━━━━━━━━\n\n📅 *Formatos aceptados:*\n\n• 25/12/2025\n• 25-12-2025\n• hoy\n• mañana\n\n━━━━━━━━━━━━━━━━━━━━\n\n📝 _Escribe la fecha de regreso:_", session)
        
        session.data['return_date'] = date
        return self._search_flights_with_data(session, phone)
    
    def _parse_airport(self, message):
        """Extrae código de aeropuerto del mensaje"""
        airports = {
            'ccs': 'CCS', 'caracas': 'CCS', 'maiquetia': 'CCS', 'maiquetía': 'CCS',
            'pmv': 'PMV', 'margarita': 'PMV', 'porlamar': 'PMV',
            'mar': 'MAR', 'maracaibo': 'MAR', 'mcbo': 'MAR',
            'vln': 'VLN', 'valencia': 'VLN',
            'bla': 'BLA', 'barcelona': 'BLA',
            'mrd': 'MRD', 'merida': 'MRD', 'mérida': 'MRD',
            'brm': 'BRM', 'barquisimeto': 'BRM',
            'pzo': 'PZO', 'puerto ordaz': 'PZO', 'ordaz': 'PZO',
            'cum': 'CUM', 'cumana': 'CUM', 'cumaná': 'CUM',
            'mia': 'MIA', 'miami': 'MIA',
            'bog': 'BOG', 'bogota': 'BOG', 'bogotá': 'BOG',
            'pty': 'PTY', 'panama': 'PTY', 'panamá': 'PTY'
        }
        
        msg_lower = message.lower().strip()
        for name, code in airports.items():
            if name in msg_lower or msg_lower == code.lower():
                return code
        return None
    
    def _parse_date(self, message):
        """Extrae fecha del mensaje"""
        msg_lower = message.lower().strip()
        
        if 'hoy' in msg_lower:
            return datetime.now(VENEZUELA_TZ).strftime('%Y-%m-%d')
        elif 'mañana' in msg_lower or 'manana' in msg_lower:
            return (datetime.now(VENEZUELA_TZ) + timedelta(days=1)).strftime('%Y-%m-%d')
        
        date_patterns = [
            (r'(\d{1,2})/(\d{1,2})/(\d{4})', 'DMY'),
            (r'(\d{1,2})-(\d{1,2})-(\d{4})', 'DMY'),
            (r'(\d{4})-(\d{1,2})-(\d{1,2})', 'YMD'),
            (r'(\d{1,2})/(\d{1,2})', 'DM'),
            (r'(\d{1,2})-(\d{1,2})', 'DM')
        ]
        
        for pattern, format_type in date_patterns:
            match = re.search(pattern, message)
            if match:
                try:
                    if format_type == 'YMD':
                        return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
                    elif format_type == 'DMY':
                        return f"{match.group(3)}-{match.group(2).zfill(2)}-{match.group(1).zfill(2)}"
                    elif format_type == 'DM':
                        year = datetime.now(VENEZUELA_TZ).year
                        month = int(match.group(2))
                        day = int(match.group(1))
                        test_date = datetime(year, month, day, tzinfo=VENEZUELA_TZ)
                        if test_date < datetime.now(VENEZUELA_TZ):
                            year += 1
                        return f"{year}-{month:02d}-{day:02d}"
                except:
                    pass
        return None
    
    def _search_flights_with_data(self, session, phone):
        """Busca vuelos con los datos recopilados"""
        origin = session.data.get('origin')
        destination = session.data.get('destination')
        date = session.data.get('date')
        return_date = session.data.get('return_date')
        trip_type = session.data.get('trip_type', 'one_way')
        is_roundtrip = trip_type == 'round_trip' and return_date
        
        logger.info(f"Buscando: {origin} -> {destination} el {date}" + (f" (vuelta: {return_date})" if is_roundtrip else ""))
        
        try:
            # Buscar vuelos de IDA con reintentos agresivos
            max_retries = 5
            flights = None
            return_flights = None
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        wati_service.send_message(phone, f"🔄 *Reintento {attempt + 1}/{max_retries}*\n\n⏳ _Buscando vuelos..._")
                    
                    flights = flight_service.search_flights(
                        origin=origin,
                        destination=destination,
                        date=date,
                        passengers={"ADT": 1}
                    )
                    
                    if attempt > 0:
                        wati_service.send_message(phone, f"✅ *¡Búsqueda exitosa en intento {attempt + 1}!*")
                    break
                    
                except Exception as e:
                    last_error = str(e)
                    error_lower = last_error.lower()
                    
                    if 'timeout' in error_lower or 'tardó demasiado' in error_lower or 'timed out' in error_lower or 'connection' in error_lower:
                        if attempt < max_retries - 1:
                            logger.warning(f"Error en búsqueda (intento {attempt + 1}/{max_retries}): {last_error}")
                            import time
                            wait_time = 5 + (attempt * 2)
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"Todos los intentos fallaron: {last_error}")
                    else:
                        raise
            
            if not flights or len(flights) == 0:
                session.reset()
                return self._send_response(phone, f"😔 *No hay vuelos de ida disponibles*\n\n\n\n📍 Ruta: *{origin} → {destination}*\n📅 Fecha: *{date}*\n\n\n\n🔄 _Intenta con otra fecha o ruta_\n\n🏠 Escribe *menu* para buscar de nuevo", session)
            
            # Buscar vuelos de VUELTA si es ida y vuelta
            if is_roundtrip:
                try:
                    return_flights = flight_service.search_flights(
                        origin=destination,
                        destination=origin,
                        date=return_date,
                        passengers={"ADT": 1}
                    )
                except Exception as e:
                    logger.warning(f"Error buscando vuelos de vuelta: {e}")
                    return_flights = []
            
            # Determinar tipo de viaje para mostrar
            tipo_viaje_text = "Ida y Vuelta" if is_roundtrip else "Solo Ida"
            
            response = f"✈️ *VUELOS DISPONIBLES*\n\n📍 *{origin} {'↔' if is_roundtrip else '→'} {destination}*\n🔄 *Tipo:* {tipo_viaje_text}\n\n"
            response += f"━━━━━━━━━━━━━━━━━━━━\n🛫 *VUELOS DE IDA* ({date})\n📊 Total: *{len(flights)} vuelos*\n\n"
            
            for i, flight in enumerate(flights, 1):  # TODOS los vuelos
                airline = flight.get('airline_name', 'N/A')
                flight_num = flight.get('flight_number', 'N/A')
                dep_time = flight.get('departure_time', 'N/A')
                arr_time = flight.get('arrival_time', 'N/A')
                duration = flight.get('duration', '')
                price = flight.get('price')
                currency = flight.get('currency', 'USD')
                
                price_text = f"${price:.2f} {currency}" if price and price > 0 else "Consultar precio"
                
                # Extraer información completa de api_data
                api_data = flight.get('api_data', {})
                api_segments = api_data.get('segments', [])
                segment = api_segments[0] if api_segments else {}
                
                is_direct = api_data.get('isDirect', True)
                order = api_data.get('order', '')
                international = api_data.get('international', False)
                airlines_list = api_data.get('airlines', [])
                baggage = api_data.get('baggage', [])
                
                aircraft = segment.get('airEquipType', '')
                flight_class = segment.get('class', '')
                stop_quantity = segment.get('stopQuantity', '0')
                meal = segment.get('meal', '')
                meal_code = segment.get('mealCode', '')
                cabins = segment.get('cabins', [])
                classes = segment.get('classes', {})
                
                response += f"*{i}* - {airline} {flight_num}\n"
                
                # Mostrar ruta completa si hay escalas
                if api_segments and len(api_segments) > 1:
                    route_parts = []
                    for seg in api_segments:
                        if not route_parts:
                            route_parts.append(seg.get('departureCode', ''))
                        route_parts.append(seg.get('arrivalCode', ''))
                    response += f"     📍 {' → '.join(route_parts)}"
                    response += f" (🔄 {len(api_segments)-1} escala)\n"
                    # Mostrar hora de salida inicial y llegada final
                    first_seg = api_segments[0]
                    last_seg = api_segments[-1]
                    first_dep = first_seg.get('departureTime', '').split(':')[0] + ':' + first_seg.get('departureTime', '').split(':')[1] if first_seg.get('departureTime') else ''
                    last_arr = last_seg.get('arrivalTime', '').split(':')[0] + ':' + last_seg.get('arrivalTime', '').split(':')[1] if last_seg.get('arrivalTime') else ''
                    response += f"     🕐 {first_dep} → {last_arr}\n"
                    if duration:
                        response += f"     ⏱️ Duración: {duration}\n"
                    if aircraft:
                        response += f"     ✈️ Aeronave: {aircraft}\n"
                else:
                    response += f"     🕐 {dep_time} → {arr_time}\n"
                    if duration:
                        response += f"     ⏱️ Duración: {duration}\n"
                    response += "     ✈️ Vuelo directo"
                    if aircraft:
                        response += f" | {aircraft}"
                    response += "\n"
                
                # Clase con asientos disponibles
                if flight_class:
                    response += f"     🎫 Clase: {flight_class}"
                    if classes and isinstance(classes, dict) and flight_class in classes:
                        seats = classes[flight_class]
                        response += f" ({seats} asientos)"
                    response += "\n"
                
                # Cabina
                if cabins and len(cabins) > 0:
                    if isinstance(cabins, list):
                        cabin_name = cabins[0]
                    elif isinstance(cabins, dict):
                        # Si es diccionario, tomar el primer valor
                        cabin_name = list(cabins.values())[0] if cabins else ''
                    else:
                        cabin_name = cabins
                    if cabin_name:
                        response += f"     🪑 Cabina: {cabin_name}\n"
                
                # Comida (sin duplicar código si ya está en meal)
                if meal and meal.strip() and meal not in ['()', '(-)', '(N)']:
                    response += f"     🍽️ Comida: {meal}\n"
                
                # Equipaje detallado
                if baggage and isinstance(baggage, list):
                    for idx, bag in enumerate(baggage[:2]):
                        if isinstance(bag, dict):
                            pieces = bag.get('pieces', '')
                            weight = bag.get('weight', '')
                            bag_type = bag.get('type', 'Equipaje')
                            if pieces or weight:
                                response += f"     🧳 {bag_type}: {pieces} pza"
                                if weight:
                                    response += f" ({weight})"
                                response += "\n"
                
                # Internacional
                if international:
                    response += f"     🌍 Vuelo internacional\n"
                
                # Aerolíneas múltiples
                if airlines_list and isinstance(airlines_list, list) and len(airlines_list) > 1:
                    response += f"     ✈️ Aerolíneas: {', '.join(airlines_list)}\n"
                
                response += f"     💵 {price_text}\n\n"
            
            # VUELOS DE VUELTA (si es ida y vuelta)
            if is_roundtrip and return_flights and len(return_flights) > 0:
                response += "━━━━━━━━━━━━━━━━━━━━\n"
                response += f"🛬 *VUELOS DE VUELTA* ({return_date})\n"
                response += f"📊 Total: *{len(return_flights)} vuelos*\n\n"
                
                for i, flight in enumerate(return_flights[:5], 1):
                    airline = flight.get('airline_name', 'N/A')
                    flight_num = flight.get('flight_number', 'N/A')
                    dep_time = flight.get('departure_time', 'N/A')
                    arr_time = flight.get('arrival_time', 'N/A')
                    price = flight.get('price')
                    currency = flight.get('currency', 'USD')
                    
                    price_text_return = f"${price:.2f} {currency}" if price and price > 0 else "Consultar precio"
                    
                    response += f"*{i}* - {airline} {flight_num}\n"
                    response += f"     🕐 {dep_time} → {arr_time}\n"
                    response += f"     💵 {price_text_return}\n\n"
            elif is_roundtrip:
                response += "━━━━━━━━━━━━━━━━━━━━\n"
                response += f"🛬 *VUELOS DE VUELTA* ({return_date})\n\n"
                response += "😔 *No hay vuelos de vuelta disponibles*\n\n"
            
            response += "\n\n👆 _Escribe el número del vuelo de IDA que deseas_\n\n💡 *Tip:* Escribe *'más barato'* para el vuelo económico"
            
            session.data['flight_options'] = flights
            session.data['return_flight_options'] = return_flights if is_roundtrip else []
            session.current_flow = 'seleccionar_vuelo'
            
            # Si el usuario pidió el más barato desde el inicio, seleccionarlo automáticamente
            if session.data.get('prefer_cheapest'):
                cheapest_flight = min(flights, key=lambda f: f.get('price', float('inf')))
                cheapest_index = flights.index(cheapest_flight) + 1
                response += f"\n\n⭐ *Recomendación:* El vuelo #{cheapest_index} es el más económico (${cheapest_flight.get('price'):.2f})"
                session.data['prefer_cheapest'] = False  # Limpiar flag
            
            return self._send_response(phone, response, session)
        except Exception as e:
            logger.error(f"Error buscando: {str(e)}", exc_info=True)
            session.reset()
            return self._send_response(phone, "❌ *Error al buscar vuelos*\n\n\n\n😅 _Ocurrió un problema técnico_\n\n🏠 Escribe *menu* para intentar de nuevo", session)
    

    def _handle_flight_selection(self, session, phone, message):
        """Selecciona vuelo"""
        flights = session.data.get('flight_options', [])
        if not flights:
            session.reset()
            return self._send_response(phone, "❌ *No hay vuelos disponibles*\n\n\n\n🏠 Escribe *menu* para buscar vuelos", session)
        
        msg_lower = message.lower().strip()
        
        # Detectar si pide el vuelo más barato/económico
        if any(word in msg_lower for word in ['barato', 'economico', 'económico', 'mas barato', 'más barato', 'menor precio', 'precio bajo', 'cheapest', 'cheap']):
            # Encontrar el vuelo con menor precio
            cheapest_flight = min(flights, key=lambda f: f.get('price', float('inf')))
            cheapest_index = flights.index(cheapest_flight)
            flight = cheapest_flight
            logger.info(f"Usuario pidió vuelo más barato: seleccionando vuelo #{cheapest_index + 1} (${flight.get('price')})")
        else:
            # Selección por número
            try:
                num = int(message.strip())
                if 1 <= num <= len(flights):
                    flight = flights[num - 1]
                else:
                    return self._send_response(phone, f"❌ *Número inválido*\n\n\n\n🔢 _Escribe un número del *1* al *{len(flights)}*_\n\n💡 O escribe *'más barato'* para el vuelo económico", session)
            except ValueError:
                return self._send_response(phone, f"❌ *Opción inválida*\n\n\n\n🔢 _Escribe un número del *1* al *{len(flights)}*_\n\n💡 O escribe *'más barato'* para el vuelo económico", session)
        
        # Continuar con la selección del vuelo
        if flight:
                session.data['selected_flight'] = flight
                
                # Verificar si hay múltiples clases con precios diferentes
                classes_prices = flight.get('classes_prices', {})
                if classes_prices and len(classes_prices) > 1:
                    # Hay múltiples clases - preguntar cuál quiere
                    session.current_flow = 'seleccionar_clase'
                else:
                    # Solo una clase o sin info de clases - ir directo a confirmar
                    session.current_flow = 'confirmar_vuelo'
                
                price = flight.get('price')
                currency = flight.get('currency', 'USD')
                duration = flight.get('duration', '')
                origin_code = flight.get('origin', '')
                dest_code = flight.get('destination', '')
                
                price_text = f"${price:.2f} {currency}" if price and price > 0 else "Consultar precio"
                
                # Extraer información completa de api_data
                api_data = flight.get('api_data', {})
                segments = api_data.get('segments', [{}])
                segment = segments[0] if segments else {}
                
                is_direct = api_data.get('isDirect', True)
                order = api_data.get('order', '')
                international = api_data.get('international', False)
                airlines_list = api_data.get('airlines', [])
                baggage = api_data.get('baggage', [])
                
                aircraft = segment.get('airEquipType', '')
                flight_class = segment.get('class', '')
                stop_quantity = segment.get('stopQuantity', '0')
                meal = segment.get('meal', '')
                meal_code = segment.get('mealCode', '')
                cabins = segment.get('cabins', [])
                available_classes = segment.get('classes', {})
                
                response = f"✅ *VUELO SELECCIONADO*\n\n"
                response += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                response += f"✈️ *{flight['airline_name']} {flight['flight_number']}*\n\n"
                
                # INFORMACIÓN DE RUTA Y HORARIOS
                response += f"📍 *RUTA Y HORARIOS*\n"
                
                # Mostrar TODOS los segmentos si hay escalas
                if segments and len(segments) > 1:
                    response += f"\n🔄 *Vuelo con {len(segments)-1} escala(s)*\n\n"
                    for idx, seg in enumerate(segments, 1):
                        seg_origin = seg.get('departureCode', '')
                        seg_dest = seg.get('arrivalCode', '')
                        seg_airline = seg.get('airlineCode', '')
                        seg_flight_num = seg.get('flightNumber', '')
                        seg_dep_time = seg.get('departureTime', '').split(':')[0] + ':' + seg.get('departureTime', '').split(':')[1] if seg.get('departureTime') else ''
                        seg_arr_time = seg.get('arrivalTime', '').split(':')[0] + ':' + seg.get('arrivalTime', '').split(':')[1] if seg.get('arrivalTime') else ''
                        seg_dep_date = seg.get('departureDate', '')
                        seg_arr_date = seg.get('arrivalDate', '')
                        seg_duration = seg.get('journeyDuration', '')
                        seg_aircraft = seg.get('airEquipType', '')
                        
                        response += f"*Segmento {idx}:* {seg_airline}{seg_flight_num}\n"
                        response += f"  📍 {seg_origin} → {seg_dest}\n"
                        response += f"  🛫 Salida: {seg_dep_time}"
                        if seg_dep_date:
                            response += f" ({seg_dep_date})"
                        response += "\n"
                        response += f"  🛬 Llegada: {seg_arr_time}"
                        if seg_arr_date:
                            response += f" ({seg_arr_date})"
                        response += "\n"
                        if seg_duration:
                            response += f"  ⏱️ Duración: {seg_duration}\n"
                        if seg_aircraft:
                            response += f"  ✈️ Aeronave: {seg_aircraft}\n"
                        response += "\n"
                    
                    # Resumen total
                    first_seg = segments[0]
                    last_seg = segments[-1]
                    first_dep = first_seg.get('departureTime', '').split(':')[0] + ':' + first_seg.get('departureTime', '').split(':')[1] if first_seg.get('departureTime') else ''
                    last_arr = last_seg.get('arrivalTime', '').split(':')[0] + ':' + last_seg.get('arrivalTime', '').split(':')[1] if last_seg.get('arrivalTime') else ''
                    response += f"*Resumen Total:*\n"
                    response += f"📅 Fecha: {flight.get('date', '')}\n"
                    response += f"🕐 Salida: {first_dep} | Llegada: {last_arr}\n"
                    if duration:
                        response += f"⏱️ Duración total: {duration}\n"
                else:
                    response += f"\n✈️ *Vuelo directo*\n\n"
                    response += f"📍 Origen: *{origin_code}*\n"
                    response += f"📍 Destino: *{dest_code}*\n"
                    response += f"📅 Fecha: *{flight.get('date', '')}*\n"
                    response += f"🛫 Salida: *{flight['departure_time']}*\n"
                    response += f"🛬 Llegada: *{flight['arrival_time']}*\n"
                    if duration:
                        response += f"⏱️ Duración: _{duration}_\n"
                
                response += "\n"
                
                # INFORMACIÓN DE CLASE Y CABINA
                response += f"🎫 *CLASE Y CABINA*\n\n"
                
                if flight_class:
                    response += f"Clase: *{flight_class}*"
                    if available_classes and isinstance(available_classes, dict) and flight_class in available_classes:
                        seats = available_classes[flight_class]
                        response += f" ({seats} asientos disponibles)"
                    response += "\n"
                
                # Cabina
                if cabins and len(cabins) > 0:
                    if isinstance(cabins, list):
                        cabin_name = cabins[0]
                    elif isinstance(cabins, dict):
                        cabin_name = list(cabins.values())[0] if cabins else ''
                    else:
                        cabin_name = cabins
                    if cabin_name:
                        response += f"Cabina: _{cabin_name}_\n"
                
                response += "\n"
                
                # Verificar si hay múltiples clases con precios
                classes_prices = flight.get('classes_prices', {})
                if classes_prices and len(classes_prices) > 1:
                    # Mostrar TODAS las clases con sus precios
                    response += f"💰 *CLASES Y PRECIOS DISPONIBLES*\n\n"
                    
                    # Ordenar clases por precio (de menor a mayor)
                    sorted_classes = sorted(classes_prices.items(), key=lambda x: x[1].get('price', 999999))
                    
                    for idx, (cls, info) in enumerate(sorted_classes, 1):
                        cls_price = info.get('price', 0)
                        cls_seats = info.get('availability', '?')
                        response += f"*{idx}* - Clase {cls}: ${cls_price:.2f} USD ({cls_seats} asientos)\n"
                    
                    response += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
                    response += "👆 *Escribe el número de la clase que deseas*\n"
                else:
                    # Solo una clase o sin info - mostrar precio único
                    response += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    response += f"💵 *PRECIO TOTAL: {price_text}*\n\n"
                    response += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    response += "❓ *¿Confirmas este vuelo?*\n\n"
                    response += "✅ *1* - Sí, reservar\n"
                    response += "❌ *2* - No, buscar otro\n"
                
                return self._send_response(phone, response, session)
        
        return self._send_response(phone, f"❌ *Error en selección*\n\n\n\n🔢 _Escribe un número del *1* al *{len(flights)}*_\n\n💡 O escribe *'más barato'* para el vuelo económico", session)
    
    def _handle_class_selection(self, session, phone, message):
        """Maneja la selección de clase de vuelo"""
        flight = session.data.get('selected_flight')
        if not flight:
            session.reset()
            return self._send_response(phone, "❌ *Error: No hay vuelo seleccionado*\n\n🏠 Escribe *menu* para buscar vuelos", session)
        
        classes_prices = flight.get('classes_prices', {})
        if not classes_prices:
            session.reset()
            return self._send_response(phone, "❌ *Error: No hay clases disponibles*\n\n🏠 Escribe *menu* para buscar vuelos", session)
        
        try:
            # Ordenar clases por precio
            sorted_classes = sorted(classes_prices.items(), key=lambda x: x[1].get('price', 999999))
            
            num = int(message.strip())
            if 1 <= num <= len(sorted_classes):
                selected_class_code, selected_class_info = sorted_classes[num - 1]
                selected_price = selected_class_info.get('price', 0)
                selected_base = selected_class_info.get('base', 0)
                
                # Actualizar el vuelo con la clase seleccionada
                flight['class'] = selected_class_code
                flight['price'] = selected_price
                flight['base'] = selected_base
                session.data['selected_flight'] = flight
                
                # Mostrar confirmación con la clase elegida
                response = f"✅ *CLASE SELECCIONADA*\n\n"
                response += f"🎫 Clase: *{selected_class_code}*\n"
                response += f"💵 Precio: *${selected_price:.2f} USD*\n\n"
                response += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                response += "❓ *¿Confirmas esta reserva?*\n\n"
                response += "✅ *1* - Sí, reservar\n"
                response += "❌ *2* - No, elegir otra clase\n"
                
                session.current_flow = 'confirmar_vuelo'
                return self._send_response(phone, response, session)
            else:
                return self._send_response(phone, f"❌ *Número inválido*\n\n🔢 Escribe un número del *1* al *{len(sorted_classes)}*", session)
        except ValueError:
            return self._send_response(phone, f"❌ *Opción inválida*\n\n🔢 Escribe un número del *1* al *{len(sorted_classes)}*", session)
    
    def _handle_flight_confirmation(self, session, phone, message):
        """Confirma o cancela la selección de vuelo"""
        msg_lower = message.lower().strip()
        
        if msg_lower in ['1', 'si', 'sí', 'ok', 'confirmar', 'reservar', 'yes', '1 - si, reservar', '1 - sí, reservar']:
            session.current_flow = 'recopilar_datos'
            return self._send_response(phone, "📝 *DATOS DEL PASAJERO*\n\n\n\n👤 Envía los datos en este formato:\n\n*Nombre Apellido, Cédula, Teléfono, Email*\n\n\n\n📝 *Ejemplo:*\nJuan Perez, V12345678, 4121234567, juan@email.com", session)
        
        elif msg_lower in ['2', 'no', 'cancelar', 'volver']:
            # Verificar si tiene múltiples clases para volver a selección de clase
            flight = session.data.get('selected_flight')
            classes_prices = flight.get('classes_prices', {}) if flight else {}
            
            if classes_prices and len(classes_prices) > 1:
                # Volver a selección de clase
                session.current_flow = 'seleccionar_clase'
                
                response = "👌 *Entendido*\n\n💰 *CLASES DISPONIBLES*\n\n"
                sorted_classes = sorted(classes_prices.items(), key=lambda x: x[1].get('price', 999999))
                for idx, (cls, info) in enumerate(sorted_classes, 1):
                    cls_price = info.get('price', 0)
                    cls_seats = info.get('availability', '?')
                    response += f"*{idx}* - Clase {cls}: ${cls_price:.2f} USD ({cls_seats} asientos)\n"
                response += "\n👆 *Escribe el número de la clase que deseas*"
                return self._send_response(phone, response, session)
            else:
                # Volver a selección de vuelo
                flights = session.data.get('flight_options', [])
                if flights:
                    session.current_flow = 'seleccionar_vuelo'
                    session.data['selected_flight'] = None
                    return self._send_response(phone, "👌 *Entendido*\n\n\n\n👆 _Escribe el número de otro vuelo:_", session)
                else:
                    session.reset()
                    return self._send_response(phone, "👌 *Reserva cancelada*\n\n\n\n🏠 Escribe *menu* para volver al inicio", session)
        
        return self._send_response(phone, "❌ *Respuesta inválida*\n\n\n\n✅ *1* - Sí, reservar\n❌ *2* - No, buscar otro\n\n", session)
    
    def _process_passenger_data(self, session, phone, message):
        """Procesa datos del pasajero - Formato: Nombre Apellido, V12345678, 4121234567, email@ejemplo.com"""
        try:
            parts = [p.strip() for p in message.split(',')]
            
            if len(parts) < 4:
                return self._send_response(phone, "❌ *Faltan datos*\n\n\n\n👤 Envía en este formato:\n\n*Nombre Apellido, Cédula, Teléfono, Email*\n\n\n\n📝 *Ejemplo:*\nJuan Perez, V12345678, 4121234567, juan@email.com", session)
            
            # Extraer datos
            name_parts = parts[0].split()
            first_name = name_parts[0] if name_parts else ''
            last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
            
            cedula = re.sub(r'[^0-9]', '', parts[1])
            phone_num = re.sub(r'[^0-9]', '', parts[2])
            email = parts[3].strip()
            
            if not all([first_name, last_name, cedula, phone_num, email]):
                return self._send_response(phone, "❌ *Datos incompletos*\n\n\n\n👤 Envía todos los datos:\n\n*Nombre Apellido, Cédula, Teléfono, Email*\n\n\n\n📝 *Ejemplo:*\nJuan Perez, V12345678, 4121234567, juan@email.com", session)
            
            # Crear reserva
            flight = session.data.get('selected_flight')
            if not flight:
                session.reset()
                return self._send_response(phone, "❌ *No hay vuelo seleccionado*\n\n\n\n🏠 Escribe *menu* para buscar vuelos", session)
            
            passenger = {
                'name': first_name.upper(),
                'lastName': last_name.upper(),
                'idNumber': cedula,
                'phone': phone_num,
                'email': email,
                'type': 'ADT',
                'nationality': 'VE',
                'documentType': 'CI',
                'birthDate': '1990-01-01',
                'gender': 'M',
                'phoneCode': '58'
            }
            
            logger.info(f"Creando reserva para {first_name} {last_name}")
            result = flight_service.create_booking(
                flight_option=flight,
                passenger_details=[passenger]
            )
            
            if result.get('success'):
                pnr = result.get('pnr', 'N/A')
                vid = result.get('vid', 'N/A')
                
                # Extraer datos del vuelo
                origin = flight.get('origin', '')
                destination = flight.get('destination', '')
                date = flight.get('date', '')
                dep_time = flight.get('departure_time', '')
                arr_time = flight.get('arrival_time', '')
                price = flight.get('price')
                currency = flight.get('currency', 'USD')
                flight_class = flight.get('class', '')
                
                api_data = flight.get('api_data', {})
                segments = api_data.get('segments', [{}])
                segment = segments[0] if segments else {}
                
                is_direct = api_data.get('isDirect', True)
                order = api_data.get('order', '')
                international = api_data.get('international', False)
                airlines_list = api_data.get('airlines', [])
                baggage = api_data.get('baggage', [])
                
                aircraft = segment.get('airEquipType', '')
                stop_quantity = segment.get('stopQuantity', '0')
                meal = segment.get('meal', '')
                meal_code = segment.get('mealCode', '')
                cabins = segment.get('cabins', [])
                
                response = "🎉 *¡RESERVA EXITOSA!*\n\n"
                response += f"🎫 *Código PNR:* `{pnr}`\n"
                response += f"🔖 *ID Viaje:* `{vid}`\n\n"
                response += "✈️ *DETALLES DEL VUELO*\n\n"
                response += f"✈️ {flight['airline_name']} {flight['flight_number']}\n"
                
                # Mostrar TODOS los segmentos si hay escalas
                if segments and len(segments) > 1:
                    response += f"📍 *Ruta completa:*\n"
                    for idx, seg in enumerate(segments, 1):
                        seg_origin = seg.get('departureCode', '')
                        seg_dest = seg.get('arrivalCode', '')
                        seg_dep_time = seg.get('departureTime', '').split(':')[0] + ':' + seg.get('departureTime', '').split(':')[1] if seg.get('departureTime') else ''
                        seg_arr_time = seg.get('arrivalTime', '').split(':')[0] + ':' + seg.get('arrivalTime', '').split(':')[1] if seg.get('arrivalTime') else ''
                        response += f"  {idx}. {seg_origin} → {seg_dest} ({seg_dep_time} - {seg_arr_time})\n"
                    response += "\n"
                    response += f"📅 Fecha: *{date}*\n"
                    # Para vuelos con escalas, mostrar horario completo
                    first_seg = segments[0]
                    last_seg = segments[-1]
                    first_dep = first_seg.get('departureTime', '').split(':')[0] + ':' + first_seg.get('departureTime', '').split(':')[1] if first_seg.get('departureTime') else ''
                    last_arr = last_seg.get('arrivalTime', '').split(':')[0] + ':' + last_seg.get('arrivalTime', '').split(':')[1] if last_seg.get('arrivalTime') else ''
                    response += f"🕐 Horario: *{first_dep} - {last_arr}*\n"
                    # Calcular duración total si existe
                    total_duration = flight.get('duration', '')
                    if total_duration:
                        response += f"⏱️ Duración: _{total_duration}_\n"
                    response += f"🔄 Tipo: _{len(segments)-1} escala(s)_\n"
                else:
                    response += f"📍 Ruta: *{origin} → {destination}*\n"
                    response += f"📅 Fecha: *{date}*\n"
                    response += f"🕐 Horario: *{dep_time} - {arr_time}*\n"
                    # Duración si existe
                    total_duration = flight.get('duration', '')
                    if total_duration:
                        response += f"⏱️ Duración: _{total_duration}_\n"
                    response += f"✈️ Tipo: _Directo_\n"
                
                if aircraft:
                    response += f"✈️ Aeronave: _{aircraft}_\n"
                
                if flight_class:
                    response += f"🎫 Clase: _{flight_class}_\n"
                
                # Cabina
                if cabins and len(cabins) > 0:
                    if isinstance(cabins, list):
                        cabin_name = cabins[0]
                    elif isinstance(cabins, dict):
                        # Si es diccionario, tomar el primer valor
                        cabin_name = list(cabins.values())[0] if cabins else ''
                    else:
                        cabin_name = cabins
                    if cabin_name:
                        response += f"🪑 Cabina: _{cabin_name}_\n"
                
                # Comida (sin duplicar código si ya está en meal)
                if meal:
                    response += f"🍽️ Comida: _{meal}_\n"
                
                # Internacional
                if international:
                    response += f"🌍 Tipo: _Vuelo internacional_\n"
                
                # Aerolíneas múltiples
                if airlines_list and isinstance(airlines_list, list) and len(airlines_list) > 1:
                    response += f"✈️ Aerolíneas: _{', '.join(airlines_list)}_\n"
                
                # Equipaje detallado
                if baggage and isinstance(baggage, list):
                    response += f"\n🧳 *Equipaje incluido:*\n"
                    for bag in baggage[:2]:
                        if isinstance(bag, dict):
                            pieces = bag.get('pieces', '')
                            weight = bag.get('weight', '')
                            bag_type = bag.get('type', 'Equipaje')
                            if pieces:
                                response += f"  • {bag_type}: {pieces} pza"
                                if weight:
                                    response += f" ({weight})"
                                response += "\n"
                
                response += "\n\n"
                response += "👤 *DATOS DEL PASAJERO*\n"
                response += "\n\n"
                response += f"👤 Nombre: *{first_name} {last_name}*\n"
                response += f"🆔 Cédula: _{cedula}_\n"
                response += f"📞 Teléfono: _{phone_num}_\n"
                response += f"📧 Email: _{email}_\n"
                
                if price and price > 0:
                    response += f"\n\n"
                    response += f"💵 *PRECIO TOTAL:* ${price:.2f} {currency}\n"
                
                response += "\n\n"
                response += "⚠️ *IMPORTANTE*\n"
                response += "\n\n"
                response += "✅ Guarda tu código PNR\n"
                response += "📧 Revisa tu email para más detalles\n"
                response += "📞 Contáctanos si necesitas ayuda\n\n"
                response += "\n\n"
                response += "🏠 Escribe *menu* para volver al inicio"
                
                session.reset()
                return self._send_response(phone, response, session)
            else:
                error = result.get('error', 'Error desconocido')
                logger.error(f"Error al crear reserva: {error}")
                
                # Mensaje personalizado según el tipo de error
                if 'expir' in error.lower() or 'tiempo' in error.lower() or 'limit' in error.lower():
                    # Error de tiempo límite - ofrecer buscar de nuevo
                    origin = flight.get('origin', '')
                    destination = flight.get('destination', '')
                    date = flight.get('date', '')
                    
                    response = f"⚠️ *¡Lo siento, {first_name}!*\n\n"
                    response += f"🕒 Los datos del vuelo expiraron mientras procesaba tu reserva.\n\n"
                    response += f"🔄 *¿Quieres que busque vuelos nuevamente?*\n\n"
                    response += f"📍 Ruta: *{origin} → {destination}*\n"
                    response += f"📅 Fecha: *{date}*\n\n"
                    response += f"✅ *1* - Sí, buscar de nuevo\n"
                    response += f"❌ *2* - No, volver al menú\n\n"
                    
                    # Guardar datos para poder buscar de nuevo
                    session.data['origin'] = origin
                    session.data['destination'] = destination
                    session.data['date'] = date
                    session.current_flow = 'reintento_busqueda'
                    
                    return self._send_response(phone, response, session)
                else:
                    # Otro tipo de error
                    return self._send_response(phone, f"😔 *Error al crear reserva*\n\n\n\n❌ {error}\n\n\n\n🏠 Escribe *menu* para reintentar", session)
                
        except Exception as e:
            logger.error(f"Error procesando datos: {str(e)}", exc_info=True)
            return self._send_response(phone, "😅 *Error procesando datos*\n\n\n\n👤 Envía en este formato:\n\n*Nombre Apellido, Cédula, Teléfono, Email*\n\n\n\n📝 *Ejemplo:*\nJuan Perez, V12345678, 4121234567, juan@email.com", session)
    
    def _check_status(self, session, phone, message):
        """Consulta reserva - Formato: ABC123"""
        try:
            # Extraer PNR
            pnr_match = re.search(r'\b([A-Z0-9]{6})\b', message.upper())
            if not pnr_match:
                return self._send_response(phone, "❌ *Código inválido*\n\n\n\n🎫 El PNR debe tener exactamente 6 caracteres\n\n\n\n📝 *Ejemplo:* ABC123", session)
            
            pnr = pnr_match.group(1)
            
            logger.info(f"Consultando: {pnr}")
            result = flight_service.get_booking_details(pnr=pnr)
            
            if result.get('success'):
                info = result
                response = f"📋 *CONSULTA DE RESERVA*\n\n\n\n🎫 *PNR:* `{pnr}`\n\n"
                
                # VID
                if info.get('vid'):
                    response += f"🆔 *VID:* {info.get('vid')}\n"
                
                # Estado
                status = info.get('status', 'N/A')
                flight_status = info.get('flight_status', '')
                if status != 'N/A':
                    response += f"📌 *Estado:* {status}"
                    if flight_status and flight_status != status:
                        response += f" ({flight_status})"
                    response += "\n"
                
                # Tipo
                if info.get('type'):
                    response += f"📋 *Tipo:* {info.get('type')}\n"
                
                # Cliente
                client = info.get('client', '')
                if client and client != 'N/A':
                    response += f"👤 *Cliente:* {client}\n"
                
                # Ruta
                route = info.get('route')
                if route and route != 'N/A':
                    response += f"📍 *Ruta:* {route}\n"
                
                # Fechas
                vencimiento = info.get('vencimiento', '')
                if vencimiento:
                    response += f"⏰ *Vencimiento:* {vencimiento}\n"
                
                if info.get('created_at'):
                    response += f"📅 *Creación:* {info.get('created_at')}\n"
                
                # Precios
                balance = info.get('balance', '')
                if balance and 'N/A' not in str(balance):
                    response += f"\n💰 *PRECIO TOTAL:* {balance}\n"
                
                if info.get('base'):
                    response += f"Base: {info.get('base')}\n"
                
                if info.get('taxes'):
                    response += f"Impuestos: {info.get('taxes')}\n"
                
                if info.get('commission'):
                    response += f"Comisión: {info.get('commission')}\n"
                
                flights = info.get('flights', [])
                if flights:
                    # Ordenar vuelos por fecha y hora de salida
                    def parse_flight_datetime(f):
                        from datetime import datetime
                        fecha = f.get('fecha', '2099-12-31')
                        hora = f.get('hora_salida', '23:59')
                        try:
                            fecha_str = f"{fecha} {hora[:5] if hora else '00:00'}"
                            for fmt in ['%Y-%m-%d %H:%M', '%d/%m/%Y %H:%M', '%d-%m-%Y %H:%M', '%d %b %Y %H:%M']:
                                try:
                                    return datetime.strptime(fecha_str, fmt)
                                except:
                                    continue
                            return datetime(2099, 12, 31)
                        except:
                            return datetime(2099, 12, 31)
                    
                    flights.sort(key=parse_flight_datetime)
                    
                    response += "\n🛫 *VUELOS:*\n"
                    for f in flights:
                        response += f"\n  ✈️ *{f.get('aerolinea')} {f.get('vuelo')}*\n"
                        response += f"  📍 Ruta: {f.get('ruta')}\n"
                        response += f"  📅 Fecha: {f.get('fecha')}\n"
                        
                        hora_salida = f.get('hora_salida', '')
                        hora_llegada = f.get('hora_llegada', '')
                        if hora_salida or hora_llegada:
                            response += f"  🕐 Horario: {hora_salida} - {hora_llegada}\n"
                        
                        clase = f.get('clase', '')
                        if clase:
                            response += f"  🎫 Clase: {clase}\n"
                        
                        asiento = f.get('asiento', '')
                        if asiento:
                            response += f"  💺 Asiento: {asiento}\n"
                        
                        equipaje = f.get('equipaje', '')
                        if equipaje:
                            response += f"  🧳 Equipaje: {equipaje}\n"
                        
                        estado = f.get('estado', '')
                        if estado:
                            response += f"  📌 Estado: {estado}\n"
                
                # Pasajeros
                passengers = info.get('passengers', [])
                if passengers:
                    response += f"\n👥 *PASAJEROS:*\n"
                    for pax in passengers:
                        if isinstance(pax, dict):
                            nombre = pax.get('nombre', '')
                            tipo = pax.get('tipo', '')
                            documento = pax.get('documento', '')
                            telefono = pax.get('telefono', '')
                            email = pax.get('email', '')
                            
                            response += f"\n  👤 {nombre}"
                            if tipo:
                                tipo_map = {'ADT': 'Adulto', 'CHD': 'Niño', 'INF': 'Infante', 'CNN': 'Niño'}
                                response += f" ({tipo_map.get(tipo, tipo)})"
                            response += "\n"
                            if documento:
                                response += f"  🆔 Documento: {documento}\n"
                            if telefono:
                                response += f"  📞 Teléfono: {telefono}\n"
                            if email:
                                response += f"  📧 Email: {email}\n"
                
                # Precios
                balance = info.get('balance', '')
                if balance and 'N/A' not in str(balance):
                    response += "\n\n"
                    response += f"💵 *PRECIO TOTAL:* {balance}\n"
                
                # Información adicional
                if info.get('agent'):
                    response += f"\n👤 *Agente:* {info.get('agent')}\n"
                
                if info.get('office'):
                    response += f"🏢 *Oficina:* {info.get('office')}\n"
                
                if info.get('ticket_number'):
                    response += f"\n🎫 *Número Ticket:* {info.get('ticket_number')}\n"
                
                if info.get('payment_method'):
                    response += f"💳 *Forma Pago:* {info.get('payment_method')}\n"
                
                if info.get('observations'):
                    response += f"\n📝 *Observaciones:*\n{info.get('observations')}\n"
                
                response += "\n\n\n"
                response += "🏠 Escribe *menu* para volver al inicio"
                
                session.reset()
                return self._send_response(phone, response, session)
            else:
                session.reset()
                return self._send_response(phone, f"😔 *Reserva no encontrada*\n\n\n\n🎫 PNR: *{pnr}*\n\n❌ No existe en el sistema\n\n\n\n🔍 Verifica el código\n\n🏠 Escribe *menu* para volver", session)
                
        except Exception as e:
            logger.error(f"Error consultando: {str(e)}", exc_info=True)
            session.reset()
            return self._send_response(phone, "😅 *Error al consultar*\n\n\n\n🚫 Ocurrió un problema técnico\n\n🏠 Escribe *menu* para volver", session)
    
    def _handle_requisitos(self, session, phone, message):
        """Requisitos migratorios"""
        try:
            msg_lower = message.lower().strip()
            
            # Intentar obtener requisitos (acepta números y nombres)
            requisitos = get_requisitos_pais(msg_lower)
            if requisitos:
                session.reset()
                return self._send_response(phone, requisitos + "\n\n\n\n🏠 Escribe *menu* para volver al inicio", session)
            
            # Mostrar menú si no detectó país
            return self._send_response(phone, get_requisitos_menu() + "\n\n👆 _Escribe el número o nombre del país_", session)
            
        except Exception as e:
            logger.error(f"Error requisitos: {str(e)}")
            session.reset()
            return self._send_response(phone, "😅 *Error*\n\n\n\n🚫 Ocurrió un problema\n\n🏠 Escribe *menu* para volver", session)
    
    def _handle_retry_search(self, session, phone, message):
        """Maneja el reintento de búsqueda después de un error de tiempo límite"""
        msg_lower = message.lower().strip()
        
        if msg_lower in ['1', 'si', 'sí', 'ok', 'buscar', 'yes']:
            # Buscar de nuevo con los datos guardados
            return self._search_flights_with_data(session, phone)
        
        elif msg_lower in ['2', 'no', 'menu', 'cancelar']:
            session.reset()
            return self._send_response(phone, self.welcome_message, session)
        
        return self._send_response(phone, "❌ *Respuesta inválida*\n\n\n\n✅ *1* - Sí, buscar de nuevo\n❌ *2* - No, volver al menú\n\n", session)
    
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
cervo_bot = CervoBot()
