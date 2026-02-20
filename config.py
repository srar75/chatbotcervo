"""
Configuración del Chatbot Cervo
"""
import os
from dotenv import load_dotenv

# Forzar recarga del archivo .env
load_dotenv(override=True)

class Config:
    # WATI Configuration
    WATI_API_URL = os.getenv('WATI_API_URL', 'https://live-mt-server.wati.io')
    WATI_API_TOKEN = os.getenv('WATI_API_TOKEN', '')
    
    # KIU API Configuration (Sistema de Reservas de Vuelos)
    KIU_API_URL = os.getenv('KIU_API_URL', 'https://api.cervotravel.app/v1')
    KIU_API_TOKEN = os.getenv('KIU_API_TOKEN', '')
    
    # OpenRouter AI Configuration (Legacy - No usado)
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
    OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini')
    
    # Gemini Configuration (Modelo de IA principal)
    # gemini-3-flash-preview: Modelo con razonamiento avanzado, mejor para flujos de conversación
    # Ventajas: Reasoning avanzado, function calling mejorado, 1M tokens de contexto
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
    
    # Testing Configuration
    TESTING_MODE = os.getenv('TESTING_MODE', 'true').lower() == 'true'
    ALLOWED_PHONE = os.getenv('ALLOWED_PHONE', '').strip()
    
    # Flask Configuration
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    
    # Aeropuertos de Venezuela
    AEROPUERTOS_VENEZUELA = {
        'CCS': 'Aeropuerto Internacional Simón Bolívar (Maiquetía)',
        'MAR': 'Aeropuerto Internacional La Chinita (Maracaibo)',
        'VLN': 'Aeropuerto Internacional Arturo Michelena (Valencia)',
        'BLA': 'Aeropuerto Internacional José Antonio Anzoátegui (Barcelona)',
        'PMV': 'Aeropuerto Internacional Del Caribe (Porlamar)',
        'MRD': 'Aeropuerto Internacional Alberto Carnevali (Mérida)',
        'BRM': 'Aeropuerto Internacional Jacinto Lara (Barquisimeto)',
        'STD': 'Aeropuerto Nacional Mayor Buenaventura Vivas (Santo Domingo)',
        'PZO': 'Aeropuerto Internacional Manuel Piar (Puerto Ordaz)',
        'CUM': 'Aeropuerto Internacional Antonio José de Sucre (Cumaná)',
        'SFD': 'Aeropuerto Nacional San Fernando de Apure'
    }
    
    # Destinos internacionales populares desde Venezuela
    DESTINOS_INTERNACIONALES = {
        'MIA': 'Aeropuerto Internacional de Miami',
        'BOG': 'Aeropuerto Internacional El Dorado (Bogotá)',
        'PTY': 'Aeropuerto Internacional Tocumen (Panamá)',
        'LIM': 'Aeropuerto Internacional Jorge Chávez (Lima)',
        'MAD': 'Aeropuerto Adolfo Suárez Madrid-Barajas',
        'MDE': 'Aeropuerto Internacional José María Córdova (Medellín)',
        'SCL': 'Aeropuerto Internacional Arturo Merino Benítez (Santiago)',
        'GRU': 'Aeropuerto Internacional de São Paulo-Guarulhos',
        'MEX': 'Aeropuerto Internacional Benito Juárez (Ciudad de México)',
        'CUN': 'Aeropuerto Internacional de Cancún'
    }
