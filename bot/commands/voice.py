"""
Comandos de voz: join, leave.
"""
import logging

import discord
from discord.ext import commands

from bot.config import config

logger = logging.getLogger(__name__)


class VoiceCommands(commands.Cog, name="Voz"):
    """Comandos para gestión de conexión de voz."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_player(self, guild_id: int):
        """Obtiene el reproductor del guild."""
        return self.bot.get_player(guild_id)

    @commands.command(name="join", aliases=["j", "conectar", "entrar"])
    async def join(self, ctx: commands.Context) -> None:
        """Une el bot al canal de voz del usuario."""
        # Verificar que el usuario esté en un canal de voz
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ Debes estar en un canal de voz para usar este comando.")
            return

        channel = ctx.author.voice.channel

        # Verificar permisos
        permissions = channel.permissions_for(ctx.guild.me)
        if not permissions.connect:
            await ctx.send("❌ No tengo permisos para unirme a ese canal de voz.")
            return
        if not permissions.speak:
            await ctx.send("❌ No tengo permisos para hablar en ese canal de voz.")
            return

        player = self._get_player(ctx.guild.id)

        # Conectar
        success = await player.connect(channel)
        if success:
            await ctx.send(f"🎵 Conectado a **{channel.name}**")
            logger.info(f"Bot unido a {channel.name} en {ctx.guild.name}")
        else:
            await ctx.send("❌ No se pudo conectar al canal de voz.")

    @commands.command(name="leave", aliases=["l", "salir", "desconectar", "dc"])
    async def leave(self, ctx: commands.Context) -> None:
        """Desconecta el bot del canal de voz."""
        player = self._get_player(ctx.guild.id)

        if not player.voice_client or not player.voice_client.is_connected():
            await ctx.send("❌ No estoy conectado a ningún canal de voz.")
            return

        await player.disconnect()
        self.bot.remove_player(ctx.guild.id)
        await ctx.send("👋 Desconectado del canal de voz.")
        logger.info(f"Bot desconectado de {ctx.guild.name}")

    @commands.command(name="move", aliases=["mover"])
    async def move(self, ctx: commands.Context, *, channel_name: str = None) -> None:
        """Mueve el bot a otro canal de voz (por nombre)."""
        if not channel_name:
            await ctx.send("❌ Especifica el nombre del canal: `!move <nombre_canal>`")
            return

        player = self._get_player(ctx.guild.id)

        if not player.voice_client or not player.voice_client.is_connected():
            await ctx.send("❌ No estoy conectado a ningún canal de voz.")
            return

        # Buscar canal por nombre
        target_channel = discord.utils.get(ctx.guild.voice_channels, name=channel_name)
        if not target_channel:
            await ctx.send(f"❌ No se encontró el canal de voz: **{channel_name}**")
            return

        # Verificar permisos
        permissions = target_channel.permissions_for(ctx.guild.me)
        if not permissions.connect or not permissions.speak:
            await ctx.send("❌ No tengo permisos en ese canal.")
            return

        await player.voice_client.move_to(target_channel)
        await ctx.send(f"🔀 Movido a **{target_channel.name}**")


async def setup(bot: commands.Bot) -> None:
    """Registra el cog en el bot."""
    await bot.add_cog(VoiceCommands(bot))