# ✅ ACTUALIZACIÓN: Pregunta Obligatoria por Número de Pasajeros

## 🎯 Cambio Implementado

El bot ahora **SIEMPRE** preguntará por el número de pasajeros antes de buscar vuelos.

## 📋 Flujo Actualizado

### ANTES:
```
Usuario: "Busca vuelos de Caracas a Porlamar para mañana"
Bot: [Busca inmediatamente para 1 pasajero por defecto]
```

### AHORA:
```
Usuario: "Busca vuelos de Caracas a Porlamar para mañana"
Bot: "¿Para cuántas personas es el vuelo?"
Usuario: "2 personas"
Bot: [Busca vuelos para 2 pasajeros]
```

## 🔧 Detalles Técnicos

### Instrucción Agregada al System Prompt:

```
* OBLIGATORIO: Si NO mencionan cuántas personas viajan, 
  pregunta PRIMERO "¿Para cuántas personas es el vuelo?" 
  antes de buscar

* Si falta algún dato (origen, destino, fecha o número de pasajeros): 
  pregunta SOLO lo que falta
```

### Orden de Preguntas:

1. **Número de pasajeros** (si no se mencionó) ⭐ NUEVO
2. **Origen** (si no se mencionó)
3. **Destino** (si no se mencionó)
4. **Fecha** (si no se mencionó)
5. **Tipo de viaje** (ida o ida y vuelta, si no se mencionó)
6. **Fecha de regreso** (si es ida y vuelta y no se mencionó)
7. **Buscar vuelos** ✈️

## 💡 Ejemplos de Uso

### Ejemplo 1: Usuario no menciona número de pasajeros
```
Usuario: "Quiero volar a Miami mañana"
Bot: "¿Para cuántas personas es el vuelo?"
Usuario: "3"
Bot: [Busca vuelos para 3 pasajeros]
```

### Ejemplo 2: Usuario menciona número de pasajeros
```
Usuario: "Busca vuelos para 2 personas de CCS a PMV mañana"
Bot: [Busca directamente sin preguntar]
```

### Ejemplo 3: Falta múltiple información
```
Usuario: "Quiero volar a Porlamar"
Bot: "¿Para cuántas personas es el vuelo?"
Usuario: "1"
Bot: "¿Desde qué ciudad viajas?"
Usuario: "Caracas"
Bot: "¿Para qué fecha?"
Usuario: "Mañana"
Bot: [Busca vuelos]
```

## 📁 Archivos Modificados

- ✅ `gemini_agent_bot.py` - System prompt actualizado

## ✅ Beneficios

1. **Precisión** - Siempre busca para el número correcto de pasajeros
2. **Precios correctos** - Los precios se calculan según número de pasajeros
3. **Mejor experiencia** - Usuario sabe exactamente qué información dar
4. **Evita errores** - No asume 1 pasajero por defecto

## ✅ Estado

**Implementación completa y funcionando** 🦌👥✈️

El bot ahora preguntará SIEMPRE por el número de pasajeros antes de buscar vuelos!
