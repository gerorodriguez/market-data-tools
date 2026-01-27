"""
OMS WebSocket Connector
Maneja la conexión WebSocket con el servidor OMS.
Implementa las mejores prácticas de Primary:
- Heartbeat cada 30 segundos
- Máximo 1000 instrumentos por mensaje de suscripción
"""
import asyncio
import json
import logging
from typing import Callable, Optional, Dict, Any
import websockets
from websockets.exceptions import ConnectionClosed


class OMSWebSocketConnector:
    """
    Clase para manejar la conexión WebSocket con el servidor OMS.
    Implementa las mejores prácticas de Primary/Matba Rofex.
    """
    
    # Constantes según mejores prácticas
    HEARTBEAT_INTERVAL = 30  # segundos
    MAX_INSTRUMENTS_PER_SUBSCRIPTION = 1000  # máximo por mensaje
    
    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        """
        Inicializa el conector WebSocket.
        
        Args:
            url: URL del servidor WebSocket (ej: 'wss://api.lbo.xoms.com.ar')
            headers: Diccionario con headers adicionales para la conexión.
        """
        self.url = url
        self.headers = headers or {}
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.message_handler: Optional[Callable[[Dict[str, Any]], None]] = None
        self.error_handler: Optional[Callable[[Exception], None]] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    async def connect(self) -> bool:
        """
        Establece la conexión WebSocket con el servidor.
        
        Returns:
            True si la conexión fue exitosa, False en caso contrario.
        """
        try:
            self.logger.info(f'Conectando a {self.url}...')
            
            # Convertir headers a lista de tuplas (formato requerido por websockets)
            headers_list = None
            if self.headers:
                headers_list = [(key, value) for key, value in self.headers.items()]
            
            # Intentar con extra_headers (versiones recientes) o additional_headers (versiones antiguas)
            try:
                self.websocket = await websockets.connect(
                    self.url,
                    extra_headers=headers_list,
                    ping_interval=20,
                    ping_timeout=10
                )
            except TypeError:
                # Si extra_headers no funciona, intentar con additional_headers
                self.websocket = await websockets.connect(
                    self.url,
                    additional_headers=headers_list,
                    ping_interval=20,
                    ping_timeout=10
                )
            
            self.is_connected = True
            self.logger.info('Conexión WebSocket establecida exitosamente')
            
            # Iniciar tarea para recibir mensajes
            self._receive_task = asyncio.create_task(self._receive_messages())
            
            # Iniciar heartbeat según mejores prácticas (cada 30 segundos)
            self._heartbeat_task = asyncio.create_task(self._send_heartbeat())
            
            return True
        except Exception as e:
            self.logger.error(f'Error al conectar: {str(e)}')
            self.is_connected = False
            if self.error_handler:
                self.error_handler(e)
            return False
    
    async def disconnect(self):
        """
        Cierra la conexión WebSocket.
        """
        # Cancelar tarea de recepción
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        # Cancelar tarea de heartbeat
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            try:
                await self.websocket.close()
                self.logger.info('Conexión WebSocket cerrada')
            except Exception as e:
                self.logger.error(f'Error al cerrar conexión: {str(e)}')
        
        self.is_connected = False
        self.websocket = None
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """
        Envía un mensaje al servidor WebSocket.
        
        Args:
            message: Diccionario con el mensaje a enviar.
        
        Returns:
            True si el mensaje fue enviado exitosamente, False en caso contrario.
        """
        if not self.is_connected or not self.websocket:
            self.logger.error('No hay conexión WebSocket activa')
            return False
        
        try:
            message_json = json.dumps(message)
            await self.websocket.send(message_json)
            self.logger.info(f'Mensaje enviado: {message_json}')
            return True
        except ConnectionClosed:
            self.logger.error('La conexión WebSocket se cerró')
            self.is_connected = False
            return False
        except Exception as e:
            self.logger.error(f'Error al enviar mensaje: {str(e)}')
            if self.error_handler:
                self.error_handler(e)
            return False
    
    async def _receive_messages(self):
        """
        Tarea asíncrona para recibir mensajes del servidor.
        """
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    self.logger.info(f'Mensaje recibido: {message}')
                    
                    if self.message_handler:
                        self.message_handler(data)
                except json.JSONDecodeError as e:
                    self.logger.warning(f'Error al decodificar mensaje JSON: {str(e)}')
                except Exception as e:
                    self.logger.error(f'Error al procesar mensaje: {str(e)}')
        except ConnectionClosed:
            self.logger.info('Conexión WebSocket cerrada por el servidor')
            self.is_connected = False
        except asyncio.CancelledError:
            self.logger.info('Recepción de mensajes cancelada')
        except Exception as e:
            self.logger.error(f'Error en recepción de mensajes: {str(e)}')
            self.is_connected = False
            if self.error_handler:
                self.error_handler(e)
    
    def set_message_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """
        Establece el manejador de mensajes recibidos.
        
        Args:
            handler: Función que se llamará cuando se reciba un mensaje.
        """
        self.message_handler = handler
    
    def set_error_handler(self, handler: Callable[[Exception], None]):
        """
        Establece el manejador de errores.
        
        Args:
            handler: Función que se llamará cuando ocurra un error.
        """
        self.error_handler = handler
    
    async def _send_heartbeat(self):
        """
        Envía pings periódicos para mantener la conexión activa.
        Según las mejores prácticas de Primary: 1 latido cada 30 segundos.
        """
        try:
            while self.is_connected and self.websocket:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                
                if not self.is_connected or not self.websocket:
                    break
                
                try:
                    # Enviar ping al servidor
                    pong_waiter = await self.websocket.ping()
                    await asyncio.wait_for(pong_waiter, timeout=10)
                    self.logger.debug('Heartbeat enviado correctamente')
                
                except asyncio.TimeoutError:
                    self.logger.warning('Timeout esperando pong del servidor')
                    self.is_connected = False
                    break
                
                except Exception as e:
                    self.logger.error(f'Error enviando heartbeat: {str(e)}')
                    self.is_connected = False
                    break
        
        except asyncio.CancelledError:
            self.logger.debug('Heartbeat cancelado')
        except Exception as e:
            self.logger.error(f'Error en tarea de heartbeat: {str(e)}')
            self.is_connected = False
