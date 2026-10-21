"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR GUARD // CREDENTIAL FORGING & ROLE OPERATIONS (NEW GEN v6.0)
  Capacidades: Role-Create con IA (LiveAction), Cuarentena Táctica Strip-Roles,
               Asignación Masiva con Barra de Carga Dinámica y Temp-Roles
═══════════════════════════════════════════════════════════════════════════════
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from utils.ia import preguntar_ia, extraer_json
from utils.helpers import crear_case
from utils.ui import formato_editorial, LiveActionController

COLORES_NATIVOS = {
    "rojo": discord.Color.red(), "azul": discord.Color.blue(), "verde": discord.Color.green(),
    "amarillo": discord.Color.gold(), "naranja": discord.Color.orange(), "morado": discord.Color.purple(),
    "rosa": discord.Color.from_rgb(255, 105, 180), "cyan": discord.Color.teal(),
    "blanco": discord.Color.from_rgb(250, 250, 250), "negro": discord.Color.from_rgb(20, 20, 20)
}

def resolver_color(txt: str) -> discord.Color:
    if not txt:
        return discord.Color.default()
    limpio = txt.strip().lower().replace("#", "")
    if limpio in COLORES_NATIVOS:
        return COLORES_NATIVOS[limpio]
    try:
        return discord.Color(int(limpio, 16))
    except ValueError:
        return discord.Color.default()

class Roles(commands.Cog):
    """Gestión de credenciales, contención táctica y creación asistida por IA."""
    def __init__(self, bot):
        self.bot = bot

    # ═════════════════════════════════════════════════════════════
    #  1. CREACIÓN QUIRÚRGICA DE ROLES CON IA (LIVE-ACTION)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(
        name="role-create-ia",
        description="Diseña un rol configurando su matriz de permisos y color mediante Cerebras AI"
    )
    @app_commands.describe(
        descripcion="Explica qué funciones tendrá el rol",
        nombre="Nombre opcional para el rol",
        color="Color en español o código HEX (#FF0055)"
    )
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_create_ia(self, ctx, descripcion: str, nombre: str = None, color: str = None):
        await ctx.defer()

        live = LiveActionController(ctx, "Forja de Credenciales // AI Role Engine", total_pasos=3)
        await live.iniciar()

        await live.actualizar("Analizando privilegios requeridos y directivas de seguridad...", exito=True)

        permisos_validos = [p for p, _ in discord.Permissions.none()]
        prompt = f"""El administrador necesita un rol con este propósito:
"{descripcion}"
Nombre sugerido: {nombre or 'Ninguno (elige uno profesional)'}

Permisos reconocidos por discord.py:
{permisos_validos}

Reglas:
1. Concede estrictamente los permisos necesarios para la tarea.
2. NUNCA asignes 'administrator' a menos que se exija explícitamente.
3. Si el rol es cosmético o de nivel, devuelve permisos vacíos [].

Devuelve SOLO este JSON:
{{
  "nombre": "Nombre del Rol",
  "color": "#HEX",
  "separado": true/false,
  "mencionable": true/false,
  "permisos": ["permiso1", "permiso2"]
}}"""

        await live.actualizar("Calculando matriz de privilegios con Cerebras AI...", exito=True)
        raw_ia = await preguntar_ia(prompt, json_mode=True, max_tokens=250)
        data = extraer_json(raw_ia)

        if not data:
            await live.finalizar("La IA no devolvió una matriz de permisos válida.", error=True)
            return

        nombre_final = (nombre or data.get("nombre", "Rol Personalizado"))[:100]
        color_final = resolver_color(color or data.get("color", "#5865F2"))

        # Auditar permisos contra la jerarquía del bot
        perms = discord.Permissions.none()
        bot_perms = ctx.guild.me.guild_permissions
        concedidos, rechazados = [], []

        for p in data.get("permisos", []):
            p_clean = str(p).strip().lower()
            if hasattr(perms, p_clean):
                if getattr(bot_perms, p_clean, False) or bot_perms.administrator:
                    setattr(perms, p_clean, True)
                    concedidos.append(p_clean)
                else:
                    rechazados.append(p_clean)

        await live.actualizar(f"Inyectando credencial '{nombre_final}' en la jerarquía...", exito=True)

        try:
            nuevo_rol = await ctx.guild.create_role(
                name=nombre_final,
                color=color_final,
                permissions=perms,
                hoist=bool(data.get("separado", True)),
                mentionable=bool(data.get("mencionable", False)),
                reason=f"Role IA por {ctx.author}: {descripcion[:60]}"
            )
            await live.finalizar(f"Credencial {nuevo_rol.name} forjada exitosamente.", error=False)

            perms_txt = ", ".join(f"`{p}`" for p in concedidos) if concedidos else "*Sin permisos elevados (Cosmético)*"
            aviso_rechazos = f"\n> ⚠️ *Permisos omitidos por superar mi jerarquía:* {', '.join(f'`{p}`' for p in rechazados)}" if rechazados else ""

            cuerpo = (
                f"> **Credencial:** {nuevo_rol.mention} (`{nuevo_rol.name}`)\n"
                f"> **Color:** `#{nuevo_rol.color.value:06X}` | **Lista Separada:** `{'Sí' if nuevo_rol.hoist else 'No'}`\n\n"
                f"**Privilegios Asignados:**\n"
                f"> {perms_txt}{aviso_rechazos}\n\n"
                f"-# Forjado y auditado mediante Cerebras Cognitive Engine."
            )
            await ctx.channel.send(formato_editorial("CREDENCIAL FORJADA POR IA", cuerpo, badge="ROLE-FORGE"))

        except Exception as e:
            await live.finalizar(f"Fallo al forjar el rol: {e}", error=True)

    # ═════════════════════════════════════════════════════════════
    #  2. PROTOCOLO DE CUARENTENA (STRIP-ROLES)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="strip-roles", description="🚨 Despoja de todos sus roles a un usuario (Aislamiento de cuenta comprometida)")
    @app_commands.describe(usuario="Miembro a poner en cuarentena inmediata")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def strip_roles(self, ctx, usuario: discord.Member):
        await ctx.defer()
        if usuario.id == ctx.guild.owner_id:
            return await ctx.send("⛔ Imposible aislar al dueño de la infraestructura.", ephemeral=True)
        if usuario.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("⛔ Jerarquía insuficiente: El objetivo tiene un rol superior o igual al tuyo.", ephemeral=True)

        roles_remover = [r for r in usuario.roles if r.name != "@everyone" and not r.managed and r < ctx.guild.me.top_role]
        if not roles_remover:
            return await ctx.send(f"⚠️ {usuario.mention} no tiene roles que puedan ser revocados por mi nivel de acceso.", ephemeral=True)

        try:
            await usuario.remove_roles(*roles_remover, reason=f"Protocolo de Cuarentena ejecutado por {ctx.author}")
        except Exception as e:
            return await ctx.send(f"❌ Error al revocar privilegios: `{e}`", ephemeral=True)

        case_id = crear_case("strip-roles", usuario.id, ctx.author.id, "Cuarentena preventiva por sospecha de sabotaje", {"removidos": len(roles_remover)})

        cuerpo = (
            f"> **Sujeto Aislado:** {usuario.mention} (`{usuario.id}`)\n"
            f"> **Credenciales Revocadas:** `{len(roles_remover)}` roles despojados\n"
            f"> **Oficial:** {ctx.author.mention} | **Expediente:** `#{case_id}`\n\n"
            f"**Estado de Seguridad:** La cuenta ha sido despojada de accesos administrativos y canalizada al área de contención."
        )
        await ctx.send(formato_editorial("CUARENTENA PREVENTIVA // STRIP-ROLES", cuerpo, badge="PANIC-SECURITY"))

    # ═════════════════════════════════════════════════════════════
    #  3. ASIGNACIONES MASIVAS CON BARRA EN VIVO (ROLE-ALL / ROLE-BOTS)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="role-all", description="Otorga un rol a todos los humanos con seguimiento en vivo")
    @app_commands.describe(rol="Rol a asignar masivamente")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_all(self, ctx, rol: discord.Role):
        await ctx.defer()
        if rol >= ctx.guild.me.top_role or rol >= ctx.author.top_role:
            return await ctx.send("⛔ Jerarquía insuficiente sobre el rol seleccionado.", ephemeral=True)

        humanos = [m for m in ctx.guild.members if not m.bot and rol not in m.roles]
        total = len(humanos)
        if total == 0:
            return await ctx.send(f"✦ Todos los miembros humanos ya cuentan con la credencial {rol.mention}.")

        live = LiveActionController(ctx, f"Asignación Masiva // {rol.name}", total_pasos=total)
        await live.iniciar()

        asignados, fallos = 0, 0
        for i, m in enumerate(humanos, 1):
            try:
                await m.add_roles(rol, reason=f"Role-All por {ctx.author}")
                asignados += 1
            except Exception:
                fallos += 1

            if i % 4 == 0 or i == total:
                await live.actualizar(f"Inyectando credencial a {m.display_name} (Éxitos: {asignados} | Fallos: {fallos})...", exito=True)
                await asyncio.sleep(1.0)

        await live.finalizar(f"Despliegue finalizado: {asignados} asignados, {fallos} fallos.", error=(fallos > asignados))

    @commands.hybrid_command(name="role-bots", description="Otorga un rol a todos los bots del servidor")
    @app_commands.describe(rol="Rol para los bots")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_bots(self, ctx, rol: discord.Role):
        await ctx.defer()
        if rol >= ctx.guild.me.top_role:
            return await ctx.send("⛔ Jerarquía insuficiente sobre el rol seleccionado.", ephemeral=True)

        bots = [m for m in ctx.guild.members if m.bot and rol not in m.roles]
        total = len(bots)
        if total == 0:
            return await ctx.send(f"✦ Todos los bots ya cuentan con la credencial {rol.mention}.")

        live = LiveActionController(ctx, f"Sincronización Bots // {rol.name}", total_pasos=total)
        await live.iniciar()

        asignados, fallos = 0, 0
        for i, b in enumerate(bots, 1):
            try:
                await b.add_roles(rol, reason=f"Role-Bots por {ctx.author}")
                asignados += 1
            except Exception:
                fallos += 1

            if i % 3 == 0 or i == total:
                await live.actualizar(f"Sincronizando bot {b.name} (Éxitos: {asignados} | Fallos: {fallos})...", exito=True)
                await asyncio.sleep(1.0)

        await live.finalizar(f"Sincronización completada: {asignados} bots actualizados.", error=False)

    # ═════════════════════════════════════════════════════════════
    #  4. GESTIÓN MANUAL Y ROL TEMPORAL (TEMP-ROLE)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="temp-role", description="Asigna un rol de forma provisional por una cantidad de minutos")
    @app_commands.describe(usuario="Miembro objetivo", rol="Rol temporal", minutos="Duración en minutos")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def temp_role(self, ctx, usuario: discord.Member, rol: discord.Role, minutos: int):
        await ctx.defer()
        if rol >= ctx.guild.me.top_role or rol >= ctx.author.top_role:
            return await ctx.send("⛔ Jerarquía insuficiente para manipular esta credencial.", ephemeral=True)
        if minutos <= 0:
            return await ctx.send("⚠️ La duración debe ser mayor a 0 minutos.", ephemeral=True)

        await usuario.add_roles(rol, reason=f"Temp-Role ({minutos}m) por {ctx.author}")
        await ctx.send(f"✦ Credencial {rol.mention} concedida a {usuario.mention} por `{minutos} minutos`.")

        await asyncio.sleep(minutos * 60)
        if rol in usuario.roles:
            try:
                await usuario.remove_roles(rol, reason="Expiración programada de Temp-Role")
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(Roles(bot))