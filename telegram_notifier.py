"""
Telegram Notifier
Servicio para enviar alertas a Telegram cuando hay cambios en los instrumentos de caución.
"""
import os
import logging
import html
from typing import Optional
import aiohttp
from dotenv import load_dotenv
import pathlib

# Cargar variables de entorno desde .env
script_dir = pathlib.Path(__file__).parent.absolute()
env_path = script_dir / '.env'
load_dotenv(dotenv_path=env_path)
load_dotenv()


class TelegramNotifier:
    """
    Clase para enviar notificaciones a Telegram mediante el Bot API.
    """
    
    def __init__(self):
        """
        Inicializa el notificador de Telegram.
        """
        self.logger = logging.getLogger(__name__)
        
        # Obtener credenciales del .env
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.bot_token:
            raise ValueError(
                'La variable TELEGRAM_BOT_TOKEN debe estar definida en el archivo .env'
            )
        
        if not self.chat_id:
            raise ValueError(
                'La variable TELEGRAM_CHAT_ID debe estar definida en el archivo .env'
            )
        
        self.api_url = f'https://api.telegram.org/bot{self.bot_token}/sendMessage'
    
    async def send_message(self, message: str) -> bool:
        """
        Envía un mensaje a Telegram.
        
        Args:
            message: Mensaje a enviar.
        
        Returns:
            True si el mensaje fue enviado exitosamente, False en caso contrario.
        """
        try:
            payload = {
                'chat_id': self.chat_id,
                'text': message
                # Sin parse_mode para evitar problemas de parseo
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info('Mensaje enviado a Telegram exitosamente')
                        return True
                    else:
                        error_text = await response.text()
                        error_message = f'Error al enviar mensaje a Telegram. Status: {response.status}'
                        
                        # Mensajes de error más descriptivos
                        if 'chat not found' in error_text.lower():
                            error_message += (
                                '\n❌ Chat no encontrado. Posibles causas:\n'
                                '1. El TELEGRAM_CHAT_ID es incorrecto\n'
                                '2. No has iniciado una conversación con el bot (envía /start al bot primero)\n'
                                '3. Si es un grupo, el bot debe estar agregado al grupo\n'
                                '\nPara obtener tu chat_id correcto:\n'
                                f'1. Envía un mensaje a tu bot\n'
                                f'2. Visita: https://api.telegram.org/bot{self.bot_token}/getUpdates\n'
                                f'3. Busca "chat":{{"id":...}} en la respuesta'
                            )
                        elif 'unauthorized' in error_text.lower():
                            error_message += '\n❌ Bot token inválido. Verifica tu TELEGRAM_BOT_TOKEN'
                        else:
                            error_message += f'\nRespuesta: {error_text[:200]}'
                        
                        self.logger.error(error_message)
                        print(f'\n{error_message}\n')
                        return False
        except aiohttp.ClientError as e:
            self.logger.error(f'Error de conexión al enviar mensaje a Telegram: {str(e)}')
            return False
        except Exception as e:
            self.logger.error(f'Error inesperado al enviar mensaje a Telegram: {str(e)}')
            return False
    
    async def send_cauction_alert(
        self,
        symbol: str,
        bid: Optional[float],
        offer: Optional[float],
        previous_bid: Optional[float] = None,
        previous_offer: Optional[float] = None
    ) -> bool:
        """
        Envía una alerta específica sobre cambios en caución.
        
        Args:
            symbol: Símbolo del instrumento (ej: 'MERV - XMEV - PESOS - 1D').
            bid: Precio bid actual.
            offer: Precio offer actual.
            previous_bid: Precio bid anterior (opcional).
            previous_offer: Precio offer anterior (opcional).
        
        Returns:
            True si el mensaje fue enviado exitosamente, False en caso contrario.
        """
        # Formatear mensaje en texto plano (sin formato HTML/Markdown para evitar errores de parseo)
        message_parts = [
            f'🚨 Alerta de Caución - Bid > 50',
            f'',
            f'Instrumento: {symbol}',
        ]
        
        if bid is not None:
            bid_change = ''
            if previous_bid is not None and previous_bid != bid:
                change = bid - previous_bid
                change_pct = (change / previous_bid * 100) if previous_bid != 0 else 0
                direction = '📈' if change > 0 else '📉'
                bid_change = f' ({direction} {change:+.2f}, {change_pct:+.2f}%)'
            message_parts.append(f'Bid: {bid:.2f}{bid_change}')
        
        if offer is not None:
            offer_change = ''
            if previous_offer is not None and previous_offer != offer:
                change = offer - previous_offer
                change_pct = (change / previous_offer * 100) if previous_offer != 0 else 0
                direction = '📈' if change > 0 else '📉'
                offer_change = f' ({direction} {change:+.2f}, {change_pct:+.2f}%)'
            message_parts.append(f'Offer: {offer:.2f}{offer_change}')
        
        message = '\n'.join(message_parts)
        
        return await self.send_message(message)
