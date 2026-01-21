"""
OMS Authentication
Maneja la autenticación con el servidor OMS para obtener el token.
"""
import os
import logging
from typing import Optional
import aiohttp
from dotenv import load_dotenv
import pathlib

# Cargar variables de entorno desde .env
script_dir = pathlib.Path(__file__).parent.absolute()
env_path = script_dir / '.env'
load_dotenv(dotenv_path=env_path)
load_dotenv()


class OMSAuth:
    """
    Clase para manejar la autenticación con el servidor OMS.
    """
    
    def __init__(self, auth_url: Optional[str] = None):
        """
        Inicializa el cliente de autenticación.
        
        Args:
            auth_url: URL del endpoint de autenticación (opcional, se construye desde OMS_HOST si no se proporciona).
        """
        # Obtener host del .env
        oms_host = os.getenv('OMS_HOST', 'oms_host')
        
        # Construir URL de autenticación
        if auth_url:
            self.auth_url = auth_url
        else:
            # Asegurar que el host no tenga protocolo
            oms_host = oms_host.replace('https://', '').replace('http://', '').replace('wss://', '').replace('ws://', '')
            self.auth_url = f'https://{oms_host}/auth/getToken'
        
        self.token: Optional[str] = None
        self.logger = logging.getLogger(__name__)
        
        # Obtener credenciales del .env
        self.username = os.getenv('OMS_USER')
        self.password = os.getenv('OMS_PASSWORD')
        
        if not self.username or not self.password:
            raise ValueError(
                'Las variables OMS_USER y OMS_PASSWORD deben estar definidas en el archivo .env'
            )
    
    async def get_token(self) -> Optional[str]:
        """
        Obtiene el token de autenticación del servidor OMS.
        El token viene en el header X-Auth-Token de la respuesta.
        
        Returns:
            El token de autenticación si la solicitud fue exitosa, None en caso contrario.
        """
        try:
            self.logger.info('Obteniendo token de autenticación...')
            
            headers = {
                'X-Username': self.username,
                'X-Password': self.password
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.auth_url, headers=headers) as response:
                    if response.status == 200:
                        # El token viene en el header X-Auth-Token
                        token = response.headers.get('X-Auth-Token') or response.headers.get('x-auth-token')
                        
                        if not token:
                            self.logger.error('No se encontró el header X-Auth-Token en la respuesta')
                            return None
                        
                        token = token.strip()
                        
                        if not token:
                            self.logger.error('El token recibido está vacío')
                            return None
                        
                        self.token = token
                        self.logger.info('Token obtenido exitosamente')
                        return self.token
                    else:
                        error_text = await response.text()
                        self.logger.error(
                            f'Error al obtener token. Status: {response.status}, '
                            f'Respuesta: {error_text[:200]}'
                        )
                        return None
        except aiohttp.ClientError as e:
            self.logger.error(f'Error de conexión al obtener token: {str(e)}')
            return None
        except Exception as e:
            self.logger.error(f'Error inesperado al obtener token: {str(e)}')
            return None
    
    def get_token_sync(self) -> Optional[str]:
        """
        Obtiene el token de forma síncrona (wrapper para compatibilidad).
        
        Returns:
            El token de autenticación si la solicitud fue exitosa, None en caso contrario.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.get_token())
