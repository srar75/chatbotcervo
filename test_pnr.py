"""
Test de consulta de PNR
"""
from flight_booking_service import flight_service
import json

pnr = "BORQSC"

print(f"\n{'='*50}")
print(f"CONSULTANDO PNR: {pnr}")
print(f"{'='*50}\n")

result = flight_service.get_booking_details(pnr=pnr)

print("RESULTADO COMPLETO:")
print(json.dumps(result, indent=2, ensure_ascii=False))

print(f"\n{'='*50}")
print("ANÁLISIS:")
print(f"{'='*50}")
print(f"Success: {result.get('success')}")
print(f"PNR: {result.get('pnr')}")
print(f"VID: {result.get('vid')}")
print(f"Estado: {result.get('status')}")
print(f"Pasajeros: {len(result.get('passengers', []))}")
print(f"Vuelos: {len(result.get('flights', []))}")

if result.get('flights'):
    print(f"\n{'='*50}")
    print("VUELOS ENCONTRADOS:")
    print(f"{'='*50}")
    for i, vuelo in enumerate(result.get('flights', []), 1):
        print(f"\nVuelo {i}:")
        print(f"  Aerolínea: {vuelo.get('aerolinea')}")
        print(f"  Número: {vuelo.get('vuelo')}")
        print(f"  Ruta: {vuelo.get('ruta')}")
        print(f"  Fecha: {vuelo.get('fecha')}")
        print(f"  Salida: {vuelo.get('hora_salida')}")
        print(f"  Llegada: {vuelo.get('hora_llegada')}")
        print(f"  Clase: {vuelo.get('clase')}")
        print(f"  Estado: {vuelo.get('estado')}")
else:
    print("\n[!] NO SE ENCONTRARON VUELOS EN LA RESPUESTA")
