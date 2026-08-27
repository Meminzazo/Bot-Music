"""
Gestión de cola de reproducción por guild.
"""
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from bot.music.downloader import TrackInfo

logger = logging.getLogger(__name__)


@dataclass
class MusicQueue:
    """Cola de reproducción para un guild específico."""
    guild_id: int
    max_size: int = 50

    # Cola principal (FIFO)
    _queue: deque[TrackInfo] = field(default_factory=deque)
    # Historial de reproducidas (para funcionalidad de "previous" futura)
    _history: deque[TrackInfo] = field(default_factory=deque)

    # Canción actualmente reproduciéndose
    current: Optional[TrackInfo] = None

    def add(self, track: TrackInfo) -> bool:
        """Añade una pista a la cola. Retorna True si se añadió."""
        if len(self._queue) >= self.max_size:
            logger.warning(f"Cola llena para guild {self.guild_id}")
            return False

        self._queue.append(track)
        logger.info(f"Track añadido a cola [{self.guild_id}]: {track.title} (cola: {len(self._queue)})")
        return True

    def add_next(self, track: TrackInfo) -> bool:
        """Añade una pista al principio de la cola (próxima a sonar)."""
        if len(self._queue) >= self.max_size:
            return False

        self._queue.appendleft(track)
        logger.info(f"Track añadido al inicio [{self.guild_id}]: {track.title}")
        return True

    def get_next(self) -> Optional[TrackInfo]:
        """Obtiene y remueve la siguiente pista de la cola."""
        if not self._queue:
            return None

        track = self._queue.popleft()
        # Mover actual a historial
        if self.current:
            self._history.append(self.current)
        self.current = track
        logger.info(f"Siguiente track [{self.guild_id}]: {track.title}")
        return track

    def skip(self) -> Optional[TrackInfo]:
        """Salta la canción actual y retorna la siguiente."""
        if self.current:
            self._history.append(self.current)
        return self.get_next()

    def clear(self) -> int:
        """Limpia la cola y retorna el número de elementos removidos."""
        count = len(self._queue)
        self._queue.clear()
        logger.info(f"Cola limpiada [{self.guild_id}]: {count} tracks removidos")
        return count

    def remove(self, index: int) -> Optional[TrackInfo]:
        """Remueve una pista por índice (0-based)."""
        if 0 <= index < len(self._queue):
            track = self._queue[index]
            del self._queue[index]
            logger.info(f"Track removido [{self.guild_id}]: {track.title}")
            return track
        return None

    def move(self, from_index: int, to_index: int) -> bool:
        """Mueve una pista de posición en la cola."""
        if 0 <= from_index < len(self._queue) and 0 <= to_index < len(self._queue):
            track = self._queue[from_index]
            del self._queue[from_index]
            self._queue.insert(to_index, track)
            return True
        return False

    def shuffle(self) -> None:
        """Mezcla la cola aleatoriamente."""
        import random
        random.shuffle(self._queue)
        logger.info(f"Cola mezclada [{self.guild_id}]")

    def get_queue_list(self) -> list[TrackInfo]:
        """Retorna lista de la cola actual (sin modificar)."""
        return list(self._queue)

    def get_history_list(self) -> list[TrackInfo]:
        """Retorna historial de reproducidas."""
        return list(self._history)

    def __len__(self) -> int:
        return len(self._queue)

    def __bool__(self) -> bool:
        return bool(self._queue)

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    def peek(self) -> Optional[TrackInfo]:
        """Mira la siguiente pista sin removerla."""
        return self._queue[0] if self._queue else None


class QueueManager:
    """Gestor de colas para múltiples guilds."""

    def __init__(self, max_queue_size: int = 50):
        self._queues: dict[int, MusicQueue] = {}
        self.max_queue_size = max_queue_size

    def get_queue(self, guild_id: int) -> MusicQueue:
        """Obtiene o crea la cola para un guild."""
        if guild_id not in self._queues:
            self._queues[guild_id] = MusicQueue(guild_id, self.max_queue_size)
        return self._queues[guild_id]

    def remove_queue(self, guild_id: int) -> bool:
        """Elimina la cola de un guild."""
        if guild_id in self._queues:
            del self._queues[guild_id]
            return True
        return False

    def has_queue(self, guild_id: int) -> bool:
        return guild_id in self._queues