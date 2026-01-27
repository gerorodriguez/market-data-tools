# Mejores Prácticas de Primary/Matba Rofex - Implementación

Este documento explica la implementación de las **mejores prácticas oficiales** de Primary/Matba Rofex según el documento "Buenas Prácticas de Consumo en APIs de Riesgo PreTrade y Trading" (Julio 2021).

## 📚 Índice

1. [Resumen de Mejores Prácticas](#resumen-de-mejores-prácticas)
2. [Implementación Técnica](#implementación-técnica)
3. [Uso en el Proyecto](#uso-en-el-proyecto)
4. [Testing](#testing)
5. [Referencias](#referencias)

---

## Resumen de Mejores Prácticas

### 🔑 API REST - Autenticación

| Endpoint | Límite | Justificación |
|----------|--------|---------------|
| `/auth/getToken` | **1 request/día** | El token dura máximo 24 horas y expira al final del día |

**Implementación:**
- ✅ Caché persistente de token en archivo `.token_cache.json`
- ✅ Verificación automática de expiración
- ✅ Rate limiting para evitar múltiples requests

### 📊 API REST - Instrumentos

| Endpoint | Límite | Justificación |
|----------|--------|---------------|
| `/instruments/all` | **1 request/día** | La lista no cambia durante el día |
| `/instruments/details` | **1 request/día** | La información no cambia durante la rueda |
| `/instruments/detail` | **1 request/instrumento/día** | La información no cambia durante la rueda |

**Implementación:**
- ✅ Rate limiting configurado para cada endpoint
- ⚠️ **Recomendación**: Si necesitas >10 instrumentos, usa `/instruments/all`

### 📈 API REST - Market Data

| Endpoint | Límite | Justificación |
|----------|--------|---------------|
| `/marketdata/get` | **1 request/segundo** | Solo para consulta de cierres |
| `/data/getTrades` | **1 request/30 segundos** | La información se actualiza cada 30 segundos |

**Implementación:**
- ✅ Rate limiting configurado
- ⚠️ **IMPORTANTE**: Para información en tiempo real, **usar WebSocket** (no REST polling)

### 📡 API WebSocket (RECOMENDADO)

| Aspecto | Límite | Justificación |
|---------|--------|---------------|
| **Conexiones** | **1/día** | Una conexión es suficiente para toda la información |
| **Suscripciones** | **1000 instrumentos/mensaje** | Límite técnico del sistema |
| **Heartbeat** | **1 ping/30 segundos** | Mantener la conexión activa |

**Implementación:**
- ✅ Heartbeat automático cada 30 segundos
- ✅ División automática de suscripciones en lotes de 1000
- ✅ Reconexión automática si se pierde la conexión
- ✅ Una única conexión persistente durante todo el día

### ⚡ API REST - Órdenes

| Endpoint | Límite | Justificación |
|----------|--------|---------------|
| `/order/replaceById` | **1 request/segundo** | Mantener rendimiento |
| `/order/cancelById` | **1 request/segundo** | Mantener rendimiento |
| `/order/allById` | **1 request/30 segundos** | - |

**Implementación:**
- ✅ Rate limiting configurado
- ⚠️ **Recomendación**: Para estado de órdenes en tiempo real, usar WebSocket

### 💼 API REST - Risk

| Endpoint | Límite | Justificación |
|----------|--------|---------------|
| `/risk/position/getPositions` | **1 request/5 segundos** | Mantener rendimiento |
| `/risk/accountReport` | **1 request/5 segundos** | La información se actualiza cada 5 segundos |

**Implementación:**
- ✅ Rate limiting configurado

---

## Implementación Técnica

### 1. Token Cache (`token_cache.py`)

Gestiona el caché persistente de tokens de autenticación.

**Características:**
- Almacena el token en archivo JSON
- Verifica automáticamente la expiración (23 horas para margen de seguridad)
- Carga automática al iniciar

**Uso:**

```python
from token_cache import TokenCache

cache = TokenCache('.token_cache.json')

# Guardar token
cache.set_token('mi_token_aqui', expires_in_hours=24)

# Obtener token (retorna None si expiró)
token = cache.get_token()

# Verificar validez
if cache.is_valid():
    print('Token válido')

# Ver tiempo restante
time_left = cache.get_time_until_expiration()
print(f'Expira en {time_left.total_seconds() / 3600:.1f} horas')
```

### 2. Rate Limiter (`rate_limiter.py`)

Controla la frecuencia de llamadas a la API según los límites recomendados.

**Características:**
- Configuración predefinida para todos los endpoints
- Verificación automática de límites
- Espera inteligente si se alcanza un límite
- Historial de llamadas con limpieza automática

**Uso:**

```python
from rate_limiter import get_rate_limiter

limiter = get_rate_limiter()

# Verificar si se puede llamar
endpoint = '/auth/getToken'
if limiter.can_call(endpoint):
    # Hacer la llamada
    response = await hacer_llamada()
    # Registrar la llamada
    limiter.record_call(endpoint)
else:
    print('Límite alcanzado')
    next_time = limiter.get_next_allowed_time(endpoint)
    print(f'Próxima llamada: {next_time}')

# Esperar automáticamente si es necesario
await limiter.wait_if_needed(endpoint)
```

### 3. Best Practices Config (`best_practices_config.py`)

Configuración centralizada de todas las mejores prácticas.

**Uso:**

```python
from best_practices_config import BestPracticesConfig

# Ver resumen completo
BestPracticesConfig.print_summary()

# Obtener recomendaciones
recommendations = BestPracticesConfig.get_recommendations()

# Acceder a constantes
max_instruments = BestPracticesConfig.WEBSOCKET_MAX_INSTRUMENTS_PER_SUBSCRIPTION
heartbeat_interval = BestPracticesConfig.WEBSOCKET_HEARTBEAT_INTERVAL_SECONDS
```

### 4. OMS Auth Mejorado (`oms_auth.py`)

Cliente de autenticación con caché y rate limiting integrados.

**Mejoras:**
- Caché automático de tokens
- Rate limiting integrado
- Logging detallado

**Uso:**

```python
from oms_auth import OMSAuth

auth = OMSAuth()

# Obtener token (usa caché si está disponible)
token = await auth.get_token()

# Forzar refresh (ignorar caché)
token = await auth.get_token(force_refresh=True)
```

### 5. WebSocket Connector Mejorado (`oms_websocket_connector.py`)

Conector WebSocket con heartbeat automático.

**Mejoras:**
- Heartbeat cada 30 segundos
- División automática de suscripciones en lotes de 1000
- Mejor manejo de reconexiones

**Características:**
- Ping automático cada 30 segundos
- Timeout de 10 segundos para pong
- Logging detallado

### 6. OMS Client Mejorado (`oms_client.py`)

Cliente principal con división automática de suscripciones.

**Mejoras:**
- División automática de instrumentos en lotes de 1000
- Pausa entre mensajes para no saturar
- Logging detallado

**Ejemplo:**

```python
from oms_client import OMSClient

client = OMSClient()
await client.connect()

# Si tienes 2500 instrumentos, se dividen automáticamente en 3 mensajes:
# - Mensaje 1: 1000 instrumentos
# - Mensaje 2: 1000 instrumentos  
# - Mensaje 3: 500 instrumentos
products = [{'symbol': f'TICKER_{i}', 'marketId': 'ROFX'} for i in range(2500)]
await client.send_smd_request(products=products)
```

---

## Uso en el Proyecto

### Configuración Inicial

Las mejores prácticas están **habilitadas por defecto** en todo el proyecto. No requiere configuración adicional.

### Scanner de Arbitraje

El scanner ya utiliza todas las mejores prácticas:

```bash
python arbitrage_scanner.py
```

**¿Qué hace automáticamente?**
1. ✅ Obtiene el token (usa caché si está disponible)
2. ✅ Establece 1 conexión WebSocket
3. ✅ Divide los instrumentos en lotes de 1000
4. ✅ Envía heartbeat cada 30 segundos
5. ✅ Reconecta automáticamente si se cae

### Alertas de Caución

```bash
python caucion_alert.py
```

**Mejoras aplicadas:**
- Token cacheado (no solicita uno nuevo cada vez)
- Conexión WebSocket con heartbeat
- Rate limiting automático

### Cliente Base

```bash
python oms_client.py
```

**Mejoras aplicadas:**
- Token cacheado
- División automática de instrumentos
- Heartbeat activo

---

## Testing

### Ejecutar Tests

Para verificar que las mejores prácticas funcionan correctamente:

```bash
python test_best_practices.py
```

**Tests incluidos:**
1. **Token Cache**: Verifica que el caché funcione correctamente
2. **Rate Limiter**: Verifica que los límites se respeten
3. **Config**: Verifica que la configuración sea correcta

### Ver Resumen de Configuración

```bash
python best_practices_config.py
```

Muestra un resumen completo de todas las mejores prácticas implementadas.

### Logs

Todos los componentes tienen logging detallado:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

**Mensajes típicos:**
- `Token cargado desde caché (expira en X horas)`
- `Heartbeat enviado correctamente`
- `Dividiendo 2500 instrumentos en lotes de 1000`
- `Rate limit alcanzado para /auth/getToken`

---

## Beneficios de la Implementación

### 🚀 Mejor Rendimiento
- Menos llamadas a la API = menor latencia
- Conexión WebSocket persistente = datos en tiempo real
- Caché de token = inicio más rápido

### 💰 Menor Carga en Servidores
- Respeta los límites de la API
- No satura los servidores con polling
- Uso eficiente de recursos

### 🛡️ Más Confiable
- Reconexión automática
- Heartbeat mantiene la conexión activa
- Rate limiting evita errores por límites excedidos

### 📊 Mejor Experiencia
- Datos en tiempo real sin delays
- Sin interrupciones por límites
- Logging claro para debugging

---

## Comparativa: Antes vs Después

### ❌ Antes (Sin Mejores Prácticas)

```python
# Solicitar token cada vez
token = await auth.get_token()  # Llamada REST cada vez

# Polling de market data cada segundo
while True:
    data = await get_market_data()  # REST cada segundo ❌
    await asyncio.sleep(1)

# Sin heartbeat
# Conexión se cae sin aviso
```

**Problemas:**
- Múltiples requests de token por día (excede límite)
- Polling REST ineficiente y con latencia
- Conexiones se caen sin heartbeat
- Puede exceder rate limits

### ✅ Después (Con Mejores Prácticas)

```python
# Token cacheado (1 vez/día máximo)
token = await auth.get_token()  # Usa caché ✅

# WebSocket con datos en tiempo real
await client.connect()  # 1 conexión/día ✅
await client.send_smd_request(products)  # Datos en tiempo real ✅
# Heartbeat automático cada 30s ✅

# División automática si >1000 instrumentos
# Rate limiting automático en REST
```

**Beneficios:**
- ✅ Respeta límite de 1 request/día para token
- ✅ Datos en tiempo real sin polling
- ✅ Heartbeat mantiene conexión activa
- ✅ División automática de instrumentos
- ✅ Rate limiting integrado

---

## Checklist de Implementación

Si estás usando este proyecto, verifica que:

- ✅ El archivo `.token_cache.json` está en `.gitignore`
- ✅ El token se solicita máximo 1 vez por día
- ✅ Usas WebSocket para market data en tiempo real (no polling REST)
- ✅ Los instrumentos se dividen en lotes de máximo 1000
- ✅ El heartbeat está activo cada 30 segundos
- ✅ Solo mantienes 1 conexión WebSocket activa
- ✅ El rate limiting está habilitado para llamadas REST

---

## Referencias

### Documentación Oficial

- **API Hub Primary**: https://apihub.primary.com.ar/
- **Consultas**: mpi@primary.com.ar
- **Documento**: "Buenas Prácticas de Consumo en APIs de Riesgo PreTrade y Trading" (Julio 2021)

### Endpoints Key

| Aspecto | Recomendación |
|---------|---------------|
| **Market Data en tiempo real** | ✅ WebSocket (no REST polling) |
| **Estado de órdenes** | ✅ WebSocket (no REST polling) |
| **Envío masivo de órdenes** | ✅ WebSocket o FIX (no REST) |
| **Token de autenticación** | ✅ Cachear y reutilizar (1 vez/día) |
| **Instrumentos** | ✅ Consultar 1 vez/día (no cambian) |

### Límites Importantes

```
Token:             1 request / día
Instruments:       1 request / día
Market Data REST:  1 request / segundo (solo cierres)
WebSocket:         1 conexión / día
Heartbeat:         1 ping / 30 segundos
Suscripciones:     máx 1000 instrumentos / mensaje
```

---

## Soporte

Si tienes dudas sobre la implementación:

1. Revisa los logs (nivel INFO o DEBUG)
2. Ejecuta los tests: `python test_best_practices.py`
3. Ve el resumen de config: `python best_practices_config.py`
4. Contacta a Primary: mpi@primary.com.ar

---

**¡Implementación completa de mejores prácticas de Primary/Matba Rofex!** 🎉

