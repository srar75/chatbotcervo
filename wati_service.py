"""
Servicio de integración con WATI API
"""
import requests
import logging
from config import Config

logger = logging.getLogger(__name__)


class WatiService:
    """Servicio para enviar mensajes a través de WATI"""
    
    def __init__(self):
        self.base_url = Config.WATI_API_URL
        # Evitar duplicar "Bearer " si ya está en el token
        token = Config.WATI_API_TOKEN
        if token.startswith('Bearer '):
            auth_header = token
        else:
            auth_header = f'Bearer {token}'
        self.headers = {
            'Authorization': auth_header,
            'Content-Type': 'application/json'
        }
        # Propiedades de compatibilidad
        self.api_url = self.base_url
        self.api_token = token
    
    def send_message(self, phone: str, message: str):
        """
        Envía un mensaje de texto simple a través de WATI
        Divide mensajes largos en múltiples partes si es necesario
        """
        try:
            # Limpiar número de teléfono
            phone = phone.replace('+', '').replace(' ', '').replace('-', '')
            
            # Protección contra mensajes infinitos o repetitivos
            if len(message) > 20000:
                logger.warning(f"Mensaje extremadamente largo detectado ({len(message)} chars). Truncando.")
                message = message[:20000] + "\n\n...(Mensaje truncado por seguridad)"

            # Dividir mensaje si es muy largo (máximo 3500 caracteres por mensaje para estar seguros)
            max_length = 3500
            if len(message) > max_length:  # Dividir si supera el límite
                # Dividir en partes de forma ordenada
                parts = []
                current_part = ""
                lines = message.split('\n')
                
                for i, line in enumerate(lines):
                    test_part = current_part + ('\n' if current_part else '') + line
                    
                    if len(test_part) > max_length and current_part:
                        parts.append(current_part.strip())
                        current_part = line
                    else:
                        current_part = test_part
                
                if current_part.strip():
                    parts.append(current_part.strip())
                
                # Limitar a máximo 5 partes para evitar bucles de spam
                if len(parts) > 5:
                    logger.warning(f"Mensaje dividido en demasiadas partes ({len(parts)}). Limitando a 5.")
                    parts = parts[:5]
                    parts[-1] += "\n\n...(Contenido adicional omitido)"

                # Enviar cada parte con numeración
                logger.info(f"Mensaje largo dividido en {len(parts)} partes")
                for i, part in enumerate(parts, 1):
                    if len(parts) > 1:
                        part_message = f"[Parte {i}/{len(parts)}]\n\n{part}"
                    else:
                        part_message = part
                    
                    result = self._send_single_message(phone, part_message)
                    if not result.get('success'):
                        return result
                    if i < len(parts):
                        import time
                        time.sleep(1)
                
                return {'success': True, 'response': 'Mensaje enviado en partes'}
            else:
                return self._send_single_message(phone, message)
                
        except Exception as e:
            logger.error(f"Excepción enviando mensaje: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _format_whatsapp_text(self, text: str) -> str:
        """Formatea el texto para WhatsApp manteniendo negritas con asteriscos"""
        if not text:
            return text
        # WhatsApp usa *texto* para negritas (un asterisco, no dos)
        # Convertir **texto** a *texto*
        import re
        # Reemplazar **texto** por *texto*
        formatted = re.sub(r'\*\*([^*]+)\*\*', r'*\1*', text)
        return formatted
    
    def _send_single_message(self, phone: str, message: str):
        """Envía un solo mensaje a través de WATI"""
        try:
            # Formatear texto para WhatsApp
            formatted_message = self._format_whatsapp_text(message)
            
            # Verificar que el mensaje no esté vacío
            if not formatted_message or not formatted_message.strip():
                logger.error(f"Mensaje vacío después de formatear. Original: {message[:100]}")
                formatted_message = message  # Usar mensaje original si el formateado está vacío
            
            logger.info(f"Enviando mensaje a WATI: phone={phone}")
            logger.info(f"WATI BASE URL: {self.base_url}")
            logger.info(f"WATI TOKEN (primeros 50 chars): {self.headers.get('Authorization', '')[:50]}...")
            
            # Si el mensaje es corto, usar query parameter
            # Si es largo, usar POST body
            if len(formatted_message) < 2000:
                url = f"{self.base_url}/api/v1/sendSessionMessage/{phone}?messageText={requests.utils.quote(formatted_message)}"
                logger.info(f"WATI URL COMPLETA: {url[:150]}...")
                response = requests.post(url, headers=self.headers, timeout=30)
            else:
                # Mensaje largo: usar POST body
                url = f"{self.base_url}/api/v1/sendSessionMessage/{phone}"
                logger.info(f"WATI URL COMPLETA: {url}")
                # WATI espera form data, no JSON
                response = requests.post(url, data={'messageText': formatted_message}, headers={'Authorization': self.headers['Authorization']}, timeout=30)
            
            logger.info(f"Respuesta WATI: Status={response.status_code}")
            logger.info(f"Respuesta WATI Body: {response.text[:500]}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok') == True or result.get('result') == 'success' or result.get('result') == True:
                    logger.info(f"Mensaje enviado exitosamente a {phone}")
                    return {'success': True, 'response': result}
                else:
                    # Si es "Invalid Contact", solo advertir pero no fallar
                    if result.get('info') == 'Invalid Contact':
                        logger.warning(f"Contacto {phone} no registrado en WATI (modo test local)")
                        return {'success': True, 'response': result, 'warning': 'Contacto no registrado'}
                    logger.warning(f"WATI respondió 200 pero sin éxito: {result}")
                    return {'success': False, 'response': result}
            else:
                logger.error(f"Error enviando mensaje: {response.status_code} - {response.text}")
                return {'success': False, 'error': response.text}
                
        except Exception as e:
            logger.error(f"Error en _send_single_message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_template_message(self, phone: str, template_name: str, parameters: list = None):
        """
        Envía un mensaje de plantilla a través de WATI
        """
        try:
            phone = phone.replace('+', '').replace(' ', '').replace('-', '')
            
            url = f"{self.base_url}/api/v1/sendTemplateMessage/{phone}"
            
            payload = {
                "template_name": template_name,
                "broadcast_name": "cervo_bot"
            }
            
            if parameters:
                payload["parameters"] = [{"name": f"param{i+1}", "value": p} for i, p in enumerate(parameters)]
            
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"Template enviado exitosamente a {phone}")
                return {'success': True, 'response': response.json()}
            else:
                logger.error(f"Error enviando template: {response.status_code} - {response.text}")
                return {'success': False, 'error': response.text}
                
        except Exception as e:
            logger.error(f"Excepción enviando template: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_interactive_buttons(self, phone: str, message: str, buttons: list):
        """
        Envía un mensaje con botones interactivos
        """
        try:
            phone = phone.replace('+', '').replace(' ', '').replace('-', '')
            
            url = f"{self.base_url}/api/v1/sendInteractiveButtonsMessage"
            
            payload = {
                "whatsappNumber": phone,
                "type": "button",
                "body": {
                    "text": message
                },
                "action": {
                    "buttons": [{"type": "reply", "reply": {"id": btn['id'], "title": btn['title']}} for btn in buttons[:3]]
                }
            }
            
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"Botones enviados exitosamente a {phone}")
                return {'success': True, 'response': response.json()}
            else:
                logger.error(f"Error enviando botones: {response.status_code} - {response.text}")
                # Fallback: enviar mensaje de texto normal
                return self.send_message(phone, message)
                
        except Exception as e:
            logger.error(f"Excepción enviando botones: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_list_message(self, phone: str, message: str, button_text: str, sections: list):
        """
        Envía un mensaje con lista de opciones
        """
        try:
            phone = phone.replace('+', '').replace(' ', '').replace('-', '')
            
            url = f"{self.base_url}/api/v1/sendInteractiveListMessage"
            
            payload = {
                "whatsappNumber": phone,
                "type": "list",
                "body": {
                    "text": message
                },
                "action": {
                    "button": button_text,
                    "sections": sections
                }
            }
            
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return {'success': True, 'response': response.json()}
            else:
                # Fallback: enviar mensaje de texto
                return self.send_message(phone, message)
                
        except Exception as e:
            logger.error(f"Excepción enviando lista: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def download_media(self, media_url: str) -> dict:
        """
        Descarga media (imagen) desde WATI usando autenticación
        Returns: {'success': True, 'content': bytes, 'content_type': str} o {'success': False, 'error': str}
        """
        try:
            logger.info(f"Descargando media desde: {media_url}")
            
            # Intentar primero sin autenticación (por si es URL pública)
            try:
                response = requests.get(media_url, timeout=30)
                if response.status_code == 200 and len(response.content) > 100:
                    logger.info(f"Media descargada exitosamente (pública): {len(response.content)} bytes")
                    return {
                        'success': True, 
                        'content': response.content,
                        'content_type': response.headers.get('Content-Type', 'image/jpeg')
                    }
            except Exception as e:
                logger.info(f"Descarga pública falló, intentando con auth: {e}")
            
            # Si falló, intentar con autenticación WATI
            headers = {
                'Authorization': self.headers.get('Authorization', ''),
                'Accept': 'image/*,*/*'
            }
            
            response = requests.get(media_url, headers=headers, timeout=30)
            
            if response.status_code == 200 and len(response.content) > 100:
                logger.info(f"Media descargada exitosamente (con auth): {len(response.content)} bytes")
                return {
                    'success': True, 
                    'content': response.content,
                    'content_type': response.headers.get('Content-Type', 'image/jpeg')
                }
            
            # Si la URL contiene un ID de media, intentar obtener mediante API de WATI
            if '/media/' in media_url or 'mediaId' in media_url:
                # Extraer media ID
                import re
                media_id_match = re.search(r'media[/=]([a-zA-Z0-9_-]+)', media_url)
                if media_id_match:
                    media_id = media_id_match.group(1)
                    api_url = f"{self.base_url}/api/v1/getMedia/{media_id}"
                    logger.info(f"Intentando API de media: {api_url}")
                    
                    response = requests.get(api_url, headers=self.headers, timeout=30)
                    if response.status_code == 200:
                        # La respuesta puede ser la imagen directa o un JSON con URL
                        content_type = response.headers.get('Content-Type', '')
                        if 'image' in content_type:
                            return {
                                'success': True,
                                'content': response.content,
                                'content_type': content_type
                            }
                        else:
                            # Puede ser JSON con URL real
                            try:
                                data = response.json()
                                real_url = data.get('url') or data.get('mediaUrl')
                                if real_url:
                                    final_response = requests.get(real_url, timeout=30)
                                    if final_response.status_code == 200:
                                        return {
                                            'success': True,
                                            'content': final_response.content,
                                            'content_type': final_response.headers.get('Content-Type', 'image/jpeg')
                                        }
                            except:
                                pass
            
            logger.error(f"No se pudo descargar media: {response.status_code}")
            return {'success': False, 'error': f'Error descargando: HTTP {response.status_code}'}
            
        except Exception as e:
            logger.error(f"Excepción descargando media: {str(e)}")
            return {'success': False, 'error': str(e)}


# Instancia global
wati_service = WatiService()
