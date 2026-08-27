#!/usr/bin/env python3
"""
Bot DJ Discord - Punto de entrada principal.
Bot de música para Discord que reproduce audio de YouTube/SoundCloud.
"""
import asyncio
import logging
import sys
from pathlib import Path

import discord
from discord.ext import commands

from bot.config import config

# Configurar logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


class DJBot(commands.Bot):
    """Bot principal de Discord con funcionalidades de DJ."""

    def __init__(self):
        # Configurar intents necesarios
        intents = discord.Intents.default()
        intents.message_content = True  # Para leer comandos
        intents.voice_states = True     # Para gestión de voz
        intents.guilds = True           # Para info de servidores

        super().__init__(
            command_prefix=config.PREFIX,
            intents=intents,
            help_command=None,  # Usaremos nuestro propio help
            case_insensitive=True,
        )

        # Diccionario para guardar players por guild
        self.players: dict[int, "MusicPlayer"] = {}

    async def setup_hook(self) -> None:
        """Se ejecuta al iniciar el bot, antes de conectar a Discord."""
        logger.info("Cargando extensiones (cogs)...")

        # Cargar cogs (módulos de comandos)
        try:
            await self.load_extension("bot.commands.voice")
            await self.load_extension("bot.commands.music")
            logger.info("Extensiones cargadas correctamente")
        except Exception as e:
            logger.error(f"Error cargando extensiones: {e}")
            raise

    async def on_ready(self) -> None:
        """Se ejecuta cuando el bot está listo y conectado."""
        logger.info(f"Bot conectado como {self.user} (ID: {self.user.id})")
        logger.info(f"Conectado a {len(self.guilds)} servidor(es)")

        # Mostrar servidores
        for guild in self.guilds:
            logger.info(f"  - {guild.name} (ID: {guild.id})")

        # Establecer presencia
        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name=f"{config.PREFIX}help | DJ Bot"
        )
        await self.change_presence(activity=activity)

    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        """Manejo global de errores de comandos."""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignorar comandos no encontrados

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Falta un argumento requerido: `{error.param.name}`")
            return

        if isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Argumento inválido: {error}")
            return

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Espera {error.retry_after:.1f}s antes de usar este comando de nuevo")
            return

        # Log del error para debugging
        logger.error(f"Error en comando {ctx.command}: {error}", exc_info=True)
        await ctx.send("❌ Ocurrió un error inesperado. Revisa los logs.")

    def get_player(self, guild_id: int) -> "MusicPlayer":
        """Obtiene o crea el reproductor para un guild."""
        if guild_id not in self.players:
            from bot.music.player import MusicPlayer
            self.players[guild_id] = MusicPlayer(self, guild_id)
        return self.players[guild_id]

    def remove_player(self, guild_id: int) -> None:
        """Elimina el reproductor de un guild."""
        if guild_id in self.players:
            del self.players[guild_id]


async def main() -> None:
    """Función principal de entrada."""
    # Validar configuración
    errors = config.validate()
    if errors:
        logger.error("Errores de configuración:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)

    # Crear y ejecutar bot
    bot = DJBot()

    try:
        logger.info("Iniciando bot...")
        await bot.start(config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Deteniendo bot por interrupción del usuario...")
    except discord.LoginFailure:
        logger.error("Token de Discord inválido. Revisa tu .env")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await bot.close()


if __name__ == "__main__":
    # Windows fix para asyncio
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())