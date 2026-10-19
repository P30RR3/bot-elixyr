import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
from utils.helpers import obtener_guild_config, actualizar_guild_config
from utils.ia import preguntar_ia

class IALogView(discord.ui.View):
    def __init__(self, contenido: str):
        super().__init__(timeout=None)
        self.contenido = contenido

    @discord.ui.button(label="Peritaje Forense IA", style=discord.ButtonStyle.secondary, emoji="🧠", custom_id="ia_audit_btn")
    async def auditar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        prompt = (
            f"Actúa como analista de un SOC de Discord. Analiza este mensaje borrado/editado: \"{self.contenido}\".\n"
            f"Determina: 1. Nivel de Amenaza, 2. Intención oculta, 3. Contramedida recomendada. Sé frío y directo. Máximo 3 líneas."
        )
        analisis = await preguntar_ia(prompt)
        salida = (
            f"### 🧠 DICTAMEN FORENSE // CEREBRAS AI\n"
            f"> **Muestra:** *\"{self.contenido[:180]}\"*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{analisis}\n\n"
            f"-# Telemetría de seguridad procesada para el Staff."
        )
        await interaction.followup.send(salida, ephemeral=True)

class Logs(commands.Cog):
    """Centro de Operaciones de Seguridad (SOC): Auditoría continua en tiempo real."""
    def __init__(self, bot):
        self.bot = bot

    def _canal_seguridad(self, guild: discord.Guild):
        cfg = obtener_guild_config(guild.id)
        ch_id = cfg.get("audit_channel") or cfg.get("log_channel")
        return guild.get_channel(int(ch_id)) if ch_id else None

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot: return
        ch = self._canal_seguridad(message.guild)
        if not ch: return

        txt = message.content[:1000] if message.content else "*[Sin texto / Archivo]*"
        reporte = (
            f"### 🗑️ REGISTRO // MENSAJE DESTRUIDO\n"
            f"> **Autor:** {message.author.mention} `[{message.author.id}]`\n"
            f"> **Canal:** {message.channel.mention} • <t:{int(datetime.now(timezone.utc).timestamp())}:T>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{txt}"
        )
        await ch.send(reporte, view=IALogView(message.content) if message.content else None)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        ch = self._canal_seguridad(before.guild)
        if not ch: return

        if not before.permissions.administrator and after.permissions.administrator:
            alerta = (
                f"# 🚨 ALERTA SOC // ESCALADA DE PRIVILEGIOS CRÍTICA\n"
                f"✦ ────────────────────────────────────────── ✦\n"
                f"> **Rol Modificado:** {after.mention} (`{after.name}`)\n"
                f"> **Amenaza:** Se le otorgó el permiso de **ADMINISTRADOR TOTAL**.\n"
                f"> *Revisar el registro de auditoría de inmediato.*\n"
                f"✦ ────────────────────────────────────────── ✦"
            )
            await ch.send(alerta)

    @commands.hybrid_command(name="setup-logs", description="Designa el canal SOC receptor de telemetría")
    @commands.has_permissions(administrator=True)
    async def setup_logs(self, ctx, canal: discord.TextChannel):
        await ctx.defer()
        actualizar_guild_config(ctx.guild.id, "audit_channel", canal.id)
        actualizar_guild_config(ctx.guild.id, "log_channel", canal.id)
        await ctx.send(f"🛡️ **Centro SOC activado:** Telemetría de seguridad enrutada a {canal.mention}.")

async def setup(bot):
    await bot.add_cog(Logs(bot))