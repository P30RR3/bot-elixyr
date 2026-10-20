import discord
from discord.ext import commands
from utils.helpers import obtener_guild_config, actualizar_guild_config
from utils.ui import formato_editorial

class DefconView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    async def _actualizar_panel(self, interaction: discord.Interaction, modo: str, color: str):
        actualizar_guild_config(self.guild_id, "antiraid_mode", modo)
        actualizar_guild_config(self.guild_id, "automod_mode", modo)
        
        estado = f"### 🛡️ POSTURA TÁCTICA ACTUALIZADA\n> El servidor ha entrado en **DEFCON {modo.upper()}** ({color}).\n> *Filtros IA y Anti-Raid sincronizados.*"
        await interaction.response.send_message(estado, ephemeral=True)

    @discord.ui.button(label="DEFCON 5 (Pacífico)", style=discord.ButtonStyle.success, emoji="🟢", custom_id="defcon_5")
    async def btn_pacifico(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("⛔ Acceso denegado.", ephemeral=True)
        await self._actualizar_panel(interaction, "pacifico", "Verde")

    @discord.ui.button(label="DEFCON 3 (Intermedio)", style=discord.ButtonStyle.primary, emoji="🟡", custom_id="defcon_3")
    async def btn_intermedio(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("⛔ Acceso denegado.", ephemeral=True)
        await self._actualizar_panel(interaction, "intermedio", "Amarillo")

    @discord.ui.button(label="DEFCON 1 (Hardcore)", style=discord.ButtonStyle.danger, emoji="🔴", custom_id="defcon_1")
    async def btn_hardcore(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("⛔ Acceso denegado.", ephemeral=True)
        await self._actualizar_panel(interaction, "hard", "Rojo")

class SOCPanel(commands.Cog):
    """Dashboard interactivo para control de seguridad en tiempo real."""
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="terminal", description="Despliega el panel de control interactivo del SOC")
    @commands.has_permissions(administrator=True)
    async def terminal(self, ctx):
        await ctx.defer()
        
        cfg = obtener_guild_config(ctx.guild.id)
        modo_actual = cfg.get("antiraid_mode", "intermedio").upper()
        
        contenido = (
            f"> **Red Protegida:** `{ctx.guild.name}`\n"
            f"> **Postura Actual:** `DEFCON {modo_actual}`\n"
            f"> **Motor IA:** `En línea (Cerebras)`\n\n"
            f"**Instrucciones de Operación:**\n"
            f"Utiliza los controles inferiores para alterar la agresividad del cortafuegos y el sistema Anti-Raid en tiempo real. "
            f"El modo Hardcore baneará amenazas instantáneamente."
        )
        
        mensaje_formateado = formato_editorial("TERMINAL DE CONTROL SOC", contenido, badge="DEFCON")
        
        view = DefconView(ctx.guild.id)
        await ctx.send(mensaje_formateado, view=view)

async def setup(bot):
    await bot.add_cog(SOCPanel(bot))