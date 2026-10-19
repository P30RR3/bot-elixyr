import discord
from discord.ext import commands
from discord import app_commands
from utils.helpers import cargar_config, guardar_config
from utils.ia import preguntar_ia
from datetime import datetime, timezone

CONFIG = cargar_config()

# ─────────────────────────────────────────────────────────────
#  VISTA 1: SELECTOR DESPLEGABLE DE NOTIFICACIONES / INTERESES
# ─────────────────────────────────────────────────────────────
class NotificationRolesSelect(discord.ui.Select):
    def __init__(self, opciones_roles):
        # opciones_roles es una lista de tuplas: (label, description, emoji, role_id)
        options = [
            discord.SelectOption(label=label, description=desc, emoji=emoji, value=str(role_id))
            for label, desc, emoji, role_id in opciones_roles
        ]
        super().__init__(
            placeholder="🔔 Configura tus alertas y suscripciones...",
            min_values=0,
            max_values=len(options),
            custom_id="select_notif_roles",
            options=options,
        )
        self.todos_los_roles = [role_id for _, _, _, role_id in opciones_roles]

    async def callback(self, interaction: discord.Interaction):
        seleccionados = [int(val) for val in self.values]
        miembro = interaction.user
        roles_agregados, roles_removidos = [], []

        for rid in self.todos_los_roles:
            rol = interaction.guild.get_role(rid)
            if not rol:
                continue
            if rid in seleccionados:
                if rol not in miembro.roles:
                    await miembro.add_roles(rol, reason="Auto-Rol: Selección voluntaria")
                    roles_agregados.append(rol.name)
            else:
                if rol in miembro.roles:
                    await miembro.remove_roles(rol, reason="Auto-Rol: Deselección voluntaria")
                    roles_removidos.append(rol.name)

        resumen = []
        if roles_agregados:
            resumen.append(f"✅ **Activados:** {', '.join(roles_agregados)}")
        if roles_removidos:
            resumen.append(f"❌ **Desactivados:** {', '.join(roles_removidos)}")
        if not resumen:
            resumen.append("No se realizaron modificaciones a tus roles.")

        await interaction.response.send_message("\n".join(resumen), ephemeral=True)


class NotificationRolesView(discord.ui.View):
    def __init__(self, opciones_roles):
        super().__init__(timeout=None)
        self.add_item(NotificationRolesSelect(opciones_roles))


# ─────────────────────────────────────────────────────────────
#  VISTA 2: BOTONES DE VERIFICACIÓN ESTILIZADOS
# ─────────────────────────────────────────────────────────────
class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Completar Acceso", style=discord.ButtonStyle.secondary, emoji="🛡️", custom_id="verify_btn")
    async def verificar(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        guest_role_id = CONFIG.get("guest_role")
        verified_role_id = CONFIG.get("verified_role")

        verified_role = guild.get_role(verified_role_id) if verified_role_id else None
        guest_role = guild.get_role(guest_role_id) if guest_role_id else None

        if not verified_role:
            return await interaction.response.send_message("⚠️ El rol de verificación aún no ha sido configurado en el sistema.", ephemeral=True)

        if verified_role in user.roles:
            return await interaction.response.send_message("✨ Ya cuentas con acceso verificado al servidor.", ephemeral=True)

        try:
            if guest_role and guest_role in user.roles:
                await user.remove_roles(guest_role, reason="Verificación completada")
            await user.add_roles(verified_role, reason="Verificación completada")
            await interaction.response.send_message(f"🔓 **Bienvenido/a {user.mention}.** Tu identidad ha sido autenticada exitosamente.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Error de jerarquía: Mi rol no tiene permisos suficientes para otorgarte el rango.", ephemeral=True)


# ─────────────────────────────────────────────────────────────
#  COG PRINCIPAL DE AUTO-ROLES
# ─────────────────────────────────────────────────────────────
class AutoRol(commands.Cog):
    """Gestor integral de auto-roles, bienvenida con diseño editorial y asesor de paletas IA."""
    def __init__(self, bot):
        self.bot = bot

    # ─────────────────────────────────────────────────────────
    # BIENVENIDA Y AUTO-ROL DE INGRESO
    # ─────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            return
        guild = member.guild

        # 1. Asignar rol inicial
        guest_role_id = CONFIG.get("guest_role")
        if guest_role_id:
            guest_role = guild.get_role(guest_role_id)
            if guest_role:
                try:
                    await member.add_roles(guest_role, reason="Rol inicial de bienvenida")
                except Exception:
                    pass

        # 2. Mensaje en canal de bienvenida sin embeds genéricos
        welcome_channel_id = CONFIG.get("welcome_channel")
        if welcome_channel_id:
            canal = guild.get_channel(welcome_channel_id)
            if canal:
                antiguedad_dias = (datetime.now(timezone.utc) - member.created_at).days
                canal_verify = f"<#{CONFIG.get('verify_channel')}>" if CONFIG.get('verify_channel') else "nuestro canal de reglas"

                formato = (
                    f"# ✨ NUEVO INGRESO // {member.name.upper()}\n"
                    f"> ¡Le damos la bienvenida a {member.mention} a **{guild.name}**!\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"▸ **Cuenta creada:** <t:{int(member.created_at.timestamp())}:R> (`{antiguedad_dias} días de antigüedad`)\n"
                    f"▸ **Primer paso:** Dirígete a {canal_verify} para activar tu perfil y desbloquear los canales.\n\n"
                    f"-# Eres el miembro número #{guild.member_count} de la comunidad."
                )
                try:
                    await canal.send(formato)
                except Exception:
                    pass

    # ─────────────────────────────────────────────────────────
    # COMANDO: PUBLICAR PANEL DE NOTIFICACIONES / INTERESES
    # ─────────────────────────────────────────────────────────
    @commands.hybrid_command(name="panel-notificaciones", description="Crea un panel interactivo desplegable para que los usuarios elijan sus alertas")
    @app_commands.describe(
        rol_anuncios="Rol para avisos importantes",
        rol_eventos="Rol para eventos y dinámicas",
        rol_actualizaciones="Rol para cambios y parches"
    )
    @commands.has_permissions(administrator=True)
    async def panel_notificaciones(self, ctx, rol_anuncios: discord.Role, rol_eventos: discord.Role, rol_actualizaciones: discord.Role):
        await ctx.defer()

        opciones = [
            ("Anuncios y Noticias", "Avisos importantes de la administración", "📢", rol_anuncios.id),
            ("Eventos y Dinámicas", "Notificaciones de actividades y reuniones", "🎉", rol_eventos.id),
            ("Parches y Cambios", "Actualizaciones técnicas y del bot", "⚙️", rol_actualizaciones.id),
        ]

        contenido = (
            f"# 🔔 CENTRO DE NOTIFICACIONES // {ctx.guild.name.upper()}\n"
            f"> Selecciona únicamente los temas sobre los que deseas recibir menciones directas.\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▸ 📢 **Anuncios:** {rol_anuncios.mention}\n"
            f"▸ 🎉 **Eventos:** {rol_eventos.mention}\n"
            f"▸ ⚙️ **Parches:** {rol_actualizaciones.mention}\n\n"
            f"-# Utiliza el menú inferior. Puedes activarlos o desactivarlos en cualquier momento."
        )

        view = NotificationRolesView(opciones)
        await ctx.channel.send(contenido, view=view)
        await ctx.send("✅ **Panel de roles publicado con éxito.**", ephemeral=True)

    # ─────────────────────────────────────────────────────────
    # COMANDO: PUBLICAR PANEL DE ACCESO / VERIFICACIÓN
    # ─────────────────────────────────────────────────────────
    @commands.hybrid_command(name="verificar-panel", description="Publica el panel con botón de verificación de identidad")
    @commands.has_permissions(administrator=True)
    async def verificar_panel(self, ctx):
        await ctx.defer()
        contenido = (
            f"# 🛡️ ACCESO A LA COMUNIDAD // {ctx.guild.name.upper()}\n"
            f"> Para acceder al resto de los canales y participar en las conversaciones, es necesario verificar tu cuenta.\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▸ Haz clic en el botón de abajo para registrar tu entrada.\n"
            f"▸ Este proceso descarta cuentas bot automáticas y ataques de spam.\n\n"
            f"-# Al pulsar el botón confirmas que cumples con las normativas del servidor."
        )
        await ctx.channel.send(contenido, view=VerifyView())
        await ctx.send("✅ **Panel de verificación desplegado.**", ephemeral=True)

    # ─────────────────────────────────────────────────────────
    # COMANDO: ASESOR DE ROLES Y PALETAS DE COLOR CON IA
    # ─────────────────────────────────────────────────────────
    @commands.hybrid_command(name="ia-sugerir-roles", description="La IA diseña una estructura estética de roles y colores para tu servidor")
    @app_commands.describe(tematica="¿De qué trata tu servidor? (ej: Gaming competitivo, Moda, Cyberpunk, Anime, Programación)")
    @commands.has_permissions(administrator=True)
    async def ia_sugerir_roles(self, ctx, *, tematica: str):
        await ctx.defer()

        prompt = (
            f"Actúa como un diseñador de moda y branding visual especializado en Discord.\n"
            f"El servidor tiene esta temática: '{tematica}'.\n\n"
            f"Diseña una propuesta de roles con alto valor estético que incluya:\n"
            f"1. **3 Roles de Rango/Nivel:** Con nombres creativos acordes a la temática.\n"
            f"2. **Paleta de Colores Hexadecimales:** Recomienda 3 códigos Hex (ej: #2b2d31, #f43f5e) que combinen a la perfección en tema oscuro de Discord.\n"
            f"3. **3 Roles de Intereses o Cosméticos:** Para que la comunidad interactúe.\n\n"
            f"Usa Markdown limpio con encabezados (##) y viñetas (▸). No agregues charlas introductorias."
        )

        propuesta = await preguntar_ia(prompt)

        salida = (
            f"# 🎨 ASESORÍA DE MARCA Y ROLES // {ctx.guild.name.upper()}\n"
            f"> **Temática analizada:** *{tematica}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{propuesta}\n\n"
            f"-# Sugerencia generada por el motor de diseño Cerebras AI."
        )
        await ctx.send(salida)


async def setup(bot):
    await bot.add_cog(AutoRol(bot))