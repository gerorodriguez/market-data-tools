"""
Ejemplo de uso del sistema de arbitraje de plazos
Muestra cómo usar las clases principales sin necesidad del WebSocket.
"""
import asyncio
from datetime import datetime

from instrument import TradedInstrument, MarketData
from settlement_arbitrage_processor import SettlementArbitrageProcessor


def main():
    """
    Ejemplo de uso del procesador de arbitraje.
    """
    print("=" * 80)
    print("EJEMPLO DE USO DEL SISTEMA DE ARBITRAJE DE PLAZOS")
    print("=" * 80)
    print()
    
    # 1. Crear procesador
    print("1️⃣  Creando procesador de arbitraje...")
    processor = SettlementArbitrageProcessor(
        tickers_file='tickers.csv',
        comision_broker=0.10  # 0.10%
    )
    
    stats = processor.get_stats()
    print(f"   ✅ Cargados {stats['total_instruments']} instrumentos")
    print(f"   📊 Total de símbolos a monitorear: {stats['total_symbols']}")
    print()
    
    # 2. Simular datos de mercado para un instrumento (ejemplo: AL30)
    print("2️⃣  Simulando datos de mercado para AL30...")
    
    # Datos para AL30 - CI
    al30_ci_data = MarketData(
        symbol='MERV - XMEV - AL30 - CI',
        bid_price=55000.0,
        bid_size=1000.0,
        offer_price=55100.0,
        offer_size=1000.0,
        last_price=55050.0,
        timestamp=datetime.now()
    )
    
    # Datos para AL30 - 24hs
    al30_24hs_data = MarketData(
        symbol='MERV - XMEV - AL30 - 24hs',
        bid_price=55200.0,  # Más caro en 24hs
        bid_size=1000.0,
        offer_price=55300.0,
        offer_size=1000.0,
        last_price=55250.0,
        timestamp=datetime.now()
    )
    
    processor.update_market_data('MERV - XMEV - AL30 - CI', al30_ci_data)
    processor.update_market_data('MERV - XMEV - AL30 - 24hs', al30_24hs_data)
    
    print(f"   AL30 CI:   Bid=${al30_ci_data.bid_price:,.2f}  Offer=${al30_ci_data.offer_price:,.2f}")
    print(f"   AL30 24hs: Bid=${al30_24hs_data.bid_price:,.2f}  Offer=${al30_24hs_data.offer_price:,.2f}")
    print()
    
    # 3. Detectar oportunidades
    print("3️⃣  Detectando oportunidades de arbitraje...")
    
    trades = processor.get_settlement_term_trades(
        tasa_caucion=35.0,  # 35% TNA
        dias_liq_24h=1,
        only_with_tickers_owned=False
    )
    
    print(f"   🔍 Encontradas {len(trades)} oportunidades potenciales")
    print()
    
    # 4. Calcular P&L
    print("4️⃣  Calculando P&L para las oportunidades...")
    
    processor.calculate_trades(
        trades=trades,
        nominales=100,  # 100 nominales
        tasa_caucion=35.0,
        dias_liq_24h=1,
        arancel_tomadora=10.0,
        arancel_colocadora=10.0
    )
    print()
    
    # 5. Filtrar y ordenar por rentabilidad
    print("5️⃣  Filtrando y ordenando por rentabilidad...")
    
    profitable = processor.filter_profitable_trades(trades, min_profit=0)
    sorted_trades = processor.sort_trades_by_profitability(profitable)
    
    print(f"   💰 {len(profitable)} oportunidades rentables")
    print()
    
    # 6. Mostrar resultados
    print("=" * 80)
    print("OPORTUNIDADES DETECTADAS")
    print("=" * 80)
    print()
    
    if not sorted_trades:
        print("❌ No se encontraron oportunidades rentables con estos precios.")
        print()
        print("💡 Tip: En un mercado real, el scanner detectará oportunidades cuando:")
        print("   • El spread entre plazos sea mayor al costo de la caución")
        print("   • Los precios bid/offer permitan ejecutar la operación")
        print()
    else:
        for i, trade in enumerate(sorted_trades, 1):
            print(f"Oportunidad #{i}")
            print("-" * 80)
            
            tipo_caucion = "Colocadora" if trade.es_caucion_colocadora else "Tomadora"
            emoji_caucion = "📥" if trade.es_caucion_colocadora else "📤"
            
            print(f"Ticker:        {trade.sell.instrument.ticker}")
            print(f"Operación:     Venta {trade.sell.instrument.settlement} @ ${trade.sell_price:,.2f}")
            print(f"               Compra {trade.buy.instrument.settlement} @ ${trade.buy_price:,.2f}")
            print(f"Caución:       {emoji_caucion} {tipo_caucion} - {abs(trade.dias_caucion)} día(s)")
            print()
            print(f"Spread:        {trade.spread:.4f}%")
            print(f"Spread TNA:    {trade.spread_tna:.2f}%")
            print(f"Tasa Caución:  {trade.caucion.tna:.2f}%")
            print(f"Spread-Cauc:   {trade.spread_caucion:.2f}%")
            print()
            print(f"💰 P&L:        ${trade.profit_loss:,.2f}")
            print(f"📊 Rentab:     {trade.profit_loss_percentage:.3f}%")
            print()
            print(f"Nominales:     {trade.trade_size:,.0f}")
            print(f"Venta Total:   ${trade.sell_total_neto:,.2f}")
            print(f"Compra Total:  ${trade.buy_total_neto:,.2f}")
            print(f"Int. Caución:  ${trade.caucion.interes_neto:,.2f}")
            print()
    
    # 7. Explicación de cómo funciona
    print("=" * 80)
    print("¿CÓMO FUNCIONA EL ARBITRAJE DE PLAZOS?")
    print("=" * 80)
    print()
    print("📚 Conceptos básicos:")
    print()
    print("• CI (Contado Inmediato): Liquidación hoy")
    print("• 24hs: Liquidación en 1 día hábil")
    print()
    print("🔄 Dos tipos de operaciones:")
    print()
    print("1️⃣  CAUCIÓN TOMADORA (Vendo CI / Compro 24hs):")
    print("   • Compro hoy en CI → necesito pagar hoy")
    print("   • Vendo mañana en 24hs → cobro mañana")
    print("   • TOMO caución para financiar la compra de hoy")
    print("   • P&L = Diferencia de precio - Costo de caución")
    print()
    print("2️⃣  CAUCIÓN COLOCADORA (Vendo 24hs / Compro CI):")
    print("   • Vendo mañana en 24hs → entrego mañana")
    print("   • Compro hoy en CI → recibo hoy")
    print("   • COLOCO en caución el dinero hasta mañana")
    print("   • P&L = Diferencia de precio + Ganancia de caución")
    print()
    print("💡 El scanner detecta automáticamente cuál operación es rentable")
    print("   y te alerta cuando el spread supera el costo de la caución.")
    print()
    print("=" * 80)
    print()


if __name__ == '__main__':
    main()
