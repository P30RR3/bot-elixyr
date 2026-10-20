import discord
from discord.ext import commands
from discord import app_commands
from utils.ia import preguntar_ia, extraer_json
from utils.ui import barra_progreso, formato_editorial
import asyncio

# Paleta de colores comunes en español para mapeo directo
COLORES_NATIVOS = {
    "rojo": discord.Color.red(),
    "azul": discord.Color.blue(),
    "verde": discord.Color.green(),
    "amarillo": discord.Color.gold(),
    "naranja": discord.Color.orange(),
    "morado": discord.Color.purple(),
    "purpura": discord.Color.purple(),
    "rosa": discord.Color.from_rgb(255, 105, 180),
    "cyan": discord.Color.teal(),
    "turquesa": discord.Color.teal(),
    "blanco": discord.Color.from_rgb(250, 250, 250),
    "negro": discord.Color.from_rgb(20, 20, 20),
    "gris": discord.Color.light_grey(),
    "oscuro": discord.Color.dark_grey(),
}

def resolver_color(color_texto: str) -> discord.Color | None:
    """Convierte texto en español o código Hex en un discord.Color válido."""
    if not color_texto:
        return None
    texto_limpio = color_texto.strip().lower().replace("#", "")
    if texto_limpio in COLORES_NATIVOS:
        return COLORES_NATIVOS[texto_limpio]
    try:
        return discord.Color(int(texto_limpio, 16))
    except ValueError:
        return None

class Roles(commands.Cog):
    """Gestión de credenciales, contención táctica y creación asistida por IA."""
    def __init__(self, bot):
        self.bot = bot

    # ═════════════════════════════════════════════════════════════
    #  1. CREACIÓN QUIRÚRGICA DE ROLES CON IA
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(
        name="role-create-ia",
        description="Crea un rol configurando permisos, color y jerarquía con Cerebras AI"
    )
    @app_commands.describe(
        descripcion="Explica qué hará el rol (ej: mod que solo borre mensajes y mutee, sin banear)",
        nombre="Opcional: Nombre exacto para el rol",
        color="Opcional: Código Hex (#FF0055) o color en español (rojo, azul, morado...)"
    )
    @commands.has_permissions(manage_roles=True)
    async def role_create_ia(self, ctx, descripcion: str, nombre: str = None, color: str = None):
        await ctx.defer()
        msg_wait = await ctx.send("🧠 *Analizando directivas y calculando matriz de permisos...*")

        # Lista de permisos reales que soporta discord.py
        permisos_validos = [p for p, _ in discord.Permissions.none()]

        sys_prompt = "Eres un arquitecto de seguridad y permisos de Discord. Responde ÚNICAMENTE con un JSON válido."

        prompt = f"""El usuario necesita un rol con este propósito:
"{descripcion}"
Nombre sugerido: {"Ninguno (invéntalo acorde)" if not nombre else nombre}

Permisos permitidos en discord.py:
{permisos_validos}

Directrices obligatorias:
1. Analiza qué permisos necesita estrictamente para cumplir su función.
2. NO asignes administrator a menos que sea explícitamente requerido.
3. Si el rol es puramente cosmético o de nivel, devuelve permisos vacíos [].

Devuelve SOLO este JSON:
{{
  "nombre": "Nombre del Rol",
  "color": "#HEX",
  "separado": true/false,
  "mencionable": true/false,
  "permisos": ["permiso_1", "permiso_2"]
}}"""

        respuesta = await preguntar_ia(prompt, json_mode=True, system_prompt=sys_prompt)

        # Usamos el extractor blindado en lugar de confiar ciegamente
        data = extraer_json(respuesta)
        if not data:
            return await msg_wait.edit(content="⚠️ **Error Crítico:** La IA devolvió un formato corrupto o incomprensible. Operación abortada.")

        nombre_final = (nombre or data.get("nombre", "Rol Personalizado"))[:100]

        # ─── Resolver Color (Prioridad: Usuario > IA > Default) ───
        color_final = resolver_color(color)
        if not color_final:
            color_hex_ia = str(data.get("color", "#5865F2")).replace("#", "").strip()
            try:
                color_final = discord.Color(int(color_hex_ia, 16))
            except ValueError:
                color_final = discord.Color.default()

        # ─── Auditoría y Asignación de Permisos ───
        perms = discord.Permissions.none()
        permisos_concedidos = []
        permisos_rechazados = []

        bot_perms = ctx.guild.me.guild_permissions
        es_bot_admin = bot_perms.administrator

        for p in data.get("permisos", []):
            p_clean = str(p).strip().lower()
            if hasattr(perms, p_clean):
                # Discord rechaza crear roles con permisos superiores a los del propio bot
                tiene_el_bot = getattr(bot_perms, p_clean, False) or es_bot_admin
                if tiene_el_bot:
                    setattr(perms, p_clean, True)
                    permisos_concedidos.append(p_clean)
                else:
                    permisos_rechazados.append(p_clean)

        # ─── Creación del Rol en Discord ───
        try:
            nuevo_rol = await ctx.guild.create_role(
                name=nombre_final,
                color=color_final,
                permissions=perms,
                hoist=bool(data.get("separado", True)),
                mentionable=bool(data.get("mencionable", False)),
                reason=f"Role IA creado por {ctx.author}: {descripcion[:100]}"
            )
        except discord.Forbidden:
            return await msg_wait.edit(content="⛔ **Error de Jerarquía:** No tengo permisos para gestionar roles con ese nivel de privilegios.")
        except Exception as err:
            return await msg_wait.edit(content=f"⚠️ **Fallo al forjar el rol:** `{err}`")

        perms_txt = ", ".join(f"`{p}`" for p in permisos_concedidos) if permisos_concedidos else "*Ninguno (Rol estándar / Cosmético)*"
        aviso_rechazo = f"\n> ⚠️ *Permisos omitidos por jerarquía del bot:* {', '.join(f'`{p}`' for p in permisos_rechazados)}" if permisos_rechazados else ""

        panel = (
            f"### 🛡️ CREDENCIAL FORJADA POR IA // {nuevo_rol.mention}\n"
            f"✦ ────────────────────────────────────────── ✦\n"
            f"> **Identificador:** `{nuevo_rol.name}`\n"
            f"> **Color Asignado:** `#{nuevo_rol.color.value:06X}`\n"
            f"> **Lista Separada (Hoist):** `{'Activo 🟢' if nuevo_rol.hoist else 'Inactivo ⚪'}`\n"
            f"> **Mencionable:** `{'Sí' if nuevo_rol.mentionable else 'No'}`\n\n"
            f"**Permisos autorizados:**\n"
            f"> {perms_txt}{aviso_rechazo}\n"
            f"✦ ────────────────────────────────────────── ✦\n"
            f"-# Optimizado y creado con Cerebras AI."
        )
        await msg_wait.edit(content=panel)

    # ═════════════════════════════════════════════════════════════
    #  2. PROTOCOLO DE CUARENTENA (STRIP-ROLES)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="strip-roles", description="🚨 Despoja todos los roles a un usuario (Aislamiento de cuenta comprometida)")
    @app_commands.describe(usuario="Miembro a poner en cuarentena")
    @commands.has_permissions(administrator=True)
    async def strip_roles(self, ctx, usuario: discord.Member):
        await ctx.defer()
        if usuario.id == ctx.guild.owner_id:
            return await ctx.send("⛔ Imposible aislar al propietario de la infraestructura.")
        if usuario.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("⛔ **Jerarquía insuficiente:** El objetivo tiene un rol igual o superior al tuyo.")

        roles_remover = [r for r in usuario.roles if r.name != "@everyone" and not r.managed and r < ctx.guild.me.top_role]
        if not roles_remover:
            return await ctx.send(f"⚠️ {usuario.mention} no tiene roles removibles.")

        try:
            await usuario.remove_roles(*roles_remover, reason=f"Protocolo de Cuarentena ejecutado por {ctx.author}")
        except Exception as e:
            return await ctx.send(f"⚠️ Error de jerarquía: `{e}`")

        prompt = (
            f"Alerta de Seguridad: Se ejecutó STRIP-ROLES sobre '{usuario.name}'. Se le retiraron {len(roles_remover)} roles de golpe. "
            f"Redacta un memorando de cuarentena formal de 2 líneas indicando que la cuenta ha sido aislada."
        )
        dictamen = await preguntar_ia(prompt)

        panel = (
            f"# ☣️ CUARENTENA TÁCTICA // PRIVILEGIOS REVOCADOS\n"
            f"✦ ────────────────────────────────────────── ✦\n"
            f"> **Sujeto Aislado:** {usuario.mention} (`{usuario.id}`)\n"
            f"> **Roles Despojados:** `{len(roles_remover)}` credenciales revocadas.\n"
            f"> **Oficial:** {ctx.author.mention}\n\n"
            f"**🧠 Dictamen Forense:**\n"
            f"> *{dictamen}*\n"
            f"✦ ────────────────────────────────────────── ✦"
        )
        await ctx.send(panel)

    # ═════════════════════════════════════════════════════════════
    #  3. ROL TEMPORAL (TEMP-ROLE)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="temp-role", description="Asigna un rol por una cantidad fija de minutos")
    @app_commands.describe(usuario="Destinatario", rol="Rol temporal", minutos="Minutos de duración")
    @commands.has_permissions(manage_roles=True)
    async def temp_role(self, ctx, usuario: discord.Member, rol: discord.Role, minutos: int):
        await ctx.defer()
        if rol >= ctx.guild.me.top_role or rol >= ctx.author.top_role:
            return await ctx.send("⛔ Jerarquía insuficiente para otorgar este rol.")
        if minutos <= 0:
            return await ctx.send("⚠️ Los minutos deben ser mayores a 0.")

        await usuario.add_roles(rol, reason=f"Temp-Role por {ctx.author} ({minutos}m)")
        await ctx.send(f"✦ Rol {rol.mention} concedido a {usuario.mention} por `{minutos} minutos`.")

        await asyncio.sleep(minutos * 60)
        if rol in usuario.roles:
            try:
                await usuario.remove_roles(rol, reason="Expiración de Temp-Role")
            except Exception:
                pass

    # ═════════════════════════════════════════════════════════════
    #  4. ASIGNACIONES MASIVAS (LIVE LOADING TERMINAL)
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="role-all", description="Otorga un rol a todos los miembros humanos con barra de progreso en vivo")
    @app_commands.describe(rol="Rol a asignar masivamente")
    @commands.has_permissions(administrator=True)
    async def role_all(self, ctx, rol: discord.Role):
        await ctx.defer()
        
        if rol >= ctx.guild.me.top_role or rol >= ctx.author.top_role:
            return await ctx.send("⛔ **Jerarquía Insuficiente:** No tengo permisos para manipular este rol o es superior al tuyo.")

        humanos = [m for m in ctx.guild.members if not m.bot and rol not in m.roles]
        total = len(humanos)
        
        if total == 0:
            return await ctx.send(f"✦ Todos los miembros humanos ya poseen la credencial {rol.mention}.")

        # ─── RENDERIZADO INICIAL DEL PANEL ───
        def generar_panel(actual, asignados, fallos, completado=False):
            estado = "✅ **OPERACIÓN FINALIZADA**" if completado else "⏳ *Inyectando credenciales en la red...*"
            contenido = (
                f"> **Objetivo:** {rol.mention}\n"
                f"> **Población Objetivo:** `{total}` usuarios\n"
                f"> **Estado:** {estado}\n\n"
                f"{barra_progreso(actual, total)}\n"
                f"▸ **Completados:** `{asignados}` | **Fallos:** `{fallos}`"
            )
            return formato_editorial("DESPLIEGUE MASIVO DE CREDENCIALES", contenido, badge="SYSTEM")

        msg = await ctx.send(generar_panel(0, 0, 0))

        asignados = 0
        fallos = 0

        # ─── BUCLE DE INYECCIÓN CON RATE LIMIT PROTECTION ───
        for i, miembro in enumerate(humanos, 1):
            try:
                await miembro.add_roles(rol, reason=f"Role-All ejecutado por {ctx.author}")
                asignados += 1
            except Exception:
                fallos += 1
            
            # Actualizamos la pantalla cada 4 usuarios o si es el último
            if i % 4 == 0 or i == total:
                try:
                    await msg.edit(content=generar_panel(i, asignados, fallos, completado=(i == total)))
                except Exception:
                    pass 
            
            # Pausa táctica para no saturar la API de Discord
            await asyncio.sleep(1.2)

    @commands.hybrid_command(name="role-bots", description="Otorga un rol a todos los bots con barra de progreso en vivo")
    @app_commands.describe(rol="Rol para los bots")
    @commands.has_permissions(administrator=True)
    async def role_bots(self, ctx, rol: discord.Role):
        await ctx.defer()
        
        if rol >= ctx.guild.me.top_role:
            return await ctx.send("⛔ **Jerarquía Insuficiente.**")

        bots = [m for m in ctx.guild.members if m.bot and rol not in m.roles]
        total = len(bots)
        
        if total == 0:
            return await ctx.send(f"✦ Todos los bots ya poseen la credencial {rol.mention}.")

        def generar_panel(actual, asignados, fallos, completado=False):
            estado = "✅ **OPERACIÓN FINALIZADA**" if completado else "⚙️ *Sincronizando inteligencias artificiales...*"
            contenido = (
                f"> **Objetivo:** {rol.mention}\n"
                f"> **Población Bot:** `{total}` entidades\n"
                f"> **Estado:** {estado}\n\n"
                f"{barra_progreso(actual, total)}\n"
                f"▸ **Sincronizados:** `{asignados}` | **Fallos:** `{fallos}`"
            )
            return formato_editorial("ACTUALIZACIÓN DE SISTEMAS (BOTS)", contenido, badge="SYSTEM")

        msg = await ctx.send(generar_panel(0, 0, 0))

        asignados = 0
        fallos = 0

        for i, b in enumerate(bots, 1):
            try:
                await b.add_roles(rol, reason=f"Role-Bots por {ctx.author}")
                asignados += 1
            except Exception:
                fallos += 1
            
            if i % 3 == 0 or i == total:
                try:
                    await msg.edit(content=generar_panel(i, asignados, fallos, completado=(i == total)))
                except Exception:
                    pass
            
            await asyncio.sleep(1.2)

    # ═════════════════════════════════════════════════════════════
    #  5. GESTIÓN MANUAL DE CREDENCIALES
    # ═════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="role-add", description="Asigna un rol a un usuario manualmente")
    @app_commands.describe(usuario="Destinatario", rol="Rol")
    @commands.has_permissions(manage_roles=True)
    async def role_add(self, ctx, usuario: discord.Member, rol: discord.Role):
        await ctx.defer()
        if rol >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("⛔ Rango insuficiente.")
        await usuario.add_roles(rol, reason=f"Asignado por {ctx.author}")
        await ctx.send(f"✦ Credencial {rol.mention} otorgada a {usuario.mention}.")

    @commands.hybrid_command(name="role-remove", description="Remueve un rol de un usuario manualmente")
    @app_commands.describe(usuario="Destinatario", rol="Rol")
    @commands.has_permissions(manage_roles=True)
    async def role_remove(self, ctx, usuario: discord.Member, rol: discord.Role):
        await ctx.defer()
        if rol >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("⛔ Rango insuficiente.")
        await usuario.remove_roles(rol, reason=f"Removido por {ctx.author}")
        await ctx.send(f"✦ Credencial {rol.mention} revocada de {usuario.mention}.")

async def setup(bot):
    await bot.add_cog(Roles(bot))