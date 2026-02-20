# ✅ CHECKLIST PARA SUBIR AL SERVIDOR

## 📋 LISTA DE VERIFICACIÓN COMPLETA

---

## ANTES DE SUBIR

### ✅ Verificación Local
- [x] `gemini_agent_bot.py` compila sin errores
- [x] `document_extractor.py` compila sin errores
- [x] Todas las funcionalidades implementadas
- [x] Documentación completa generada

### ✅ Archivos Preparados
- [x] `gemini_agent_bot.py` (modificado)
- [x] `document_extractor.py` (nuevo)
- [x] `.env` (modificar GEMINI_MODEL)

---

## DURANTE LA SUBIDA

### 1. BACKUP DEL SERVIDOR ⚠️
```bash
# Conectar al servidor
ssh usuario@servidor

# Crear directorio de backup
mkdir -p ~/backups/cervo-$(date +%Y%m%d)

# Hacer backup de archivos actuales
cp /ruta/chatbot/gemini_agent_bot.py ~/backups/cervo-$(date +%Y%m%d)/
cp /ruta/chatbot/.env ~/backups/cervo-$(date +%Y%m%d)/

# Verificar backup
ls -la ~/backups/cervo-$(date +%Y%m%d)/
```

### 2. SUBIR ARCHIVOS 📤
```bash
# Desde tu computadora local
scp gemini_agent_bot.py usuario@servidor:/ruta/chatbot/
scp document_extractor.py usuario@servidor:/ruta/chatbot/
```

### 3. MODIFICAR .ENV ⚙️
```bash
# En el servidor
cd /ruta/chatbot
nano .env

# Cambiar esta línea:
# DE:   GEMINI_MODEL=gemini-3-flash-preview
# A:    GEMINI_MODEL=gemini-2.5-flash

# Guardar: Ctrl+O, Enter, Ctrl+X
```

### 4. VERIFICAR PERMISOS 🔐
```bash
# Asegurar permisos correctos
chmod 644 gemini_agent_bot.py
chmod 644 document_extractor.py
chmod 600 .env

# Verificar
ls -la gemini_agent_bot.py document_extractor.py .env
```

### 5. PROBAR COMPILACIÓN 🧪
```bash
# Probar que los archivos compilan
python3 -m py_compile gemini_agent_bot.py
python3 -m py_compile document_extractor.py

# Si no hay errores, continuar
```

### 6. REINICIAR SERVICIO 🔄
```bash
# Opción 1: Si usas systemd
sudo systemctl restart cervo-bot

# Opción 2: Si usas supervisor
sudo supervisorctl restart cervo-bot

# Opción 3: Si usas pm2
pm2 restart cervo-bot

# Opción 4: Manualmente
# Detener proceso actual
pkill -f "python.*app.py"
# Iniciar nuevo
nohup python3 app.py > cervo.log 2>&1 &
```

---

## DESPUÉS DE SUBIR

### 7. VERIFICAR LOGS 📊
```bash
# Ver logs en tiempo real
tail -f /var/log/cervo-bot.log
# O según tu configuración:
tail -f cervo.log
tail -f nohup.out

# Buscar errores
grep -i error /var/log/cervo-bot.log
```

### 8. PROBAR FUNCIONALIDADES ✅

#### Prueba 1: Activación
```
Enviar por WhatsApp: "cervo ai"
Esperado: Bot se activa correctamente
```

#### Prueba 2: Fix de Fechas
```
Usuario: "Busca vuelos para el 7 de febrero"
Esperado: Busca para 2026-02-07 (NO 2027)
```

#### Prueba 3: Pregunta por Pasajeros
```
Usuario: "Busca vuelos a Miami"
Esperado: "¿Para cuántas personas es el vuelo?"
```

#### Prueba 4: Precios por Clase
```
Usuario: "Quiero el vuelo 1"
Esperado: Muestra TODAS las clases con precios individuales
```

#### Prueba 5: Precio Correcto
```
Usuario: "Clase Q" (que cuesta $91.99)
Esperado: Confirmación muestra "$91.99" (NO $65.00)
```

#### Prueba 6: Extracción de Documento
```
Usuario: [Envía foto de cédula]
Esperado: Extrae datos y muestra confirmación
```

---

## MONITOREO POST-DESPLIEGUE

### Primeras 24 Horas
- [ ] Revisar logs cada 2 horas
- [ ] Verificar que no hay errores críticos
- [ ] Confirmar que las reservas se crean correctamente
- [ ] Validar que la extracción de documentos funciona

### Primera Semana
- [ ] Revisar logs diariamente
- [ ] Recopilar feedback de usuarios
- [ ] Monitorear uso de Gemini API
- [ ] Verificar tasa de éxito de extracción

---

## ROLLBACK (Si algo sale mal) ⚠️

### Pasos para Revertir
```bash
# 1. Detener servicio
sudo systemctl stop cervo-bot

# 2. Restaurar archivos del backup
cp ~/backups/cervo-$(date +%Y%m%d)/gemini_agent_bot.py /ruta/chatbot/
cp ~/backups/cervo-$(date +%Y%m%d)/.env /ruta/chatbot/

# 3. Eliminar document_extractor.py (si causa problemas)
rm /ruta/chatbot/document_extractor.py

# 4. Reiniciar servicio
sudo systemctl start cervo-bot

# 5. Verificar que funciona
tail -f /var/log/cervo-bot.log
```

---

## CONTACTOS DE EMERGENCIA

### Si hay problemas:
1. **Revisar logs** primero
2. **Verificar .env** (GEMINI_API_KEY, GEMINI_MODEL)
3. **Comprobar permisos** de archivos
4. **Validar conexión** a Gemini API
5. **Hacer rollback** si es necesario

---

## ✅ CHECKLIST FINAL

Antes de dar por terminado:

- [ ] Backup realizado
- [ ] Archivos subidos
- [ ] .env modificado
- [ ] Permisos correctos
- [ ] Compilación exitosa
- [ ] Servicio reiniciado
- [ ] Logs sin errores
- [ ] Prueba 1: Activación ✅
- [ ] Prueba 2: Fechas ✅
- [ ] Prueba 3: Pasajeros ✅
- [ ] Prueba 4: Precios ✅
- [ ] Prueba 5: Precio correcto ✅
- [ ] Prueba 6: Extracción ✅
- [ ] Monitoreo configurado

---

## 🎉 ¡LISTO!

Si todos los checks están marcados, **¡el despliegue fue exitoso!** 🦌✈️

---

## 📞 SOPORTE

Si necesitas ayuda:
1. Revisa los logs
2. Consulta la documentación generada
3. Verifica la configuración de .env
4. Prueba el rollback si es necesario

**¡Éxito con el despliegue!** 🚀
