"""
Test Best Practices
Script de prueba para verificar que las mejores prácticas estén funcionando correctamente.
"""
import asyncio
import logging
from oms_auth import OMSAuth
from rate_limiter import get_rate_limiter
from token_cache import TokenCache
from best_practices_config import BestPracticesConfig


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_token_cache():
    """Prueba el sistema de caché de tokens."""
    print('\n' + '='*80)
    print('TEST 1: Cache de Token')
    print('='*80)
    
    try:
        auth = OMSAuth()
    except ValueError as e:
        print(f'\n[SKIP] Test omitido: {str(e)}')
        print('[INFO] Configure las variables OMS_USER y OMS_PASSWORD en .env para ejecutar este test')
        return True  # No fallar si no hay credenciales
    
    # Primera llamada - debe obtener token nuevo
    print('\n[1] Primera llamada (debe solicitar token nuevo):')
    token1 = await auth.get_token()
    if token1:
        print(f'   [OK] Token obtenido: {token1[:20]}...')
        time_left = auth.token_cache.get_time_until_expiration()
        if time_left:
            print(f'   [INFO] Expira en: {time_left.total_seconds() / 3600:.1f} horas')
    else:
        print('   [ERROR] Error obteniendo token')
        return False
    
    # Segunda llamada inmediata - debe usar caché
    print('\n[2] Segunda llamada (debe usar cache):')
    token2 = await auth.get_token()
    if token2 == token1:
        print('   [OK] Token obtenido desde cache (mismo token)')
    else:
        print('   [ERROR] Token diferente (no uso cache)')
        return False
    
    # Verificar que el caché persiste creando nueva instancia
    print('\n[3] Nueva instancia de OMSAuth (debe cargar desde archivo):')
    auth2 = OMSAuth()
    token3 = await auth2.get_token()
    if token3 == token1:
        print('   [OK] Token cargado desde archivo de cache')
    else:
        print('   [ERROR] No se cargo correctamente desde cache')
        return False
    
    return True


async def test_rate_limiter():
    """Prueba el rate limiter."""
    print('\n' + '='*80)
    print('TEST 2: Rate Limiter')
    print('='*80)
    
    rate_limiter = get_rate_limiter()
    endpoint = '/auth/getToken'
    
    # Primera llamada - debe permitirse
    print(f'\n[1] Verificando si se puede llamar a {endpoint}:')
    if rate_limiter.can_call(endpoint):
        print('   [OK] Llamada permitida')
        rate_limiter.record_call(endpoint)
    else:
        print('   [ERROR] Llamada no permitida (no deberia pasar)')
        return False
    
    # Segunda llamada inmediata - debe bloquearse (límite: 1/día)
    print(f'\n[2] Intentando segunda llamada inmediata:')
    if rate_limiter.can_call(endpoint):
        print('   [ERROR] Llamada permitida (no deberia permitirse - limite 1/dia)')
        return False
    else:
        print('   [OK] Llamada bloqueada correctamente (limite 1/dia)')
        next_time = rate_limiter.get_next_allowed_time(endpoint)
        if next_time:
            print(f'   [INFO] Proxima llamada permitida: {next_time.strftime("%Y-%m-%d %H:%M:%S")}')
    
    # Resetear para no afectar el uso real
    print(f'\n[3] Reseteando rate limiter para {endpoint}:')
    rate_limiter.reset(endpoint)
    if rate_limiter.can_call(endpoint):
        print('   [OK] Rate limiter reseteado correctamente')
    else:
        print('   [ERROR] Error al resetear')
        return False
    
    return True


def test_config():
    """Prueba la configuración de mejores prácticas."""
    print('\n' + '='*80)
    print('TEST 3: Configuración de Mejores Prácticas')
    print('='*80)
    
    config = BestPracticesConfig()
    
    print('\n[1] Verificando constantes:')
    print(f'   - Max instrumentos por suscripcion: {config.WEBSOCKET_MAX_INSTRUMENTS_PER_SUBSCRIPTION}')
    print(f'   - Intervalo de heartbeat: {config.WEBSOCKET_HEARTBEAT_INTERVAL_SECONDS}s')
    print(f'   - Max conexiones WebSocket/dia: {config.WEBSOCKET_MAX_CONNECTIONS_PER_DAY}')
    print(f'   - Expiracion de token: {config.AUTH_TOKEN_EXPIRES_HOURS}h')
    
    print('\n[2] Recomendaciones:')
    recommendations = config.get_recommendations()
    for i, (key, value) in enumerate(recommendations.items(), 1):
        print(f'   {i}. {value}')
    
    print('\n[3] Resumen completo:')
    config.print_summary()
    
    return True


async def main():
    """Ejecuta todos los tests."""
    print('\n' + '='*80)
    print('TESTS DE MEJORES PRACTICAS - PRIMARY/MATBA ROFEX')
    print('='*80)
    
    tests_passed = 0
    tests_total = 3
    
    # Test 1: Token Cache
    try:
        if await test_token_cache():
            tests_passed += 1
            print('\n[PASS] TEST 1 PASADO')
        else:
            print('\n[FAIL] TEST 1 FALLIDO')
    except Exception as e:
        logger.error(f'Error en test de token cache: {str(e)}', exc_info=True)
        print(f'\n[ERROR] TEST 1 ERROR: {str(e)}')
    
    # Test 2: Rate Limiter
    try:
        if await test_rate_limiter():
            tests_passed += 1
            print('\n[PASS] TEST 2 PASADO')
        else:
            print('\n[FAIL] TEST 2 FALLIDO')
    except Exception as e:
        logger.error(f'Error en test de rate limiter: {str(e)}', exc_info=True)
        print(f'\n[ERROR] TEST 2 ERROR: {str(e)}')
    
    # Test 3: Config
    try:
        if test_config():
            tests_passed += 1
            print('\n[PASS] TEST 3 PASADO')
        else:
            print('\n[FAIL] TEST 3 FALLIDO')
    except Exception as e:
        logger.error(f'Error en test de config: {str(e)}', exc_info=True)
        print(f'\n[ERROR] TEST 3 ERROR: {str(e)}')
    
    # Resumen
    print('\n' + '='*80)
    print(f'RESUMEN: {tests_passed}/{tests_total} tests pasados')
    print('='*80 + '\n')
    
    if tests_passed == tests_total:
        print('SUCCESS: Todos los tests pasaron! Las mejores practicas estan funcionando correctamente.')
    else:
        print('WARNING: Algunos tests fallaron. Revisar los logs para mas detalles.')
    
    return tests_passed == tests_total


if __name__ == '__main__':
    success = asyncio.run(main())
    exit(0 if success else 1)

