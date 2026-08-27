"""
Descargador de audio usando yt-dlp.
Extrae información y URLs de audio de YouTube, SoundCloud, etc.
"""
import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import yt_dlp

from bot.config import config

logger = logging.getLogger(__name__)


@dataclass
class TrackInfo:
    """Información de una pista de audio."""
    title: str
    url: str              # URL original (YouTube, SoundCloud, etc.)
    audio_url: str        # URL directa del audio para ffmpeg
    duration: int         # Duración en segundos
    thumbnail: str        # URL de la miniatura
    uploader: str         # Canal/artista
    webpage_url: str      # URL de la página web
    requester: str        # Usuario que pidió la canción

    def __str__(self) -> str:
        return f"{self.title} ({self.duration // 60}:{self.duration % 60:02d})"


class AudioDownloader:
    """Descargador de audio asíncrono usando yt-dlp."""

    # Configuración de yt-dlp para obtener solo audio
    YDL_OPTS = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "default_search": "ytsearch",  # Buscar en YouTube si no es URL
        "source_address": "0.0.0.0",   # IPv4 para evitar problemas de red
    }

    def __init__(self):
        self._ydl = yt_dlp.YoutubeDL(self.YDL_OPTS)

    async def extract_info(self, query: str, requester: str) -> Optional[TrackInfo]:
        """
        Extrae información de audio de una URL o búsqueda.

        Args:
            query: URL de YouTube/SoundCloud o término de búsqueda
            requester: Nombre del usuario que solicita

        Returns:
            TrackInfo con metadatos y URL de audio, o None si falla
        """
        try:
            # Ejecutar en thread pool para no bloquear el event loop
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None, lambda: self._ydl.extract_info(query, download=False)
            )

            if not info:
                logger.warning(f"No se encontró info para: {query}")
                return None

            # Si es una playlist/búsqueda, tomar el primer resultado
            if "entries" in info:
                info = info["entries"][0]

            # Validar que tenga lo necesario
            if not info.get("url"):
                logger.warning(f"No hay URL de audio para: {query}")
                return None

            track = TrackInfo(
                title=info.get("title", "Desconocido"),
                url=query,
                audio_url=info["url"],
                duration=info.get("duration", 0),
                thumbnail=info.get("thumbnail", ""),
                uploader=info.get("uploader", "Desconocido"),
                webpage_url=info.get("webpage_url", query),
                requester=requester,
            )

            logger.info(f"Track extraído: {track.title} ({track.duration}s)")
            return track

        except yt_dlp.utils.DownloadError as e:
            logger.error(f"Error de yt-dlp para '{query}': {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado extrayendo info: {e}", exc_info=True)
            return None

    async def search(self, query: str, requester: str, max_results: int = 5) -> list[TrackInfo]:
        """
        Busca pistas en YouTube y retorna lista de resultados.

        Args:
            query: Término de búsqueda
            requester: Usuario que busca
            max_results: Máximo número de resultados

        Returns:
            Lista de TrackInfo
        """
        search_opts = self.YDL_OPTS.copy()
        search_opts["default_search"] = f"ytsearch{max_results}"
        search_opts["extract_flat"] = True  # Solo metadatos, no URLs de audio aún

        ydl = yt_dlp.YoutubeDL(search_opts)

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: ydl.extract_info(query, download=False)
            )

            if not result or "entries" not in result:
                return []

            tracks = []
            for entry in result["entries"][:max_results]:
                if not entry:
                    continue
                # Obtener info completa para cada resultado
                full_info = await self.extract_info(entry["url"], requester)
                if full_info:
                    tracks.append(full_info)

            return tracks

        except Exception as e:
            logger.error(f"Error en búsqueda: {e}", exc_info=True)
            return []


# Instancia global
downloader = AudioDownloader()