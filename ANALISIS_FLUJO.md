# 🔍 Análisis del Flujo de Reservas en gemini_agent_bot.py

## ✅ PUNTOS VERIFICADOS Y CORRECTOS

### 1. Búsqueda de Vuelos (`_search_flights_function`)
- ✅ Guarda vuelos en `session.data['available_flights']`
- ✅ Maneja reintentos en caso de timeout
- ✅ Normaliza códigos IATA correctamente
- ✅ Retorna estructura correcta con todos los datos

### 2. Selección de Vuelo (`_select_flight_and_get_prices_function`)
- ✅ Valida índice del vuelo
- ✅ Guarda `selected_flight_index` en sesión
- ✅ Llama a `get_all_class_prices` correctamente
- ✅ Guarda `flight_classes_prices` en sesión
- ✅ Clasifica clases por tipo (Economy, Business, First)

### 3. Confirmación de Vuelo (`_confirm_flight_selection_function`)
- ✅ Valida que la clase existe
- ✅ Guarda `selected_flight_class` en sesión
- ✅ Marca `awaiting_flight_confirmation = True`
- ✅ Maneja vuelos de ida y vuelta correctamente

### 4. Creación de Reserva (`_create_booking_function`)
- ✅ Obtiene todos los pasajeros de `passengers_list`
- ✅ Formatea datos correctamente para la API
- ✅ Incluye vuelo de vuelta si existe
- ✅ Maneja múltiples PNR para aerolíneas diferentes

## ⚠️ PROBLEMAS POTENCIALES ENCONTRADOS

### PROBLEMA 1: Interceptación de Selección de Clase
**Ubicación:** Línea ~1850 en `gemini_agent_bot.py`

```python
# DETECCIÓN DE SELECCIÓN DE CLASE (Interceptando a Gemini)
has_prices = session.data.get('flight_classes_prices') or session.data.get('return_flight_classes_prices')
if has_prices:
    class_match = re.search(r'^(?:CLASE\s+)?([A-Z])$', message.upper().strip())
```

**Problema:** Si el usuario escribe algo como "clase y por favor" o "Y es la mejor", el regex no lo detecta.

**Solución:** Hacer el regex más flexible.

---

### PROBLEMA 2: Validación de Clase en Vuelo de Vuelta
**Ubicación:** `_confirm_flight_selection_function`

```python
if is_return:
    flights = session.data.get('return_flights', [])
else:
    flights = session.data.get('available_flights', [])
```

**Problema:** Si el usuario selecciona una clase para el vuelo de vuelta, pero esa clase no existe en ese vuelo específico, puede fallar.

**Solución:** Validar contra `return_flight_classes_prices` en lugar de `flight_classes_prices`.

---

### PROBLEMA 3: Número de Pasajeros en Reserva
**Ubicación:** `_create_booking_function`

```python
passengers_list = session.data.get('passengers_list', [])
if passengers_list and len(passengers_list) > 0:
    # Usar los pasajeros de la lista
```

**Problema:** Si `num_passengers` es 2 pero solo se agregó 1 pasajero a la lista, la reserva se crea con 1 solo pasajero.

**Solución:** Validar que `len(passengers_list) == num_passengers` antes de crear la reserva.

---

### PROBLEMA 4: Vuelo de Vuelta No Se Incluye
**Ubicación:** `_create_booking_function` línea ~2800

```python
return_flights = session.data.get('return_flights', [])
return_flight_index = session.data.get('selected_return_flight_index')
```

**Problema:** Si el usuario seleccionó vuelo de vuelta pero no se guardó correctamente el índice, la reserva se crea solo con ida.

**Solución:** Agregar logging detallado y validación.

---

## 🐛 BUGS CRÍTICOS ENCONTRADOS

### BUG 1: Precio Incorrecto en Resumen
**Ubicación:** `_send_booking_success_message`

```python
precio_ida = 0
flight_classes_prices = session.data.get('flight_classes_prices', {})
if flight_classes_prices and flight_class.upper() in flight_classes_prices:
    precio_ida = flight_classes_prices[flight_class.upper()].get('price', 0)
```

**Problema:** Si `flight_classes_prices` está vacío, muestra precio $0.00

**Impacto:** El usuario ve un precio incorrecto en la confirmación.

---

### BUG 2: Detección de PNR Bloquea Palabras Comunes
**Ubicación:** Línea ~1650

```python
palabras_excluidas = ['BUENOS', 'BUENAS', 'HOLA', ...]
es_palabra_comun = potential_pnr in palabras_excluidas
```

**Problema:** Si un PNR real es "BUENOS" (poco probable pero posible), no se detecta.

**Impacto:** Bajo, pero existe.

---

## 🔧 CORRECCIONES RECOMENDADAS

### Corrección 1: Mejorar Detección de Clase
```python
# Buscar clase de forma más flexible
class_match = re.search(r'\b([A-Z])\b', message.upper())
if class_match and len(message.strip()) <= 20:  # Evitar falsos positivos en mensajes largos
    selected_class = class_match.group(1)
```

### Corrección 2: Validar Número de Pasajeros
```python
# Antes de crear reserva
expected_passengers = session.data.get('num_passengers', 1)
actual_passengers = len(passengers_list)

if actual_passengers < expected_passengers:
    return {
        "success": False,
        "error": f"Faltan datos de {expected_passengers - actual_passengers} pasajero(s)"
    }
```

### Corrección 3: Validar Vuelo de Vuelta
```python
# Agregar logging detallado
logger.info(f"=== VERIFICANDO VUELO DE VUELTA ===")
logger.info(f"return_flights: {len(return_flights) if return_flights else 0}")
logger.info(f"return_flight_index: {return_flight_index}")
logger.info(f"return_flight_class: {return_flight_class}")

if return_flights and return_flight_index:
    if 1 <= return_flight_index <= len(return_flights):
        return_flight = return_flights[return_flight_index - 1]
        logger.info(f"✅ Vuelo de vuelta incluido: {return_flight.get('flight_number')}")
    else:
        logger.error(f"❌ Índice fuera de rango: {return_flight_index}")
```

## 📊 RESUMEN

| Componente | Estado | Crítico |
|------------|--------|---------|
| Búsqueda de vuelos | ✅ OK | No |
| Selección de vuelo | ✅ OK | No |
| Obtención de precios | ✅ OK | No |
| Selección de clase | ⚠️ Mejorable | No |
| Datos de pasajeros | ✅ OK | No |
| Creación de reserva | ⚠️ Revisar | Sí |
| Vuelo de vuelta | ⚠️ Revisar | Sí |
| Consulta de PNR | ✅ Corregido | No |

## 🎯 PRIORIDADES

1. **ALTA**: Validar que vuelo de vuelta se incluye correctamente
2. **ALTA**: Validar número de pasajeros antes de crear reserva
3. **MEDIA**: Mejorar detección de selección de clase
4. **BAJA**: Mejorar manejo de precios en resumen

## 🧪 CÓMO PROBAR

Ejecuta el script de prueba:
```bash
python test_flow.py
```

Este script probará todo el flujo y te dirá exactamente dónde falla.
