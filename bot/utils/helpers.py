"""
Funciones auxiliares y utilidades varias.
"""
import discord
from discord.ext import commands


def format_duration(seconds: int) -> str:
    """Formatea segundos a MM:SS o HH:MM:SS."""
    if seconds < 0:
        return "??:??"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def create_embed(title: str, description: str = None, color: discord.Color = None, **kwargs) -> discord.Embed:
    """Crea un embed estandarizado."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color or discord.Color.blue(),
    )
    for key, value in kwargs.items():
        if key == "fields":
            for field in value:
                embed.add_field(**field)
        elif key == "footer":
            embed.set_footer(text=value)
        elif key == "thumbnail":
            embed.set_thumbnail(url=value)
        elif key == "image":
            embed.set_image(url=value)
    return embed


async def send_error(ctx: commands.Context, message: str) -> None:
    """Envía un mensaje de error estandarizado."""
    embed = create_embed("❌ Error", message, discord.Color.red())
    await ctx.send(embed=embed)


async def send_success(ctx: commands.Context, message: str) -> None:
    """Envía un mensaje de éxito estandarizado."""
    embed = create_embed("✅ Éxito", message, discord.Color.green())
    await ctx.send(embed=embed)


async def send_info(ctx: commands.Context, message: str) -> None:
    """Envía un mensaje informativo estandarizado."""
    embed = create_embed("ℹ️ Info", message, discord.Color.blue())
    await ctx.send(embed=embed)