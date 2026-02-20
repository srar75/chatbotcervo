
import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import logging
import time

# Add current directory to path
sys.path.append(os.getcwd())

class TestGeminiClientScenarios(unittest.TestCase):
    def setUp(self):
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Mock dependent services
        # NOTE: We patch 'gemini_agent_bot.flight_service' because 'flight_service' is an INSTANCE imported there.
        self.mock_wati_patcher = patch('gemini_agent_bot.wati_service')
        self.mock_flight_patcher = patch('gemini_agent_bot.flight_service')
        self.mock_kiu_patcher = patch('gemini_agent_bot.get_requisitos_pais')
        
        self.mock_wati = self.mock_wati_patcher.start()
        self.mock_flight_service = self.mock_flight_patcher.start()
        self.mock_get_requisitos = self.mock_kiu_patcher.start()

        from session_manager import session_manager
        self.session_manager = session_manager
        
        # Initialize Bot
        if not os.getenv('GEMINI_API_KEY'):
            os.environ['GEMINI_API_KEY'] = 'dummy_key_for_test'
            self.mock_genai_patcher = patch('gemini_agent_bot.genai')
            self.mock_genai = self.mock_genai_patcher.start()
            self.using_real_llm = False
            print("WARNING: No GEMINI_API_KEY found. Using MOCKED LLM.")
        else:
            self.using_real_llm = True
            print("Using REAL GEMINI API.")

        from gemini_agent_bot import GeminiAgentBot
        self.bot = GeminiAgentBot()

        # Capture WATI messages
        self.sent_messages = []
        
        def capture_message(phone, message):
            self.sent_messages.append({'phone': phone, 'message': message})
            return {'success': True}
            
        self.mock_wati.send_message.side_effect = capture_message
        self.mock_wati._send_single_message.side_effect = capture_message
        self.mock_wati.send_interactive_buttons.return_value = {'success': True}
        self.mock_wati.send_list_message.return_value = {'success': True}
        
        # Flight Service Mock
        self.mock_flight_service.search_flights.return_value = [
            {
                "flight_number": "9V123", "airline": "Venezolana", 
                "origin": "CCS", "destination": "MAD",
                "date": "2026-05-15", "departure_time": "12:00", "arrival_time": "20:00",
                "price": 500.00,
                "api_data": {"segments": [{"classes": {"Y": 5, "C": 2}, "id": "seg1"}]}
            },
             {
                "flight_number": "9V124", "airline": "Venezolana", 
                "origin": "MAD", "destination": "CCS",
                "date": "2026-05-30", "departure_time": "08:00", "arrival_time": "16:00",
                "price": 500.00,
                "api_data": {"segments": [{"classes": {"Y": 5, "C": 2}, "id": "seg2"}]}
            }
        ]
        
        self.mock_flight_service.get_all_class_prices.return_value = {
             "success": True,
             "classes_prices": {
                "Y": {"price": 500.00, "seats": 5},
                "C": {"price": 1200.00, "seats": 2}
            }
        }
        
        # Correctly mock create_booking on the instance mock
        self.mock_flight_service.create_booking.return_value = {
            "success": True, "pnr": "TESTPNR", "vid": "TESTVID",
            "message": "Reserva creada exitosamente"
        }
        
        self.mock_get_requisitos.return_value = "**Requisitos para Espana**:\n- Pasaporte vigente"

    def tearDown(self):
        self.mock_wati_patcher.stop()
        self.mock_flight_patcher.stop()
        self.mock_kiu_patcher.stop()
        if not self.using_real_llm:
            self.mock_genai_patcher.stop()

    def _get_last_response(self):
        if not self.sent_messages:
            return ""
        return self.sent_messages[-1]['message']

    def _simulate_user_message(self, phone, text):
        # Encode/decode to safe ASCII for printing
        safe_text = text.encode('ascii', 'ignore').decode('ascii')
        print(f"\nUser: {safe_text}")
        initial_len = len(self.sent_messages)
        self.bot.handle_message(phone, text)
        
        new_msgs = self.sent_messages[initial_len:]
        for msg in new_msgs:
            safe_msg = msg['message'][:200].replace(chr(10), ' ').encode('ascii', 'ignore').decode('ascii')
            print(f"Bot: {safe_msg}...") 
        
        if new_msgs:
            return new_msgs[-1]['message']
        return ""

    def test_scenario_1_requirements(self):
        phone = "584121111111"
        print("\n" + "="*50)
        print("TEST SCENARIO 1: REQUISITOS DE PAIS")
        print("="*50)
        self.session_manager.clear_session(phone)
        self._simulate_user_message(phone, "Cervo AI")
        resp = self._simulate_user_message(phone, "Requisitos para viajar a Espana")
        
        if self.using_real_llm:
            if "Espa" in resp or "Requisitos" in resp or "Pasaporte" in resp:
                print("PASSED: Requirements returned")
            else:
                safe_resp = resp[:100].encode('ascii', 'ignore').decode('ascii')
                print(f"FAILED: Requirements not returned properly. Got: {safe_resp}...")

    def test_scenario_2_one_way(self):
        phone = "584122222222"
        print("\n" + "="*50)
        print("TEST SCENARIO 2: RESERVA SOLO IDA")
        print("="*50)
        self.session_manager.clear_session(phone)
        self._simulate_user_message(phone, "Cervo AI")
        
        resp = self._simulate_user_message(phone, "Quiero un vuelo a Madrid desde Caracas para el 15 de mayo solo ida para 1 persona")
        
        # Loop until reservation
        for _ in range(30):
            if "RESERVA CREADA" in resp or "TESTPNR" in resp:
                print("PASSED: Reservation created")
                return
            
            lower_resp = resp.lower()
            answer = "Juan" # Default answer
            
            if "vuelo" in lower_resp and "?" in lower_resp and "numero" in lower_resp: answer = "El 1"
            elif "clase" in lower_resp and "?" in lower_resp: answer = "Clase Y"
            elif "confirmas" in lower_resp: answer = "Si"
            elif "foto" in lower_resp: answer = "manual"
            elif "nombre" in lower_resp: answer = "Juan"
            elif "apellido" in lower_resp: answer = "Perez"
            elif "nacionalidad" in lower_resp: answer = "Venezolano"
            elif "cedula" in lower_resp or "documento" in lower_resp: answer = "12345678"
            elif "telefono" in lower_resp: answer = "04121234567"
            elif "email" in lower_resp: answer = "juan@email.com"
            elif "sexo" in lower_resp: answer = "M"
            elif "direccion" in lower_resp: answer = "Av Principal"
            elif "ciudad" in lower_resp: answer = "Caracas"
            elif "estado" in lower_resp: answer = "Distrito Capital"
            elif "codigo postal" in lower_resp: answer = "1010"
            elif "que vuelo" in lower_resp: answer = "El 1" # Fallback selector
            
            # Prevent infinite loop on same question if logic fails
            if answer == "Juan" and "nombre" not in lower_resp:
                 # Try something else
                 pass

            resp = self._simulate_user_message(phone, answer)
            
        print("FAILED: Reservation not created in One Way Flow")

    def test_scenario_3_round_trip(self):
        phone = "584123333333"
        print("\n" + "="*50)
        print("TEST SCENARIO 3: RESERVA IDA Y VUELTA")
        print("="*50)
        self.session_manager.clear_session(phone)
        self._simulate_user_message(phone, "Cervo AI")
        
        resp = self._simulate_user_message(phone, "Vuelo ida y vuelta Caracas Madrid del 15 de mayo al 30 de mayo para 1 persona")
        
        flight_selections = 0
        
        for _ in range(40):
            if "RESERVA CREADA" in resp or "TESTPNR" in resp:
                print("PASSED: Round Trip Reservation created")
                return
                
            lower_resp = resp.lower()
            answer = "Si"
            
            if ("vuelo" in lower_resp or "disponibles" in lower_resp) and "?" in lower_resp: 
                 answer = "El 1"
                 flight_selections += 1
            elif "clase" in lower_resp: answer = "Clase Y"
            elif "confirmas" in lower_resp: answer = "Si"
            elif "foto" in lower_resp: answer = "manual"
            elif "nombre" in lower_resp: answer = "Maria"
            elif "apellido" in lower_resp: answer = "Gomez"
            elif "nacionalidad" in lower_resp: answer = "Venezolano"
            elif "cedula" in lower_resp or "documento" in lower_resp: answer = "11222333"
            elif "telefono" in lower_resp: answer = "04149998877"
            elif "email" in lower_resp: answer = "maria@email.com"
            elif "sexo" in lower_resp: answer = "F"
            elif "direccion" in lower_resp: answer = "Calle Real"
            elif "ciudad" in lower_resp: answer = "Valencia"
            elif "estado" in lower_resp: answer = "Carabobo"
            elif "codigo postal" in lower_resp: answer = "2001"
            elif "que vuelo" in lower_resp: answer = "El 1"

            resp = self._simulate_user_message(phone, answer)

        print("FAILED: Reservation not created in Round Trip Flow")

if __name__ == '__main__':
    unittest.main()
