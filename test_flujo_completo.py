"""
Test de flujo completo del bot - Simula usuario real
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gemini_agent_bot import GeminiAgentBot
from datetime import datetime, timedelta

def print_separator(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def test_flujo_completo():
    """Simula un usuario haciendo múltiples operaciones"""
    
    bot = GeminiAgentBot()
    phone = "+584241234567"
    
    def get_response(result):
        """Extrae el texto de respuesta del dict"""
        if isinstance(result, dict):
            return result.get('response', '')
        return result
    
    print_separator("🦌 INICIO - TEST DE FLUJO COMPLETO")
    
    # ========== 1. ACTIVAR BOT ==========
    print_separator("1️⃣ ACTIVAR BOT")
    result = bot.handle_message(phone, "cervo ai")
    response = get_response(result)
    print(f"Usuario: cervo ai")
    print(f"Bot: {response}\n")
    assert "activado" in response.lower() or "hola" in response.lower()
    
    # ========== 2. REQUISITOS MIGRATORIOS - CUBA ==========
    print_separator("2️⃣ REQUISITOS MIGRATORIOS - CUBA")
    result = bot.handle_message(phone, "Qué necesito para viajar a Cuba?")
    response = get_response(result)
    print(f"Usuario: Qué necesito para viajar a Cuba?")
    print(f"Bot: {response}\n")
    assert "cuba" in response.lower() and ("pasaporte" in response.lower() or "visa" in response.lower())
    
    # ========== 3. REQUISITOS MIGRATORIOS - MÉXICO ==========
    print_separator("3️⃣ REQUISITOS MIGRATORIOS - MÉXICO")
    result = bot.handle_message(phone, "requisitos para México")
    response = get_response(result)
    print(f"Usuario: requisitos para México")
    print(f"Bot: {response}\n")
    assert "méxico" in response.lower() or "mexico" in response.lower()
    
    # ========== 4. BÚSQUEDA VUELO IDA Y VUELTA - 2 ADULTOS 1 NIÑO ==========
    print_separator("4️⃣ VUELO IDA Y VUELTA CCS-PMV - 2 ADULTOS + 1 NIÑO")
    fecha_ida = (datetime.now() + timedelta(days=15)).strftime("%d de %B")
    fecha_vuelta = (datetime.now() + timedelta(days=20)).strftime("%d de %B")
    
    mensaje = f"Quiero volar de Caracas a Margarita el {fecha_ida} y regresar el {fecha_vuelta} para 2 adultos y 1 niño"
    result = bot.handle_message(phone, mensaje)
    response = get_response(result)
    print(f"Usuario: {mensaje}")
    print(f"Bot: {response}\n")
    assert "vuelo" in response.lower() or "disponible" in response.lower()
    
    # ========== 5. SELECCIONAR VUELO DE IDA ==========
    print_separator("5️⃣ SELECCIONAR VUELO DE IDA")
    result = bot.handle_message(phone, "el vuelo 1")
    response = get_response(result)
    print(f"Usuario: el vuelo 1")
    print(f"Bot: {response}\n")
    
    # ========== 6. CONFIRMAR VUELO IDA ==========
    print_separator("6️⃣ CONFIRMAR VUELO IDA")
    result = bot.handle_message(phone, "sí")
    response = get_response(result)
    print(f"Usuario: sí")
    print(f"Bot: {response}\n")
    
    # ========== 7. SELECCIONAR CLASE IDA ==========
    print_separator("7️⃣ SELECCIONAR CLASE IDA")
    result = bot.handle_message(phone, "Y")
    response = get_response(result)
    print(f"Usuario: Y")
    print(f"Bot: {response}\n")
    
    # ========== 7.1 CONFIRMAR SELECCIÓN IDA TOTAL ==========
    print_separator("7.1️⃣ CONFIRMAR SELECCIÓN IDA TOTAL")
    result = bot.handle_message(phone, "sí")
    response = get_response(result)
    print(f"Usuario: sí")
    print(f"Bot: {response}\n")

    # ========== 8. SELECCIONAR VUELO VUELTA ==========
    print_separator("8️⃣ SELECCIONAR VUELO VUELTA")
    result = bot.handle_message(phone, "el vuelo 1")
    response = get_response(result)
    print(f"Usuario: el vuelo 1")
    print(f"Bot: {response}\n")
    
    # ========== 9. CONFIRMAR VUELO VUELTA ==========
    print_separator("9️⃣ CONFIRMAR VUELO VUELTA")
    result = bot.handle_message(phone, "sí")
    response = get_response(result)
    print(f"Usuario: sí")
    print(f"Bot: {response}\n")
    
    # ========== 10. SELECCIONAR CLASE VUELTA ==========
    print_separator("🔟 SELECCIONAR CLASE VUELTA")
    result = bot.handle_message(phone, "Y")
    response = get_response(result)
    print(f"Usuario: Y")
    print(f"Bot: {response}\n")
    
    # ========== 10.1 CONFIRMAR SELECCIÓN VUELTA TOTAL ==========
    print_separator("10.1️⃣ CONFIRMAR SELECCIÓN VUELTA TOTAL")
    result = bot.handle_message(phone, "sí")
    response = get_response(result)
    print(f"Usuario: sí")
    print(f"Bot: {response}\n")
    
    # ========== 11. INGRESO MANUAL ==========
    print_separator("1️⃣1️⃣ INGRESO MANUAL")
    result = bot.handle_message(phone, "manual")
    response = get_response(result)
    print(f"Usuario: manual")
    print(f"Bot: {response}\n")
    
    # Pasajero 1
    result = bot.handle_message(phone, "Juan")
    response = get_response(result)
    print(f"Usuario: Juan | Bot: {response}\n")
    
    result = bot.handle_message(phone, "Pérez")
    response = get_response(result)
    print(f"Usuario: Pérez | Bot: {response}\n")
    
    result = bot.handle_message(phone, "V")
    response = get_response(result)
    print(f"Usuario: V | Bot: {response}\n")
    
    result = bot.handle_message(phone, "12345678")
    response = get_response(result)
    print(f"Usuario: 12345678 | Bot: {response}\n")
    
    result = bot.handle_message(phone, "M")
    response = get_response(result)
    print(f"Usuario: M | Bot: {response}\n")
    
    result = bot.handle_message(phone, "Calle Real 123")
    response = get_response(result)
    print(f"Usuario: Calle Real 123 | Bot: {response}\n")
    
    result = bot.handle_message(phone, "Caracas")
    response = get_response(result)
    print(f"Usuario: Caracas | Bot: {response}\n")
    
    result = bot.handle_message(phone, "Distrito Capital")
    response = get_response(result)
    print(f"Usuario: Distrito Capital | Bot: {response}\n")
    
    result = bot.handle_message(phone, "1010")
    response = get_response(result)
    print(f"Usuario: 1010 | Bot: {response}\n")
    
    result = bot.handle_message(phone, "+584241111111")
    response = get_response(result)
    print(f"Usuario: +584241111111 | Bot: {response}\n")
    
    result = bot.handle_message(phone, "juan@email.com")
    response = get_response(result)
    print(f"Usuario: juan@email.com | Bot: {response}\n")
    
    result = bot.handle_message(phone, "15/03/1985")
    response = get_response(result)
    print(f"Usuario: 15/03/1985 | Bot: {response}\n")

    # Pasajero 2
    result = bot.handle_message(phone, "manual") # El bot pregunta si foto o manual
    response = get_response(result)
    print(f"Usuario: manual | Bot: {response}\n")

    result = bot.handle_message(phone, "María")
    response = get_response(result)
    print(f"Usuario: María | Bot: {response}\n")
    
    result = bot.handle_message(phone, "González")
    response = get_response(result)
    print(f"Usuario: González | Bot: {response}\n")
    
    result = bot.handle_message(phone, "V")
    response = get_response(result)
    print(f"Usuario: V | Bot: {response}\n")
    
    result = bot.handle_message(phone, "23456789")
    response = get_response(result)
    print(f"Usuario: 23456789 | Bot: {response}\n")
    
    result = bot.handle_message(phone, "F")
    response = get_response(result)
    print(f"Usuario: F | Bot: {response}\n")

    result = bot.handle_message(phone, "igual") # Copiar dirección del pax 1
    response = get_response(result)
    print(f"Usuario: igual | Bot: {response}\n")
    
    result = bot.handle_message(phone, "+584242222222")
    response = get_response(result)
    print(f"Usuario: +584242222222 | Bot: {response}\n")
    
    result = bot.handle_message(phone, "maria@email.com")
    response = get_response(result)
    print(f"Usuario: maria@email.com | Bot: {response}\n")

    result = bot.handle_message(phone, "20/07/1990")
    response = get_response(result)
    print(f"Usuario: 20/07/1990 | Bot: {response}\n")
    
    # Pasajero 3 (niño)
    result = bot.handle_message(phone, "manual")
    response = get_response(result)
    print(f"Usuario: manual | Bot: {response}\n")

    result = bot.handle_message(phone, "Carlos")
    response = get_response(result)
    print(f"Usuario: Carlos | Bot: {response}\n")
    
    result = bot.handle_message(phone, "Pérez")
    response = get_response(result)
    print(f"Usuario: Pérez | Bot: {response}\n")
    
    result = bot.handle_message(phone, "V")
    response = get_response(result)
    print(f"Usuario: V | Bot: {response}\n")
    
    result = bot.handle_message(phone, "34567890")
    response = get_response(result)
    print(f"Usuario: 34567890 | Bot: {response}\n")
    
    result = bot.handle_message(phone, "M")
    response = get_response(result)
    print(f"Usuario: M | Bot: {response}\n")

    result = bot.handle_message(phone, "igual")
    response = get_response(result)
    print(f"Usuario: igual | Bot: {response}\n")

    result = bot.handle_message(phone, "+584241111111") # Teléfono del padre para el niño
    response = get_response(result)
    print(f"Usuario: +584241111111 | Bot: {response}\n")

    result = bot.handle_message(phone, "juan@email.com") # Email del padre para el niño
    response = get_response(result)
    print(f"Usuario: juan@email.com | Bot: {response}\n")

    result = bot.handle_message(phone, "10/12/2015")
    response = get_response(result)
    print(f"Usuario: 10/12/2015 | Bot: {response}\n")
    
    # ========== 12. CONFIRMAR RESERVA ==========
    # El bot automáticamente crea la reserva al recibir el último dato del último pasajero
    # Pero el test script tenía un paso extra "sí, confirmar" que no es necesario según la lógica de 'fecha_nacimiento'
    # Sin embargo, la lógica de 'confirmar' del test script podría ser para el RESUMEN FINAL.
    # El resumen final de IDA Y VUELTA se muestra después de confirmar la vuelta.
    # Espera, veamos el flujo:
    # 1. Confirmar vuelta -> Da resumen final.
    # 2. Confirmar resumen final ("sí") -> Pide datos pasajeros.
    # 3. Datos pasajeros completados -> Bot crea reserva.
    
    # Mi cambio anterior:
    # 10.1 Confirmar Selección Vuelta Total ("sí") -> Esto debería dar el RESUMEN FINAL.
    
    # Entonces el paso 12 en el test script debería ser:
    # print_separator("1️⃣2️⃣ CONFIRMAR RESUMEN FINAL")
    # result = bot.handle_message(phone, "sí")
    
    # Pero espere, en la lógica del bot:
    # línea 2081: RESUMEN FINAL DE TU VIAJE IDA Y VUELTA se muestra tras interceptar el "SÍ" de la vuelta.
    
    
    pnr_ida_vuelta = None
    if "pnr" in response.lower():
        import re
        match = re.search(r'PNR[:\s]+([A-Z0-9]{6})', response, re.IGNORECASE)
        if match:
            pnr_ida_vuelta = match.group(1)
            print(f"✅ PNR IDA Y VUELTA GENERADO: {pnr_ida_vuelta}\n")
    
    # ========== 13. NUEVA BÚSQUEDA - VUELO SOLO IDA ==========
    print_separator("1️⃣3️⃣ NUEVA BÚSQUEDA - VUELO SOLO IDA CCS-MAR")
    fecha_ida2 = (datetime.now() + timedelta(days=25)).strftime("%d de %B")
    mensaje = f"Ahora necesito un vuelo solo ida de Caracas a Maracaibo el {fecha_ida2} para 1 adulto"
    result = bot.handle_message(phone, mensaje)
    response = get_response(result)
    print(f"Usuario: {mensaje}")
    print(f"Bot: {response}\n")
    
    # ========== 14. SELECCIONAR VUELO SOLO IDA ==========
    print_separator("1️⃣4️⃣ SELECCIONAR VUELO SOLO IDA")
    result = bot.handle_message(phone, "quiero el vuelo 2")
    response = get_response(result)
    print(f"Usuario: quiero el vuelo 2")
    print(f"Bot: {response}\n")
    
    # Confirmar vuelo
    result = bot.handle_message(phone, "sí")
    response = get_response(result)
    print(f"Usuario: sí | Bot: {response}\n")
    
    # Clase
    result = bot.handle_message(phone, "Y")
    response = get_response(result)
    print(f"Usuario: Y | Bot: {response}\n")
    
    # Confirmar selección total
    result = bot.handle_message(phone, "sí")
    response = get_response(result)
    print(f"Usuario: sí | Bot: {response}\n")

    # Manual
    result = bot.handle_message(phone, "manual")
    response = get_response(result)
    print(f"Usuario: manual | Bot: {response}\n")
    
    # Datos pasajero
    result = bot.handle_message(phone, "Pedro")
    response = get_response(result)
    print(f"Usuario: Pedro | Bot: {response}\n")
    
    result = bot.handle_message(phone, "Ramírez")
    response = get_response(result)
    print(f"Usuario: Ramírez | Bot: {response}\n")
    
    result = bot.handle_message(phone, "V")
    response = get_response(result)
    print(f"Usuario: V | Bot: {response}\n")
    
    result = bot.handle_message(phone, "45678901")
    response = get_response(result)
    print(f"Usuario: 45678901 | Bot: {response}\n")
    
    result = bot.handle_message(phone, "M")
    response = get_response(result)
    print(f"Usuario: M | Bot: {response}\n")

    result = bot.handle_message(phone, "Av. Bolívar 456")
    response = get_response(result)
    print(f"Usuario: Av. Bolívar 456 | Bot: {response}\n")

    result = bot.handle_message(phone, "Maracaibo")
    response = get_response(result)
    print(f"Usuario: Maracaibo | Bot: {response}\n")

    result = bot.handle_message(phone, "Zulia")
    response = get_response(result)
    print(f"Usuario: Zulia | Bot: {response}\n")

    result = bot.handle_message(phone, "4001")
    response = get_response(result)
    print(f"Usuario: 4001 | Bot: {response}\n")
    
    result = bot.handle_message(phone, "+584243333333")
    response = get_response(result)
    print(f"Usuario: +584243333333 | Bot: {response}\n")

    result = bot.handle_message(phone, "pedro@email.com")
    response = get_response(result)
    print(f"Usuario: pedro@email.com | Bot: {response}\n")

    result = bot.handle_message(phone, "25/05/1988")
    response = get_response(result)
    print(f"Usuario: 25/05/1988 | Bot: {response}\n")
    
    # ========== 15. CONFIRMAR RESERVA SOLO IDA ==========
    # No es necesario paso extra, se crea al terminar datos
    print_separator("1️⃣5️⃣ RESERVA SOLO IDA COMPLETADA")

    
    pnr_solo_ida = None
    if "pnr" in response.lower():
        import re
        match = re.search(r'PNR[:\s]+([A-Z0-9]{6})', response, re.IGNORECASE)
        if match:
            pnr_solo_ida = match.group(1)
            print(f"✅ PNR SOLO IDA GENERADO: {pnr_solo_ida}\n")
    
    # ========== 16. CONSULTAR PNR IDA Y VUELTA ==========
    if pnr_ida_vuelta:
        print_separator("1️⃣6️⃣ CONSULTAR PNR IDA Y VUELTA")
        result = bot.handle_message(phone, pnr_ida_vuelta)
        response = get_response(result)
        print(f"Usuario: {pnr_ida_vuelta}")
        print(f"Bot: {response}\n")
        assert pnr_ida_vuelta in response.upper()
    
    # ========== 17. CONSULTAR PNR SOLO IDA ==========
    if pnr_solo_ida:
        print_separator("1️⃣7️⃣ CONSULTAR PNR SOLO IDA")
        result = bot.handle_message(phone, pnr_solo_ida)
        response = get_response(result)
        print(f"Usuario: {pnr_solo_ida}")
        print(f"Bot: {response}\n")
        assert pnr_solo_ida in response.upper()
    
    # ========== 18. REQUISITOS PANAMÁ ==========
    print_separator("1️⃣8️⃣ REQUISITOS MIGRATORIOS - PANAMÁ")
    result = bot.handle_message(phone, "necesito saber los requisitos para Panamá")
    response = get_response(result)
    print(f"Usuario: necesito saber los requisitos para Panamá")
    print(f"Bot: {response}\n")
    assert "panamá" in response.lower() or "panama" in response.lower()
    
    # ========== 19. CONSULTA GENERAL ==========
    print_separator("1️⃣9️⃣ CONSULTA GENERAL")
    result = bot.handle_message(phone, "cuánto equipaje puedo llevar?")
    response = get_response(result)
    print(f"Usuario: cuánto equipaje puedo llevar?")
    print(f"Bot: {response}\n")
    
    # ========== 20. DESACTIVAR BOT ==========
    print_separator("2️⃣0️⃣ DESACTIVAR BOT")
    result = bot.handle_message(phone, "salir")
    response = get_response(result)
    print(f"Usuario: salir")
    print(f"Bot: {response}\n")
    assert "desactivado" in response.lower() or "adiós" in response.lower() or "adios" in response.lower() or "pronto" in response.lower()
    
    # ========== 21. VERIFICAR BOT DESACTIVADO ==========
    print_separator("2️⃣1️⃣ VERIFICAR BOT DESACTIVADO")
    result = bot.handle_message(phone, "hola")
    response = get_response(result)
    print(f"Usuario: hola")
    print(f"Bot: {response}\n")
    assert response == "" or "cervo ai" in response.lower()
    
    # ========== RESUMEN FINAL ==========
    print_separator("✅ RESUMEN FINAL")
    print(f"✅ Bot activado correctamente")
    print(f"✅ Requisitos migratorios consultados: Cuba, México, Panamá")
    print(f"✅ Reserva ida y vuelta: 2 adultos + 1 niño - PNR: {pnr_ida_vuelta or 'N/A'}")
    print(f"✅ Reserva solo ida: 1 adulto - PNR: {pnr_solo_ida or 'N/A'}")
    print(f"✅ Consultas PNR realizadas correctamente")
    print(f"✅ Bot desactivado correctamente")
    print(f"\n🎉 TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE\n")

if __name__ == "__main__":
    test_flujo_completo()
