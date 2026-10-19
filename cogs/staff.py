import discord
from discord.ext import commands
from discord import app_commands
from utils.helpers import agregar_nota, obtener_notas, historial_usuario, obtener_warns
from utils.ia import preguntar_ia
from datetime import datetime, timezone

class Staff(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="userinfo", description="Genera el expediente completo y perfil conductual de un usuario con IA")
    async def userinfo(self, ctx, usuario: discord.Member = None):
        await ctx.defer()
        user = usuario or ctx.author
        warns = obtener_warns(user.id)
        casos = historial_usuario(user.id)
        notas = obtener_notas(user.id)
        dias_cuenta = (datetime.now(timezone.utc) - user.created_at).days

        prompt = (
            f"Actúa como un perfilador de ciberseguridad. Evalúa a este miembro: "
            f"{dias_cuenta} días de antigüedad, {len(warns)} advertencias, {len(casos)} sanciones y {len(notas)} notas del staff. "
            f"Emite: 1) Nivel de Riesgo (Bajo, Moderado, Crítico), 2) Perfil de Confiabilidad en 2 líneas concisas."
        )
        perfil_ia = await preguntar_ia(prompt)

        dossier = (
            f"# 👤 EXPEDIENTE DE IDENTIDAD ▸ {user.display_name.upper()}\n"
            f"✦ ────────────────────────────────────────── ✦\n"
            f"> • **Mención / ID:** {user.mention} (`{user.id}`)\n"
            f"> • **Creación de Identidad:** <t:{int(user.created_at.timestamp())}:R>\n"
            f"> • **Ingreso a la Red:** <t:{int(user.joined_at.timestamp())}:R>\n"
            f"> • **Historial Táctico:** `{len(warns)}` Warns | `{len(casos)}` Sanciones | `{len(notas)}` Notas\n\n"
            f"**🧠 Evaluación de Inteligencia (IA):**\n"
            f"{perfil_ia}\n"
            f"✦ ────────────────────────────────────────── ✦"
        )
        await ctx.send(dossier)

    @commands.hybrid_command(name="note", description="Registra una nota confidencial en el expediente de un miembro")
    @commands.has_permissions(manage_messages=True)
    async def note(self, ctx, usuario: discord.Member, *, nota: str):
        await ctx.defer()
        agregar_nota(usuario.id, ctx.author.id, nota)
        await ctx.send(f"### 📝 NOTA CONFIDENCIAL AÑADIDA\n> **Sujeto:** {usuario.mention}\n> **Oficial:** {ctx.author.mention}\n> **Registro:** *{nota}*")

async def setup(bot):
    await bot.add_cog(Staff(bot))