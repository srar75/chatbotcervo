#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Servicio para extraer datos de documentos (cédula/pasaporte) usando Gemini Vision
"""
import os
import logging
import requests
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class DocumentExtractor:
    """Extrae datos de cédulas y pasaportes usando Gemini Vision"""
    
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY o GOOGLE_API_KEY no configurada")
        
        self.client = genai.Client(api_key=api_key)
        self.model = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
    
    def extract_from_image(self, image_url: str) -> dict:
        """
        Extrae datos de una imagen de cédula o pasaporte
        
        Args:
            image_url: URL de la imagen del documento
            
        Returns:
            {
                "success": bool,
                "document_type": "cedula" | "pasaporte" | "unknown",
                "data": {
                    "nombre": str,
                    "apellido": str,
                    "cedula": str (solo para cédula),
                    "pasaporte": str (solo para pasaporte),
                    "nacionalidad": str,
                    "fecha_nacimiento": str (YYYY-MM-DD),
                    "sexo": "M" | "F",
                    "fecha_vencimiento": str (YYYY-MM-DD, solo pasaporte)
                },
                "missing_fields": list,  # Campos que no se pudieron extraer
                "error": str (si hay error)
            }
        """
        try:
            logger.info(f"Extrayendo datos de documento desde: {image_url}")
            
            # Usar el servicio de WATI para descargar la imagen con autenticación correcta
            from wati_service import wati_service
            
            download_result = wati_service.download_media(image_url)
            
            if not download_result.get('success'):
                error_msg = download_result.get('error', 'Error desconocido')
                logger.error(f"Error descargando imagen con WATI: {error_msg}")
                return {
                    "success": False,
                    "error": f"No se pudo descargar la imagen: {error_msg}"
                }
            
            image_data = download_result.get('content')
            if not image_data or len(image_data) < 100:
                logger.error(f"Imagen descargada vacía o muy pequeña: {len(image_data) if image_data else 0} bytes")
                return {
                    "success": False,
                    "error": "La imagen descargada está vacía o corrupta"
                }
            
            logger.info(f"Imagen descargada exitosamente. Tamaño: {len(image_data)} bytes")
            
            # Prompt para extraer datos
            prompt = """Analiza esta imagen de un documento de identidad (cédula venezolana o pasaporte).

Extrae TODOS los datos que puedas identificar claramente y devuélvelos en formato JSON con esta estructura EXACTA:

{
  "document_type": "cedula" o "pasaporte",
  "nombre": "nombre(s) de la persona",
  "apellido": "apellido(s) de la persona",
  "numero_documento": "número de cédula o pasaporte",
  "nacionalidad": "código de país de 2 letras (ej: VE, US, CO)",
  "fecha_nacimiento": "YYYY-MM-DD",
  "sexo": "M" o "F" (H=M, V=M, F=F, M=F si es mujer),
  "fecha_vencimiento": "YYYY-MM-DD" (solo si es pasaporte y está visible),
  "fecha_vencimiento": "YYYY-MM-DD" (solo si es pasaporte y está visible),
  "estado_civil": "SOLTERO/A", "CASADO/A", "VIUDO/A", "DIVORCIADO/A" (si está visible)
}

REGLAS IMPORTANTES:
- Si es cédula venezolana, document_type debe ser "cedula"
- Si es pasaporte, document_type debe ser "pasaporte"
- Para cédula venezolana, la nacionalidad es "VE"
- El número de documento debe ser SOLO números (sin guiones, puntos ni letras)
- Si un campo NO está visible o legible, usa null
- Nombres y apellidos en MAYÚSCULAS
- Fechas siempre en formato YYYY-MM-DD
- Sexo: "M" para masculino, "F" para femenino

Devuelve SOLO el JSON, sin texto adicional."""

            # Llamar a Gemini Vision
            # Usar formato correcto para contenido multimodal
            import base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": image_base64
                                }
                            }
                        ]
                    }
                ]
            )
            
            # Extraer respuesta
            if not response or not response.text:
                return {
                    "success": False,
                    "error": "Gemini no devolvió respuesta"
                }
            
            result_text = response.text.strip()
            logger.info(f"Respuesta de Gemini: {result_text}")
            
            # Limpiar respuesta (quitar markdown si existe)
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            # Parsear JSON
            import json
            try:
                extracted_data = json.loads(result_text)
            except json.JSONDecodeError as e:
                logger.error(f"Error parseando JSON: {e}\nTexto: {result_text}")
                return {
                    "success": False,
                    "error": "No se pudo interpretar la respuesta del modelo"
                }
            
            # Validar y normalizar datos
            document_type = extracted_data.get('document_type', 'unknown')
            
            # Construir datos normalizados
            # Solo guardamos lo que es útil, sin requerir campos innecesarios
            data = {
                "nombre": extracted_data.get('nombre'),
                "apellido": extracted_data.get('apellido'),
                "nacionalidad": extracted_data.get('nacionalidad', 'VE'),
                # Estos campos son opcionales, se extraen si están disponibles
                "fecha_nacimiento": extracted_data.get('fecha_nacimiento'),
                "sexo": extracted_data.get('sexo'),
                "estado_civil": extracted_data.get('estado_civil'),
                "fecha_nacimiento": extracted_data.get('fecha_nacimiento'),
                "sexo": extracted_data.get('sexo'),
                "estado_civil": extracted_data.get('estado_civil')
            }
            
            # LÓGICA DE INFERENCIA DE SEXO POR ESTADO CIVIL
            if not data.get('sexo') and data.get('estado_civil'):
                civil = str(data.get('estado_civil', '')).upper()
                # Verificar terminaciones masculinas
                if 'SOLTERO' in civil or 'CASADO' in civil or 'VIUDO' in civil or 'DIVORCIADO' in civil:
                    data['sexo'] = 'M'
                # Verificar terminaciones femeninas
                elif 'SOLTERA' in civil or 'CASADA' in civil or 'VIUDA' in civil or 'DIVORCIADA' in civil:
                    data['sexo'] = 'F'
            
            # Agregar número de documento según tipo
            numero_doc = extracted_data.get('numero_documento')
            if document_type == 'cedula':
                data['cedula'] = numero_doc
                data['tipo_documento'] = 'CI'
            elif document_type == 'pasaporte':
                data['pasaporte'] = numero_doc
                data['tipo_documento'] = 'P'
                data['fecha_vencimiento'] = extracted_data.get('fecha_vencimiento')
            
            # Identificar campos faltantes
            # SOLO los campos REALMENTE necesarios según tipo de vuelo
            # VUELOS NACIONALES: nombre, apellido, cédula/pasaporte, teléfono, email
            # VUELOS INTERNACIONALES: + país nacimiento, país documento, vencimiento
            missing_fields = []
            
            # Campos básicos obligatorios (para TODOS los vuelos)
            required_fields = ['nombre', 'apellido']
            
            if document_type == 'cedula':
                required_fields.append('cedula')
            elif document_type == 'pasaporte':
                required_fields.append('pasaporte')
            else:
                # Si no detectó el tipo, asumimos que necesita algún documento
                if not data.get('cedula') and not data.get('pasaporte'):
                    required_fields.append('cedula')  # O pasaporte
            
            # Verificar campos de documento
            for field in required_fields:
                if not data.get(field):
                    missing_fields.append(field)
            
            # Agregar sexo si falta
            if not data.get('sexo'):
                missing_fields.append('sexo')

            # SIEMPRE agregar teléfono y email como faltantes (al final)
            missing_fields.append('telefono')
            missing_fields.append('email')
            
            return {
                "success": True,
                "document_type": document_type,
                "data": data,
                "missing_fields": missing_fields
            }
            
        except requests.RequestException as e:
            logger.error(f"Error descargando imagen: {str(e)}")
            return {
                "success": False,
                "error": f"Error descargando imagen: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error extrayendo datos de documento: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


# Instancia global
document_extractor = DocumentExtractor()
