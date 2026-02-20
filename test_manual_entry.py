
import unittest
from unittest.mock import MagicMock, patch
from gemini_agent_bot import GeminiAgentBot

class TestManualEntryFlow(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_wati = MagicMock()
        self.mock_flight_service = MagicMock()
        self.mock_session_manager = MagicMock()
        
        # Patch them
        self.patches = [
            patch('gemini_agent_bot.wati_service', self.mock_wati),
            patch('gemini_agent_bot.flight_service', self.mock_flight_service),
            patch('gemini_agent_bot.session_manager', self.mock_session_manager)
        ]
        for p in self.patches:
            p.start()
            
        # Instantiate bot
        # We need to set GEMINI_API_KEY env var or mock os.getenv if not present, but let's assume it's handled or we can patch os.environ
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'fake_key'}):
             self.bot = GeminiAgentBot()
             # Mock the client to avoid real API calls
             self.bot.client = MagicMock()

        self.phone = "584121234567"
        self.session = MagicMock()
        self.session.data = {}
        self.session.is_active = True
        self.session.data['mode'] = 'ai'
        self.mock_session_manager.get_session.return_value = self.session

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_manual_entry_flow(self):
        print("\n🚀 Testing Manual Passenger Entry Flow")
        
        # Setup initial state: waiting after flight confirmation
        self.session.data['awaiting_flight_confirmation'] = True
        self.session.data['waiting_for_field'] = None
        self.session.data['num_passengers'] = 1
        self.session.data['passengers_list'] = []

        # 1. User says "manual"
        print("1. Sending 'manual'")
        self.bot.handle_message(self.phone, "manual")
        # Check response: Should ask for Name
        # We can inspect what wati_service.send_message was called with
        args, _ = self.mock_wati.send_message.call_args
        print(f"   Response: {args[1]}")
        self.assertIn("Nombre", args[1])
        self.assertEqual(self.session.data['waiting_for_field'], 'nombre')

        # 2. User sends Name
        print("2. Sending Name 'Juan'")
        self.bot.handle_message(self.phone, "Juan")
        args, _ = self.mock_wati.send_message.call_args
        print(f"   Response: {args[1]}")
        self.assertIn("APELLIDO", args[1]) # Expecting prompt for Last Name
        self.assertEqual(self.session.data['extracted_data']['nombre'], 'JUAN')
        self.assertEqual(self.session.data['waiting_for_field'], 'apellido')

        # 3. User sends Last Name
        print("3. Sending Last Name 'Perez'")
        self.bot.handle_message(self.phone, "Perez")
        args, _ = self.mock_wati.send_message.call_args
        print(f"   Response: {args[1]}")
        self.assertIn("VENEZOLANO", args[1]) # Expecting prompt for Nationality
        self.assertEqual(self.session.data['extracted_data']['apellido'], 'PEREZ')
        self.assertEqual(self.session.data['waiting_for_field'], 'nacionalidad')

        # 4. User sends Nationality
        print("4. Sending Nationality 'V'")
        self.bot.handle_message(self.phone, "V")
        args, _ = self.mock_wati.send_message.call_args
        print(f"   Response: {args[1]}")
        self.assertIn("CÉDULA", args[1]) 
        self.assertEqual(self.session.data['extracted_data']['nacionalidad'], 'VE')

        # 5. User sends ID
        print("5. Sending ID '12345678'")
        self.bot.handle_message(self.phone, "12345678")
        args, _ = self.mock_wati.send_message.call_args
        print(f"   Response: {args[1]}")
        self.assertIn("SEXO", args[1])

        # 6. User sends Sex
        print("6. Sending Sex 'M'")
        self.bot.handle_message(self.phone, "M")
        args, _ = self.mock_wati.send_message.call_args
        print(f"   Response: {args[1]}")
        self.assertIn("DIRECCIÓN", args[1])

        # 7. User sends Address
        print("7. Sending Address 'Av Principal'")
        self.bot.handle_message(self.phone, "Av Principal")
        args, _ = self.mock_wati.send_message.call_args
        print(f"   Response: {args[1]}")
        self.assertIn("CIUDAD", args[1])

        # 8. City
        print("8. Sending City 'Caracas'")
        self.bot.handle_message(self.phone, "Caracas")
        args, _ = self.mock_wati.send_message.call_args
        self.assertIn("ESTADO", args[1])

        # 9. State
        print("9. Sending State 'Distrito Capital'")
        self.bot.handle_message(self.phone, "Distrito Capital")
        args, _ = self.mock_wati.send_message.call_args
        self.assertIn("CÓDIGO POSTAL", args[1])

        # 10. Zip
        print("10. Sending Zip '1010'")
        self.bot.handle_message(self.phone, "1010")
        args, _ = self.mock_wati.send_message.call_args
        self.assertIn("TELÉFONO", args[1])

        # 11. Phone
        print("11. Sending Phone '04121234567'")
        self.bot.handle_message(self.phone, "04121234567")
        args, _ = self.mock_wati.send_message.call_args
        self.assertIn("correo", args[1].lower()) # Email

        # 12. Email
        print("12. Sending Email 'juan@test.com'")
        # Note: In the code, if fecha_nacimiento is missing, it asks for it.
        # But if it was extracted from image (not here), it might calculate type.
        # Here we expect it to ask for Birth Date.
        self.bot.handle_message(self.phone, "juan@test.com")
        args, _ = self.mock_wati.send_message.call_args
        print(f"   Response: {args[1]}")
        self.assertIn("NACIMIENTO", args[1])

        # 13. Birth Date
        print("13. Sending DOB '25/12/1990'")
        # Mock create_booking_function to avoid complex logic inside it failing
        self.bot._create_booking_function = MagicMock(return_value={'success': True, 'pnr': 'TEST1234', 'message': 'Success'})
        
        # Also need available_flights in session for success message logic
        self.session.data['available_flights'] = [{'flight_number': '123', 'price': 100}]
        self.session.data['selected_flight_index'] = 1
        
        self.bot.handle_message(self.phone, "25/12/1990")
        
        # Should finish passenger 1
        # Since num_passengers = 1, it should proceed to create booking
        args, _ = self.mock_wati.send_message.call_args
        print(f"   Final Response: {args[1]}")
        self.assertIn("RESERVA CREADA", args[1])
        
        # Verify passenger was added
        self.assertEqual(len(self.session.data['passengers_list']), 1)
        pax = self.session.data['passengers_list'][0]
        self.assertEqual(pax['nombre'], 'JUAN')
        self.assertEqual(pax['apellido'], 'PEREZ')
        self.assertEqual(pax['fecha_nacimiento'], '1990-12-25')
        self.assertEqual(pax['tipo'], 'ADT') # Calculated from 1990

if __name__ == '__main__':
    unittest.main()
