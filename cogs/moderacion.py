"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR GUARD // DISCIPLINARY DIVISION (NEW GEN v6.0)
  Capacidades: Triple Jerarquía, Sentencias Asistidas por IA, Escalada de Warns,
               Softban Táctico y Notificaciones Forenses al Infractor
═══════════════════════════════════════════════════════════════════════════════
"""

import discord
from discord.ext import commands
from discord import app_commands
import datetime
import inspect
import asyncio
import logging
from utils.helpers import crear_case, agregar_warn, obtener_warns
from utils.ui import formato_editorial, embed_sancion, LiveActionController
from utils.ia import preguntar_ia

logger = logging.getLogger("ElixyrMod")

async def _ejecutar_helper(func, *args, **kwargs):
    """Garantiza compatibilidad absoluta si helpers.py es síncrono o asíncrono."""
    res = func(*args, **kwargs)
    if inspect.isawaitable(res):
        return await res
    return res

class Moderacion(commands.Cog):
    """Módulo de ejecución disciplinaria táctica y neutralización de objetivos."""
    def __init__(self, bot):
        self.bot = bot

    async def _redactar_dictamen_ia(self, accion: str, motivo: str, usuario: str) -> str:
        prompt = (
            f"Actúa como el tribunal de disciplina y seguridad informática de un servidor.\n"
            f"Acción a ejecutar: '{accion.upper()}' sobre el usuario '{usuario}'.\n"
            f"Causa informada: '{motivo}'.\n"
            f"Redacta un dictamen judicial formal de 1 sola línea, frío, severo y sin emojis."
        )
        res = await preguntar_ia(prompt, max_tokens=70)
        if res.startswith("❌") or res.startswith("⚠️"):
            return motivo
        return res.replace('"', '').strip()

    def _verificar_jerarquias(self, ctx, target: discord.Member) -> str | None:
        if target.id == ctx.guild.owner_id:
            return "Imposible sancionar al Propietario de la infraestructura."
        if target.id == self.bot.user.id:
            return "No puedo aplicar medidas disciplinarias contra mi propio núcleo."
        if target.top_role >= ctx.guild.me.top_role:
            return "Jerarquía insuficiente: El rol del objetivo es superior o igual a mi credencial más alta."
        if target.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return "Jerarquía insuficiente: El rol del objetivo es igual o superior a tu credencial."
        return None

    # ═════════════════════════════════════════════════════════════
    #  1. BANEO DEFINITIVO (BAN)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="ban", description="Banea permanentemente a un miembro con dictamen judicial IA")
    @app_commands.describe(
        usuario="Miembro a neutralizar",
        dias_borrado="Días de historial a purgar (0 a 7)",
        razon="Justificación de la exclusión"
    )
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, usuario: discord.Member, dias_borrado: int = 1, *, razon: str = "Amenaza al servidor"):
        await ctx.defer()
        
        error_jerarquia = self._verificar_jerarquias(ctx, usuario)
        if error_jerarquia:
            return await ctx.send(f"⛔ **Acceso Denegado:** {error_jerarquia}", ephemeral=True)

        dias = max(0, min(dias_borrado, 7))
        dictamen = await self._redactar_dictamen_ia("Baneo Permanente", razon, usuario.name)
        
        case_id = await _ejecutar_helper(crear_case, "ban", usuario.id, ctx.author.id, dictamen, {"purgado": f"{dias}d"})

        # Notificación por DM previa al baneo
        try:
            aviso_dm = (
                f"# ⛔ EXCLUSIÓN PERMANENTE // {ctx.guild.name.upper()}\n"
                f"> **Expediente:** `#{case_id}`\n"
                f"> **Fundamento Legal:** {dictamen}\n\n"
                f"-# Esta decisión es definitiva e irrevocable por los canales estándar."
            )
            await usuario.send(aviso_dm)
        except Exception:
            pass

        # Ejecución del Baneo en Discord
        await usuario.ban(reason=f"[Caso #{case_id}] {dictamen}", delete_message_seconds=dias * 86400)
        
        embed = embed_sancion("ban", usuario, ctx.author, dictamen, case_id, {"Historial purgado": f"{dias} días"})
        await ctx.send(embed=embed)

    # ═════════════════════════════════════════════════════════════
    #  2. REVOCAR BANEO (UNBAN)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="unban", description="Revoca la exclusión de un usuario mediante su ID")
    @app_commands.describe(usuario_id="ID numérico del usuario a perdonar", razon="Motivo del indulto")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx, usuario_id: str, *, razon: str = "Indulto concedido por la administración"):
        await ctx.defer()
        if not usuario_id.isdigit():
            return await ctx.send("⚠️ El parámetro debe ser un ID numérico válido.", ephemeral=True)

        user_obj = discord.Object(id=int(usuario_id))
        try:
            await ctx.guild.unban(user_obj, reason=f"Revocado por {ctx.author}: {razon}")
            case_id = await _ejecutar_helper(crear_case, "unban", usuario_id, ctx.author.id, razon)
            
            panel = (
                f"> **Sujeto Indultado:** <@{usuario_id}> (`{usuario_id}`)\n"
                f"> **Oficial:** {ctx.author.mention}\n"
                f"> **Expediente:** `#{case_id}`\n"
                f"> **Motivo:** *{razon}*"
            )
            await ctx.send(formato_editorial("EXCLUSIÓN REVOCADA (UNBAN)", panel, badge="JUSTICE"))
        except discord.NotFound:
            await ctx.send("⚠️ El usuario no figura en la lista de baneos de este servidor.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❌ Error al revocar sanción: `{e}`", ephemeral=True)

    # ═════════════════════════════════════════════════════════════
    #  3. EXPULSIÓN TÁCTICA (KICK)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="kick", description="Expulsa a un miembro de la red con notificación IA")
    @app_commands.describe(usuario="Miembro a expulsar", razon="Motivo de la expulsión")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, usuario: discord.Member, *, razon: str = "Infracción de directivas perimetrales"):
        await ctx.defer()
        
        error_jerarquia = self._verificar_jerarquias(ctx, usuario)
        if error_jerarquia:
            return await ctx.send(f"⛔ **Acceso Denegado:** {error_jerarquia}", ephemeral=True)

        dictamen = await self._redactar_dictamen_ia("Expulsión", razon, usuario.name)
        case_id = await _ejecutar_helper(crear_case, "kick", usuario.id, ctx.author.id, dictamen)

        try:
            await usuario.send(f"### 🛑 EXPULSIÓN DE LA RED ▸ {ctx.guild.name}\n> **Expediente:** `#{case_id}`\n> **Dictamen:** {dictamen}")
        except Exception:
            pass

        await usuario.kick(reason=f"[Caso #{case_id}] {dictamen}")
        embed = embed_sancion("kick", usuario, ctx.author, dictamen, case_id)
        await ctx.send(embed=embed)

    # ═════════════════════════════════════════════════════════════
    #  4. SOFTBAN (EXPULSIÓN CON PURGA DE CHAT)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="softban", description="Expulsa y purga los mensajes recientes de un usuario tóxico")
    @app_commands.describe(usuario="Miembro objetivo", dias="Días de mensajes a borrar (1 a 7)", razon="Motivo del softban")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def softban(self, ctx, usuario: discord.Member, dias: int = 2, *, razon: str = "Purga de conducta"):
        await ctx.defer()
        error_jerarquia = self._verificar_jerarquias(ctx, usuario)
        if error_jerarquia:
            return await ctx.send(f"⛔ {error_jerarquia}", ephemeral=True)

        dias_s = max(1, min(dias, 7))
        case_id = await _ejecutar_helper(crear_case, "softban", usuario.id, ctx.author.id, razon, {"purgado": f"{dias_s}d"})

        await usuario.ban(reason=f"Softban [Caso #{case_id}]: {razon}", delete_message_seconds=dias_s * 86400)
        await ctx.guild.unban(usuario, reason="Softban: Re-ingreso autorizado tras purga")

        embed = embed_sancion("softban", usuario, ctx.author, razon, case_id, {"Mensajes erradicados": f"{dias_s} días"})
        await ctx.send(embed=embed)

    # ═════════════════════════════════════════════════════════════
    #  5. AISLAMIENTO TEMPORAL (MUTE / TIMEOUT)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="mute", description="Aísla temporalmente a un miembro en el servidor")
    @app_commands.describe(usuario="Miembro a silenciar", minutos="Minutos de aislamiento (máx 40320 = 28 días)", razon="Motivo")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def mute(self, ctx, usuario: discord.Member, minutos: int = 15, *, razon: str = "Disrupción de la frecuencia"):
        await ctx.defer()
        error_jerarquia = self._verificar_jerarquias(ctx, usuario)
        if error_jerarquia:
            return await ctx.send(f"⛔ {error_jerarquia}", ephemeral=True)

        minutos_validos = max(1, min(minutos, 40320))
        dictamen = await self._redactar_dictamen_ia(f"Aislamiento de {minutos_validos}m", razon, usuario.name)
        case_id = await _ejecutar_helper(crear_case, "mute", usuario.id, ctx.author.id, dictamen, {"duracion": f"{minutos_validos}m"})

        expiracion = discord.utils.utcnow() + datetime.timedelta(minutes=minutos_validos)
        await usuario.timeout(expiracion, reason=f"[Caso #{case_id}] {dictamen}")

        embed = embed_sancion("mute", usuario, ctx.author, dictamen, case_id, {"Duración de Aislamiento": f"{minutos_validos} minutos"})
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="unmute", description="Restaura la voz y comunicación de un usuario silenciado")
    @app_commands.describe(usuario="Miembro a liberar", razon="Causa de la restitución")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def unmute(self, ctx, usuario: discord.Member, *, razon: str = "Aislamiento revocado"):
        await ctx.defer()
        error_jerarquia = self._verificar_jerarquias(ctx, usuario)
        if error_jerarquia:
            return await ctx.send(f"⛔ {error_jerarquia}", ephemeral=True)

        await usuario.timeout(None, reason=f"Unmute por {ctx.author}: {razon}")
        case_id = await _ejecutar_helper(crear_case, "unmute", usuario.id, ctx.author.id, razon)

        await ctx.send(embed=embed_sancion("unmute", usuario, ctx.author, razon, case_id))

    # ═════════════════════════════════════════════════════════════
    #  6. ADVERTENCIAS FORMALES (WARN CON ESCALADA AUTOMÁTICA)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="warn", description="Asigna una advertencia formal con escalada disciplinaria automática")
    @app_commands.describe(usuario="Miembro a advertir", razon="Infracción cometida")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx, usuario: discord.Member, *, razon: str = "Infracción a las directivas"):
        await ctx.defer()
        error_jerarquia = self._verificar_jerarquias(ctx, usuario)
        if error_jerarquia:
            return await ctx.send(f"⛔ {error_jerarquia}", ephemeral=True)

        total_warns = await _ejecutar_helper(agregar_warn, ctx.guild.id, usuario.id, ctx.author.id, razon)
        case_id = await _ejecutar_helper(crear_case, "warn", usuario.id, ctx.author.id, razon, {"acumuladas": total_warns})

        escalada_info = "Ninguna acción automática requerida."
        
        # Protocolo de Escalada Automática (Escudo Activo)
        if total_warns == 3:
            try:
                await usuario.timeout(discord.utils.utcnow() + datetime.timedelta(hours=1), reason="Escalada: 3 advertencias acumuladas")
                escalada_info = "⚡ **Escalada Activada:** Aislamiento temporal de `1 hora` aplicado automáticamente."
            except Exception:
                escalada_info = "⚠️ Intento de aislamiento fallido por jerarquía."
        elif total_warns >= 5:
            try:
                await usuario.kick(reason=f"Escalada Automática: {total_warns} advertencias acumuladas")
                escalada_info = "🚨 **Escalada Crítica:** Expulsión del servidor ejecutada automáticamente."
            except Exception:
                escalada_info = "⚠️ Intento de expulsión fallido por jerarquía."

        extra_data = {"Advertencias Acumuladas": f"{total_warns} warns", "Respuesta Automática": escalada_info}
        embed = embed_sancion("warn", usuario, ctx.author, razon, case_id, extra_data)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Moderacion(bot))