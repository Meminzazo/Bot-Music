"""
Reproductor de música usando discord.py voice client y ffmpeg.
Maneja la reproducción real de audio en el canal de voz.
"""
import asyncio
import logging
from typing import Optional, Callable

import discord
from discord.ext import commands

from bot.music.queue import MusicQueue, QueueManager
from bot.music.downloader import AudioDownloader, TrackInfo

logger = logging.getLogger(__name__)


class MusicPlayer:
    """
    Reproductor de música para un guild específico.
    Maneja la conexión de voz, cola y reproducción.
    """

    def __init__(self, bot: commands.Bot, guild_id: int):
        self.bot = bot
        self.guild_id = guild_id
        self.queue = MusicQueue(guild_id)
        self.downloader = AudioDownloader()

        # Estado
        self.voice_client: Optional[discord.VoiceClient] = None
        self.volume: float = 0.5
        self._playing: bool = False
        self._paused: bool = False
        self._current_task: Optional[asyncio.Task] = None

        # Callbacks
        self.on_track_start: Optional[Callable[[TrackInfo], None]] = None
        self.on_track_end: Optional[Callable[[TrackInfo], None]] = None
        self.on_queue_empty: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None

    @property
    def is_playing(self) -> bool:
        return self._playing and not self._paused

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def current_track(self) -> Optional[TrackInfo]:
        return self.queue.current

    async def connect(self, channel: discord.VoiceChannel) -> bool:
        """
        Conecta el bot al canal de voz.

        Args:
            channel: Canal de voz al que conectar

        Returns:
            True si se conectó exitosamente
        """
        try:
            if self.voice_client and self.voice_client.is_connected():
                # Ya conectado, mover si es diferente canal
                if self.voice_client.channel.id != channel.id:
                    await self.voice_client.move_to(channel)
                return True

            self.voice_client = await channel.connect()
            logger.info(f"Conectado a canal de voz: {channel.name} (guild: {self.guild_id})")
            return True

        except Exception as e:
            logger.error(f"Error conectando a voz: {e}", exc_info=True)
            if self.on_error:
                self.on_error(e)
            return False

    async def disconnect(self) -> None:
        """Desconecta el bot del canal de voz y limpia estado."""
        self.stop()

        if self.voice_client and self.voice_client.is_connected():
            await self.voice_client.disconnect()
            logger.info(f"Desconectado de voz (guild: {self.guild_id})")

        self.voice_client = None
        self.queue.clear()
        self.queue.current = None

    def set_volume(self, volume: float) -> None:
        """Establece el volumen (0.0 - 1.0)."""
        self.volume = max(0.0, min(1.0, volume))
        if self.voice_client and self.voice_client.source:
            self.voice_client.source.volume = self.volume

    async def play(self, track: TrackInfo) -> bool:
        """
        Reproduce una pista específica.

        Args:
            track: TrackInfo a reproducir

        Returns:
            True si inició reproducción
        """
        if not self.voice_client or not self.voice_client.is_connected():
            logger.error("No hay conexión de voz para reproducir")
            return False

        # Detener reproducción actual si hay
        if self.voice_client.is_playing():
            self.voice_client.stop()

        try:
            # Crear source de audio con ffmpeg
            # -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5: reconexión automática
            # -vn: sin video
            ffmpeg_options = {
                "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                "options": "-vn",
            }

            source = discord.FFmpegPCMAudio(track.audio_url, **ffmpeg_options)
            source = discord.PCMVolumeTransformer(source, volume=self.volume)

            # Reproducir con callback de fin
            def after_playing(error: Optional[Exception]):
                if error:
                    logger.error(f"Error en reproducción: {error}")
                    if self.on_error:
                        self.on_error(error)
                else:
                    logger.info(f"Track finalizado: {track.title}")

                # Programar siguiente en event loop
                asyncio.run_coroutine_threadsafe(self._on_track_end(), self.bot.loop)

            self.voice_client.play(source, after=after_playing)
            self._playing = True
            self._paused = False

            if self.on_track_start:
                self.on_track_start(track)

            logger.info(f"Reproduciendo: {track.title}")
            return True

        except Exception as e:
            logger.error(f"Error iniciando reproducción: {e}", exc_info=True)
            self._playing = False
            if self.on_error:
                self.on_error(e)
            return False

    async def _on_track_end(self) -> None:
        """Callback interno cuando termina una pista."""
        self._playing = False

        if self.on_track_end and self.queue.current:
            self.on_track_end(self.queue.current)

        # Reproducir siguiente en cola
        next_track = self.queue.get_next()
        if next_track:
            await self.play(next_track)
        else:
            logger.info("Cola vacía, reproducción terminada")
            if self.on_queue_empty:
                self.on_queue_empty()

    def pause(self) -> bool:
        """Pausa la reproducción actual."""
        if self.voice_client and self.voice_client.is_playing() and not self._paused:
            self.voice_client.pause()
            self._paused = True
            logger.info("Reproducción pausada")
            return True
        return False

    def resume(self) -> bool:
        """Reanuda la reproducción pausada."""
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()
            self._paused = False
            logger.info("Reproducción reanudada")
            return True
        return False

    def stop(self) -> None:
        """Detiene la reproducción y limpia la cola."""
        if self.voice_client and (self.voice_client.is_playing() or self.voice_client.is_paused()):
            self.voice_client.stop()
        self._playing = False
        self._paused = False
        self.queue.clear()
        self.queue.current = None
        logger.info("Reproducción detenida y cola limpiada")

    def skip(self) -> bool:
        """Salta la canción actual."""
        if self.voice_client and (self.voice_client.is_playing() or self.voice_client.is_paused()):
            self.voice_client.stop()  # Esto disparará _on_track_end
            return True
        return False

    async def add_to_queue(self, query: str, requester: str, play_next: bool = False) -> Optional[TrackInfo]:
        """
        Añade una pista a la cola (o la reproduce si no hay nada sonando).

        Args:
            query: URL o término de búsqueda
            requester: Usuario que solicita
            play_next: Si True, añade al principio de la cola

        Returns:
            TrackInfo si se añadió, None si falló
        """
        track = await self.downloader.extract_info(query, requester)
        if not track:
            return None

        if play_next:
            self.queue.add_next(track)
        else:
            self.queue.add(track)

        # Si no hay nada reproduciéndose, empezar
        if not self.is_playing and not self.queue.current:
            next_track = self.queue.get_next()
            if next_track:
                await self.play(next_track)

        return track


class PlayerManager:
    """Gestor de reproductores para múltiples guilds."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._players: dict[int, MusicPlayer] = {}

    def get_player(self, guild_id: int) -> MusicPlayer:
        """Obtiene o crea el reproductor para un guild."""
        if guild_id not in self._players:
            self._players[guild_id] = MusicPlayer(self.bot, guild_id)
        return self._players[guild_id]

    def remove_player(self, guild_id: int) -> None:
        """Elimina el reproductor de un guild."""
        if guild_id in self._players:
            del self._players[guild_id]

    def has_player(self, guild_id: int) -> bool:
        return guild_id in self._players