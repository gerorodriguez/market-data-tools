# Variables de Entorno Requeridas

Este documento describe las variables de entorno necesarias para ejecutar el proyecto.

## Archivo .env

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

## Variables para OMS (Order Management System)

### OMS_HOST
- **Descripción**: Host del servidor OMS (sin protocolo)
- **Ejemplo**: `OMS_HOST=api.xxx.xoms.com.ar`
- **Valor por defecto**: `api.xxx.xoms.com.ar`
- **Requerido**: No (tiene valor por defecto)

### OMS_USER
- **Descripción**: Usuario para autenticación con el servidor OMS
- **Ejemplo**: `OMS_USER=mi_usuario_oms`
- **Requerido**: Sí

### OMS_PASSWORD
- **Descripción**: Contraseña para autenticación con el servidor OMS
- **Ejemplo**: `OMS_PASSWORD=mi_contraseña_segura`
- **Requerido**: Sí

## Variables para Telegram (Solo para el servidor de alertas)

### TELEGRAM_BOT_TOKEN
- **Descripción**: Token del bot de Telegram para enviar alertas
- **Cómo obtenerlo**:
  1. Busca `@BotFather` en Telegram
  2. Envía el comando `/newbot`
  3. Sigue las instrucciones para crear tu bot
  4. Copia el token que te proporciona BotFather
- **Ejemplo**: `TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
- **Requerido**: Solo si usas `caucion_alert.py`

### TELEGRAM_CHAT_ID
- **Descripción**: ID del chat donde se enviarán las alertas (puede ser tu ID personal o un grupo)
- **Cómo obtenerlo**:
  
  **Opción 1 - Usando @userinfobot:**
  1. Busca `@userinfobot` en Telegram
  2. Inicia una conversación con él
  3. Te mostrará tu chat ID (un número, puede ser negativo si es un grupo)
  
  **Opción 2 - Usando la API de Telegram:**
  1. Envía un mensaje a tu bot
  2. Visita: `https://api.telegram.org/bot<tu_bot_token>/getUpdates`
  3. Busca el campo `"chat":{"id":...}` en la respuesta JSON
  4. El número que aparece es tu chat ID
  
  **Opción 3 - Para grupos:**
  1. Agrega tu bot al grupo
  2. Envía un mensaje en el grupo
  3. Visita: `https://api.telegram.org/bot<tu_bot_token>/getUpdates`
  4. Busca el campo `"chat":{"id":...}` (será un número negativo)

**Opción 4 - Usando el script incluido (Más fácil):**
```bash
python get_telegram_chat_id.py
```
Este script te mostrará todos los chats disponibles después de que envíes un mensaje a tu bot.

- **Ejemplo**: `TELEGRAM_CHAT_ID=123456789` o `TELEGRAM_CHAT_ID=-987654321` (para grupos)
- **Requerido**: Solo si usas `caucion_alert.py`

**⚠️ IMPORTANTE - Error "chat not found":**
Si recibes el error "Bad Request: chat not found", significa que:
1. El bot no ha recibido ningún mensaje tuyo aún → Envía `/start` o cualquier mensaje al bot primero
2. El Chat ID es incorrecto → Usa `python get_telegram_chat_id.py` para obtenerlo correctamente
3. Si es un grupo → Asegúrate de que el bot esté agregado al grupo y haya recibido un mensaje

## Ejemplo de archivo .env completo

```env
# Variables de entorno para OMS
OMS_HOST=oms_host
OMS_USER=mi_usuario_oms
OMS_PASSWORD=mi_contraseña_segura

# Variables de entorno para Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789

# Variables opcionales para Scanner de Arbitraje (valores por defecto)
TASA_CAUCION_TNA=35.0
ARANCEL_TOMADORA_TNA=10.0
ARANCEL_COLOCADORA_TNA=10.0
COMISION_BROKER=0.10
DIAS_LIQ_24H=1
MIN_PROFIT_PERCENTAGE=0.1
ALERT_COOLDOWN_SECONDS=300
LOG_LEVEL=INFO
```

## Notas de Seguridad

⚠️ **IMPORTANTE**: 
- Nunca subas el archivo `.env` a un repositorio público
- El archivo `.env` ya está incluido en `.gitignore` para proteger tus credenciales
- Mantén tus tokens y contraseñas seguros
- Si compartes el código, usa `.env.example` como plantilla sin valores reales
