"""
OMS Client
Implementación del cliente que utiliza el OMSWebSocketConnector
para enviar mensajes al servidor OMS.
"""
import asyncio
import logging
import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import pathlib

from oms_websocket_connector import OMSWebSocketConnector
from oms_auth import OMSAuth
from market_data_store import MarketDataStore

# Cargar variables de entorno desde .env
script_dir = pathlib.Path(__file__).parent.absolute()
env_path = script_dir / '.env'
load_dotenv(dotenv_path=env_path)
load_dotenv()


class OMSClient:
    """
    Cliente para interactuar con el servidor OMS mediante WebSocket.
    """

    def __init__(self, url: Optional[str] = None, data_store_path: str = 'market_data.csv'):
        """
        Inicializa el cliente OMS.

        Args:
            url: URL del servidor WebSocket OMS (opcional, se construye desde OMS_HOST si no se proporciona).
            data_store_path: Ruta del archivo CSV donde se guardará la market data.
        """
        # Obtener host del .env
        oms_host = os.getenv('OMS_HOST')
        
        # Construir URL WebSocket
        if url:
            self.url = url
        else:
            # Asegurar que el host no tenga protocolo
            oms_host = oms_host.replace('https://', '').replace('http://', '').replace('wss://', '').replace('ws://', '')
            self.url = f'wss://{oms_host}'
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
        Implementa las mejores prácticas de Primary: máximo 1000 instrumentos por mensaje.

        Args:
            level: Nivel de profundidad de la suscripción.
            entries: Lista de entradas a suscribir (ej: ['BI', 'OF']).
            products: Lista de productos a suscribir, cada uno con 'symbol' y 'marketId'.

        Returns:
            True si todos los mensajes fueron enviados exitosamente.
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

        if not self.connector:
            self.logger.error('No hay conexión activa')
            return False

        # Dividir en lotes de máximo 1000 instrumentos según mejores prácticas
        max_instruments = 1000
        total_products = len(products)
        
        if total_products <= max_instruments:
            # Un solo mensaje
            message = {
                'type': 'smd',
                'level': level,
                'entries': entries,
                'products': products,
            }
            return await self.connector.send_message(message)
        
        # Múltiples mensajes
        self.logger.info(
            f'Dividiendo {total_products} instrumentos en lotes de {max_instruments} '
            f'(mejores prácticas Primary)'
        )
        
        success = True
        for i in range(0, total_products, max_instruments):
            batch = products[i:i + max_instruments]
            batch_num = (i // max_instruments) + 1
            total_batches = (total_products + max_instruments - 1) // max_instruments
            
            self.logger.info(
                f'Enviando lote {batch_num}/{total_batches} con {len(batch)} instrumentos'
            )
            
            message = {
                'type': 'smd',
                'level': level,
                'entries': entries,
                'products': batch,
            }
            
            if not await self.connector.send_message(message):
                self.logger.error(f'Error enviando lote {batch_num}')
                success = False
            
            # Pequeña pausa entre mensajes para no saturar
            if i + max_instruments < total_products:
                await asyncio.sleep(0.1)
        
        return success
    
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
