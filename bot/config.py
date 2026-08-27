"""
Configuración del bot DJ Discord.
Carga variables de entorno y proporciona configuración tipada.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Config:
    """Configuración centralizada del bot."""

    # Discord
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")

    # Bot
    PREFIX: str = os.getenv("PREFIX", "!")
    MAX_QUEUE_SIZE: int = int(os.getenv("MAX_QUEUE_SIZE", "50"))
    DEFAULT_VOLUME: float = float(os.getenv("DEFAULT_VOLUME", "0.5"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls) -> list[str]:
        """Valida la configuración y retorna lista de errores."""
        errors = []

        if not cls.DISCORD_TOKEN or cls.DISCORD_TOKEN == "tu_token_de_discord_aqui":
            errors.append("DISCORD_TOKEN no configurado en .env")

        if not 0.0 <= cls.DEFAULT_VOLUME <= 1.0:
            errors.append("DEFAULT_VOLUME debe estar entre 0.0 y 1.0")

        if cls.MAX_QUEUE_SIZE < 1:
            errors.append("MAX_QUEUE_SIZE debe ser mayor a 0")

        return errors


# Instancia global de configuración
config = Config()