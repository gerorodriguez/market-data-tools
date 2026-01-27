"""
Rate Limiter
Implementa rate limiting según las mejores prácticas de Primary/Matba Rofex.
"""
import time
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict


logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter para controlar la frecuencia de llamadas a la API.
    Implementa las mejores prácticas recomendadas por Primary.
    """
    
    # Configuración según documento de buenas prácticas
    RATE_LIMITS = {
        # API REST - Autenticación
        '/auth/getToken': {'calls': 1, 'period': 86400},  # 1 vez/día
        
        # API REST - Segmentos e Instrumentos
        '/segment/all': {'calls': 1, 'period': 86400},  # 1 vez/día
        '/instruments/all': {'calls': 1, 'period': 86400},  # 1 vez/día
        '/instruments/details': {'calls': 1, 'period': 86400},  # 1 vez/día
        '/instruments/detail': {'calls': 1, 'period': 86400},  # 1 vez/día (por instrumento)
        '/instruments/byCFICode': {'calls': 1, 'period': 86400},  # 1 vez/día
        '/instruments/bySegment': {'calls': 1, 'period': 86400},  # 1 vez/día
        
        # API REST - Órdenes
        '/order/replaceById': {'calls': 1, 'period': 1},  # 1 vez/segundo
        '/order/cancelById': {'calls': 1, 'period': 1},  # 1 vez/segundo
        '/order/allById': {'calls': 1, 'period': 30},  # 1 vez/30 segundos
        '/order/byExecId': {'calls': 1, 'period': 30},  # 1 vez/30 segundos
        
        # API REST - Market Data
        '/marketdata/get': {'calls': 1, 'period': 1},  # 1 vez/segundo (solo para cierres)
        '/data/getTrades': {'calls': 1, 'period': 30},  # 1 vez/30 segundos
        
        # API REST - Risk
        '/risk/position/getPositions': {'calls': 1, 'period': 5},  # 1 vez/5 segundos
        '/risk/position/detailedPositions': {'calls': 1, 'period': 5},  # 1 vez/5 segundos
        '/risk/accountReport': {'calls': 1, 'period': 5},  # 1 vez/5 segundos
        '/risk/currency/getAll': {'calls': 1, 'period': 86400},  # 1 vez/día
    }
    
    def __init__(self):
        """Inicializa el rate limiter."""
        self.call_history: Dict[str, list] = defaultdict(list)
    
    def can_call(self, endpoint: str) -> bool:
        """
        Verifica si se puede realizar una llamada al endpoint.
        
        Args:
            endpoint: Endpoint de la API (ej: '/auth/getToken')
        
        Returns:
            True si se puede realizar la llamada, False si excede el límite
        """
        # Si no hay límite configurado, permitir la llamada
        if endpoint not in self.RATE_LIMITS:
            return True
        
        limit_config = self.RATE_LIMITS[endpoint]
        max_calls = limit_config['calls']
        period = limit_config['period']
        
        now = time.time()
        cutoff_time = now - period
        
        # Limpiar llamadas antiguas
        self.call_history[endpoint] = [
            call_time for call_time in self.call_history[endpoint]
            if call_time > cutoff_time
        ]
        
        # Verificar si se puede hacer la llamada
        return len(self.call_history[endpoint]) < max_calls
    
    def record_call(self, endpoint: str):
        """
        Registra una llamada al endpoint.
        
        Args:
            endpoint: Endpoint de la API
        """
        self.call_history[endpoint].append(time.time())
    
    async def wait_if_needed(self, endpoint: str) -> bool:
        """
        Espera si es necesario antes de realizar una llamada.
        
        Args:
            endpoint: Endpoint de la API
        
        Returns:
            True si se realizó la espera, False si no fue necesario
        """
        if self.can_call(endpoint):
            return False
        
        # Calcular tiempo de espera
        if endpoint not in self.RATE_LIMITS:
            return False
        
        limit_config = self.RATE_LIMITS[endpoint]
        period = limit_config['period']
        
        if not self.call_history[endpoint]:
            return False
        
        oldest_call = min(self.call_history[endpoint])
        now = time.time()
        wait_time = period - (now - oldest_call)
        
        if wait_time > 0:
            logger.warning(
                f'Rate limit alcanzado para {endpoint}. '
                f'Esperando {wait_time:.1f} segundos...'
            )
            import asyncio
            await asyncio.sleep(wait_time)
            return True
        
        return False
    
    def get_next_allowed_time(self, endpoint: str) -> Optional[datetime]:
        """
        Obtiene la próxima vez que se podrá llamar al endpoint.
        
        Args:
            endpoint: Endpoint de la API
        
        Returns:
            Datetime del próximo momento permitido, None si se puede llamar ahora
        """
        if self.can_call(endpoint):
            return None
        
        if endpoint not in self.RATE_LIMITS:
            return None
        
        limit_config = self.RATE_LIMITS[endpoint]
        period = limit_config['period']
        
        if not self.call_history[endpoint]:
            return None
        
        oldest_call = min(self.call_history[endpoint])
        next_allowed = datetime.fromtimestamp(oldest_call + period)
        
        return next_allowed
    
    def reset(self, endpoint: Optional[str] = None):
        """
        Resetea el historial de llamadas.
        
        Args:
            endpoint: Endpoint específico a resetear, None para resetear todos
        """
        if endpoint:
            self.call_history[endpoint] = []
        else:
            self.call_history.clear()


# Instancia global
_global_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """Obtiene la instancia global del rate limiter."""
    return _global_rate_limiter

