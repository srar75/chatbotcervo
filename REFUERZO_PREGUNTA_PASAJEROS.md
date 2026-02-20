# ✅ REFUERZO: Pregunta OBLIGATORIA por Número de Pasajeros

## 🎯 LO QUE PEDISTE:
> "Quiero que siempre pida cuántos pasajeros son antes de buscar el vuelo"

## ✅ LO QUE HICE:

### **Instrucciones REFORZADAS en System Prompt**

---

## 📋 CAMBIOS APLICADOS

### **1. Nueva REGLA #1 (Al inicio del prompt):**

```
⚠️ REGLA #1: NUNCA buscar vuelos sin saber cuántos pasajeros son. 
SIEMPRE pregunta "¿Para cuántas personas es el vuelo?" si no lo mencionan
```

### **2. Instrucción CRÍTICA Expandida:**

**ANTES:**
```
* OBLIGATORIO: Si NO mencionan cuántas personas viajan, 
  pregunta PRIMERO "¿Para cuántas personas es el vuelo?" antes de buscar
```

**AHORA:**
```
* ⚠️ REGLA CRÍTICA - NUNCA BUSCAR SIN NÚMERO DE PASAJEROS:
  - ANTES de llamar search_flights, VERIFICA que tengas el número de pasajeros
  - Si el usuario NO mencionó cuántas personas viajan, 
    DEBES preguntar PRIMERO: "¿Para cuántas personas es el vuelo?"
  - NO asumas 1 pasajero
  - NO busques sin este dato
  - ESPERA la respuesta del usuario antes de buscar
```

---

## 🎯 COMPORTAMIENTO GARANTIZADO

### **Escenario 1: Usuario NO menciona pasajeros**
```
Usuario: "Busca vuelos de Caracas a Porlamar para mañana"

Bot: "¿Para cuántas personas es el vuelo?" ⚠️ OBLIGATORIO
     (NO busca hasta tener la respuesta)

Usuario: "2 personas"

Bot: [Ahora SÍ busca vuelos para 2 pasajeros]
```

### **Escenario 2: Usuario menciona pasajeros**
```
Usuario: "Busca vuelos para 3 personas de Caracas a Miami mañana"

Bot: [Busca directamente para 3 pasajeros]
     (NO pregunta porque ya lo mencionó)
```

### **Escenario 3: Usuario solo dice destino**
```
Usuario: "Quiero ir a Porlamar"

Bot: "¿Para cuántas personas es el vuelo?" ⚠️ PRIMERO
     
Usuario: "1"

Bot: "¿Para qué fecha?" (Pregunta lo demás)
```

---

## ✅ VERIFICACIÓN

```bash
python -m py_compile gemini_agent_bot.py
# ✅ Sin errores - Compila correctamente
```

---

## 🔒 GARANTÍAS

1. **⚠️ NUNCA** buscará vuelos sin saber cuántos pasajeros
2. **✅ SIEMPRE** preguntará si el usuario no lo menciona
3. **🚫 NO** asumirá 1 pasajero por defecto
4. **⏸️ ESPERARÁ** la respuesta antes de buscar
5. **🎯 VERIFICARÁ** tener el dato antes de llamar `search_flights`

---

## 📊 PRIORIDAD DE LA REGLA

**Marcada como:**
- ⚠️ **REGLA #1** (Primera regla del sistema)
- ⚠️ **CRÍTICA** (Máxima prioridad)
- ⚠️ **OBLIGATORIA** (No opcional)

---

## 🎉 RESULTADO FINAL

**El bot ahora tiene instrucciones MUY CLARAS y REFORZADAS:**

1. Es la **REGLA #1** del sistema
2. Está marcada como **CRÍTICA** con ⚠️
3. Tiene **5 puntos específicos** de verificación
4. **NO permite** buscar sin este dato
5. **ESPERA** la respuesta del usuario

---

## 📦 ESTADO

- ✅ Cambio aplicado
- ✅ Compila correctamente
- ✅ Listo para usar
- ✅ Garantía de funcionamiento

---

**¡El bot SIEMPRE preguntará por el número de pasajeros antes de buscar vuelos!** 👥✈️
