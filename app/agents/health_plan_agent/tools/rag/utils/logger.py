"""
utils/logger.py

Configurador de logging estruturado em JSON para toda a aplicação.
"""
import logging
import sys

from pythonjsonlogger import jsonlogger
from app.config import LOG_LEVEL


def get_logger(name: str) -> logging.Logger:
    """
    Retorna um logger configurado para saída estruturada em JSON.

    Args:
        name (str): nome do logger (geralmente __name__ do módulo).

    Returns:
        logging.Logger: instância de logger configurada.
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # Evita adicionar múltiplos handlers se já configurado
    if not logger.handlers:
        handler = logging.StreamHandler(stream=sys.stdout)
        formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(levelname)s %(name)s %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
