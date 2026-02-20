#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
from dotenv import load_dotenv
load_dotenv()

from gemini_agent_bot import gemini_agent_bot

test_phone = "584121234567"

print("PRUEBA 1: Activar bot")
result1 = gemini_agent_bot.handle_message(test_phone, "cervo ai")
print(f"Resultado: {result1}")

print("\nPRUEBA 2: Mensaje de prueba")
result2 = gemini_agent_bot.handle_message(test_phone, "hola")
print(f"Resultado: {result2}")

print("\nPRUEBA COMPLETADA")
