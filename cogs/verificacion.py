import discord
from discord.ext import commands
from discord import app_commands
from utils.helpers import obtener_guild_config
from utils.ia import preguntar_ia
from utils.ui import embed_exito, embed_error, formato_editorial
import logging

logger = logging.getLogger("ElixyrCaptcha")

class CaptchaModal(discord.ui.Modal, title="Verificación Cognitiva"):
    respuesta = discord.ui.TextInput(
        label="Tu respuesta:",
        style=discord.TextStyle.short,
        placeholder="Escribe la respuesta al acertijo aquí...",
        required=True,
        max_length=50
    )

    def __init__(self, acertijo: str, rol_verificado_id: int):
        super().__init__()
        self.acertijo = acertijo
        self.rol_verificado_id = rol_verificado_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Validamos la respuesta con la IA
        prompt_validacion = (
            f"El acertijo era: '{self.acertijo}'.\n"
            f"El usuario respondió: '{self.respuesta.value}'.\n"
            f"¿Es una respuesta lógicamente correcta o aceptable? Responde ÚNICAMENTE con la palabra TRUE o FALSE."
        )
        
        veredicto = await preguntar_ia(prompt_validacion, max_tokens=10)
        
        if "TRUE" in veredicto.upper():
            rol = interaction.guild.get_role(int(self.rol_verificado_id))
            if rol:
                try:
                    await interaction.user.add_roles(rol, reason="AI-Captcha superado")
                    await interaction.followup.send(embed=embed_exito("ACCESO CONCEDIDO", "Tu firma cognitiva ha sido validada. Bienvenido a la red."))
                except discord.Forbidden:
                    await interaction.followup.send(embed=embed_error("Error Interno", "No tengo jerarquía para asignarte el rol."))
            else:
                await interaction.followup.send(embed=embed_error("Error de Configuración", "El rol de verificado no existe."))
        else:
            await interaction.followup.send(embed=embed_error("ACCESO DENEGADO", "Respuesta incorrecta. Eres sospechoso de ser una entidad automatizada. Inténtalo de nuevo."))

class CaptchaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Iniciar Verificación", style=discord.ButtonStyle.primary, emoji="🧠", custom_id="btn_ai_captcha")
    async def btn_verificar(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = obtener_guild_config(interaction.guild.id)
        rol_id = cfg.get("verified_role")
        
        if not rol_id:
            return await interaction.response.send_message(embed=embed_error("Sistema Inactivo", "El administrador no ha configurado el rol de verificado."), ephemeral=True)
            
        if interaction.user.get_role(int(rol_id)):
            return await interaction.response.send_message(embed=embed_exito("Ya Verificado", "Ya posees acceso a la red."), ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        
        # Generamos un acertijo único
        prompt_acertijo = (
            "Genera un acertijo lógico o matemático extremadamente simple, de una sola línea. "
            "Debe ser fácil para un humano pero imposible de predecir para un bot. "
            "Ejemplo: 'Si tengo 3 manzanas y me como 1, ¿cuántas me quedan?' o '¿De qué color es el cielo despejado de día?'. "
            "Devuelve SOLO la pregunta, sin comillas ni saludos."
        )
        
        acertijo = await preguntar_ia(prompt_acertijo, max_tokens=50)
        
        if acertijo.startswith("⚠️"):
            return await interaction.followup.send("El motor cognitivo está reiniciándose. Intenta en unos segundos.", ephemeral=True)

        # Enviamos el modal con el acertijo
        modal = CaptchaModal(acertijo, rol_id)
        # Truco: Discord no deja enviar un modal desde un defer, así que enviamos un mensaje con un botón que abre el modal
        # Para simplificar la UX, le pedimos al usuario que use un comando o le damos el acertijo aquí.
        # Corrección de UX: Como ya hicimos defer, enviaremos el acertijo y un botón para responder.
        
        view_respuesta = discord.ui.View(timeout=120)
        btn_responder = discord.ui.Button(label="Responder Acertijo", style=discord.ButtonStyle.success, emoji="✍️")
        
        async def modal_callback(inter: discord.Interaction):
            await inter.response.send_modal(CaptchaModal(acertijo, rol_id))
            
        btn_responder.callback = modal_callback
        view_respuesta.add_item(btn_responder)
        
        await interaction.followup.send(f"**Prueba de Turing (AI-Captcha):**\n> {acertijo}", view=view_respuesta, ephemeral=True)

class Verificacion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="setup-captcha", description="Despliega el panel de verificación cognitiva (AI-Captcha)")
    @app_commands.describe(rol_verificado="El rol que se dará al pasar la prueba")
    @commands.has_permissions(administrator=True)
    async def setup_captcha(self, ctx, rol_verificado: discord.Role):
        await ctx.defer()
        
        from utils.helpers import actualizar_guild_config
        actualizar_guild_config(ctx.guild.id, "verified_role", rol_verificado.id)
        
        contenido = (
            f"> **Protocolo de Seguridad:** `TURING-TEST V2`\n"
            f"> **Nivel de Encriptación:** `Cognitivo`\n\n"
            f"Para acceder a los canales seguros de esta red, debes demostrar que eres una entidad humana.\n"
            f"Haz clic en el botón inferior. El motor de Inteligencia Artificial generará una prueba lógica única para ti."
        )
        
        panel = formato_editorial("CONTROL DE ACCESO BIOMÉTRICO", contenido, badge="FIREWALL")
        await ctx.send(panel, view=CaptchaView())

async def setup(bot):
    await bot.add_cog(Verificacion(bot))