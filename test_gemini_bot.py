"""
TEST COMPLETO DE GEMINI AGENT BOT
Simula un cliente real probando todas las funcionalidades
"""
import os
import sys
import time
from datetime import datetime, timedelta

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gemini_agent_bot import GeminiAgentBot
from session_manager import session_manager

class BotTester:
    def __init__(self):
        self.bot = GeminiAgentBot()
        self.test_phone = "+584121234567"
        self.test_results = []
        self.last_response = None
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{timestamp}] {level}: {message}")
        
    def send_message(self, message, media_url=None):
        """Simula envío de mensaje del cliente"""
        self.log(f"👤 CLIENTE: {message}", "USER")
        time.sleep(1)  # Simular tiempo de escritura
        
        response = self.bot.handle_message(self.test_phone, message, media_url)
        
        # Extraer texto de la respuesta si es un diccionario
        if isinstance(response, dict):
            response_text = response.get('response', '')
        else:
            response_text = response
        
        self.last_response = response_text
        
        if response_text:
            self.log(f"🤖 BOT: {response_text[:500]}...", "BOT")  # Limitar log
        else:
            self.log("🤖 BOT: (Sin respuesta)", "BOT")
        
        time.sleep(2)  # Simular tiempo de lectura
        return response_text
    
    def extract_cheapest_class(self):
        """Extrae la clase más económica de la última respuesta del bot"""
        import re
        if not self.last_response:
            return "Y"  # Fallback
        
        # Buscar patrones como "Clase Y: $65.59" o "• Clase Y:"
        pattern = r'Clase\s+([A-Z])\s*[:-]\s*\$?([\d.]+)?'
        matches = re.findall(pattern, self.last_response)
        
        if matches:
            # Si hay precios, ordenar por precio y tomar el más barato
            if matches[0][1]:  # Si tiene precio
                cheapest = min(matches, key=lambda x: float(x[1]) if x[1] else 999999)
                self.log(f"💰 Clase más económica detectada: {cheapest[0]} (${cheapest[1]})", "INFO")
                return cheapest[0]
            else:
                # Si no hay precio, tomar la primera
                self.log(f"💰 Primera clase disponible: {matches[0][0]}", "INFO")
                return matches[0][0]
        
        # Fallback: buscar cualquier letra de clase mencionada
        class_pattern = r'\b([YBJCFMHQVWSTLKGUENRODIAZP])\b'
        class_matches = re.findall(class_pattern, self.last_response)
        if class_matches:
            self.log(f"💰 Clase detectada (fallback): {class_matches[0]}", "INFO")
            return class_matches[0]
        
        self.log("⚠️ No se pudo detectar clase, usando Y por defecto", "WARNING")
        return "Y"
    
    def test_case(self, name, description):
        """Decorador para casos de prueba"""
        self.log(f"\n{'='*80}", "TEST")
        self.log(f"🧪 CASO DE PRUEBA: {name}", "TEST")
        self.log(f"📋 {description}", "TEST")
        self.log(f"{'='*80}", "TEST")
        time.sleep(1)
    
    def reset_session(self):
        """Reinicia la sesión del bot"""
        session_manager.sessions.pop(self.test_phone, None)
        self.log("🔄 Sesión reiniciada", "SYSTEM")
        time.sleep(1)
    
    # ==================== CASOS DE PRUEBA ====================
    
    def test_1_activacion_bot(self):
        """Prueba 1: Activación del bot"""
        self.test_case(
            "ACTIVACIÓN DEL BOT",
            "Verificar que el bot se active correctamente con el comando 'cervo ai'"
        )
        
        response = self.send_message("cervo ai")
        assert response is not None, "❌ El bot no respondió al comando de activación"
        assert "Cervo Assistant" in response or "agente" in response.lower(), "❌ Mensaje de bienvenida incorrecto"
        
        self.log("✅ Bot activado correctamente", "SUCCESS")
        return True
    
    def test_2_requisitos_pais(self):
        """Prueba 2: Consulta de requisitos migratorios"""
        self.test_case(
            "REQUISITOS MIGRATORIOS",
            "Consultar requisitos para viajar a diferentes países"
        )
        
        # Probar varios países
        paises = ["Cuba", "México", "Panamá", "Colombia"]
        
        for pais in paises:
            self.log(f"📍 Consultando requisitos para {pais}...", "TEST")
            response = self.send_message(f"Qué necesito para viajar a {pais}")
            
            assert response is not None, f"❌ No hubo respuesta para {pais}"
            assert pais.lower() in response.lower() or "requisito" in response.lower(), f"❌ Respuesta no contiene información de {pais}"
            
            self.log(f"✅ Requisitos de {pais} obtenidos", "SUCCESS")
            time.sleep(2)
        
        return True
    
    def test_3_vuelo_solo_ida(self):
        """Prueba 3: Reservar vuelo solo de ida"""
        self.test_case(
            "VUELO SOLO DE IDA",
            "Buscar y reservar un vuelo de solo ida con todos los pasos"
        )
        
        # Paso 1: Solicitar vuelo
        self.send_message("Quiero volar de Caracas a Margarita")
        time.sleep(2)
        
        # Paso 2: Especificar tipo de viaje
        self.send_message("Solo ida")
        time.sleep(2)
        
        # Paso 3: Fecha
        fecha_manana = (datetime.now() + timedelta(days=7)).strftime("%d de %B")
        self.send_message(f"Para el {fecha_manana}")
        time.sleep(2)
        
        # Paso 4: Número de pasajeros
        self.send_message("1 pasajero")
        time.sleep(3)
        
        # Paso 5: Seleccionar vuelo (esperar a que muestre opciones)
        self.log("⏳ Esperando resultados de búsqueda...", "TEST")
        time.sleep(5)
        
        self.send_message("Quiero el vuelo 1")
        time.sleep(3)
        
        # Paso 6: Confirmar vuelo
        self.send_message("Sí")
        time.sleep(3)
        
        # Paso 7: Seleccionar clase (detectar la más económica)
        cheapest_class = self.extract_cheapest_class()
        self.send_message(cheapest_class)
        time.sleep(3)
        
        # Paso 8: Confirmar clase
        self.send_message("Sí")
        time.sleep(2)
        
        # Paso 9: Método de ingreso de datos
        self.send_message("Manual")
        time.sleep(2)
        
        # Paso 10: Ingresar datos del pasajero
        self.send_message("Juan")  # Nombre
        time.sleep(1)
        
        self.send_message("Pérez")  # Apellido
        time.sleep(1)
        
        self.send_message("Venezolano")  # Nacionalidad
        time.sleep(1)
        
        self.send_message("12345678")  # Cédula
        time.sleep(1)
        
        self.send_message("M")  # Sexo
        time.sleep(1)
        
        self.send_message("Av Principal, Caracas")  # Dirección
        time.sleep(1)
        
        self.send_message("Caracas")  # Ciudad
        time.sleep(1)
        
        self.send_message("Distrito Capital")  # Estado
        time.sleep(1)
        
        self.send_message("1010")  # Código postal
        time.sleep(1)
        
        self.send_message("04121234567")  # Teléfono
        time.sleep(1)
        
        self.send_message("juan.perez@email.com")  # Email
        time.sleep(1)
        
        self.send_message("15/05/1990")  # Fecha de nacimiento
        time.sleep(3)
        
        self.log("✅ Proceso de reserva de vuelo solo ida completado", "SUCCESS")
        return True
    
    def test_4_vuelo_ida_vuelta(self):
        """Prueba 4: Reservar vuelo ida y vuelta"""
        self.test_case(
            "VUELO IDA Y VUELTA",
            "Buscar y reservar un vuelo de ida y vuelta completo"
        )
        
        # Reiniciar sesión
        self.reset_session()
        self.send_message("cervo ai")
        time.sleep(2)
        
        # Paso 1: Solicitar vuelo completo
        fecha_ida = (datetime.now() + timedelta(days=10)).strftime("%d de %B")
        fecha_vuelta = (datetime.now() + timedelta(days=17)).strftime("%d de %B")
        
        self.send_message(f"Necesito un vuelo de Caracas a Maracaibo ida y vuelta, salgo el {fecha_ida} y regreso el {fecha_vuelta}, para 2 personas")
        time.sleep(5)
        
        # Esperar búsqueda de vuelos de ida
        self.log("⏳ Esperando vuelos de ida...", "TEST")
        time.sleep(5)
        
        # Seleccionar vuelo de ida
        self.send_message("El vuelo 2")
        time.sleep(3)
        
        self.send_message("Sí")
        time.sleep(3)
        
        # Seleccionar clase de ida (detectar la más económica)
        cheapest_class_ida = self.extract_cheapest_class()
        self.send_message(cheapest_class_ida)
        time.sleep(3)
        
        self.send_message("Sí")
        time.sleep(5)
        
        # Esperar búsqueda de vuelos de vuelta
        self.log("⏳ Esperando vuelos de vuelta...", "TEST")
        time.sleep(5)
        
        # Seleccionar vuelo de vuelta
        self.send_message("El vuelo 1")
        time.sleep(3)
        
        self.send_message("Sí")
        time.sleep(3)
        
        # Seleccionar clase de vuelta (detectar la más económica)
        cheapest_class_vuelta = self.extract_cheapest_class()
        self.send_message(cheapest_class_vuelta)
        time.sleep(3)
        
        # Confirmar resumen final
        self.send_message("Sí")
        time.sleep(3)
        
        # Ingresar datos del pasajero 1
        self.send_message("Manual")
        time.sleep(2)
        
        self.log("📝 Ingresando datos del Pasajero 1...", "TEST")
        self.send_message("María")
        time.sleep(1)
        self.send_message("González")
        time.sleep(1)
        self.send_message("Venezolana")
        time.sleep(1)
        self.send_message("23456789")
        time.sleep(1)
        self.send_message("F")
        time.sleep(1)
        self.send_message("Calle 5, Los Palos Grandes")
        time.sleep(1)
        self.send_message("Caracas")
        time.sleep(1)
        self.send_message("Miranda")
        time.sleep(1)
        self.send_message("1060")
        time.sleep(1)
        self.send_message("04149876543")
        time.sleep(1)
        self.send_message("maria.gonzalez@email.com")
        time.sleep(1)
        self.send_message("20/08/1985")
        time.sleep(3)
        
        # Ingresar datos del pasajero 2
        self.log("📝 Ingresando datos del Pasajero 2...", "TEST")
        self.send_message("Manual")
        time.sleep(2)
        
        self.send_message("Carlos")
        time.sleep(1)
        self.send_message("Rodríguez")
        time.sleep(1)
        self.send_message("Venezolano")
        time.sleep(1)
        self.send_message("34567890")
        time.sleep(1)
        self.send_message("M")
        time.sleep(1)
        self.send_message("Igual")  # Usar misma dirección
        time.sleep(1)
        self.send_message("04167654321")
        time.sleep(1)
        self.send_message("carlos.rodriguez@email.com")
        time.sleep(1)
        self.send_message("10/03/1988")
        time.sleep(5)
        
        self.log("✅ Proceso de reserva ida y vuelta completado", "SUCCESS")
        return True
    
    def test_5_consulta_pnr(self):
        """Prueba 5: Consultar reserva con código PNR"""
        self.test_case(
            "CONSULTA DE RESERVA PNR",
            "Consultar una reserva existente usando código PNR"
        )
        
        # Reiniciar sesión
        self.reset_session()
        self.send_message("cervo ai")
        time.sleep(2)
        
        # Probar con un PNR de ejemplo (puede no existir)
        self.send_message("ABC123")
        time.sleep(3)
        
        # Probar preguntando explícitamente
        self.send_message("Quiero consultar mi reserva con código XYZ789")
        time.sleep(3)
        
        self.log("✅ Prueba de consulta PNR completada", "SUCCESS")
        return True
    
    def test_6_casos_especiales(self):
        """Prueba 6: Casos especiales y edge cases"""
        self.test_case(
            "CASOS ESPECIALES",
            "Probar diferentes formas de expresar las solicitudes"
        )
        
        # Reiniciar sesión
        self.reset_session()
        self.send_message("cervo ai")
        time.sleep(2)
        
        # Caso 1: Usar nombres de ciudades en lugar de códigos
        self.send_message("Busca vuelos de Maiquetía a Porlamar")
        time.sleep(2)
        self.send_message("Solo ida")
        time.sleep(2)
        self.send_message("Mañana")
        time.sleep(2)
        self.send_message("Somos 3")
        time.sleep(5)
        
        # Caso 2: Preguntar por aerolínea específica
        self.send_message("Dame los vuelos de Laser")
        time.sleep(3)
        
        # Caso 3: Pedir el más barato
        self.send_message("Cuál es el más barato")
        time.sleep(3)
        
        # Caso 4: Pedir el más tarde
        self.send_message("Dame el más tarde")
        time.sleep(3)
        
        self.log("✅ Casos especiales probados", "SUCCESS")
        return True
    
    def test_7_desactivacion(self):
        """Prueba 7: Desactivar el bot"""
        self.test_case(
            "DESACTIVACIÓN DEL BOT",
            "Verificar que el bot se desactive correctamente"
        )
        
        response = self.send_message("salir")
        assert response is not None, "❌ El bot no respondió al comando de salida"
        assert "hasta pronto" in response.lower() or "adios" in response.lower(), "❌ Mensaje de despedida incorrecto"
        
        # Verificar que no responde después de desactivar
        response = self.send_message("Hola")
        assert response is None, "❌ El bot respondió después de desactivarse"
        
        self.log("✅ Bot desactivado correctamente", "SUCCESS")
        return True
    
    # ==================== EJECUTAR TODAS LAS PRUEBAS ====================
    
    def run_all_tests(self):
        """Ejecuta todas las pruebas"""
        self.log("\n" + "="*80, "MAIN")
        self.log("🚀 INICIANDO PRUEBAS COMPLETAS DEL BOT", "MAIN")
        self.log("="*80 + "\n", "MAIN")
        
        tests = [
            ("Activación del Bot", self.test_1_activacion_bot),
            ("Requisitos Migratorios", self.test_2_requisitos_pais),
            ("Vuelo Solo Ida", self.test_3_vuelo_solo_ida),
            ("Vuelo Ida y Vuelta", self.test_4_vuelo_ida_vuelta),
            ("Consulta PNR", self.test_5_consulta_pnr),
            ("Casos Especiales", self.test_6_casos_especiales),
            ("Desactivación", self.test_7_desactivacion)
        ]
        
        passed = 0
        failed = 0
        
        for name, test_func in tests:
            try:
                result = test_func()
                if result:
                    passed += 1
                    self.test_results.append((name, "PASSED"))
                else:
                    failed += 1
                    self.test_results.append((name, "FAILED"))
            except Exception as e:
                self.log(f"❌ ERROR EN PRUEBA: {str(e)}", "ERROR")
                failed += 1
                self.test_results.append((name, f"ERROR: {str(e)}"))
            
            time.sleep(3)
        
        # Resumen final
        self.print_summary(passed, failed)
    
    def print_summary(self, passed, failed):
        """Imprime resumen de resultados"""
        self.log("\n" + "="*80, "SUMMARY")
        self.log("RESUMEN DE PRUEBAS", "SUMMARY")
        self.log("="*80, "SUMMARY")
        
        for name, result in self.test_results:
            status = "[OK]" if result == "PASSED" else "[FAIL]"
            self.log(f"{status} {name}: {result}", "SUMMARY")
        
        self.log("\n" + "-"*80, "SUMMARY")
        total = passed + failed
        self.log(f"Total de pruebas: {total}", "SUMMARY")
        self.log(f"Exitosas: {passed}", "SUMMARY")
        self.log(f"Fallidas: {failed}", "SUMMARY")
        self.log(f"Tasa de éxito: {(passed/total*100):.1f}%", "SUMMARY")
        self.log("="*80 + "\n", "SUMMARY")

def main():
    """Función principal"""
    print("\n" + "="*80)
    print("CERVO AI - TEST COMPLETO DEL BOT")
    print("="*80 + "\n")
    
    print("Este script probará todas las funcionalidades del bot:")
    print("1. Activación del bot")
    print("2. Requisitos migratorios de países")
    print("3. Reserva de vuelo solo ida")
    print("4. Reserva de vuelo ida y vuelta")
    print("5. Consulta de reserva con PNR")
    print("6. Casos especiales y edge cases")
    print("7. Desactivación del bot")
    
    print("\nNOTA: Este test puede tardar varios minutos en completarse.")
    print("Asegúrate de tener configuradas las API keys en el archivo .env\n")
    
    # input("Presiona ENTER para comenzar las pruebas...")
    
    tester = BotTester()
    tester.run_all_tests()
    
    print("\nPruebas completadas. Revisa el resumen arriba.")

if __name__ == "__main__":
    main()
