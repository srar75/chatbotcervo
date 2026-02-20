#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script de prueba para verificar el bot"""

import sys
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Importar el bot
from gemini_agent_bot import gemini_agent_bot

# Número de prueba
test_phone = "584121234567"

print("=" * 60)
print("PRUEBA DEL BOT CERVO AI")
print("=" * 60)

# Prueba 1: Activar el bot
print("\n1. Activando bot con 'cervo ai'...")
try:
    result = gemini_agent_bot.handle_message(test_phone, "cervo ai")
    print(f"   ✅ Resultado: {result}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Prueba 2: Enviar mensaje de prueba
print("\n2. Enviando mensaje de prueba...")
try:
    result = gemini_agent_bot.handle_message(test_phone, "hola")
    print(f"   ✅ Resultado: {result}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("PRUEBA COMPLETADA")
print("=" * 60)
