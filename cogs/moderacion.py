import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import datetime
from utils.helpers import crear_case, agregar_warn, obtener_warns, limpiar_warns
from utils.ui import embed_sancion
from utils.ia import preguntar_ia

class Moderacion(commands.Cog):
    """División disciplinaria: neutralización individual y asistida por IA."""
    def __init__(self, bot):
        self.bot = bot

    async def _redactar_sancion_ia(self, accion: str, motivo: str, usuario_nombre: str):
        prompt = (
            f"Actúa como el departamento disciplinario de ciberseguridad. "
            f"Se aplicará '{accion.upper()}' al usuario '{usuario_nombre}' por: '{motivo}'. "
            f"Redacta un veredicto de 1 línea, sin emojis infantiles, formal, frío y contundente."
        )
        res = await preguntar_ia(prompt)
        return res.replace('"', '').strip() if not res.startswith("❌") else motivo

    @commands.hybrid_command(name="ban", description="Banea permanentemente con fundamento de seguridad IA")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, usuario: discord.Member, dias_mensajes: int = 0, *, razon: str = "Amenaza al servidor"):
        await ctx.defer()
        if usuario.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("⛔ Jerarquía inválida sobre el objetivo.")

        dictamen_ia = await self._redactar_sancion_ia("Baneo Permanente", razon, usuario.name)
        case_id = crear_case("ban", usuario.id, ctx.author.id, dictamen_ia)

        try: await usuario.send(f"### ⛔ BANEO DEFINITIVO ▸ {ctx.guild.name}\n> **Expediente:** `#{case_id}`\n> **Fundamento:** {dictamen_ia}")
        except Exception: pass

        await usuario.ban(reason=f"[Caso #{case_id}] {dictamen_ia}", delete_message_days=min(dias_mensajes, 7))
        
        embed = embed_sancion("ban", usuario, ctx.author, dictamen_ia, case_id)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="kick", description="Expulsa a un miembro con notificación disciplinaria IA")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, usuario: discord.Member, *, razon: str = "Infracción de directivas"):
        await ctx.defer()
        if usuario.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("⛔ Jerarquía inválida sobre el objetivo.")

        dictamen_ia = await self._redactar_sancion_ia("Expulsión", razon, usuario.name)
        case_id = crear_case("kick", usuario.id, ctx.author.id, dictamen_ia)

        try: await usuario.send(f"### 🛑 EXPULSIÓN ▸ {ctx.guild.name}\n> **Expediente:** `#{case_id}`\n> **Dictamen:** {dictamen_ia}")
        except Exception: pass

        await usuario.kick(reason=f"[Caso #{case_id}] {dictamen_ia}")
        embed = embed_sancion("kick", usuario, ctx.author, dictamen_ia, case_id)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="mute", description="Aísla temporalmente a un miembro")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, usuario: discord.Member, minutos: int = 15, *, razon: str = "Disrupción"):
        await ctx.defer()
        dictamen_ia = await self._redactar_sancion_ia(f"Aislamiento de {minutos}m", razon, usuario.name)
        case_id = crear_case("mute", usuario.id, ctx.author.id, dictamen_ia, {"duracion": f"{minutos}m"})
        
        await usuario.timeout(discord.utils.utcnow() + datetime.timedelta(minutes=minutos), reason=dictamen_ia)
        embed = embed_sancion("mute", usuario, ctx.author, dictamen_ia, case_id, {"Duración": f"{minutos} minutos"})
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="warn", description="Asigna una advertencia disciplinaria formal")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx, usuario: discord.Member, *, razon: str = "Infracción"):
        await ctx.defer()
        total = agregar_warn(usuario.id, ctx.author.id, razon)
        case_id = crear_case("warn", usuario.id, ctx.author.id, razon, {"acumuladas": total})
        
        embed = embed_sancion("warn", usuario, ctx.author, razon, case_id, {"Advertencias Acumuladas": total})
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Moderacion(bot))