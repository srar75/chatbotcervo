"""
Gestión de sesiones y estado de conversación para el Chatbot Cervo
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConversationState:
    """Estado de una conversación individual"""
    
    def __init__(self, phone: str):
        self.phone = phone
        self.is_active = False  # El bot solo responde si está activo (usuario escribió "cervo bot")
        self.current_flow = None  # buscar_itinerario, cotizar, reservar, consultar_estatus
        self.step = 0
        self.data = {}
        self.context = self.data  # Alias para compatibilidad
        self.history = []
        self.last_activity = datetime.now()
        self.reservation_data = {
            'first_name': None,
            'last_name': None,
            'cedula': None,
            'phone': None,
            'passenger_type': None,
            'cedula_photo': False,
            'origin': None,
            'destination': None,
            'date': None,
            'selected_itinerary': None,
            'selected_fare': None
        }
    
    def update_activity(self):
        """Actualiza el timestamp de última actividad"""
        self.last_activity = datetime.now()
    
    def is_expired(self, timeout_minutes: int = 120):
        """Verifica si la sesión ha expirado (2 horas por defecto)"""
        return datetime.now() - self.last_activity > timedelta(minutes=timeout_minutes)
    
    def reset(self, full_reset: bool = False):
        """Reinicia el estado de la conversación"""
        if full_reset:
            self.is_active = False  # Desactivar el bot completamente
        self.current_flow = None
        self.step = 0
        self.data = {}
        self.reservation_data = {
            'first_name': None,
            'last_name': None,
            'cedula': None,
            'phone': None,
            'email': None,
            'passenger_type': None,
            'cedula_photo': False,
            'origin': None,
            'destination': None,
            'date': None,
            'selected_itinerary': None,
            'selected_fare': None
        }
        self.update_activity()
    
    def activate(self):
        """Activa el bot para esta sesión"""
        self.is_active = True
        self.reset()
        self.update_activity()
    
    def deactivate(self):
        """Desactiva el bot para esta sesión"""
        self.is_active = False
        self.reset(full_reset=True)
    
    def add_message(self, role: str, content: str, reasoning_details=None):
        """Agrega un mensaje al historial, opcionalmente con reasoning_details de Amazon Nova"""
        msg = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        # Agregar reasoning_details si está disponible (para Amazon Nova)
        if reasoning_details:
            msg['reasoning_details'] = reasoning_details
        
        self.history.append(msg)
        # Mantener solo los últimos 20 mensajes
        if len(self.history) > 20:
            self.history = self.history[-20:]
        self.update_activity()
    
    def get_conversation_history(self):
        """Obtiene el historial en formato para la API, incluyendo reasoning_details si existen"""
        result = []
        for msg in self.history:
            item = {'role': msg['role'], 'content': msg['content']}
            if msg.get('reasoning_details'):
                item['reasoning_details'] = msg['reasoning_details']
            result.append(item)
        return result
    
    def update_reservation_data(self, **kwargs):
        """Actualiza los datos de reservación"""
        for key, value in kwargs.items():
            if key in self.reservation_data and value:
                self.reservation_data[key] = value
        self.update_activity()
    
    def is_reservation_complete(self):
        """Verifica si tiene todos los datos necesarios para la reservación"""
        required = ['first_name', 'last_name', 'cedula', 'phone', 'passenger_type', 'origin', 'destination', 'date']
        return all(self.reservation_data.get(field) for field in required)
    
    def get_missing_reservation_fields(self):
        """Obtiene los campos faltantes para la reservación"""
        field_names = {
            'first_name': 'nombre',
            'last_name': 'apellido',
            'cedula': 'cédula',
            'phone': 'teléfono',
            'passenger_type': 'tipo de pasajero (niño, adulto o tercera edad)',
            'origin': 'ciudad de origen',
            'destination': 'ciudad de destino',
            'date': 'fecha del viaje',
            'cedula_photo': 'foto del anverso de la cédula'
        }
        
        missing = []
        for field, name in field_names.items():
            if not self.reservation_data.get(field):
                missing.append(name)
        return missing


class SessionManager:
    """Gestiona todas las sesiones de conversación"""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationState] = {}
    
    def get_session(self, phone: str) -> ConversationState:
        """Obtiene o crea una sesión para un número de teléfono"""
        phone = self._normalize_phone(phone)
        
        if phone not in self.sessions:
            self.sessions[phone] = ConversationState(phone)
            logger.info(f"Nueva sesion creada para {phone}")
        else:
            session = self.sessions[phone]
            if session.is_expired():
                logger.info(f"Sesion expirada para {phone}, desactivando")
                session.deactivate()  # Desactivar cuando expira
        
        return self.sessions[phone]
    
    def _normalize_phone(self, phone: str) -> str:
        """Normaliza el número de teléfono"""
        return phone.replace('+', '').replace(' ', '').replace('-', '')
    
    def clear_session(self, phone: str):
        """Limpia una sesión específica"""
        phone = self._normalize_phone(phone)
        if phone in self.sessions:
            del self.sessions[phone]
            logger.info(f"Sesión eliminada para {phone}")
    
    def cleanup_expired_sessions(self):
        """Limpia todas las sesiones expiradas"""
        expired = [phone for phone, session in self.sessions.items() if session.is_expired()]
        for phone in expired:
            del self.sessions[phone]
        if expired:
            logger.info(f"Limpiadas {len(expired)} sesiones expiradas")
    
    # Métodos de compatibilidad con código existente
    def get_or_create_session(self, phone: str) -> ConversationState:
        """Alias de get_session para compatibilidad"""
        return self.get_session(phone)
    
    def update_context(self, phone: str, key: str, value: Any):
        """Actualiza el contexto de una sesión"""
        session = self.get_session(phone)
        session.data[key] = value
        session.update_activity()



# Instancia global del gestor de sesiones
session_manager = SessionManager()
