"""
Script de ayuda para obtener el Chat ID de Telegram
Ejecuta este script después de configurar tu TELEGRAM_BOT_TOKEN en el .env
"""
import os
import json
import aiohttp
import asyncio
from dotenv import load_dotenv
import pathlib

# Cargar variables de entorno desde .env
script_dir = pathlib.Path(__file__).parent.absolute()
env_path = script_dir / '.env'
load_dotenv(dotenv_path=env_path)
load_dotenv()


async def get_chat_id():
    """
    Obtiene el chat_id del usuario desde la API de Telegram.
    """
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        print('❌ Error: TELEGRAM_BOT_TOKEN no está configurado en el archivo .env')
        print('\nPor favor, configura tu bot token primero:')
        print('1. Busca @BotFather en Telegram')
        print('2. Envía el comando /newbot')
        print('3. Sigue las instrucciones y copia el token')
        print('4. Agrega TELEGRAM_BOT_TOKEN=tu_token en tu archivo .env')
        return
    
    api_url = f'https://api.telegram.org/bot{bot_token}/getUpdates'
    
    print('🔍 Obteniendo información de chats...')
    print('⚠️  IMPORTANTE: Asegúrate de haber enviado al menos un mensaje a tu bot primero\n')
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if not data.get('ok'):
                        print(f'❌ Error de la API: {data.get("description", "Error desconocido")}')
                        return
                    
                    results = data.get('result', [])
                    
                    if not results:
                        print('⚠️  No se encontraron mensajes.')
                        print('\nPasos a seguir:')
                        print('1. Busca tu bot en Telegram (usa el nombre que le diste a @BotFather)')
                        print('2. Inicia una conversación con el bot')
                        print('3. Envía cualquier mensaje al bot (por ejemplo: /start o "Hola")')
                        print('4. Ejecuta este script nuevamente')
                        return
                    
                    print('✅ Chats encontrados:\n')
                    chat_ids = set()
                    
                    for update in results:
                        message = update.get('message', {})
                        if message:
                            chat = message.get('chat', {})
                            chat_id = chat.get('id')
                            chat_type = chat.get('type', 'unknown')
                            chat_title = chat.get('title') or chat.get('first_name', 'Sin nombre')
                            
                            if chat_id:
                                chat_ids.add((chat_id, chat_type, chat_title))
                    
                    if chat_ids:
                        print('📋 Lista de Chat IDs encontrados:\n')
                        for chat_id, chat_type, chat_title in sorted(chat_ids):
                            chat_type_emoji = '👤' if chat_type == 'private' else '👥' if chat_type == 'group' else '📢'
                            print(f'{chat_type_emoji} {chat_title}')
                            print(f'   Tipo: {chat_type}')
                            print(f'   Chat ID: {chat_id}')
                            print()
                        
                        print('💡 Copia el Chat ID que necesites y agrégalo a tu archivo .env:')
                        print('   TELEGRAM_CHAT_ID=tu_chat_id')
                        print('\n📝 Nota: Si es un grupo, el Chat ID será un número negativo')
                    else:
                        print('⚠️  No se pudieron extraer los Chat IDs de los mensajes')
                
                elif response.status == 401:
                    print('❌ Error: Bot token inválido o no autorizado')
                    print('Verifica que tu TELEGRAM_BOT_TOKEN sea correcto')
                else:
                    error_text = await response.text()
                    print(f'❌ Error HTTP {response.status}: {error_text[:200]}')
    
    except aiohttp.ClientError as e:
        print(f'❌ Error de conexión: {str(e)}')
    except Exception as e:
        print(f'❌ Error inesperado: {str(e)}')


if __name__ == '__main__':
    print('=' * 60)
    print('🔧 Herramienta para obtener Chat ID de Telegram')
    print('=' * 60)
    print()
    asyncio.run(get_chat_id())
