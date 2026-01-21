# Market Data Tools - OMS WebSocket Client

Cliente WebSocket para conectarse al servidor OMS y recibir datos de mercado en tiempo real.

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

## Estructura del proyecto

- `oms_websocket_connector.py`: Clase base para manejar conexiones WebSocket
- `oms_auth.py`: Manejo de autenticación y obtención de tokens
- `oms_client.py`: Cliente principal que implementa la funcionalidad completa
- `telegram_notifier.py`: Servicio para enviar alertas a Telegram
- `caucion_alert.py`: Servidor de monitoreo de caución con alertas a Telegram
- `market_data_store.py`: Utilidad para persistir datos de mercado en CSV
- `main.py`: Archivo principal del proyecto

## Notas

- El token se obtiene automáticamente antes de establecer la conexión WebSocket
- El formato del header de autorización puede necesitar ajustes según la documentación de la API
- Los mensajes recibidos se muestran en consola y se registran en los logs
- El servidor de alertas de caución requiere las variables de entorno de Telegram configuradas
- Las alertas se envían solo cuando el precio bid es mayor a 50
- No se repiten alertas si el cambio es menor al 10% desde la última alerta
