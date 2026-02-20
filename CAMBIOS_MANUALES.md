# 🔧 CAMBIOS MANUALES PARA APLICAR A gemini_agent_bot.py

## ⚠️ IMPORTANTE
Los cambios automáticos causaron problemas de encoding.
Debes aplicar estos cambios MANUALMENTE en el archivo.

---

## CAMBIO 1: Actualizar System Prompt (línea ~49)

### BUSCAR esta línea:
```python
  * Si mencionan origen, destino y fecha: llama search_flights INMEDIATAMENTE sin preguntar nada
```

### REEMPLAZAR por:
```python
  * OBLIGATORIO: Si NO mencionan cuántas personas viajan, pregunta PRIMERO "¿Para cuántas personas es el vuelo?" antes de buscar
  * Si falta algún dato (origen, destino, fecha o número de pasajeros): pregunta SOLO lo que falta
```

---

## CAMBIO 2: Agregar Nueva Herramienta (línea ~436, ANTES de confirm_flight_selection)

### AGREGAR este bloque COMPLETO:
```python
                        types.FunctionDeclaration(
                            name="select_flight_and_get_prices",
                            description="OBLIGATORIO: Llama esta función cuando el usuario seleccione un vuelo (ejemplo: 'opción 1', 'vuelo 2', 'el primero'). Esta función obtiene automáticamente los precios de TODAS las clases disponibles para ese vuelo y los muestra al usuario para que elija.",
                            parameters={
                                "type": "object",
                                "properties": {
                                    "flight_index": {
                                        "type": "integer",
                                        "description": "Número del vuelo seleccionado (1, 2, 3, etc.)"
                                    }
                                },
                                "required": ["flight_index"]
                            }
                        ),

```

---

## CAMBIO 3: Actualizar descripción de confirm_flight_selection (línea ~438)

### BUSCAR:
```python
description="Muestra los detalles del vuelo seleccionado con la clase elegida y pide confirmación al usuario ANTES de proceder con la reserva. SIEMPRE llama esta función cuando el usuario seleccione un vuelo Y una clase.",
```

### REEMPLAZAR por:
```python
description="Muestra los detalles del vuelo seleccionado con la clase elegida y pide confirmación al usuario ANTES de proceder con la reserva. SOLO llama esta función DESPUÉS de que el usuario haya elegido una clase de las opciones mostradas.",
```

---

## CAMBIO 4: Agregar Manejador de Función (línea ~624, ANTES de confirm_flight_selection)

### AGREGAR este bloque:
```python
            elif function_name == "select_flight_and_get_prices":
                # Nueva función: seleccionar vuelo y obtener precios de todas las clases
                wati_service.send_message(phone, "💰 *Consultando precios de todas las clases disponibles...*\\n\\n⏳ Un momento por favor...")
                result = self._select_flight_and_get_prices_function(
                    function_args.get('flight_index'),
                    session
                )
```

---

## CAMBIO 5: Agregar Nueva Función (línea ~897, ANTES de _confirm_flight_selection_function)

### AGREGAR esta función COMPLETA:
```python
    
    def _select_flight_and_get_prices_function(self, flight_index, session):
        """Selecciona un vuelo y obtiene precios de TODAS las clases disponibles"""
        try:
            flights = session.data.get('available_flights', [])
            
            if not flights:
                return {"success": False, "message": "No hay vuelos disponibles. Primero debes buscar vuelos."}
            
            if flight_index < 1 or flight_index > len(flights):
                return {"success": False, "message": f"Número de vuelo inválido. Debe ser entre 1 y {len(flights)}"}
            
            selected_flight = flights[flight_index - 1]
            
            # Guardar vuelo seleccionado en sesión
            session.data['selected_flight_index'] = flight_index
            session.data['selected_flight'] = selected_flight
            
            # Obtener precios de todas las clases usando el servicio
            logger.info(f"Obteniendo precios de todas las clases para vuelo {flight_index}...")
            pricing_result = flight_service.get_all_class_prices(selected_flight)
            
            if not pricing_result.get('success'):
                return {
                    "success": False,
                    "message": "No se pudieron obtener los precios de las clases. Por favor intenta de nuevo."
                }
            
            classes_prices = pricing_result.get('classes_prices', {})
            
            if not classes_prices:
                return {
                    "success": False,
                    "message": "No se encontraron precios disponibles para este vuelo."
                }
            
            # Guardar precios en sesión
            session.data['flight_classes_prices'] = classes_prices
            
            # Clasificar clases por tipo
            economy_classes = []
            business_classes = []
            first_classes = []
            
            economy_codes = ['Y', 'B', 'M', 'H', 'Q', 'V', 'W', 'S', 'T', 'L', 'K', 'G', 'U', 'E', 'N', 'R', 'O']
            business_codes = ['J', 'C', 'D', 'I', 'Z']
            first_codes = ['F', 'A', 'P']
            
            for class_code, class_data in classes_prices.items():
                class_info = {
                    "codigo": class_code,
                    "precio": class_data['price'],
                    "asientos": class_data['availability']
                }
                
                if class_code in economy_codes:
                    economy_classes.append(class_info)
                elif class_code in business_codes:
                    business_classes.append(class_info)
                elif class_code in first_codes:
                    first_classes.append(class_info)
                else:
                    economy_classes.append(class_info)
            
            # Ordenar por precio (más barato primero)
            economy_classes.sort(key=lambda x: x['precio'])
            business_classes.sort(key=lambda x: x['precio'])
            first_classes.sort(key=lambda x: x['precio'])
            
            # Construir respuesta
            return {
                "success": True,
                "flight_index": flight_index,
                "aerolinea": selected_flight.get('airline_name'),
                "vuelo": selected_flight.get('flight_number'),
                "ruta": f"{selected_flight.get('origin')} → {selected_flight.get('destination')}",
                "fecha": selected_flight.get('date'),
                "salida": selected_flight.get('departure_time'),
                "llegada": selected_flight.get('arrival_time'),
                "duracion": selected_flight.get('duration'),
                "economy_classes": economy_classes,
                "business_classes": business_classes,
                "first_classes": first_classes,
                "total_classes": len(classes_prices),
                "message": f"Vuelo seleccionado. Aquí están los precios de todas las clases disponibles. Por favor elige la clase que prefieras."
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo precios de clases: {str(e)}")
            return {"success": False, "error": str(e)}
```

---

## CAMBIO 6: Actualizar .env

### BUSCAR:
```
GEMINI_MODEL=gemini-3-flash-preview
```

### REEMPLAZAR por:
```
GEMINI_MODEL=gemini-2.5-flash
```

---

## CAMBIO 7: Agregar document_extractor.py

Este es un archivo NUEVO. Copia el contenido del archivo `document_extractor.py` que ya está creado.

---

## ✅ VERIFICACIÓN

Después de hacer los cambios:

1. Ejecuta: `python -m py_compile gemini_agent_bot.py`
2. Si no hay errores, el archivo está correcto
3. Prueba con: `python start.py`

---

## 📝 NOTA

Si prefieres, puedo crear un script que haga SOLO los cambios esenciales sin tocar el encoding del archivo.
¿Quieres que cree ese script?
