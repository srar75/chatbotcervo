# 🦌 CERVO AI - Chatbot de Reservaciones de Vuelos

Bot conversacional inteligente para búsqueda y reservación de vuelos usando Gemini AI.

## 🚀 Inicio Rápido

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Configurar variables de entorno
Edita el archivo `.env` con tus credenciales:
- `GEMINI_API_KEY`: Tu API key de Google Gemini
- `WATI_API_TOKEN`: Token de WATI para WhatsApp
- `KIU_API_TOKEN`: Token de la API de reservaciones

### 3. Iniciar el servidor
```bash
python app.py
```

El servidor estará disponible en: `http://localhost:5000`

## 📱 Uso del Bot

### Activar el bot
Envía el mensaje: **`cervo ai`**

### Funcionalidades

1. **Búsqueda de vuelos**
   - "Quiero volar de Caracas a Margarita el 15 de marzo"
   - "Busca vuelos de CCS a MIA para mañana"
   - "Necesito ir a Maracaibo ida y vuelta"

2. **Consulta de reservas**
   - Envía el código PNR (6 caracteres): `ABC123`

3. **Requisitos de viaje**
   - "Qué necesito para viajar a Cuba"
   - "Requisitos para viajar a México"

### Desactivar el bot
Envía: **`salir`**

## 🛠️ Archivos Principales

- `app.py` - Servidor Flask y webhook de WATI
- `gemini_agent_bot.py` - Bot conversacional con IA
- `flight_booking_service.py` - Servicio de búsqueda y reservas
- `kiu_service.py` - Integración con API de KIU
- `wati_service.py` - Integración con WhatsApp (WATI)
- `session_manager.py` - Gestión de sesiones de usuario
- `requisitos_migratorios.py` - Base de datos de requisitos por país
- `config.py` - Configuración general

## 🌐 Endpoints

- `GET /` - Página de inicio
- `GET /health` - Health check
- `POST /webhook` - Webhook para mensajes de WATI
- `GET /test` - Interfaz de prueba

## 📝 Notas

- El bot usa **Gemini 3 Flash** para conversación natural
- Soporta búsquedas de vuelos nacionales e internacionales
- Maneja reservas con múltiples pasajeros
- Detecta automáticamente códigos PNR

## 🔧 Modo Testing

Para probar localmente sin WATI:
1. Abre `http://localhost:5000/test` en tu navegador
2. Escribe "cervo ai" para activar el bot
3. Comienza a conversar

---

**Desarrollado para Cervo Travel** 🦌✈️
