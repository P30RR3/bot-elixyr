"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR GUARD // AI-CAPTCHA & TURING PROTOCOL (NEW GEN v6.0)
  Capacidades: Desafíos Lógicos Dinámicos con Cerebras AI, Contingencia Local,
               Blindaje Anti-Fuerza Bruta y Registro de Acceso Biométrico
═══════════════════════════════════════════════════════════════════════════════
"""

import discord
from discord.ext import commands
from discord import app_commands
import random
import time
import logging
from collections import defaultdict
from utils.helpers import obtener_guild_config, actualizar_guild_config
from utils.ia import preguntar_ia
from utils.ui import formato_editorial

logger = logging.getLogger("ElixyrCaptcha")

# Banco de Contingencia Local de Alta Velocidad (0ms si la IA está ocupada)
BANCO_CONTINGENCIA = [
    {"q": "¿De qué color es la hierba fresca?", "a": ["verde", "green"]},
    {"q": "Si tienes 3 llaves y consigues 2 más, ¿cuántas tienes?", "a": ["5", "cinco"]},
    {"q": "¿Cuál es el resultado de sumar 10 + 20?", "a": ["30", "treinta"]},
    {"q": "¿En qué planeta vivimos?", "a": ["tierra", "earth"]},
    {"q": "¿Qué elemento respiran los seres humanos?", "a": ["oxigeno", "aire"]},
    {"q": "¿Cuántos días tiene una semana normal?", "a": ["7", "siete"]}
]

class CaptchaModal(discord.ui.Modal, title="Prueba de Turing Biometría"):
    respuesta = discord.ui.TextInput(
        label="Tu Respuesta",
        placeholder="Escribe la solución exacta aquí...",
        required=True,
        max_length=50
    )

    def __init__(self, acertijo: str, rol_id: int, respuestas_fallback: list = None):
        super().__init__()
        self.acertijo = acertijo
        self.rol_id = rol_id
        self.respuestas_fallback = respuestas_fallback

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_input = self.respuesta.value.strip().lower()

        validado = False

        if self.respuestas_fallback:
            validado = any(r in user_input for r in self.respuestas_fallback)
        else:
            prompt = (
                f"El acertijo planteado fue: '{self.acertijo}'.\n"
                f"La respuesta dada por el usuario es: '{user_input}'.\n"
                f"¿Es lógicamente aceptable y correcta? Responde ÚNICAMENTE con la palabra TRUE o FALSE."
            )
            dictamen = await preguntar_ia(prompt, max_tokens=10)
            if "TRUE" in dictamen.upper():
                validado = True

        rol = interaction.guild.get_role(int(self.rol_id))

        if validado:
            if rol:
                try:
                    await interaction.user.add_roles(rol, reason="AI-Captcha superado exitosamente")
                    cuerpo = (
                        f"> Identidad validada: {interaction.user.mention}\n"
                        f"> Acceso concedido al sector seguro del servidor."
                    )
                    await interaction.followup.send(formato_editorial("AUTENTICACIÓN CONCEDIDA", cuerpo, badge="BIOMETRIC-OK"), ephemeral=True)
                except discord.Forbidden:
                    await interaction.followup.send("⚠️ Error de jerarquía: Mi rol no puede otorgar esa credencial.", ephemeral=True)
            else:
                await interaction.followup.send("⚠️ El rol de verificación ya no existe en el servidor.", ephemeral=True)
        else:
            await interaction.followup.send(
                "⛔ **Acceso Denegado:** Respuesta errónea. Firma cognitiva sospechosa de automatización.",
                ephemeral=True
            )

class CaptchaGateView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.intentos_fallidos = defaultdict(lambda: {"count": 0, "cooldown": 0})

    @discord.ui.button(label="Iniciar Autenticación", style=discord.ButtonStyle.primary, emoji="🧠", custom_id="btn_turing_start")
    async def verificar_click(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        ahora = time.time()

        # ─── PROTECCIÓN ANTI-FUERZA BRUTA ───
        if self.intentos_fallidos[uid]["count"] >= 3:
            tiempo_restante = int(self.intentos_fallidos[uid]["cooldown"] - ahora)
            if tiempo_restante > 0:
                return await interaction.response.send_message(
                    f"⛔ **Terminal Bloqueada:** Demasiados intentos fallidos. Reintenta en `{tiempo_restante}s`.",
                    ephemeral=True
                )
            else:
                self.intentos_fallidos[uid] = {"count": 0, "cooldown": 0}

        cfg = obtener_guild_config(interaction.guild.id)
        rol_id = cfg.get("verified_role")

        if not rol_id:
            return await interaction.response.send_message("⚠️ El sistema de verificación no tiene un rol configurado (`/setup-captcha`).", ephemeral=True)

        if interaction.user.get_role(int(rol_id)):
            return await interaction.response.send_message("✨ Ya cuentas con acceso verificado a la red.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        # Generar desafío con Cerebras AI
        prompt = (
            "Genera un acertijo lógico o matemático extremadamente simple de 1 sola frase. "
            "Debe ser obvio para un humano pero sin patrones predecibles para bots. "
            "Devuelve SOLO el acertijo, sin comillas ni introducciones."
        )
        acertijo = await preguntar_ia(prompt, max_tokens=60)
        resp_fallback = None

        if acertijo.startswith("❌") or acertijo.startswith("⚠️") or len(acertijo) < 5:
            seleccion = random.choice(BANCO_CONTINGENCIA)
            acertijo = seleccion["q"]
            resp_fallback = seleccion["a"]

        # Crear botón para disparar el Modal
        vista_respuesta = discord.ui.View(timeout=120)
        btn_modal = discord.ui.Button(label="Resolver Desafío", style=discord.ButtonStyle.success, emoji="✍️")

        async def callback_modal(inter: discord.Interaction):
            await inter.response.send_modal(CaptchaModal(acertijo, rol_id, resp_fallback))

        btn_modal.callback = callback_modal
        vista_respuesta.add_item(btn_modal)

        cuerpo = (
            f"**Desafío Cognitivo Generado:**\n"
            f"> *\"{acertijo}\"*\n\n"
            f"-# Pulsa el botón inferior para ingresar tu respuesta."
        )
        await interaction.followup.send(formato_editorial("PRUEBA DE TURING // CONTROL BIOMÉTRICO", cuerpo, badge="TURING-GATE"), view=vista_respuesta, ephemeral=True)

class Verificacion(commands.Cog):
    """Módulo de control de acceso perimetral biométrico y anti-bots."""
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="setup-captcha", description="Publica el portal de acceso seguro con AI-Captcha")
    @app_commands.describe(rol_verificado="Rol que se otorgará tras superar la prueba")
    @commands.has_permissions(administrator=True)
    async def setup_captcha(self, ctx, rol_verificado: discord.Role):
        await ctx.defer()
        actualizar_guild_config(ctx.guild.id, "verified_role", rol_verificado.id)

        contenido = (
            f"> **Protocolo de Acceso:** `TURING-BIOMETRIC V6`\n"
            f"> **Credencial Asignada:** {rol_verificado.mention}\n\n"
            f"Para interactuar en esta red y evitar ataques de cuentas automatizadas, "
            f"es imperativo demostrar tu firma cognitiva humana.\n\n"
            f"Haz clic en el botón inferior para que el motor genere un desafío lógico único."
        )
        panel = formato_editorial(f"CONTROL DE ACCESO BIOMÉTRICO // {ctx.guild.name.upper()}", contenido, badge="GATEKEEPER")
        await ctx.channel.send(panel, view=CaptchaGateView(self.bot))
        await ctx.send("✦ **Portal de verificación desplegado exitosamente.**", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Verificacion(bot))