"""
Script de verificación completa de kiu_service y flight_booking_service
"""
import logging
from datetime import datetime, timedelta
from kiu_service import kiu_service
from flight_booking_service import flight_service

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_kiu_service():
    """Prueba todas las funciones de kiu_service"""
    print("\n" + "="*70)
    print("VERIFICACIÓN DE KIU_SERVICE")
    print("="*70)
    
    results = []
    
    # Test 1: Health Check
    print("\n[1] Health Check...")
    try:
        result = kiu_service.health_check()
        status = "✅" if result.get('success') else "❌"
        print(f"{status} Health Check: {result.get('message', result.get('error'))}")
        results.append(("Health Check", result.get('success', False)))
    except Exception as e:
        print(f"❌ Health Check: {e}")
        results.append(("Health Check", False))
    
    # Test 2: Search Flights
    print("\n[2] Search Flights (CCS->PMV)...")
    try:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        result = kiu_service.search_flights('CCS', 'PMV', tomorrow)
        
        if result.get('success'):
            flights = result.get('data', {}).get('departureFlight', [])
            print(f"✅ Search Flights: {len(flights)} vuelos encontrados")
            if flights:
                first = flights[0]
                segments = first.get('segments', [])
                if segments:
                    seg = segments[0]
                    print(f"   Primer vuelo: {seg.get('airlineName')} {seg.get('flightNumber')}")
                    print(f"   Precio: ${first.get('price', 'N/A')}")
                    print(f"   Clases: {list(seg.get('classes', {}).keys())}")
            results.append(("Search Flights", True))
        else:
            print(f"❌ Search Flights: {result.get('error')}")
            results.append(("Search Flights", False))
    except Exception as e:
        print(f"❌ Search Flights: {e}")
        results.append(("Search Flights", False))
    
    # Test 3: Get Booking Status (con PNR de prueba)
    print("\n[3] Get Booking Status...")
    test_pnr = input("Ingresa un PNR válido para probar (o Enter para saltar): ").strip()
    if test_pnr:
        try:
            result = kiu_service.get_booking_status(test_pnr)
            if result.get('success'):
                data = result.get('data', {})
                loc = data.get('loc', {})
                print(f"✅ Get Booking Status: PNR {loc.get('localizador', 'N/A')}")
                print(f"   Estado: {loc.get('estado', 'N/A')}")
                print(f"   Precio: {loc.get('precio', 'N/A')}")
                results.append(("Get Booking Status", True))
            else:
                print(f"❌ Get Booking Status: {result.get('error')}")
                results.append(("Get Booking Status", False))
        except Exception as e:
            print(f"❌ Get Booking Status: {e}")
            results.append(("Get Booking Status", False))
    else:
        print("⏭️  Saltado")
        results.append(("Get Booking Status", None))
    
    return results

def test_flight_service():
    """Prueba todas las funciones de flight_booking_service"""
    print("\n" + "="*70)
    print("VERIFICACIÓN DE FLIGHT_BOOKING_SERVICE")
    print("="*70)
    
    results = []
    
    # Test 1: Search Flights
    print("\n[1] Search Flights (CCS->PMV)...")
    try:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        flights = flight_service.search_flights('CCS', 'PMV', tomorrow)
        
        if flights and len(flights) > 0:
            print(f"✅ Search Flights: {len(flights)} vuelos")
            first = flights[0]
            print(f"   Primer vuelo: {first.get('airline_name')} {first.get('flight_number')}")
            print(f"   Precio: ${first.get('price')}")
            print(f"   Origen: {first.get('origin')} -> Destino: {first.get('destination')}")
            print(f"   Salida: {first.get('departure_time')} - Llegada: {first.get('arrival_time')}")
            results.append(("Search Flights", True, flights))
        else:
            print(f"❌ Search Flights: No se encontraron vuelos")
            results.append(("Search Flights", False, None))
    except Exception as e:
        print(f"❌ Search Flights: {e}")
        results.append(("Search Flights", False, None))
    
    # Test 2: Get All Class Prices (si hay vuelos)
    if results[0][1] and results[0][2]:
        print("\n[2] Get All Class Prices...")
        try:
            first_flight = results[0][2][0]
            pricing = flight_service.get_all_class_prices(first_flight)
            
            if pricing.get('success'):
                classes = pricing.get('classes_prices', {})
                print(f"✅ Get All Class Prices: {len(classes)} clases")
                for code, data in list(classes.items())[:3]:
                    print(f"   Clase {code}: ${data.get('price')} ({data.get('availability')} asientos)")
                results.append(("Get All Class Prices", True))
            else:
                print(f"❌ Get All Class Prices: {pricing.get('error')}")
                results.append(("Get All Class Prices", False))
        except Exception as e:
            print(f"❌ Get All Class Prices: {e}")
            results.append(("Get All Class Prices", False))
    
    # Test 3: Get Booking Details
    print("\n[3] Get Booking Details...")
    test_pnr = input("Ingresa un PNR válido para probar (o Enter para saltar): ").strip()
    if test_pnr:
        try:
            result = flight_service.get_booking_details(pnr=test_pnr)
            if result.get('success'):
                print(f"✅ Get Booking Details: PNR {result.get('pnr')}")
                print(f"   Estado: {result.get('status', 'N/A')}")
                print(f"   Cliente: {result.get('client', 'N/A')}")
                print(f"   Pasajeros: {len(result.get('passengers', []))}")
                print(f"   Vuelos: {len(result.get('flights', []))}")
                results.append(("Get Booking Details", True))
            else:
                print(f"❌ Get Booking Details: {result.get('error')}")
                results.append(("Get Booking Details", False))
        except Exception as e:
            print(f"❌ Get Booking Details: {e}")
            results.append(("Get Booking Details", False))
    else:
        print("⏭️  Saltado")
        results.append(("Get Booking Details", None))
    
    return results

def print_summary(kiu_results, flight_results):
    """Imprime resumen de resultados"""
    print("\n" + "="*70)
    print("RESUMEN DE VERIFICACIÓN")
    print("="*70)
    
    print("\n📦 KIU_SERVICE:")
    for name, status in kiu_results:
        if status is None:
            icon = "⏭️ "
        elif status:
            icon = "✅"
        else:
            icon = "❌"
        print(f"  {icon} {name}")
    
    print("\n✈️  FLIGHT_BOOKING_SERVICE:")
    for item in flight_results:
        name = item[0]
        status = item[1]
        if status is None:
            icon = "⏭️ "
        elif status:
            icon = "✅"
        else:
            icon = "❌"
        print(f"  {icon} {name}")
    
    # Calcular estadísticas
    kiu_passed = sum(1 for _, s in kiu_results if s is True)
    kiu_total = sum(1 for _, s in kiu_results if s is not None)
    
    flight_passed = sum(1 for item in flight_results if item[1] is True)
    flight_total = sum(1 for item in flight_results if item[1] is not None)
    
    print("\n📊 ESTADÍSTICAS:")
    print(f"  KIU Service: {kiu_passed}/{kiu_total} pruebas pasadas")
    print(f"  Flight Service: {flight_passed}/{flight_total} pruebas pasadas")
    
    total_passed = kiu_passed + flight_passed
    total_tests = kiu_total + flight_total
    
    if total_tests > 0:
        percentage = (total_passed / total_tests) * 100
        print(f"\n  TOTAL: {total_passed}/{total_tests} ({percentage:.1f}%)")
        
        if percentage == 100:
            print("\n  🎉 ¡TODOS LOS SERVICIOS FUNCIONAN CORRECTAMENTE!")
        elif percentage >= 75:
            print("\n  ⚠️  La mayoría de servicios funcionan, revisa los errores")
        else:
            print("\n  ❌ Hay problemas críticos que requieren atención")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║     VERIFICACIÓN COMPLETA DE SERVICIOS                          ║
║     kiu_service.py + flight_booking_service.py                  ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        kiu_results = test_kiu_service()
        flight_results = test_flight_service()
        print_summary(kiu_results, flight_results)
    except KeyboardInterrupt:
        print("\n\n⚠️  Verificación interrumpida por el usuario")
    except Exception as e:
        print(f"\n\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
