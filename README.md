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
OMS_USER=tu_usuario
OMS_PASSWORD=tu_password
```

## Uso

### Ejecutar el cliente

```bash
python oms_client.py
```

El cliente:
1. Obtiene automáticamente el token de autenticación desde `https://api.lbo.xoms.com.ar/auth/getToken`
2. Se conecta al servidor WebSocket `wss://api.lbo.xoms.com.ar`
3. Envía la solicitud SMD con los productos configurados
4. Mantiene la conexión activa y muestra los mensajes recibidos

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
- `main.py`: Archivo principal del proyecto

## Notas

- El token se obtiene automáticamente antes de establecer la conexión WebSocket
- El formato del header de autorización puede necesitar ajustes según la documentación de la API
- Los mensajes recibidos se muestran en consola y se registran en los logs
