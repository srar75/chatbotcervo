"""
WSGI entry point para Apache
Con logging detallado para diagnosticar errores
"""
import sys
import os
import logging

# Configurar logging ANTES de todo
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger('wsgi')

# Ruta del proyecto en el servidor
PROJECT_PATH = '/home/ftp/watiapp'

logger.info(f"=== WSGI Iniciando ===")
logger.info(f"PROJECT_PATH: {PROJECT_PATH}")
logger.info(f"Python executable: {sys.executable}")
logger.info(f"Python version: {sys.version}")

# Verificar que el directorio existe
if not os.path.exists(PROJECT_PATH):
    logger.error(f"ERROR: El directorio {PROJECT_PATH} NO EXISTE!")
else:
    logger.info(f"Directorio {PROJECT_PATH} existe")
    logger.info(f"Contenido: {os.listdir(PROJECT_PATH)}")

# Agregar el directorio del proyecto al path
sys.path.insert(0, PROJECT_PATH)
logger.info(f"sys.path actualizado")

# Cambiar al directorio del proyecto
os.chdir(PROJECT_PATH)
logger.info(f"Directorio actual: {os.getcwd()}")

# Cargar variables de entorno
try:
    from dotenv import load_dotenv
    env_path = os.path.join(PROJECT_PATH, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        logger.info(f"Variables de entorno cargadas desde {env_path}")
    else:
        logger.error(f"ERROR: Archivo .env NO EXISTE en {env_path}")
except ImportError as e:
    logger.error(f"ERROR: No se pudo importar dotenv: {e}")
except Exception as e:
    logger.error(f"ERROR cargando .env: {e}")

# Importar la aplicación Flask
try:
    logger.info("Importando app Flask...")
    from app import app as application
    logger.info("App Flask importada correctamente!")
except ImportError as e:
    logger.error(f"ERROR ImportError: {e}")
    logger.error(f"sys.path: {sys.path}")
    # Crear una app de error para mostrar el problema
    from flask import Flask
    application = Flask(__name__)
    
    @application.route('/')
    def error_page():
        return f"Error de importación: {str(e)}", 500
except Exception as e:
    logger.error(f"ERROR general importando app: {e}")
    import traceback
    logger.error(traceback.format_exc())
    # Crear una app de error
    from flask import Flask
    application = Flask(__name__)
    
    @application.route('/')
    def error_page():
        return f"Error: {str(e)}", 500

logger.info("=== WSGI Configurado ===")

if __name__ == "__main__":
    application.run()
