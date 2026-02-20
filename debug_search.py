from flight_booking_service import flight_service as flight_booking_service
import logging

# Configurar logging para ver detalles
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_search():
    origin = "MAR"
    destination = "PMV"
    date = "19/02/2026"
    
    print(f"Testing search: {origin} -> {destination} on {date}")
    
    try:
        results = flight_booking_service.search_flights(
            origin=origin,
            destination=destination,
            date=date,
            passengers={"ADT": 2, "CHD": 0, "INF": 0}
        )
        
        print(f"Resultados encontrados: {len(results)}")
        for flight in results:
            print(f" - {flight['airline']} {flight['flight_number']} ({flight['price']})")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_search()
