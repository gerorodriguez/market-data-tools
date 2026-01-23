"""
Settlement Trade
Módulo para representar y calcular operaciones de arbitraje de plazos de liquidación.
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from instrument import InstrumentWithData, InstrumentDetail
from caucion import Caucion


@dataclass
class SettlementTrade:
    """
    Representa una operación de arbitraje entre dos plazos de liquidación.
    
    La operación consiste en:
    1. Comprar en un plazo (buy)
    2. Vender en otro plazo (sell)
    3. Caucionar (colocar o tomar) la diferencia de días
    """
    
    buy: InstrumentWithData  # Instrumento a comprar
    sell: InstrumentWithData  # Instrumento a vender
    
    # Configuración por defecto
    dias_liq_24h: int = 1
    
    # Datos de la operación (se calculan con calculate())
    buy_price: float = 0.0
    buy_total_sin_comisiones: float = 0.0
    buy_comision_derechos: float = 0.0
    buy_total_neto: float = 0.0
    buy_size: float = 0.0
    
    sell_price: float = 0.0
    sell_total_sin_comisiones: float = 0.0
    sell_comision_derechos: float = 0.0
    sell_total_neto: float = 0.0
    sell_size: float = 0.0
    
    trade_size: float = 0.0
    dias_caucion: int = 0
    es_caucion_colocadora: bool = False
    total_a_caucionar: float = 0.0
    
    caucion: Optional[Caucion] = None
    
    profit_loss: float = 0.0
    profit_loss_percentage: float = 0.0
    
    spread_tna: float = 0.0
    spread_caucion: float = 0.0
    
    def has_data(self) -> bool:
        """Verifica si ambos instrumentos tienen datos de mercado."""
        return self.buy.data is not None and self.sell.data is not None
    
    def calculate(
        self,
        nominales: float,
        tasa_caucion: float,
        dias_liq_24h: int = 1,
        sell_price: Optional[float] = None,
        buy_price: Optional[float] = None,
        arancel_tomadora: float = 10.0,
        arancel_colocadora: float = 10.0
    ):
        """
        Calcula todos los valores de la operación de arbitraje.
        
        Args:
            nominales: Cantidad de nominales a operar (0 = usar mínimo disponible)
            tasa_caucion: Tasa Nominal Anual de caución (%)
            dias_liq_24h: Días de liquidación para 24hs
            sell_price: Precio de venta (None = usar bid del mercado)
            buy_price: Precio de compra (None = usar offer del mercado)
            arancel_tomadora: TNA del arancel para caución tomadora (%)
            arancel_colocadora: TNA del arancel para caución colocadora (%)
        """
        self.dias_liq_24h = dias_liq_24h
        
        # Verificar que tengamos datos de mercado
        if not self.has_data() or not self.sell.has_bids() or not self.buy.has_offers():
            return
        
        # Obtener precios del mercado si no se especificaron
        if sell_price is None:
            sell_price = self.sell.data.bid_price
        
        if buy_price is None:
            buy_price = self.buy.data.offer_price
        
        # Obtener tamaños disponibles
        self.sell_size = self.sell.data.bid_size or 0
        self.buy_size = self.buy.data.offer_size or 0
        
        # Si no se especificaron nominales, usar el mínimo disponible
        if nominales <= 0:
            nominales = min(self.sell_size, self.buy_size)
        
        self.trade_size = nominales
        
        # --- CÁLCULO DE VENTA ---
        self.sell_price = sell_price
        self.sell_total_sin_comisiones = (
            self.sell_price * self.trade_size * self.sell.instrument.price_conversion_factor
        )
        self.sell_comision_derechos = self.sell.instrument.calculate_comision_derechos(
            self.sell_total_sin_comisiones
        )
        self.sell_total_neto = self.sell_total_sin_comisiones - self.sell_comision_derechos
        
        # --- CÁLCULO DE COMPRA ---
        self.buy_price = buy_price
        self.buy_total_sin_comisiones = (
            self.buy_price * self.trade_size * self.buy.instrument.price_conversion_factor
        )
        self.buy_comision_derechos = self.buy.instrument.calculate_comision_derechos(
            self.buy_total_sin_comisiones
        )
        self.buy_total_neto = self.buy_total_sin_comisiones + self.buy_comision_derechos
        
        # --- CÁLCULO DE CAUCIÓN ---
        # Calcular días de diferencia entre plazos
        # sell.calculate_settlement_days(buy) = días_sell - días_buy
        # Si es positivo: vendo después, tengo que financiar la compra (TOMADORA)
        # Si es negativo: vendo primero, puedo colocar el dinero (COLOCADORA)
        self.dias_caucion = self.sell.instrument.calculate_settlement_days(
            self.buy.instrument, dias_liq_24h
        )
        
        self.es_caucion_colocadora = self.dias_caucion < 0
        
        # Total a caucionar: si es colocadora uso el neto de venta, si es tomadora uso el neto de compra
        self.total_a_caucionar = (
            self.sell_total_neto if self.es_caucion_colocadora else self.buy_total_neto
        )
        
        # Crear objeto Caucion
        self.caucion = Caucion(
            dias=self.dias_caucion,
            tna=tasa_caucion,
            importe_bruto=self.total_a_caucionar,
            arancel_tomadora=arancel_tomadora,
            arancel_colocadora=arancel_colocadora
        )
        
        # --- CÁLCULO DE SPREAD Y P&L ---
        if self.dias_caucion != 0:
            # Spread TNA = diferencia de precios anualizada
            self.spread_tna = abs(
                ((self.sell_price / self.buy_price) - 1) / abs(self.dias_caucion) * 365 * 100
            )
        
        # P&L según tipo de caución
        if self.caucion.es_colocadora:
            # Colocadora: gano el spread + el interés de la caución
            self.profit_loss = self.sell_total_neto - self.buy_total_neto + self.caucion.interes_neto
        else:
            # Tomadora: gano el spread - el costo de la caución
            self.profit_loss = self.sell_total_neto - self.buy_total_neto - self.caucion.interes_neto
        
        # P&L porcentual sobre el monto invertido
        self.profit_loss_percentage = (
            self.profit_loss / self.buy_total_sin_comisiones * 100
            if self.buy_total_sin_comisiones != 0
            else 0
        )
        
        # Spread después de descontar caución
        self.spread_caucion = self.spread_tna - tasa_caucion
    
    @property
    def spread(self) -> float:
        """
        Calcula el spread actual entre venta y compra (en porcentaje).
        
        Returns:
            Spread porcentual (puede ser negativo)
        """
        if not self.has_data() or not self.sell.has_bids() or not self.buy.has_offers():
            return -100.0
        
        sell_price = self.sell.data.bid_price
        buy_price = self.buy.data.offer_price
        
        return ((sell_price / buy_price) - 1) * 100
    
    @property
    def spread_last(self) -> float:
        """
        Calcula el spread basado en últimos precios operados.
        
        Returns:
            Spread porcentual basado en last prices
        """
        if not self.has_data() or not self.buy.has_last_price() or not self.sell.has_last_price():
            return -100.0
        
        return ((self.buy.data.last_price / self.sell.data.last_price) - 1) * 100
    
    def __repr__(self) -> str:
        tipo_caucion = "Colocadora" if self.es_caucion_colocadora else "Tomadora"
        return (
            f"SettlementTrade("
            f"Venta: {self.sell.instrument.ticker}-{self.sell.instrument.settlement} @ ${self.sell_price:.2f}, "
            f"Compra: {self.buy.instrument.ticker}-{self.buy.instrument.settlement} @ ${self.buy_price:.2f}, "
            f"Caucion: {tipo_caucion} {abs(self.dias_caucion)}d, "
            f"P&L: ${self.profit_loss:,.2f} ({self.profit_loss_percentage:.3f}%)"
            f")"
        )
    
    def to_dict(self) -> dict:
        """Convierte el trade a un diccionario para fácil visualización."""
        return {
            'ticker': self.sell.instrument.ticker,
            'venta_plazo': self.sell.instrument.settlement,
            'venta_precio': round(self.sell_price, 2),
            'compra_plazo': self.buy.instrument.settlement,
            'compra_precio': round(self.buy_price, 2),
            'spread_pct': round(self.spread, 4),
            'dias_caucion': abs(self.dias_caucion),
            'tipo_caucion': 'Colocadora' if self.es_caucion_colocadora else 'Tomadora',
            'tasa_caucion': round(self.caucion.tna, 2) if self.caucion else 0,
            'spread_tna': round(self.spread_tna, 2),
            'profit_loss': round(self.profit_loss, 2),
            'profit_loss_pct': round(self.profit_loss_percentage, 4),
            'nominales': round(self.trade_size, 0),
            'venta_total': round(self.sell_total_neto, 2),
            'compra_total': round(self.buy_total_neto, 2),
        }


def get_settlement_term_trade(
    buy: InstrumentWithData,
    sell: InstrumentWithData,
    tasa_caucion: float,
    dias_liq_24h: int = 1
) -> Optional[SettlementTrade]:
    """
    Crea un SettlementTrade si existe una oportunidad de arbitraje.
    
    Esta función filtra las oportunidades verificando que:
    1. Existan precios disponibles (bids y offers)
    2. La banda de precios esté habilitada
    3. El spread sea mayor al costo de la caución
    
    Args:
        buy: Instrumento a comprar
        sell: Instrumento a vender
        tasa_caucion: TNA de la caución (%)
        dias_liq_24h: Días de liquidación para 24hs
        
    Returns:
        SettlementTrade si hay oportunidad, None si no
    """
    if not sell.has_bids() or not buy.has_offers():
        return None
    
    sell_bid_price = sell.data.bid_price
    buy_offer_price = buy.data.offer_price
    
    sell_offer_price = sell.data.offer_price
    buy_bid_price = buy.data.bid_price
    
    # Verificar que la banda esté habilitada
    if sell_bid_price >= sell_offer_price or buy_bid_price >= buy_offer_price:
        return None
    
    # Calcular días de diferencia
    days = sell.instrument.calculate_settlement_days(buy.instrument, dias_liq_24h)
    
    # Calcular costo de caución con un margen del 10%
    caucion_rate = tasa_caucion / 365 * abs(days) / 100
    target_sell_price = buy_offer_price * (1 - caucion_rate * 1.1)
    
    # Verificar si el precio de venta es suficiente para cubrir costos
    if sell_bid_price >= target_sell_price:
        return SettlementTrade(buy=buy, sell=sell)
    
    return None
