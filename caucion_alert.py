"""
Caución Alert Server
Servidor que monitorea los instrumentos de caución (1D y 3D) y envía alertas a Telegram
cuando hay cambios en los precios bid y offer.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from oms_client import OMSClient
from telegram_notifier import TelegramNotifier


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CauctionAlertServer:
    """
    Servidor que monitorea los instrumentos de caución y envía alertas a Telegram.
    """
    
    # Símbolos de caución a monitorear
    CAUCTION_SYMBOLS = [
        'MERV - XMEV - PESOS - 1D',
        'MERV - XMEV - PESOS - 3D'
    ]
    
    def __init__(self):
        """
        Inicializa el servidor de alertas de caución.
        """
        self.client = OMSClient()
        self.notifier = TelegramNotifier()
        
        # Diccionario para almacenar el último estado conocido de cada instrumento
        # Estructura: {symbol: {'bid': float, 'offer': float, 'timestamp': datetime}}
        self.last_state: Dict[str, Dict[str, Any]] = {}
        
        # Diccionario para almacenar el último valor alertado de cada instrumento
        # Estructura: {symbol: {'bid': float, 'offer': float, 'timestamp': datetime}}
        self.last_alerted: Dict[str, Dict[str, Any]] = {}
        
        # Configurar el handler de mensajes del cliente
        self.client.connector = None  # Se inicializará en connect
        original_on_message = self.client._on_message
        self.client._on_message = self._handle_market_data
    
    def _handle_market_data(self, message: Dict[str, Any]):
        """
        Maneja los mensajes de market data recibidos del servidor.
        
        Args:
            message: Mensaje recibido del servidor.
        """
        try:
            # Guardar el mensaje original (para persistencia)
            self.client.data_store.append_message(message)
            
            # Procesar el mensaje para detectar cambios en caución (de forma asíncrona)
            # El websocket connector ya está en un contexto asíncrono, así que podemos crear la tarea
            try:
                loop = asyncio.get_running_loop()
                # Si hay un loop corriendo, crear la tarea
                asyncio.ensure_future(self._process_market_data(message), loop=loop)
            except RuntimeError:
                # Si no hay loop corriendo, crear uno nuevo (no debería pasar normalmente)
                logger.warning('No hay event loop corriendo, creando uno nuevo')
                asyncio.run(self._process_market_data(message))
        except Exception as e:
            logger.error(f'Error al procesar mensaje de market data: {str(e)}')
    
    async def _process_market_data(self, message: Dict[str, Any]):
        """
        Procesa el mensaje de market data y detecta cambios en los instrumentos de caución.
        
        Args:
            message: Mensaje recibido del servidor.
        """
        # El formato del mensaje puede variar, pero típicamente contiene:
        # - type: tipo de mensaje
        # - marketData: array con datos de mercado
        #   - symbol: símbolo del instrumento
        #   - marketId: ID del mercado
        #   - entries: array con entradas (BI, OF, etc.)
        #     - price: precio
        #     - size: tamaño
        
        if not isinstance(message, dict):
            return
        
        # Buscar datos de mercado en el mensaje
        # Puede venir como 'marketData' o directamente como array
        market_data = message.get('marketData', [])
        
        # Si no hay marketData, intentar buscar directamente en el mensaje
        if not market_data and isinstance(message.get('data'), list):
            market_data = message.get('data', [])
        
        # Si aún no hay datos, el mensaje completo podría ser un array
        if not market_data and isinstance(message, list):
            market_data = message
        
        if not isinstance(market_data, list):
            return
        
        for instrument_data in market_data:
            if not isinstance(instrument_data, dict):
                continue
                
            symbol = instrument_data.get('symbol')
            
            # Solo procesar instrumentos de caución
            if symbol not in self.CAUCTION_SYMBOLS:
                continue
            
            # Extraer bid y offer
            # Los entries pueden venir en diferentes formatos
            entries = instrument_data.get('entries', [])
            if not entries and instrument_data.get('bid'):
                # Formato alternativo: bid y offer directamente
                bid = instrument_data.get('bid')
                offer = instrument_data.get('offer')
                if bid is not None or offer is not None:
                    await self._check_and_alert(symbol, bid, offer)
                continue
            
            bid = None
            offer = None
            
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                    
                entry_type = entry.get('type')
                price = entry.get('price')
                
                # También intentar con diferentes nombres de campos
                if price is None:
                    price = entry.get('value')
                if price is None:
                    price = entry.get('bid') if entry_type == 'BI' else entry.get('offer')
                
                if entry_type == 'BI' and price is not None:
                    try:
                        bid = float(price)
                    except (ValueError, TypeError):
                        pass
                
                elif entry_type == 'OF' and price is not None:
                    try:
                        offer = float(price)
                    except (ValueError, TypeError):
                        pass
            
            # Si tenemos datos nuevos, comparar con el estado anterior
            if bid is not None or offer is not None:
                await self._check_and_alert(symbol, bid, offer)
    
    async def _check_and_alert(
        self,
        symbol: str,
        bid: Optional[float],
        offer: Optional[float]
    ):
        """
        Compara el estado actual con el anterior y envía alerta solo si:
        1. El precio bid es mayor a 50
        2. El cambio desde la última alerta es >= 10%
        
        Args:
            symbol: Símbolo del instrumento.
            bid: Precio bid actual.
            offer: Precio offer actual.
        """
        # Necesitamos el bid para verificar la condición
        if bid is None:
            # Actualizar estado pero no alertar
            self.last_state[symbol] = {
                'bid': bid,
                'offer': offer,
                'timestamp': datetime.now()
            }
            return
        
        # Solo alertar si el bid es mayor a 50
        if bid <= 50.0:
            logger.debug(
                f'{symbol}: Bid {bid:.2f} <= 50, no se envía alerta. '
                f'Bid: {bid:.2f}, Offer: {offer:.2f if offer else "N/A"}'
            )
            # Actualizar estado pero no alertar
            self.last_state[symbol] = {
                'bid': bid,
                'offer': offer,
                'timestamp': datetime.now()
            }
            return
        
        # Verificar si debemos alertar basado en el cambio desde la última alerta
        last_alerted = self.last_alerted.get(symbol)
        
        if last_alerted:
            last_alerted_bid = last_alerted.get('bid')
            last_alerted_offer = last_alerted.get('offer')
            
            # Calcular el cambio porcentual desde la última alerta
            # Usamos el cambio en el bid como criterio principal
            bid_change_pct = 0
            offer_change_pct = 0
            
            if last_alerted_bid is not None and last_alerted_bid != 0:
                bid_change_pct = abs((bid - last_alerted_bid) / last_alerted_bid * 100)
            
            if offer is not None and last_alerted_offer is not None and last_alerted_offer != 0:
                offer_change_pct = abs((offer - last_alerted_offer) / last_alerted_offer * 100)
            
            # Solo alertar si el cambio es >= 10%
            max_change = max(bid_change_pct, offer_change_pct)
            
            if max_change < 10.0:
                logger.debug(
                    f'{symbol}: Cambio {max_change:.2f}% < 10% desde última alerta, '
                    f'no se envía nueva alerta. Bid actual: {bid:.2f}'
                )
                # Actualizar estado pero no alertar
                self.last_state[symbol] = {
                    'bid': bid,
                    'offer': offer,
                    'timestamp': datetime.now()
                }
                return
        
        # Condiciones cumplidas: bid > 50 y (primera alerta o cambio >= 10%)
        logger.info(
            f'🚨 Alerta de caución para {symbol}: '
            f'Bid {bid:.2f} > 50. '
            f'Bid: {bid:.2f}, Offer: {offer:.2f if offer else "N/A"}'
        )
        
        # Obtener valores anteriores para mostrar en la alerta
        previous_state = self.last_state.get(symbol, {})
        previous_bid = previous_state.get('bid')
        previous_offer = previous_state.get('offer')
        
        # Enviar alerta a Telegram
        await self.notifier.send_cauction_alert(
            symbol=symbol,
            bid=bid,
            offer=offer,
            previous_bid=previous_bid,
            previous_offer=previous_offer
        )
        
        # Actualizar el estado guardado
        self.last_state[symbol] = {
            'bid': bid,
            'offer': offer,
            'timestamp': datetime.now()
        }
        
        # Actualizar el último valor alertado
        self.last_alerted[symbol] = {
            'bid': bid,
            'offer': offer,
            'timestamp': datetime.now()
        }
    
    async def start(self):
        """
        Inicia el servidor de monitoreo de caución.
        """
        try:
            logger.info('🚀 Iniciando servidor de alertas de caución...')
            
            # Enviar mensaje de inicio a Telegram
            await self.notifier.send_message(
                'El servidor se ha iniciado y está monitoreando:\n'
                '• MERV - XMEV - PESOS - 1D\n'
                '• MERV - XMEV - PESOS - 3D'
            )
            
            # Conectar al servidor WebSocket
            logger.info('Conectando al servidor WebSocket...')
            if not await self.client.connect():
                logger.error('No se pudo establecer la conexión')
                await self.notifier.send_message(
                    '❌ <b>Error de Conexión</b>\n\n'
                    'No se pudo conectar al servidor WebSocket OMS.'
                )
                return
            
            logger.info('✅ Conexión establecida')
            
            # Enviar solicitud SMD solo para los instrumentos de caución
            logger.info('Enviando solicitud SMD para instrumentos de caución...')
            await self.client.send_smd_request(
                level=1,
                entries=['BI', 'OF'],  # Solo bid y offer
                products=[
                    {
                        'symbol': 'MERV - XMEV - PESOS - 1D',
                        'marketId': 'ROFX',
                    },
                    {
                        'symbol': 'MERV - XMEV - PESOS - 3D',
                        'marketId': 'ROFX',
                    },
                ]
            )
            
            logger.info('✅ Suscripción a market data activa')
            await self.notifier.send_message(
                '✅ Suscripción Activa\n\n'
                'Monitoreando cambios en bid y offer de los instrumentos de caución.\n\n'
            )
            
            # Mantener el servidor corriendo indefinidamente
            logger.info('⏳ Servidor en ejecución. Presiona Ctrl+C para detener...')
            try:
                while True:
                    await asyncio.sleep(60)  # Verificar cada minuto que la conexión sigue activa
                    if not self.client.connector or not self.client.connector.is_connected:
                        logger.warning('Conexión perdida, intentando reconectar...')
                        await self.notifier.send_message(
                            '⚠️ <b>Conexión Perdida</b>\n\n'
                            'Intentando reconectar al servidor WebSocket...'
                        )
                        if await self.client.connect():
                            await self.client.send_smd_request(
                                level=1,
                                entries=['BI', 'OF'],
                                products=[
                                    {
                                        'symbol': 'MERV - XMEV - PESOS - 1D',
                                        'marketId': 'ROFX',
                                    },
                                    {
                                        'symbol': 'MERV - XMEV - PESOS - 3D',
                                        'marketId': 'ROFX',
                                    },
                                ]
                            )
                            await self.notifier.send_message(
                                '✅ <b>Reconexión Exitosa</b>\n\n'
                                'El servidor se ha reconectado y está monitoreando nuevamente.'
                            )
            except KeyboardInterrupt:
                logger.info('Interrupción del usuario recibida')
                await self.notifier.send_message(
                    '🛑 <b>Servidor Detenido</b>\n\n'
                    'El servidor de alertas de caución se ha detenido.'
                )
        
        except Exception as e:
            logger.error(f'Error en el servidor: {str(e)}', exc_info=True)
            await self.notifier.send_message(
                f'❌ <b>Error en el Servidor</b>\n\n'
                f'Se produjo un error: {str(e)}'
            )
        finally:
            await self.client.disconnect()
            logger.info('Servidor desconectado')
    
    async def stop(self):
        """
        Detiene el servidor de monitoreo.
        """
        logger.info('Deteniendo servidor...')
        await self.client.disconnect()
        await self.notifier.send_message(
            '🛑 <b>Servidor Detenido</b>\n\n'
            'El servidor de alertas de caución se ha detenido correctamente.'
        )


async def main():
    """
    Función principal para ejecutar el servidor de alertas de caución.
    """
    server = CauctionAlertServer()
    await server.start()


if __name__ == '__main__':
    asyncio.run(main())
