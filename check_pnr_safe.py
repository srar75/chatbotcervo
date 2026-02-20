from flight_booking_service import flight_service
import json
import logging

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)

pnr = 'SSUMJO'
print(f'Checking {pnr}...')
res = flight_service.get_booking_details(pnr)
print("RESULTADO:")
print(json.dumps(res, indent=2, default=str))
