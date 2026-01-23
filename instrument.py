"""
Instrument
Módulo para representar instrumentos financieros y sus datos de mercado.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class MarketData:
    """
    Representa los datos de mercado de un instrumento.
    """
    symbol: str
    bid_price: Optional[float] = None
    bid_size: Optional[float] = None
    offer_price: Optional[float] = None
    offer_size: Optional[float] = None
    last_price: Optional[float] = None
    timestamp: Optional[datetime] = None
    
    def has_bids(self) -> bool:
        """Retorna True si hay precios de compra disponibles."""
        return self.bid_price is not None and self.bid_price > 0
    
    def has_offers(self) -> bool:
        """Retorna True si hay precios de venta disponibles."""
        return self.offer_price is not None and self.offer_price > 0
    
    def has_last_price(self) -> bool:
        """Retorna True si hay último precio operado."""
        return self.last_price is not None and self.last_price > 0


@dataclass
class InstrumentDetail:
    """
    Representa los detalles de un instrumento financiero.
    """
    symbol: str
    ticker: str
    settlement: str  # 'CI' o '24hs'
    market_id: str = 'ROFX'
    currency: str = 'ARS'
    price_conversion_factor: float = 1.0
    
    # Configuración de comisiones (%)
    comision_broker: float = 0.10
    derechos_mercado: float = 0.01  # Bonos por defecto
    
    def is_ci(self) -> bool:
        """Retorna True si es Contado Inmediato."""
        return self.settlement == 'CI'
    
    def is_24hs(self) -> bool:
        """Retorna True si es 24 horas."""
        return self.settlement == '24hs'
    
    def get_settlement_days(self, dias_liq_24h: int = 1) -> int:
        """
        Retorna los días de liquidación del instrumento.
        
        Args:
            dias_liq_24h: Días de liquidación configurados para 24hs
            
        Returns:
            0 para CI, dias_liq_24h para 24hs
        """
        return 0 if self.is_ci() else dias_liq_24h
    
    def calculate_settlement_days(self, other: 'InstrumentDetail', dias_liq_24h: int = 1) -> int:
        """
        Calcula la diferencia de días de liquidación entre dos instrumentos.
        
        Args:
            other: Otro instrumento para comparar
            dias_liq_24h: Días de liquidación configurados para 24hs
            
        Returns:
            Diferencia de días (positivo = necesito tomar caución, negativo = puedo colocar)
        """
        my_days = self.get_settlement_days(dias_liq_24h)
        other_days = other.get_settlement_days(dias_liq_24h)
        return my_days - other_days
    
    def calculate_comision_derechos(self, amount_in_pesos: float) -> float:
        """
        Calcula comisiones y derechos de mercado.
        
        Args:
            amount_in_pesos: Monto de la operación en pesos
            
        Returns:
            Total de comisiones + derechos de mercado
        """
        tasa_total = (self.comision_broker + self.derechos_mercado) / 100
        return amount_in_pesos * tasa_total
    
    def set_ticker_type(self, ticker: str):
        """
        Configura las tasas de derechos de mercado según el tipo de ticker.
        
        Args:
            ticker: Ticker sin sufijos (ej: 'AL30', 'AAPL')
        """
        # Lista de CEDEARs (acciones extranjeras)
        cedears = [
            'AAPL', 'AMD', 'AMZN', 'BABA', 'BIDU', 'BRKB', 'DIA', 'DISN',
            'EEM', 'GOLD', 'GOOGL', 'INTC', 'KO', 'MELI', 'MRK', 'MSFT',
            'NVDA', 'PBR', 'QCOM', 'QQQ', 'SPY', 'TSLA', 'XLE', 'XOM'
        ]
        
        # Lista de Letras del Tesoro
        letras = ['X18O3', 'X20Y4', 'S31O3']
        
        if ticker.upper() in cedears:
            # CEDEARs y Acciones: 0.08%
            self.derechos_mercado = 0.08
        elif ticker.upper() in letras:
            # Letras: 0.001%
            self.derechos_mercado = 0.001
        else:
            # Bonos: 0.01% (default)
            self.derechos_mercado = 0.01


@dataclass
class InstrumentWithData:
    """
    Representa un instrumento con sus datos de mercado actuales.
    """
    instrument: InstrumentDetail
    data: Optional[MarketData] = None
    
    def has_bids(self) -> bool:
        """Retorna True si hay datos de mercado con bids."""
        return self.data is not None and self.data.has_bids()
    
    def has_offers(self) -> bool:
        """Retorna True si hay datos de mercado con offers."""
        return self.data is not None and self.data.has_offers()
    
    def has_last_price(self) -> bool:
        """Retorna True si hay último precio."""
        return self.data is not None and self.data.has_last_price()
    
    def update_data(self, symbol: str, market_data: MarketData) -> bool:
        """
        Actualiza los datos de mercado si el símbolo coincide.
        
        Args:
            symbol: Símbolo del instrumento
            market_data: Nuevos datos de mercado
            
        Returns:
            True si se actualizó
        """
        if self.instrument.symbol == symbol:
            self.data = market_data
            return True
        return False
    
    def __repr__(self) -> str:
        bid = f"${self.data.bid_price:.2f}" if self.has_bids() else "N/A"
        offer = f"${self.data.offer_price:.2f}" if self.has_offers() else "N/A"
        return f"InstrumentWithData({self.instrument.ticker}-{self.instrument.settlement}, Bid={bid}, Offer={offer})"


class TradedInstrument:
    """
    Representa un instrumento que puede operar en múltiples plazos (CI y 24hs).
    """
    
    def __init__(
        self,
        ticker: str,
        market_id: str = 'ROFX',
        comision_broker: float = 0.10
    ):
        """
        Inicializa un instrumento con sus múltiples plazos.
        
        Args:
            ticker: Ticker base (ej: 'AL30', 'GGAL')
            market_id: ID del mercado
            comision_broker: Comisión del broker en porcentaje
        """
        self.ticker = ticker
        self.market_id = market_id
        
        # Crear instrumentos para cada plazo
        ci_detail = InstrumentDetail(
            symbol=self._build_symbol(ticker, 'CI'),
            ticker=ticker,
            settlement='CI',
            market_id=market_id,
            comision_broker=comision_broker
        )
        ci_detail.set_ticker_type(ticker)
        
        t24_detail = InstrumentDetail(
            symbol=self._build_symbol(ticker, '24hs'),
            ticker=ticker,
            settlement='24hs',
            market_id=market_id,
            comision_broker=comision_broker
        )
        t24_detail.set_ticker_type(ticker)
        
        self.ci = InstrumentWithData(ci_detail)
        self.t24 = InstrumentWithData(t24_detail)
    
    def _build_symbol(self, ticker: str, settlement: str) -> str:
        """
        Construye el símbolo completo del instrumento.
        
        Args:
            ticker: Ticker base
            settlement: Plazo de liquidación ('CI' o '24hs')
            
        Returns:
            Símbolo completo (ej: 'MERV - XMEV - AL30 - CI')
        """
        return f'MERV - XMEV - {ticker} - {settlement}'
    
    def update_data(self, symbol: str, market_data: MarketData) -> bool:
        """
        Actualiza los datos de mercado para el instrumento correspondiente.
        
        Args:
            symbol: Símbolo del instrumento
            market_data: Datos de mercado actualizados
            
        Returns:
            True si se actualizó algún instrumento
        """
        return self.ci.update_data(symbol, market_data) or self.t24.update_data(symbol, market_data)
    
    def contains_symbol(self, symbol: str) -> bool:
        """Verifica si el símbolo pertenece a este instrumento."""
        return symbol in [self.ci.instrument.symbol, self.t24.instrument.symbol]
    
    def get_all_symbols(self) -> List[str]:
        """Retorna todos los símbolos de este instrumento."""
        return [self.ci.instrument.symbol, self.t24.instrument.symbol]
    
    def __repr__(self) -> str:
        return f"TradedInstrument({self.ticker}, CI={self.ci.data is not None}, 24hs={self.t24.data is not None})"
