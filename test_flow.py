"""
Script de prueba completo para verificar el flujo de búsqueda, clases y reservas
"""
import logging
from datetime import datetime, timedelta
from gemini_agent_bot import gemini_agent_bot
from session_manager import session_manager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_complete_flow():
    """Prueba el flujo completo: búsqueda -> selección -> clases -> reserva"""
    
    phone = "584121234567"
    print("\n" + "="*70)
    print("PRUEBA COMPLETA DEL FLUJO DE RESERVAS")
    print("="*70)
    
    # Limpiar sesión
    session = session_manager.get_session(phone)
    session.clear()
    
    # 1. ACTIVAR BOT
    print("\n[1] Activando bot...")
    result = gemini_agent_bot.handle_message(phone, "cervo ai")
    print(f"✓ Bot activado")
    
    # 2. BUSCAR VUELOS
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"\n[2] Buscando vuelos CCS->PMV para {tomorrow}...")
    result = gemini_agent_bot.handle_message(phone, f"Quiero volar de Caracas a Margarita el {tomorrow} ida para 1 persona")
    
    # Verificar que se guardaron vuelos
    session = session_manager.get_session(phone)
    flights = session.data.get('available_flights', [])
    print(f"✓ Vuelos encontrados: {len(flights)}")
    
    if not flights:
        print("❌ ERROR: No se encontraron vuelos")
        return False
    
    # Mostrar primer vuelo
    first_flight = flights[0]
    print(f"   Primer vuelo: {first_flight.get('airline_name')} {first_flight.get('flight_number')}")
    print(f"   Precio: ${first_flight.get('price')}")
    
    # 3. SELECCIONAR VUELO
    print(f"\n[3] Seleccionando vuelo 1...")
    result = gemini_agent_bot.handle_message(phone, "1")
    
    # Verificar que se guardó el índice
    selected_index = session.data.get('selected_flight_index')
    print(f"✓ Vuelo seleccionado: índice {selected_index}")
    
    if not selected_index:
        print("❌ ERROR: No se guardó el índice del vuelo seleccionado")
        return False
    
    # 4. CONFIRMAR VUELO
    print(f"\n[4] Confirmando vuelo...")
    result = gemini_agent_bot.handle_message(phone, "si")
    
    # Verificar que se obtuvieron precios de clases
    classes_prices = session.data.get('flight_classes_prices', {})
    print(f"✓ Clases disponibles: {len(classes_prices)}")
    
    if not classes_prices:
        print("❌ ERROR: No se obtuvieron precios de clases")
        return False
    
    # Mostrar clases
    for class_code, class_data in list(classes_prices.items())[:3]:
        print(f"   Clase {class_code}: ${class_data.get('price')} ({class_data.get('availability')} asientos)")
    
    # 5. SELECCIONAR CLASE
    first_class = list(classes_prices.keys())[0]
    print(f"\n[5] Seleccionando clase {first_class}...")
    result = gemini_agent_bot.handle_message(phone, first_class)
    
    # Verificar que se guardó la clase
    selected_class = session.data.get('selected_flight_class')
    print(f"✓ Clase seleccionada: {selected_class}")
    
    if not selected_class:
        print("❌ ERROR: No se guardó la clase seleccionada")
        return False
    
    # 6. CONFIRMAR SELECCIÓN
    print(f"\n[6] Confirmando selección...")
    result = gemini_agent_bot.handle_message(phone, "si")
    
    # Verificar que está esperando datos
    awaiting = session.data.get('awaiting_flight_confirmation')
    print(f"✓ Esperando datos de pasajero: {awaiting}")
    
    if not awaiting:
        print("❌ ERROR: No está esperando datos de pasajero")
        return False
    
    # 7. PROPORCIONAR DATOS (MANUAL)
    print(f"\n[7] Proporcionando datos de pasajero...")
    
    # Nombre
    result = gemini_agent_bot.handle_message(phone, "manual")
    result = gemini_agent_bot.handle_message(phone, "JUAN")
    
    # Apellido
    result = gemini_agent_bot.handle_message(phone, "PEREZ")
    
    # Nacionalidad
    result = gemini_agent_bot.handle_message(phone, "venezolano")
    
    # Cédula
    result = gemini_agent_bot.handle_message(phone, "12345678")
    
    # Sexo
    result = gemini_agent_bot.handle_message(phone, "M")
    
    # Dirección
    result = gemini_agent_bot.handle_message(phone, "Av Principal, Caracas")
    
    # Teléfono
    result = gemini_agent_bot.handle_message(phone, "04121234567")
    
    # Email (esto debería crear la reserva)
    print(f"\n[8] Creando reserva...")
    result = gemini_agent_bot.handle_message(phone, "test@email.com")
    
    print("\n" + "="*70)
    print("RESUMEN DE LA PRUEBA")
    print("="*70)
    
    # Verificar estado final
    session = session_manager.get_session(phone)
    
    checks = {
        "Vuelos encontrados": len(session.data.get('available_flights', [])) > 0,
        "Vuelo seleccionado": session.data.get('selected_flight_index') is not None,
        "Clase seleccionada": session.data.get('selected_flight_class') is not None,
        "Precios obtenidos": len(session.data.get('flight_classes_prices', {})) > 0,
        "Datos de pasajero": len(session.data.get('passengers_list', [])) > 0
    }
    
    for check, passed in checks.items():
        status = "✓" if passed else "❌"
        print(f"{status} {check}")
    
    all_passed = all(checks.values())
    
    if all_passed:
        print("\n✅ TODAS LAS PRUEBAS PASARON")
    else:
        print("\n❌ ALGUNAS PRUEBAS FALLARON")
    
    return all_passed

if __name__ == "__main__":
    try:
        success = test_complete_flow()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
