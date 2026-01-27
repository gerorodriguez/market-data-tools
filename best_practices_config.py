"""
Best Practices Configuration
Configuración centralizada según las mejores prácticas de Primary/Matba Rofex.
Basado en el documento "Buenas Prácticas de Consumo en APIs de Riesgo PreTrade y Trading"
"""
from typing import Dict


class BestPracticesConfig:
    """
    Configuración de mejores prácticas para consumo de APIs de Primary.
    """
    
    # ========== API REST ==========
    
    # Autenticación
    AUTH_TOKEN_MAX_CALLS_PER_DAY = 1  # 1 request/día
    AUTH_TOKEN_EXPIRES_HOURS = 24  # El token expira a las 24 horas
    
    # Segmentos e Instrumentos
    SEGMENTS_MAX_CALLS_PER_DAY = 1  # 1 request/día
    INSTRUMENTS_ALL_MAX_CALLS_PER_DAY = 1  # 1 request/día
    INSTRUMENTS_DETAILS_MAX_CALLS_PER_DAY = 1  # 1 request/día
    INSTRUMENTS_DETAIL_MAX_CALLS_PER_DAY = 1  # 1 request/día por instrumento
    INSTRUMENTS_BY_CFI_MAX_CALLS_PER_DAY = 1  # 1 request/día por CFICode
    INSTRUMENTS_BY_SEGMENT_MAX_CALLS_PER_DAY = 1  # 1 request/día por segmento
    
    # Market Data
    MARKET_DATA_GET_MAX_CALLS_PER_SECOND = 1  # 1 request/segundo (solo para cierres)
    # Nota: Para información en tiempo real se debe usar WebSocket
    DATA_GET_TRADES_MAX_CALLS_PER_30_SECONDS = 1  # 1 request/30 segundos
    
    # Órdenes
    ORDER_REPLACE_MAX_CALLS_PER_SECOND = 1  # 1 request/segundo
    ORDER_CANCEL_MAX_CALLS_PER_SECOND = 1  # 1 request/segundo
    ORDER_ALL_BY_ID_MAX_CALLS_PER_30_SECONDS = 1  # 1 request/30 segundos
    ORDER_BY_EXEC_ID_MAX_CALLS_PER_30_SECONDS = 1  # 1 request/30 segundos
    # Nota: Para estado de órdenes en tiempo real se debe usar WebSocket
    
    # Risk
    RISK_POSITIONS_MAX_CALLS_PER_5_SECONDS = 1  # 1 request/5 segundos
    RISK_DETAILED_POSITIONS_MAX_CALLS_PER_5_SECONDS = 1  # 1 request/5 segundos
    RISK_ACCOUNT_REPORT_MAX_CALLS_PER_5_SECONDS = 1  # 1 request/5 segundos (actualiza cada 5s)
    RISK_CURRENCY_MAX_CALLS_PER_DAY = 1  # 1 request/día
    
    # ========== API WebSocket ==========
    
    # Conexiones
    WEBSOCKET_MAX_CONNECTIONS_PER_DAY = 1  # 1 conexión/día es suficiente
    WEBSOCKET_MAX_INSTRUMENTS_PER_SUBSCRIPTION = 1000  # Hasta 1000 instrumentos por mensaje
    WEBSOCKET_HEARTBEAT_INTERVAL_SECONDS = 30  # 1 ping cada 30 segundos
    
    # ========== API FIX ==========
    
    # Sesiones
    FIX_MAX_LOGONS_PER_DAY = 1  # 1 sesión/día
    FIX_ORDER_MASS_STATUS_REQUEST_PER_DAY = 1  # 1 vez/día (después del logon)
    FIX_SECURITY_LIST_MAX_CALLS_PER_DAY = 1  # 1 vez/día
    FIX_HEARTBEAT_INTERVAL_SECONDS = 30  # 1 vez/30 segundos
    
    # ========== Recomendaciones Adicionales ==========
    
    @staticmethod
    def get_recommendations() -> Dict[str, str]:
        """
        Retorna un diccionario con recomendaciones adicionales.
        
        Returns:
            Diccionario con recomendaciones clave
        """
        return {
            'market_data_realtime': 'Usar WebSocket en lugar de polling REST',
            'order_status': 'Suscribirse por WebSocket para actualizaciones de estado de órdenes',
            'massive_orders': 'Enviar órdenes masivas por WebSocket o FIX, no REST',
            'order_cancellations': 'Para algoritmos, cancelar órdenes por WebSocket o FIX',
            'instruments_query': 'Si consulta >10 instrumentos, mejor usar /instruments/all',
            'token_management': 'Cachear el token y reutilizarlo durante el día',
            'websocket_persistence': 'Mantener una única conexión WebSocket activa durante el día',
            'rate_limiting': 'Implementar rate limiting local para evitar exceder límites',
        }
    
    @staticmethod
    def print_summary():
        """Imprime un resumen de las mejores practicas."""
        print('\n' + '='*80)
        print('MEJORES PRACTICAS - PRIMARY/MATBA ROFEX')
        print('='*80)
        
        print('\n[WEBSOCKET] (Recomendado para market data en tiempo real):')
        print(f'  - Conexiones: {BestPracticesConfig.WEBSOCKET_MAX_CONNECTIONS_PER_DAY} por dia')
        print(f'  - Instrumentos por suscripcion: max {BestPracticesConfig.WEBSOCKET_MAX_INSTRUMENTS_PER_SUBSCRIPTION}')
        print(f'  - Heartbeat: cada {BestPracticesConfig.WEBSOCKET_HEARTBEAT_INTERVAL_SECONDS} segundos')
        
        print('\n[AUTENTICACION]:')
        print(f'  - Token: {BestPracticesConfig.AUTH_TOKEN_MAX_CALLS_PER_DAY} request por dia')
        print(f'  - Duracion: {BestPracticesConfig.AUTH_TOKEN_EXPIRES_HOURS} horas (expira al final del dia)')
        
        print('\n[INSTRUMENTOS]:')
        print(f'  - Listados: {BestPracticesConfig.INSTRUMENTS_ALL_MAX_CALLS_PER_DAY} vez por dia')
        print('  - No cambian durante la rueda')
        
        print('\n[RATE LIMITS REST]:')
        print(f'  - Market Data: {BestPracticesConfig.MARKET_DATA_GET_MAX_CALLS_PER_SECOND}/segundo (solo cierres)')
        print(f'  - Ordenes (replace/cancel): {BestPracticesConfig.ORDER_REPLACE_MAX_CALLS_PER_SECOND}/segundo')
        print(f'  - Risk/Positions: {BestPracticesConfig.RISK_POSITIONS_MAX_CALLS_PER_5_SECONDS}/5 segundos')
        
        print('\n[RECOMENDACIONES]:')
        for key, value in BestPracticesConfig.get_recommendations().items():
            print(f'  - {value}')
        
        print('\n' + '='*80)
        print('Para mas informacion: https://apihub.primary.com.ar/')
        print('Consultas: mpi@primary.com.ar')
        print('='*80 + '\n')


if __name__ == '__main__':
    # Mostrar resumen al ejecutar el módulo
    BestPracticesConfig.print_summary()

