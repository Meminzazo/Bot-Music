"""
Comandos de música: play, pause, skip, queue, nowplaying, stop, volume.
"""
import logging

import discord
from discord.ext import commands

from bot.music.downloader import TrackInfo
from bot.config import config

logger = logging.getLogger(__name__)


class MusicCommands(commands.Cog, name="Música"):
    """Comandos para reproducción de música."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_player(self, guild_id: int):
        """Obtiene el reproductor del guild."""
        return self.bot.get_player(guild_id)

    def _require_voice(self, ctx: commands.Context):
        """Verifica que el bot esté en un canal de voz."""
        player = self._get_player(ctx.guild.id)
        if not player.voice_client or not player.voice_client.is_connected():
            raise commands.CommandError("No estoy conectado a un canal de voz. Usa `!join` primero.")

    def _require_playing(self, ctx: commands.Context):
        """Verifica que haya algo reproduciéndose."""
        player = self._get_player(ctx.guild.id)
        if not player.is_playing and not player.is_paused:
            raise commands.CommandError("No hay nada reproduciéndose actualmente.")

    @commands.command(name="play", aliases=["p", "reproducir", "tocar"])
    async def play(self, ctx: commands.Context, *, query: str = None) -> None:
        """
        Reproduce música de YouTube o añade a la cola.
        Uso: !play <URL o búsqueda>
        """
        if not query:
            await ctx.send("❌ Especifica qué reproducir: `!play <URL o búsqueda>`")
            return

        # Verificar que el usuario esté en canal de voz
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ Debes estar en un canal de voz para usar este comando.")
            return

        # Conectar si no está conectado
        player = self._get_player(ctx.guild.id)
        if not player.voice_client or not player.voice_client.is_connected():
            channel = ctx.author.voice.channel
            permissions = channel.permissions_for(ctx.guild.me)
            if not permissions.connect or not permissions.speak:
                await ctx.send("❌ No tengo permisos para unirme/hablar en tu canal de voz.")
                return
            await player.connect(channel)

        # Mostrar mensaje de "buscando..."
        searching_msg = await ctx.send(f"🔍 Buscando: **{query}**...")

        # Añadir a cola
        track = await player.add_to_queue(query, ctx.author.display_name)
        if not track:
            await searching_msg.edit(content="❌ No se encontró ninguna canción. Intenta con otra búsqueda.")
            return

        # Responder según si empezó a sonar o se añadió a cola
        if player.is_playing and player.queue.current != track:
            # Se añadió a cola
            position = len(player.queue)
            await searching_msg.edit(
                content=f"✅ Añadido a la cola (#{position}): **{track.title}**\n"
                        f"👤 Pedido por: {track.requester}"
            )
        else:
            # Empezó a sonar
            await searching_msg.edit(
                content=f"🎵 **Reproduciendo ahora:** [{track.title}]({track.webpage_url})\n"
                        f"⏱️ Duración: {track.duration // 60}:{track.duration % 60:02d} | "
                        f"👤 Pedido por: {track.requester}"
            )

    @commands.command(name="pause", aliases=["pausar", "parar"])
    async def pause(self, ctx: commands.Context) -> None:
        """Pausa la reproducción actual."""
        self._require_voice(ctx)
        self._require_playing(ctx)

        player = self._get_player(ctx.guild.id)
        if player.pause():
            await ctx.send("⏸️ Reproducción pausada. Usa `!resume` para continuar.")
        else:
            await ctx.send("❌ No se pudo pausar (¿ya está pausado?).")

    @commands.command(name="resume", aliases=["reanudar", "continuar", "r"])
    async def resume(self, ctx: commands.Context) -> None:
        """Reanuda la reproducción pausada."""
        self._require_voice(ctx)

        player = self._get_player(ctx.guild.id)
        if player.resume():
            await ctx.send("▶️ Reproducción reanudada.")
        else:
            await ctx.send("❌ No hay nada pausado para reanudar.")

    @commands.command(name="skip", aliases=["s", "saltar", "next", "siguiente"])
    async def skip(self, ctx: commands.Context) -> None:
        """Salta la canción actual."""
        self._require_voice(ctx)
        self._require_playing(ctx)

        player = self._get_player(ctx.guild.id)
        current_title = player.current_track.title if player.current_track else "Desconocido"

        if player.skip():
            await ctx.send(f"⏭️ Saltado: **{current_title}**")
        else:
            await ctx.send("❌ No se pudo saltar.")

    @commands.command(name="stop", aliases=["detener", "parartodo"])
    async def stop(self, ctx: commands.Context) -> None:
        """Detiene la reproducción y limpia la cola."""
        self._require_voice(ctx)

        player = self._get_player(ctx.guild.id)
        player.stop()
        await ctx.send("⏹️ Reproducción detenida y cola limpiada.")

    @commands.command(name="queue", aliases=["q", "cola", "playlist"])
    async def queue(self, ctx: commands.Context, page: int = 1) -> None:
        """Muestra la cola de reproducción."""
        self._require_voice(ctx)

        player = self._get_player(ctx.guild.id)
        queue_list = player.queue.get_queue_list()

        if not queue_list and not player.current_track:
            await ctx.send("📭 La cola está vacía.")
            return

        # Paginación
        items_per_page = 10
        total_pages = max(1, (len(queue_list) + items_per_page - 1) // items_per_page)
        page = max(1, min(page, total_pages))

        start = (page - 1) * items_per_page
        end = start + items_per_page
        page_items = queue_list[start:end]

        # Construir embed
        embed = discord.Embed(
            title="🎵 Cola de Reproducción",
            color=discord.Color.blue()
        )

        # Canción actual
        if player.current_track:
            track = player.current_track
            embed.add_field(
                name="▶️ Reproduciendo ahora",
                value=f"**[{track.title}]({track.webpage_url})**\n"
                      f"⏱️ {track.duration // 60}:{track.duration % 60:02d} | 👤 {track.requester}",
                inline=False
            )

        # Cola
        if page_items:
            queue_text = ""
            for i, track in enumerate(page_items, start=start + 1):
                queue_text += f"`#{i}` **{track.title}** ({track.duration // 60}:{track.duration % 60:02d}) - 👤 {track.requester}\n"

            embed.add_field(
                name=f"📋 Próximas ({len(queue_list)} en cola)",
                value=queue_text,
                inline=False
            )
        else:
            embed.add_field(
                name="📋 Próximas",
                value="*(cola vacía)*",
                inline=False
            )

        embed.set_footer(text=f"Página {page}/{total_pages} | Usa !queue <página> para navegar")
        await ctx.send(embed=embed)

    @commands.command(name="nowplaying", aliases=["np", "actual", "sonando"])
    async def nowplaying(self, ctx: commands.Context) -> None:
        """Muestra la canción que se está reproduciendo actualmente."""
        self._require_voice(ctx)

        player = self._get_player(ctx.guild.id)
        track = player.current_track

        if not track:
            await ctx.send("❌ No hay nada reproduciéndose.")
            return

        embed = discord.Embed(
            title="🎵 Reproduciendo Ahora",
            color=discord.Color.green()
        )

        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)

        embed.add_field(
            name=track.title,
            value=f"[{track.webpage_url}]({track.webpage_url})",
            inline=False
        )
        embed.add_field(name="⏱️ Duración", value=f"{track.duration // 60}:{track.duration % 60:02d}", inline=True)
        embed.add_field(name="👤 Pedido por", value=track.requester, inline=True)
        embed.add_field(name="🔊 Volumen", value=f"{int(player.volume * 100)}%", inline=True)

        await ctx.send(embed=embed)

    @commands.command(name="volume", aliases=["vol", "volumen", "v"])
    async def volume(self, ctx: commands.Context, level: int = None) -> None:
        """Cambia o muestra el volumen (0-100)."""
        self._require_voice(ctx)

        player = self._get_player(ctx.guild.id)

        if level is None:
            await ctx.send(f"🔊 Volumen actual: **{int(player.volume * 100)}%**")
            return

        if not 0 <= level <= 100:
            await ctx.send("❌ El volumen debe estar entre 0 y 100.")
            return

        player.set_volume(level / 100)
        await ctx.send(f"🔊 Volumen cambiado a **{level}%**")

    @commands.command(name="remove", aliases=["rm", "eliminar", "borrar"])
    async def remove(self, ctx: commands.Context, index: int) -> None:
        """Elimina una canción de la cola por su número (usa !queue para ver números)."""
        self._require_voice(ctx)

        player = self._get_player(ctx.guild.id)
        queue_list = player.queue.get_queue_list()

        if not queue_list:
            await ctx.send("❌ La cola está vacía.")
            return

        # Ajustar índice (1-based para el usuario)
        idx = index - 1
        if idx < 0 or idx >= len(queue_list):
            await ctx.send(f"❌ Índice inválido. La cola tiene {len(queue_list)} canciones.")
            return

        removed = player.queue.remove(idx)
        if removed:
            await ctx.send(f"🗑️ Eliminado de la cola: **{removed.title}**")
        else:
            await ctx.send("❌ No se pudo eliminar.")

    @commands.command(name="clear", aliases=["cl", "limpiar", "vaciar"])
    async def clear(self, ctx: commands.Context) -> None:
        """Limpia toda la cola de reproducción."""
        self._require_voice(ctx)

        player = self._get_player(ctx.guild.id)
        count = player.queue.clear()

        if count > 0:
            await ctx.send(f"🗑️ Cola limpiada: {count} canción(es) eliminada(s).")
        else:
            await ctx.send("📭 La cola ya estaba vacía.")

    @commands.command(name="shuffle", aliases=["sh", "mezclar", "aleatorio"])
    async def shuffle(self, ctx: commands.Context) -> None:
        """Mezcla la cola de reproducción aleatoriamente."""
        self._require_voice(ctx)

        player = self._get_player(ctx.guild.id)
        queue_list = player.queue.get_queue_list()

        if len(queue_list) < 2:
            await ctx.send("❌ Necesitas al menos 2 canciones en la cola para mezclar.")
            return

        player.queue.shuffle()
        await ctx.send("🔀 Cola mezclada aleatoriamente.")

    # Error handlers específicos para este cog
    @play.error
    @pause.error
    @resume.error
    @skip.error
    @stop.error
    @queue.error
    @nowplaying.error
    @volume.error
    @remove.error
    @clear.error
    @shuffle.error
    async def music_error(self, ctx: commands.Context, error: Exception) -> None:
        """Manejo de errores para comandos de música."""
        if isinstance(error, commands.CommandError):
            await ctx.send(f"❌ {error}")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Falta argumento: `{error.param.name}`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Argumento inválido: {error}")
        else:
            logger.error(f"Error en comando de música: {error}", exc_info=True)
            await ctx.send("❌ Ocurrió un error inesperado.")


async def setup(bot: commands.Bot) -> None:
    """Registra el cog en el bot."""
    await bot.add_cog(MusicCommands(bot))