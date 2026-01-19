"""
OMS Client
Implementación del cliente que utiliza el OMSWebSocketConnector
para enviar mensajes al servidor OMS.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional

from oms_websocket_connector import OMSWebSocketConnector
from oms_auth import OMSAuth
from market_data_store import MarketDataStore


class OMSClient:
    """
    Cliente para interactuar con el servidor OMS mediante WebSocket.
    """

    def __init__(self, url: str = 'wss://api.lbo.xoms.com.ar', data_store_path: str = 'market_data.csv'):
        """
        Inicializa el cliente OMS.

        Args:
            url: URL del servidor WebSocket OMS.
            data_store_path: Ruta del archivo CSV donde se guardará la market data.
        """
        self.url = url
        self.connector: Optional[OMSWebSocketConnector] = None
        self.auth = OMSAuth()
        self.token: Optional[str] = None
        self.logger = logging.getLogger(__name__)
        self.data_store = MarketDataStore(data_store_path)

    def _on_message(self, message: Dict[str, Any]):
        """
        Maneja los mensajes recibidos del servidor.

        Args:
            message: Mensaje recibido del servidor.
        """
        self.logger.info(f'Mensaje recibido del servidor: {message}')
        print(f'📨 Mensaje recibido: {message}')

        # Persistir mensaje de market data en CSV
        self.data_store.append_message(message)
    
    def _on_error(self, error: Exception):
        """
        Maneja los errores de la conexión.

        Args:
            error: Excepción ocurrida.
        """
        self.logger.error(f'Error en conexión: {str(error)}')
        print(f'❌ Error: {str(error)}')
    
    async def connect(self) -> bool:
        """
        Conecta al servidor WebSocket.
        Primero obtiene el token de autenticación y luego establece la conexión.

        Returns:
            True si la conexión fue exitosa.
        """
        # Obtener token de autenticación
        self.logger.info('Obteniendo token de autenticación...')
        self.token = await self.auth.get_token()

        if not self.token:
            self.logger.error('No se pudo obtener el token de autenticación')
            print('❌ No se pudo obtener el token de autenticación')
            return False

        # Preparar headers con el token
        headers = {
            'x-auth-token': self.token.strip()
        }

        # Crear el conector con los headers
        self.connector = OMSWebSocketConnector(self.url, headers=headers)

        # Configurar manejadores
        self.connector.set_message_handler(self._on_message)
        self.connector.set_error_handler(self._on_error)

        # Conectar
        return await self.connector.connect()
    
    async def disconnect(self):
        """
        Desconecta del servidor WebSocket.
        """
        if self.connector:
            await self.connector.disconnect()
    
    async def send_smd_request(
        self,
        level: int = 1,
        entries: List[str] = None,
        products: List[Dict[str, str]] = None,
    ) -> bool:
        """
        Envía una solicitud SMD (Subscription Market Data) al servidor.

        Args:
            level: Nivel de profundidad de la suscripción.
            entries: Lista de entradas a suscribir (ej: ['BI', 'OF']).
            products: Lista de productos a suscribir, cada uno con 'symbol' y 'marketId'.

        Returns:
            True si el mensaje fue enviado exitosamente.
        """
        if entries is None:
            entries = ['BI', 'OF', 'EV', 'TV']

        if products is None:
            products = [
                {
                    'symbol': 'MERV - XMEV - PESOS - 1D',
                    'marketId': 'ROFX',
                },
                {
                    'symbol': 'MERV - XMEV - PESOS - 3D',
                    'marketId': 'ROFX',
                },
                {
                    'symbol': 'MERV - XMEV - GGAL - 24hs',
                    'marketId': 'ROFX',
                },
                {
                    'symbol': 'MERV - XMEV - ECOG - 24hs',
                    'marketId': 'ROFX',
                },
                {
                    'symbol': 'MERV - XMEV - PAGS - 24hs',
                    'marketId': 'ROFX',
                },
                {
                    'symbol': 'MERV - XMEV - MELI - 24hs',
                    'marketId': 'ROFX',
                },
                {
                    'symbol': 'MERV - XMEV - A3 - 24hs',
                    'marketId': 'ROFX',
                },
                {
                    'symbol': 'MERV - XMEV - META - 24hs',
                    'marketId': 'ROFX',
                },
            ]

        message = {
            'type': 'smd',
            'level': level,
            'entries': entries,
            'products': products,
        }

        if not self.connector:
            self.logger.error('No hay conexión activa')
            return False

        return await self.connector.send_message(message)
    
    async def run(self, duration: int = 60):
        """
        Ejecuta el cliente y mantiene la conexión activa.

        Args:
            duration: Duración en segundos para mantener la conexión activa.
        """
        try:
            # Conectar
            if not await self.connect():
                print('❌ No se pudo establecer la conexión')
                return

            # Enviar solicitud SMD
            print('📤 Enviando solicitud SMD...')
            await self.send_smd_request()

            # Mantener la conexión activa
            print(f'⏳ Manteniendo conexión activa por {duration} segundos...')
            await asyncio.sleep(duration)

        except KeyboardInterrupt:
            print('\n⚠️  Interrupción del usuario')
        except Exception as e:
            self.logger.error(f'Error en ejecución: {str(e)}')
            print(f'❌ Error: {str(e)}')
        finally:
            await self.disconnect()
            print('👋 Cliente desconectado')


async def main():
    """
    Función principal para ejecutar el cliente OMS.
    """
    client = OMSClient()
    await client.run(duration=60)


if __name__ == '__main__':
    asyncio.run(main())
