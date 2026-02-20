#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para iniciar Cervo AI
"""
import os
import sys

def main():
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║                                                            ║
    ║           🦌 CERVO AI - Chatbot de Vuelos 🤖              ║
    ║                                                            ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    # Verificar que existe el archivo .env
    if not os.path.exists('.env'):
        print("❌ ERROR: No se encontró el archivo .env")
        print("   Por favor crea el archivo .env con las credenciales necesarias")
        sys.exit(1)
    
    print("✅ Archivo .env encontrado")
    print("🚀 Iniciando servidor Flask...")
    print("📡 El servidor estará disponible en: http://localhost:5000")
    print("🧪 Interfaz de prueba: http://localhost:5000/test")
    print("\n⚠️  Presiona Ctrl+C para detener el servidor\n")
    
    # Importar y ejecutar app
    from app import app
    from config import Config
    
    app.run(
        host='0.0.0.0',
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Servidor detenido. ¡Hasta pronto!")
        sys.exit(0)
