"""
Token Cache
Caché persistente para tokens de autenticación según buenas prácticas de Primary.
El token debe solicitarse máximo 1 vez por día ya que expira a las 24 horas.
"""
import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


class TokenCache:
    """
    Caché para almacenar y recuperar tokens de autenticación.
    Implementa las mejores prácticas: 1 request por día.
    """
    
    def __init__(self, cache_file: str = '.token_cache.json'):
        """
        Inicializa el caché de tokens.
        
        Args:
            cache_file: Ruta del archivo de caché
        """
        self.cache_file = Path(cache_file)
        self.token: Optional[str] = None
        self.expires_at: Optional[datetime] = None
        
        # Cargar caché si existe
        self._load_cache()
    
    def _load_cache(self):
        """Carga el caché desde el archivo."""
        if not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            token = data.get('token')
            expires_at_str = data.get('expires_at')
            
            if token and expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                
                # Verificar si el token aún es válido
                if expires_at > datetime.now():
                    self.token = token
                    self.expires_at = expires_at
                    logger.info(f'Token cargado desde caché. Expira: {expires_at}')
                else:
                    logger.info('Token en caché expirado, se solicitará uno nuevo')
                    self._clear_cache_file()
        
        except Exception as e:
            logger.warning(f'Error al cargar caché de token: {str(e)}')
            self._clear_cache_file()
    
    def _save_cache(self):
        """Guarda el caché en el archivo."""
        if not self.token or not self.expires_at:
            return
        
        try:
            data = {
                'token': self.token,
                'expires_at': self.expires_at.isoformat(),
                'created_at': datetime.now().isoformat()
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f'Token guardado en caché. Expira: {self.expires_at}')
        
        except Exception as e:
            logger.error(f'Error al guardar caché de token: {str(e)}')
    
    def _clear_cache_file(self):
        """Elimina el archivo de caché."""
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
        except Exception as e:
            logger.warning(f'Error al eliminar archivo de caché: {str(e)}')
    
    def get_token(self) -> Optional[str]:
        """
        Obtiene el token si está disponible y no ha expirado.
        
        Returns:
            Token válido o None si no hay token válido
        """
        if not self.token or not self.expires_at:
            return None
        
        # Verificar si el token aún es válido
        if self.expires_at <= datetime.now():
            logger.info('Token expirado')
            self.clear()
            return None
        
        return self.token
    
    def set_token(self, token: str, expires_in_hours: int = 24):
        """
        Guarda un token en el caché.
        
        Args:
            token: Token de autenticación
            expires_in_hours: Horas hasta la expiración (default: 24)
        """
        self.token = token
        # El token expira al final del día según la documentación
        # Usamos 23 horas para asegurar que se renueve antes
        self.expires_at = datetime.now() + timedelta(hours=23)
        
        # Guardar en archivo
        self._save_cache()
        
        logger.info(
            f'Token guardado. Expira en {expires_in_hours} horas '
            f'({self.expires_at.strftime("%Y-%m-%d %H:%M:%S")})'
        )
    
    def is_valid(self) -> bool:
        """
        Verifica si hay un token válido disponible.
        
        Returns:
            True si hay un token válido, False en caso contrario
        """
        return self.get_token() is not None
    
    def clear(self):
        """Limpia el caché."""
        self.token = None
        self.expires_at = None
        self._clear_cache_file()
        logger.info('Caché de token limpiado')
    
    def get_expiration_time(self) -> Optional[datetime]:
        """
        Obtiene el tiempo de expiración del token.
        
        Returns:
            Datetime de expiración o None si no hay token
        """
        return self.expires_at
    
    def get_time_until_expiration(self) -> Optional[timedelta]:
        """
        Obtiene el tiempo restante hasta la expiración.
        
        Returns:
            Timedelta hasta la expiración o None si no hay token válido
        """
        if not self.expires_at:
            return None
        
        now = datetime.now()
        if self.expires_at <= now:
            return None
        
        return self.expires_at - now

