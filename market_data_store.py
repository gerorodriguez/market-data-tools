"""
Market Data Store
Utilidad para persistir en disco los mensajes de market data recibidos.
"""
import csv
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any


class MarketDataStore:
    """
    Abstracción sencilla para guardar market data en un archivo CSV.

    Cada fila contiene:
      - timestamp: momento en que se recibió el mensaje (UTC ISO-8601)
      - raw_json: mensaje original serializado en JSON
    """

    def __init__(self, file_path: str = 'market_data.csv') -> None:
        """
        Inicializa el store de market data.

        Args:
            file_path: Ruta del archivo CSV donde se guardarán los datos.
        """
        self.file_path = file_path
        self.fieldnames = ['timestamp', 'raw_json']
        self._ensure_file_with_header()

    def _ensure_file_with_header(self) -> None:
        """
        Crea el archivo y escribe el header si aún no existe o está vacío.
        """
        file_exists = os.path.exists(self.file_path)
        needs_header = (not file_exists) or os.path.getsize(self.file_path) == 0

        if needs_header:
            with open(self.file_path, mode='w', newline='', encoding='utf-8') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=self.fieldnames)
                writer.writeheader()

    def append_message(self, message: Dict[str, Any]) -> None:
        """
        Agrega un mensaje de market data al CSV.

        Args:
            message: Mensaje recibido del WebSocket (dict).
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        raw_json = json.dumps(message, ensure_ascii=False)

        with open(self.file_path, mode='a', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self.fieldnames)
            writer.writerow(
                {
                    'timestamp': timestamp,
                    'raw_json': raw_json,
                }
            )

