"""
Configuration
Configuración centralizada para el scanner de arbitraje.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class ArbitrageConfig:
    """Configuración para el scanner de arbitraje de plazos."""
    
    # Archivos
    TICKERS_FILE = 'tickers.csv'
    MARKET_DATA_FILE = 'market_data_arbitrage.csv'
    
    # Market Data
    MARKET_ID = 'ROFX'
    
    # Tasas y comisiones (%)
    TASA_CAUCION_TNA = float(os.getenv('TASA_CAUCION_TNA', '35.0'))
    ARANCEL_TOMADORA_TNA = float(os.getenv('ARANCEL_TOMADORA_TNA', '10.0'))
    ARANCEL_COLOCADORA_TNA = float(os.getenv('ARANCEL_COLOCADORA_TNA', '10.0'))
    COMISION_BROKER = float(os.getenv('COMISION_BROKER', '0.10'))
    
    # Liquidación
    DIAS_LIQ_24H = int(os.getenv('DIAS_LIQ_24H', '1'))
    
    # Filtros de alertas
    MIN_PROFIT_PERCENTAGE = float(os.getenv('MIN_PROFIT_PERCENTAGE', '0.1'))
    ALERT_COOLDOWN_SECONDS = int(os.getenv('ALERT_COOLDOWN_SECONDS', '300'))
    
    # WebSocket
    WS_RECONNECT_INTERVAL = 60  # segundos
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def to_dict(cls):
        """Retorna la configuración como diccionario."""
        return {
            'tickers_file': cls.TICKERS_FILE,
            'market_id': cls.MARKET_ID,
            'tasa_caucion_tna': cls.TASA_CAUCION_TNA,
            'arancel_tomadora_tna': cls.ARANCEL_TOMADORA_TNA,
            'arancel_colocadora_tna': cls.ARANCEL_COLOCADORA_TNA,
            'comision_broker': cls.COMISION_BROKER,
            'dias_liq_24h': cls.DIAS_LIQ_24H,
            'min_profit_percentage': cls.MIN_PROFIT_PERCENTAGE,
            'alert_cooldown_seconds': cls.ALERT_COOLDOWN_SECONDS,
        }
    
    @classmethod
    def print_config(cls):
        """Imprime la configuración actual."""
        print("📋 Configuración del Scanner de Arbitraje:")
        print(f"   • Archivo de tickers: {cls.TICKERS_FILE}")
        print(f"   • Tasa Caución: {cls.TASA_CAUCION_TNA}% TNA")
        print(f"   • Arancel Tomadora: {cls.ARANCEL_TOMADORA_TNA}% TNA")
        print(f"   • Arancel Colocadora: {cls.ARANCEL_COLOCADORA_TNA}% TNA")
        print(f"   • Comisión Broker: {cls.COMISION_BROKER}%")
        print(f"   • Días Liquidación 24hs: {cls.DIAS_LIQ_24H}")
        print(f"   • Rentabilidad Mínima: {cls.MIN_PROFIT_PERCENTAGE}%")
        print(f"   • Cooldown Alertas: {cls.ALERT_COOLDOWN_SECONDS}s")


# Configuración para tipos de instrumentos
# Derechos de mercado según BYMA
class InstrumentTypes:
    """Configuración de derechos de mercado por tipo de instrumento."""
    
    # Derechos de mercado (%)
    CEDEARS_DERECHOS = 0.08
    BONOS_DERECHOS = 0.01
    LETRAS_DERECHOS = 0.001
    
    # Listas de instrumentos
    CEDEARS = [
        'AAPL', 'AMD', 'AMZN', 'BABA', 'BIDU', 'BRKB', 'DIA', 'DISN',
        'EEM', 'GOLD', 'GOOGL', 'INTC', 'KO', 'MELI', 'MRK', 'MSFT',
        'NVDA', 'PBR', 'QCOM', 'QQQ', 'SPY', 'TSLA', 'XLE', 'XOM',
        'META', 'NFLX', 'PYPL', 'ADBE', 'CSCO', 'ORCL', 'CRM',
        'SHOP', 'SQ', 'UBER', 'ABNB', 'COIN', 'RIOT', 'MARA'
    ]
    
    LETRAS = [
        'X18O3', 'X20Y4', 'S31O3', 'X26A4', 'X26D4'
    ]
    
    @classmethod
    def get_derechos_mercado(cls, ticker: str) -> float:
        """
        Retorna los derechos de mercado para un ticker.
        
        Args:
            ticker: Ticker sin sufijos
            
        Returns:
            Porcentaje de derechos de mercado
        """
        ticker_upper = ticker.upper()
        
        if ticker_upper in cls.CEDEARS:
            return cls.CEDEARS_DERECHOS
        elif ticker_upper in cls.LETRAS:
            return cls.LETRAS_DERECHOS
        else:
            return cls.BONOS_DERECHOS
