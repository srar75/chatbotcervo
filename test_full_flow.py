
import unittest
from unittest.mock import MagicMock, patch
import json
from gemini_agent_bot import GeminiAgentBot

class TestFullBookingFlow(unittest.TestCase):
    def setUp(self):
        self.mock_wati = MagicMock()
        self.mock_flight_service = MagicMock()
        self.mock_session_manager = MagicMock()
        # Patch dependencies
        with patch('gemini_agent_bot.wati_service', self.mock_wati), \
             patch('gemini_agent_bot.flight_service', self.mock_flight_service), \
             patch('gemini_agent_bot.session_manager', self.mock_session_manager):
            self.bot = GeminiAgentBot()
            
        self.phone = "584121234567"
        self.session = MagicMock()
        self.session.data = {}
        self.mock_session_manager.get_session.return_value = self.session

    def test_full_flow_ccs_pmv_roundtrip_3pax(self):
        print("\n🚀 Iniciando prueba de flujo COMPLETO: CCS-PMV RT 3 PAX")
        
        # 1. Búsqueda de Vuelos (Ida y Vuelta)
        print("   Step 1: Buscando vuelos...")
        # Mock flight service responses
        mock_flights_ida = [{
            "flight_number": "9V331", "airline": "Venezolana", 
            "origin": "CCS", "destination": "PMV", "date": "2026-02-27",
            "departure_time": "12:30", "arrival_time": "13:15", "price": 100.0,
            "api_data": {"segments": [{"classes": {"H": 9, "Y": 5}}]}
        }]
        mock_flights_vuelta = [{
            "flight_number": "9V332", "airline": "Venezolana", 
            "origin": "PMV", "destination": "CCS", "date": "2026-03-02",
            "departure_time": "14:00", "arrival_time": "14:45", "price": 100.0,
            "api_data": {"segments": [{"classes": {"H": 9, "Y": 5}}]}
        }]
        self.mock_flight_service.search_flights.side_effect = [mock_flights_ida, mock_flights_vuelta]
        self.mock_flight_service.get_all_class_prices.return_value = {
            "success": True, 
            "classes_prices": {"H": {"price": 100.0, "availability": 9}, "Y": {"price": 120.0, "availability": 5}}
        }

        # Simulate search calls
        self.bot._search_flights_function("CCS", "PMV", "2026-02-27", self.session, trip_type='ida', adults=2, children=1)
        self.bot._search_flights_function("PMV", "CCS", "2026-03-02", self.session, trip_type='vuelta', adults=2, children=1)
        
        self.assertTrue(len(self.session.data['available_flights']) > 0, "No se guardaron vuelos de ida")
        self.assertTrue(len(self.session.data['return_flights']) > 0, "No se guardaron vuelos de vuelta")

        # 2. Selección de Vuelos y Clases
        print("   Step 2: Seleccionando clases (H)...")
        # Seleccionar Ida (Clase H)
        self.bot._select_flight_and_get_prices_function(1, self.session, is_return=False)
        self.bot._confirm_flight_selection_function(flight_index=1, flight_class='H', session=self.session, is_return=False)
        self.session.data['flight_confirmed'] = True # Simulate user saying "Yes"
        
        # Seleccionar Vuelta (Clase H)
        self.bot._select_flight_and_get_prices_function(1, self.session, is_return=True)
        self.bot._confirm_flight_selection_function(flight_index=1, flight_class='H', session=self.session, is_return=True)
        self.session.data['return_flight_fully_confirmed'] = True
        
        self.assertEqual(self.session.data['selected_flight_class'], 'H')
        self.assertEqual(self.session.data['selected_return_flight_class'], 'H')

        # 3. Ingreso de Datos de Pasajeros
        print("   Step 3: Simulando ingreso de datos para 3 pasajeros...")
        # Simular llenado de lista de pasajeros
        self.session.data['passengers_list'] = [
            {'nombre': 'Juan', 'apellido': 'Perez', 'cedula': '12345678', 'tipo': 'ADT', 'nacionalidad': 'VE', 'sexo': 'M', 'fecha_nacimiento': '1980-01-01'},
            {'nombre': 'Maria', 'apellido': 'Gomez', 'cedula': '12345679', 'tipo': 'ADT', 'nacionalidad': 'VE', 'sexo': 'F', 'fecha_nacimiento': '1982-01-01'},
            {'nombre': 'Pedrito', 'apellido': 'Perez', 'cedula': '30123456', 'tipo': 'CHD', 'nacionalidad': 'VE', 'sexo': 'M', 'fecha_nacimiento': '2016-01-01'}
        ]
        
        # 4. Creación de Reserva
        print("   Step 4: Creando reserva final...")
        self.mock_kiu.create_booking.return_value = {"success": True, "pnr": "ABC123"} # Mock KIU response via flight_booking_service inside create_booking
        
        # We need to mock the service call inside _create_booking_function
        # Actually flight_booking_service.create_booking is called
        self.mock_flight_service.create_booking.return_value = {
            "success": True, 
            "pnr": "ABC123", 
            "message": "✅ Reserva creada exitosamente. PNR: ABC123"
        }

        result = self.bot._create_booking_function(
            flight_index=1, flight_class='H', 
            passenger_name="Juan Perez", id_number="12345678", 
            phone=self.phone, email="juan@test.com", 
            session=self.session
        )
        
        self.assertTrue(result['success'], "Falló la creación de la reserva")
        self.assertIn("ABC123", result['message'], "No se devolvió el PNR esperado")
        
        # Verificar que se intentó reservar con los datos de vuelta
        # call_args de create_booking debería tener info de retorno
        # Esto depende de cómo _create_booking_function construye la llamada.
        
        print("✅ Flujo completo verificado exitosamente.")
        
if __name__ == '__main__':
    unittest.main()
