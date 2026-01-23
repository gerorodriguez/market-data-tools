# Market Data Tools - OMS WebSocket Client & Arbitrage Scanner

Cliente WebSocket para conectarse al servidor OMS y recibir datos de mercado en tiempo real, con scanner de arbitraje de plazos de liquidación.

## Configuración

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

```env
# Variables de entorno para OMS (Order Management System)
OMS_HOST=oms_host
OMS_USER=tu_usuario_oms
OMS_PASSWORD=tu_contraseña_oms

# Variables de entorno para Telegram (requeridas para el servidor de alertas)
TELEGRAM_BOT_TOKEN=tu_bot_token_de_telegram
TELEGRAM_CHAT_ID=tu_chat_id_de_telegram
```

#### Cómo obtener las credenciales de Telegram:

**Para obtener el Bot Token:**
1. Busca `@BotFather` en Telegram
2. Envía el comando `/newbot`
3. Sigue las instrucciones para crear tu bot
4. Copia el token que te proporciona BotFather

**Para obtener el Chat ID:**

**Opción 1 - Usando el script incluido (Recomendado):**
```bash
python get_telegram_chat_id.py
```
Este script te mostrará todos los chats disponibles después de que envíes un mensaje a tu bot.

**Opción 2 - Manualmente:**
1. Busca tu bot en Telegram (usa el nombre que le diste a @BotFather)
2. Inicia una conversación con el bot y envía cualquier mensaje (ej: `/start` o "Hola")
3. Visita: `https://api.telegram.org/bot<tu_bot_token>/getUpdates`
4. Busca el campo `"chat":{"id":...}` en la respuesta JSON
5. Copia el número (puede ser negativo si es un grupo)

**Opción 3 - Usando @userinfobot:**
1. Busca `@userinfobot` en Telegram
2. Inicia una conversación con él
3. Te mostrará tu chat ID personal

## Uso

### Ejecutar el cliente básico

```bash
python main.py
```

O directamente:

```bash
python oms_client.py
```

El cliente:
1. Obtiene automáticamente el token de autenticación desde el servidor OMS configurado en `OMS_HOST`
2. Se conecta al servidor WebSocket usando el host configurado en `OMS_HOST`
3. Envía la solicitud SMD con los productos configurados
4. Mantiene la conexión activa y muestra los mensajes recibidos

### Ejecutar el servidor de alertas de caución

```bash
python caucion_alert.py
```

El servidor de alertas:
1. Se conecta al servidor WebSocket OMS
2. Se suscribe únicamente a los instrumentos de caución (1D y 3D)
3. Monitorea cambios en los precios bid y offer
4. Envía alertas a Telegram cuando detecta cambios significativos (>0.01)
5. Se mantiene ejecutándose indefinidamente hasta que lo detengas con Ctrl+C
6. Intenta reconectar automáticamente si se pierde la conexión

**Características:**
- Monitorea solo los instrumentos de caución: `MERV - XMEV - PESOS - 1D` y `MERV - XMEV - PESOS - 3D`
- **Solo alerta cuando el precio bid es mayor a 50**
- **No repite alertas si el cambio es menor al 10% desde la última alerta**
- Muestra porcentajes de cambio cuando hay variaciones
- Envía notificaciones de inicio, conexión, reconexión y errores

### Uso programático

```python
import asyncio
from oms_client import OMSClient

async def main():
    client = OMSClient()
    
    # Conectar y enviar solicitud
    if await client.connect():
        await client.send_smd_request(
            level=1,
            entries=['BI', 'OF'],
            products=[
                {'symbol': 'MERV - XMEV - PESOS - 1D', 'marketId': 'ROFX'},
                {'symbol': 'MERV - XMEV - PESOS - 3D', 'marketId': 'ROFX'}
            ]
        )
        
        # Mantener conexión activa
        await asyncio.sleep(60)
        await client.disconnect()

asyncio.run(main())
```

## Ejecutar el Scanner de Arbitraje de Plazos

```bash
python arbitrage_scanner.py
```

El scanner de arbitraje:
1. Se conecta al servidor WebSocket OMS
2. Se suscribe a todos los instrumentos configurados en `tickers.csv` (CI y 24hs)
3. Monitorea en tiempo real las oportunidades de arbitraje de plazos
4. Calcula el P&L considerando:
   - Comisiones del broker
   - Derechos de mercado según tipo de instrumento
   - Costo o ganancia de la caución
5. Envía alertas a Telegram cuando detecta oportunidades rentables
6. Filtro inteligente para evitar spam (cooldown configurable)

**Características:**
- Detecta automáticamente arbitrajes entre CI y 24hs
- Calcula caución colocadora (cuando vendes primero) o tomadora (cuando compras primero)
- Configurable: tasas de caución, aranceles, rentabilidad mínima, cooldown de alertas
- Muestra P&L, rentabilidad porcentual, spread TNA y más detalles
- Reconexión automática si se pierde la conexión

**Configuración:**

Puedes configurar el scanner de dos formas:

**Opción 1: Variables de entorno** (recomendado)

Agrega estas variables a tu archivo `.env`:

```env
# Tasas y comisiones (%)
TASA_CAUCION_TNA=35.0
ARANCEL_TOMADORA_TNA=10.0
ARANCEL_COLOCADORA_TNA=10.0
COMISION_BROKER=0.10

# Liquidación
DIAS_LIQ_24H=1

# Filtros de alertas
MIN_PROFIT_PERCENTAGE=0.1
ALERT_COOLDOWN_SECONDS=300
```

**Opción 2: Editar directamente** en `arbitrage_scanner.py` (función `main`):

```python
scanner = ArbitrageScanner(
    tickers_file='tickers.csv',          # Archivo con tickers a monitorear
    tasa_caucion=35.0,                   # TNA de la caución (%)
    dias_liq_24h=1,                      # Días de liquidación para 24hs
    arancel_tomadora=10.0,               # TNA del arancel para caución tomadora (%)
    arancel_colocadora=10.0,             # TNA del arancel para caución colocadora (%)
    min_profit_percentage=0.1,           # Rentabilidad mínima para alertar (%)
    alert_cooldown_seconds=300,          # Segundos entre alertas del mismo ticker (5 min)
    comision_broker=0.10                 # Comisión del broker (%)
)
```

**Agregar/eliminar instrumentos:**

Edita el archivo `tickers.csv`, un ticker por línea:

```csv
AL30
GD30
GGAL
MELI
AAPL
```

## Estructura del proyecto

### Archivos base
- `oms_websocket_connector.py`: Clase base para manejar conexiones WebSocket
- `oms_auth.py`: Manejo de autenticación y obtención de tokens
- `oms_client.py`: Cliente principal que implementa la funcionalidad completa
- `telegram_notifier.py`: Servicio para enviar alertas a Telegram
- `market_data_store.py`: Utilidad para persistir datos de mercado en CSV
- `main.py`: Archivo principal del proyecto

### Módulos de arbitraje
- `caucion.py`: Lógica de cálculo de caución (colocadora/tomadora)
- `instrument.py`: Clases para representar instrumentos y datos de mercado
- `settlement_trade.py`: Lógica de operaciones de arbitraje de plazos
- `settlement_arbitrage_processor.py`: Procesador que gestiona múltiples instrumentos
- `arbitrage_scanner.py`: Scanner en tiempo real con alertas a Telegram
- `tickers.csv`: Lista de tickers a monitorear

### Alertas anteriores
- `caucion_alert.py`: Servidor de monitoreo de caución (1D y 3D) con alertas a Telegram

## ¿Cómo funciona el Arbitraje de Plazos?

El arbitraje de plazos consiste en aprovechar las diferencias de precio entre dos plazos de liquidación del mismo instrumento:

### Caso 1: Vender CI / Comprar 24hs (Caución Tomadora)
1. **Compro** el título en CI (lo recibo hoy)
2. **Vendo** el título en 24hs (lo entrego mañana)
3. **Tomo** caución para financiar la compra de hoy hasta que cobre la venta de mañana

**Requiere:** Pesos o capacidad de tomar caución

### Caso 2: Vender 24hs / Comprar CI (Caución Colocadora)
1. **Vendo** el título en 24hs (lo entrego mañana)
2. **Compro** el título en CI (lo recibo hoy)
3. **Coloco** en caución el dinero que recibo hoy hasta que tenga que entregar mañana

**Requiere:** Tener el título en cartera

### Cálculo de Rentabilidad

El sistema calcula automáticamente:
- **Spread:** Diferencia porcentual entre precio de venta y compra
- **Spread TNA:** Spread anualizado según los días de diferencia
- **Costo/Ganancia de Caución:** Según tipo (tomadora/colocadora) y TNA configurada
- **Comisiones y Derechos de Mercado:** Según tipo de instrumento (0.08% CEDEARs, 0.01% Bonos, 0.001% Letras)
- **P&L Neto:** Ganancia o pérdida final después de todos los costos

**Condición de oportunidad:** El spread debe ser mayor al costo de la caución para que sea rentable.

## Notas

- El token se obtiene automáticamente antes de establecer la conexión WebSocket
- El formato del header de autorización puede necesitar ajustes según la documentación de la API
- Los mensajes recibidos se muestran en consola y se registran en los logs
- El servidor de alertas de caución requiere las variables de entorno de Telegram configuradas
- El scanner de arbitraje usa cooldown inteligente para evitar alertas repetitivas
- Todos los cálculos incluyen comisiones, derechos de mercado y costos de caución
