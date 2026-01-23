"""
Arbitrage Scanner
Servidor que monitorea en tiempo real oportunidades de arbitraje de plazos de liquidación
y envía alertas a Telegram cuando encuentra operaciones rentables.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from oms_client import OMSClient
from telegram_notifier import TelegramNotifier
from settlement_arbitrage_processor import SettlementArbitrageProcessor
from settlement_trade import SettlementTrade
from instrument import MarketData


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ArbitrageScanner:
    """
    Scanner que monitorea oportunidades de arbitraje de plazos en tiempo real.
    """
    
    def __init__(
        self,
        tickers_file: str = 'tickers.csv',
        tasa_caucion: float = 35.0,
        dias_liq_24h: int = 1,
        arancel_tomadora: float = 10.0,
        arancel_colocadora: float = 10.0,
        min_profit_percentage: float = 0.1,
        alert_cooldown_seconds: int = 300,
        comision_broker: float = 0.10
    ):
        """
        Inicializa el scanner de arbitraje.
        
        Args:
            tickers_file: Archivo CSV con tickers a monitorear
            tasa_caucion: TNA de la caución (%)
            dias_liq_24h: Días de liquidación para 24hs
            arancel_tomadora: TNA del arancel para caución tomadora (%)
            arancel_colocadora: TNA del arancel para caución colocadora (%)
            min_profit_percentage: Rentabilidad mínima para alertar (%)
            alert_cooldown_seconds: Segundos entre alertas del mismo ticker
            comision_broker: Comisión del broker (%)
        """
        self.client = OMSClient()
        self.notifier = TelegramNotifier()
        self.processor = SettlementArbitrageProcessor(
            tickers_file=tickers_file,
            comision_broker=comision_broker
        )
        
        # Configuración
        self.tasa_caucion = tasa_caucion
        self.dias_liq_24h = dias_liq_24h
        self.arancel_tomadora = arancel_tomadora
        self.arancel_colocadora = arancel_colocadora
        self.min_profit_percentage = min_profit_percentage
        self.alert_cooldown_seconds = alert_cooldown_seconds
        
        # Control de alertas
        self.last_alerts: Dict[str, datetime] = {}
        
        # Estadísticas
        self.total_opportunities = 0
        self.total_alerts_sent = 0
        
        # Configurar handler de mensajes
        self.client.connector = None
        self.client._on_message = self._handle_market_data
    
    def _handle_market_data(self, message: Dict[str, Any]):
        """
        Maneja los mensajes de market data recibidos del servidor.
        
        Args:
            message: Mensaje recibido del servidor.
        """
        try:
            # Persistir mensaje
            self.client.data_store.append_message(message)
            
            # Procesar de forma asíncrona
            try:
                loop = asyncio.get_running_loop()
                asyncio.ensure_future(self._process_market_data(message), loop=loop)
            except RuntimeError:
                logger.warning('No hay event loop corriendo')
                asyncio.run(self._process_market_data(message))
        
        except Exception as e:
            logger.error(f'Error al procesar mensaje: {str(e)}', exc_info=True)
    
    async def _process_market_data(self, message: Dict[str, Any]):
        """
        Procesa los datos de mercado y detecta oportunidades de arbitraje.
        
        Args:
            message: Mensaje del WebSocket con datos de mercado
        """
        if not isinstance(message, dict):
            return
        
        # Extraer market data del mensaje
        market_data_list = self._extract_market_data(message)
        
        if not market_data_list:
            return
        
        # Actualizar datos en el procesador
        for symbol, market_data in market_data_list:
            self.processor.update_market_data(symbol, market_data)
        
        # Detectar oportunidades cada vez que llegan datos nuevos
        await self._scan_opportunities()
    
    def _extract_market_data(self, message: Dict[str, Any]) -> List[tuple]:
        """
        Extrae los datos de mercado del mensaje del WebSocket.
        
        Args:
            message: Mensaje recibido
            
        Returns:
            Lista de tuplas (symbol, MarketData)
        """
        result = []
        
        # El mensaje puede venir en diferentes formatos
        market_data = message.get('marketData', [])
        
        if not market_data and isinstance(message.get('data'), list):
            market_data = message.get('data', [])
        
        if not market_data and isinstance(message, list):
            market_data = message
        
        if not isinstance(market_data, list):
            return result
        
        for instrument_data in market_data:
            if not isinstance(instrument_data, dict):
                continue
            
            symbol = instrument_data.get('symbol')
            if not symbol:
                continue
            
            # Extraer bid y offer
            entries = instrument_data.get('entries', [])
            
            bid_price = None
            bid_size = None
            offer_price = None
            offer_size = None
            last_price = None
            
            # Formato con entries
            if entries:
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    
                    entry_type = entry.get('type')
                    price = entry.get('price')
                    size = entry.get('size')
                    
                    if entry_type == 'BI' and price is not None:
                        bid_price = float(price)
                        bid_size = float(size) if size else None
                    
                    elif entry_type == 'OF' and price is not None:
                        offer_price = float(price)
                        offer_size = float(size) if size else None
                    
                    elif entry_type == 'LA' and price is not None:
                        last_price = float(price)
            
            # Formato alternativo con campos directos
            else:
                bid_price = instrument_data.get('bid')
                bid_size = instrument_data.get('bidSize')
                offer_price = instrument_data.get('offer')
                offer_size = instrument_data.get('offerSize')
                last_price = instrument_data.get('last')
            
            # Crear objeto MarketData
            if bid_price is not None or offer_price is not None or last_price is not None:
                market_data_obj = MarketData(
                    symbol=symbol,
                    bid_price=bid_price,
                    bid_size=bid_size,
                    offer_price=offer_price,
                    offer_size=offer_size,
                    last_price=last_price,
                    timestamp=datetime.now()
                )
                result.append((symbol, market_data_obj))
        
        return result
    
    async def _scan_opportunities(self):
        """Escanea todas las oportunidades de arbitraje disponibles."""
        try:
            # Obtener todas las oportunidades
            trades = self.processor.get_settlement_term_trades(
                tasa_caucion=self.tasa_caucion,
                dias_liq_24h=self.dias_liq_24h,
                only_with_tickers_owned=False
            )
            
            if not trades:
                return
            
            # Calcular P&L para cada trade
            self.processor.calculate_trades(
                trades=trades,
                nominales=0,  # 0 = usar mínimo disponible
                tasa_caucion=self.tasa_caucion,
                dias_liq_24h=self.dias_liq_24h,
                arancel_tomadora=self.arancel_tomadora,
                arancel_colocadora=self.arancel_colocadora
            )
            
            # Filtrar por rentabilidad
            profitable_trades = [
                t for t in trades
                if t.profit_loss_percentage >= self.min_profit_percentage
            ]
            
            if profitable_trades:
                self.total_opportunities += len(profitable_trades)
                
                # Ordenar por rentabilidad
                sorted_trades = sorted(
                    profitable_trades,
                    key=lambda t: t.profit_loss_percentage,
                    reverse=True
                )
                
                # Enviar alertas para los mejores trades
                for trade in sorted_trades[:5]:  # Top 5
                    await self._send_alert_if_needed(trade)
        
        except Exception as e:
            logger.error(f'Error al escanear oportunidades: {str(e)}', exc_info=True)
    
    async def _send_alert_if_needed(self, trade: SettlementTrade):
        """
        Envía una alerta si cumple las condiciones de cooldown.
        
        Args:
            trade: Trade con oportunidad de arbitraje
        """
        ticker = trade.sell.instrument.ticker
        now = datetime.now()
        
        # Verificar cooldown
        if ticker in self.last_alerts:
            last_alert = self.last_alerts[ticker]
            seconds_since_last = (now - last_alert).total_seconds()
            
            if seconds_since_last < self.alert_cooldown_seconds:
                logger.debug(
                    f'{ticker}: Cooldown activo ({seconds_since_last:.0f}s < {self.alert_cooldown_seconds}s)'
                )
                return
        
        # Enviar alerta
        await self._send_arbitrage_alert(trade)
        
        # Actualizar última alerta
        self.last_alerts[ticker] = now
        self.total_alerts_sent += 1
    
    async def _send_arbitrage_alert(self, trade: SettlementTrade):
        """
        Envía una alerta de arbitraje a Telegram.
        
        Args:
            trade: Trade con los detalles de la oportunidad
        """
        tipo_caucion = "📥 Colocadora" if trade.es_caucion_colocadora else "📤 Tomadora"
        
        message = (
            f"🚨 <b>Oportunidad de Arbitraje de Plazos</b>\n\n"
            f"<b>Ticker:</b> {trade.sell.instrument.ticker}\n\n"
            f"<b>Operación:</b>\n"
            f"1️⃣ Venta {trade.sell.instrument.settlement}: ${trade.sell_price:.2f}\n"
            f"2️⃣ Compra {trade.buy.instrument.settlement}: ${trade.buy_price:.2f}\n"
            f"3️⃣ Caución {tipo_caucion}: {abs(trade.dias_caucion)} día(s)\n\n"
            f"<b>Spread:</b> {trade.spread:.4f}%\n"
            f"<b>Spread TNA:</b> {trade.spread_tna:.2f}%\n"
            f"<b>Tasa Caución:</b> {trade.caucion.tna:.2f}%\n"
            f"<b>Spread - Caución:</b> {trade.spread_caucion:.2f}%\n\n"
            f"<b>💰 P&L:</b> ${trade.profit_loss:,.2f}\n"
            f"<b>📊 Rentabilidad:</b> {trade.profit_loss_percentage:.3f}%\n\n"
            f"<b>Nominales:</b> {trade.trade_size:,.0f}\n"
            f"<b>Venta Total:</b> ${trade.sell_total_neto:,.2f}\n"
            f"<b>Compra Total:</b> ${trade.buy_total_neto:,.2f}\n"
            f"<b>Interés Caución:</b> ${trade.caucion.interes_neto:,.2f}"
        )
        
        try:
            await self.notifier.send_message(message)
            logger.info(
                f'📧 Alerta enviada: {trade.sell.instrument.ticker} '
                f'P&L={trade.profit_loss_percentage:.3f}%'
            )
        except Exception as e:
            logger.error(f'Error al enviar alerta: {str(e)}')
    
    async def start(self):
        """Inicia el scanner de arbitraje."""
        try:
            logger.info('🚀 Iniciando Scanner de Arbitraje de Plazos...')
            
            # Obtener estadísticas
            stats = self.processor.get_stats()
            
            # Enviar mensaje de inicio
            await self.notifier.send_message(
                f"🚀 <b>Scanner de Arbitraje Iniciado</b>\n\n"
                f"<b>Configuración:</b>\n"
                f"• Instrumentos: {stats['total_instruments']}\n"
                f"• Tasa Caución: {self.tasa_caucion}% TNA\n"
                f"• Días 24hs: {self.dias_liq_24h}\n"
                f"• Rentabilidad mín: {self.min_profit_percentage}%\n"
                f"• Cooldown alertas: {self.alert_cooldown_seconds}s\n\n"
                f"Monitoreando {stats['total_symbols']} símbolos..."
            )
            
            # Conectar al WebSocket
            logger.info('Conectando al servidor WebSocket...')
            if not await self.client.connect():
                logger.error('No se pudo establecer la conexión')
                await self.notifier.send_message(
                    '❌ <b>Error de Conexión</b>\n\n'
                    'No se pudo conectar al servidor WebSocket OMS.'
                )
                return
            
            logger.info('✅ Conexión establecida')
            
            # Obtener símbolos a suscribir
            symbols_to_subscribe = self.processor.get_all_symbols()
            products = [
                {'symbol': symbol, 'marketId': 'ROFX'}
                for symbol in symbols_to_subscribe
            ]
            
            logger.info(f'Suscribiendo a {len(products)} instrumentos...')
            
            # Enviar solicitud SMD
            await self.client.send_smd_request(
                level=1,
                entries=['BI', 'OF', 'LA'],  # Bid, Offer, Last
                products=products
            )
            
            logger.info('✅ Suscripción activa')
            await self.notifier.send_message(
                '✅ <b>Suscripción Activa</b>\n\n'
                f'Monitoreando {len(products)} instrumentos.\n'
                f'Alertas se enviarán cuando haya oportunidades > {self.min_profit_percentage}%'
            )
            
            # Mantener el scanner corriendo
            logger.info('⏳ Scanner en ejecución. Presiona Ctrl+C para detener...')
            
            try:
                while True:
                    await asyncio.sleep(60)
                    
                    # Verificar conexión
                    if not self.client.connector or not self.client.connector.is_connected:
                        logger.warning('Conexión perdida, intentando reconectar...')
                        await self.notifier.send_message(
                            '⚠️ <b>Reconectando...</b>'
                        )
                        
                        if await self.client.connect():
                            await self.client.send_smd_request(
                                level=1,
                                entries=['BI', 'OF', 'LA'],
                                products=products
                            )
                            await self.notifier.send_message(
                                '✅ <b>Reconectado</b>'
                            )
                    
                    # Mostrar stats cada hora
                    logger.info(
                        f'📊 Stats: {self.total_opportunities} oportunidades detectadas, '
                        f'{self.total_alerts_sent} alertas enviadas'
                    )
            
            except KeyboardInterrupt:
                logger.info('Interrupción del usuario')
                await self.notifier.send_message(
                    f"🛑 <b>Scanner Detenido</b>\n\n"
                    f"<b>Estadísticas finales:</b>\n"
                    f"• Oportunidades detectadas: {self.total_opportunities}\n"
                    f"• Alertas enviadas: {self.total_alerts_sent}"
                )
        
        except Exception as e:
            logger.error(f'Error en el scanner: {str(e)}', exc_info=True)
            await self.notifier.send_message(
                f'❌ <b>Error en el Scanner</b>\n\n{str(e)}'
            )
        
        finally:
            await self.client.disconnect()
            logger.info('Scanner desconectado')
    
    async def stop(self):
        """Detiene el scanner."""
        logger.info('Deteniendo scanner...')
        await self.client.disconnect()


async def main():
    """Función principal para ejecutar el scanner."""
    scanner = ArbitrageScanner(
        tickers_file='tickers.csv',
        tasa_caucion=35.0,  # TNA %
        dias_liq_24h=1,
        arancel_tomadora=10.0,  # TNA %
        arancel_colocadora=10.0,  # TNA %
        min_profit_percentage=0.1,  # 0.1% mínimo
        alert_cooldown_seconds=300,  # 5 minutos
        comision_broker=0.10  # 0.10%
    )
    await scanner.start()


if __name__ == '__main__':
    asyncio.run(main())
