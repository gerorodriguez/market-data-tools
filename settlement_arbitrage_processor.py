"""
Settlement Arbitrage Processor
Procesador principal para detectar oportunidades de arbitraje de plazos de liquidación.
"""
import csv
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from instrument import TradedInstrument, MarketData
from settlement_trade import SettlementTrade, get_settlement_term_trade


logger = logging.getLogger(__name__)


class SettlementArbitrageProcessor:
    """
    Procesador que gestiona múltiples instrumentos y detecta oportunidades de arbitraje.
    """
    
    def __init__(
        self,
        tickers_file: str = 'tickers.csv',
        market_id: str = 'ROFX',
        comision_broker: float = 0.10
    ):
        """
        Inicializa el procesador de arbitraje.
        
        Args:
            tickers_file: Archivo CSV con los tickers a monitorear
            market_id: ID del mercado
            comision_broker: Comisión del broker en porcentaje
        """
        self.tickers_file = tickers_file
        self.market_id = market_id
        self.comision_broker = comision_broker
        self.traded_instruments: List[TradedInstrument] = []
        
        # Cargar tickers
        self._load_tickers()
    
    def _load_tickers(self):
        """Carga los tickers desde el archivo CSV."""
        tickers_path = Path(self.tickers_file)
        
        if not tickers_path.exists():
            logger.warning(f'Archivo de tickers no encontrado: {self.tickers_file}')
            return
        
        try:
            with open(tickers_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and row[0].strip():
                        ticker = row[0].strip()
                        
                        # Ignorar líneas de comentario
                        if ticker.startswith('#'):
                            continue
                        
                        instrument = TradedInstrument(
                            ticker=ticker,
                            market_id=self.market_id,
                            comision_broker=self.comision_broker
                        )
                        self.traded_instruments.append(instrument)
            
            logger.info(f'Cargados {len(self.traded_instruments)} tickers desde {self.tickers_file}')
        
        except Exception as e:
            logger.error(f'Error al cargar tickers: {str(e)}')
    
    def get_all_symbols(self) -> List[str]:
        """
        Retorna todos los símbolos a suscribir en el WebSocket.
        
        Returns:
            Lista de símbolos completos para suscripción
        """
        symbols = []
        for instrument in self.traded_instruments:
            symbols.extend(instrument.get_all_symbols())
        return symbols
    
    def update_market_data(self, symbol: str, market_data: MarketData) -> bool:
        """
        Actualiza los datos de mercado para el símbolo correspondiente.
        
        Args:
            symbol: Símbolo del instrumento
            market_data: Nuevos datos de mercado
            
        Returns:
            True si se actualizó algún instrumento
        """
        updated = False
        for instrument in self.traded_instruments:
            if instrument.update_data(symbol, market_data):
                updated = True
                break
        return updated
    
    def get_settlement_term_trades(
        self,
        tasa_caucion: float,
        dias_liq_24h: int = 1,
        only_with_tickers_owned: bool = False,
        positions: Optional[List[str]] = None
    ) -> List[SettlementTrade]:
        """
        Detecta todas las oportunidades de arbitraje de plazos.
        
        Args:
            tasa_caucion: TNA de la caución (%)
            dias_liq_24h: Días de liquidación para 24hs
            only_with_tickers_owned: Si True, solo muestra trades donde se tienen posiciones
            positions: Lista de tickers en cartera
            
        Returns:
            Lista de SettlementTrade con oportunidades detectadas
        """
        all_trades = []
        
        for instrument in self.traded_instruments:
            # Filtrar por posiciones si es necesario
            if only_with_tickers_owned:
                if positions is None or instrument.ticker not in positions:
                    continue
            
            trades = self._get_trades_for_instrument(
                instrument,
                tasa_caucion,
                dias_liq_24h,
                only_with_tickers_owned,
                positions
            )
            
            if trades:
                all_trades.extend(trades)
        
        return all_trades
    
    def _get_trades_for_instrument(
        self,
        instrument: TradedInstrument,
        tasa_caucion: float,
        dias_liq_24h: int,
        only_with_tickers_owned: bool,
        positions: Optional[List[str]]
    ) -> List[SettlementTrade]:
        """
        Detecta oportunidades de arbitraje para un instrumento específico.
        
        Args:
            instrument: Instrumento a analizar
            tasa_caucion: TNA de la caución
            dias_liq_24h: Días de liquidación para 24hs
            only_with_tickers_owned: Filtrar por posiciones
            positions: Lista de tickers en cartera
            
        Returns:
            Lista de trades encontrados
        """
        trades = []
        
        # Caso 1: Vender 24hs / Comprar CI (requiere tener el título)
        if only_with_tickers_owned:
            if positions and instrument.ticker in positions:
                trade = get_settlement_term_trade(
                    buy=instrument.ci,
                    sell=instrument.t24,
                    tasa_caucion=tasa_caucion,
                    dias_liq_24h=dias_liq_24h
                )
                if trade:
                    trades.append(trade)
        else:
            trade = get_settlement_term_trade(
                buy=instrument.ci,
                sell=instrument.t24,
                tasa_caucion=tasa_caucion,
                dias_liq_24h=dias_liq_24h
            )
            if trade:
                trades.append(trade)
        
        # Caso 2: Vender CI / Comprar 24hs (requiere pesos o tomar caución)
        trade = get_settlement_term_trade(
            buy=instrument.t24,
            sell=instrument.ci,
            tasa_caucion=tasa_caucion,
            dias_liq_24h=dias_liq_24h
        )
        if trade:
            trades.append(trade)
        
        return trades
    
    def calculate_trades(
        self,
        trades: List[SettlementTrade],
        nominales: float,
        tasa_caucion: float,
        dias_liq_24h: int = 1,
        arancel_tomadora: float = 10.0,
        arancel_colocadora: float = 10.0
    ):
        """
        Calcula P&L para todos los trades.
        
        Args:
            trades: Lista de trades a calcular
            nominales: Cantidad de nominales a operar (0 = usar mínimo disponible)
            tasa_caucion: TNA de la caución (%)
            dias_liq_24h: Días de liquidación para 24hs
            arancel_tomadora: TNA del arancel para caución tomadora (%)
            arancel_colocadora: TNA del arancel para caución colocadora (%)
        """
        for trade in trades:
            trade.calculate(
                nominales=nominales,
                tasa_caucion=tasa_caucion,
                dias_liq_24h=dias_liq_24h,
                arancel_tomadora=arancel_tomadora,
                arancel_colocadora=arancel_colocadora
            )
    
    def filter_profitable_trades(
        self,
        trades: List[SettlementTrade],
        min_profit: float = 0.0
    ) -> List[SettlementTrade]:
        """
        Filtra trades por rentabilidad mínima.
        
        Args:
            trades: Lista de trades
            min_profit: Profit mínimo en pesos (0 = solo positivos)
            
        Returns:
            Lista filtrada de trades
        """
        return [trade for trade in trades if trade.profit_loss > min_profit]
    
    def sort_trades_by_profitability(
        self,
        trades: List[SettlementTrade],
        reverse: bool = True
    ) -> List[SettlementTrade]:
        """
        Ordena trades por rentabilidad.
        
        Args:
            trades: Lista de trades
            reverse: True = mayor a menor (default)
            
        Returns:
            Lista ordenada
        """
        return sorted(trades, key=lambda t: t.profit_loss_percentage, reverse=reverse)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estadísticas del procesador.
        
        Returns:
            Diccionario con estadísticas
        """
        total_instruments = len(self.traded_instruments)
        with_ci_data = sum(1 for i in self.traded_instruments if i.ci.data is not None)
        with_24hs_data = sum(1 for i in self.traded_instruments if i.t24.data is not None)
        
        return {
            'total_instruments': total_instruments,
            'with_ci_data': with_ci_data,
            'with_24hs_data': with_24hs_data,
            'total_symbols': len(self.get_all_symbols())
        }
