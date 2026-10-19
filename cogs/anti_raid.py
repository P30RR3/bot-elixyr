import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils.helpers import obtener_guild_config, actualizar_guild_config, crear_case
from utils.ia import preguntar_ia
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import asyncio
import math
import re

# ═════════════════════════════════════════════════════════════════════════════
#  CONSTANTES Y MOTORES DE EXPRESIÓN REGULAR PARA PERFILADO
# ═════════════════════════════════════════════════════════════════════════════

# Nombres comúnmente usados por bots de spam o raiders
REGEX_SUSPICIOUS_NAMES = re.compile(
    r"(discord\.gg|twitter\.com|twitch\.tv|youtube\.com|free.*nitro|nitro.*free|"
    r"steam.*promo|admin|mod|staff|system|announcement|giveaway|bot)", 
    re.IGNORECASE
)

# ═════════════════════════════════════════════════════════════════════════════
#  CLASE PRINCIPAL DEL ESCUDO PERIMETRAL (ANTI-RAID V5)
# ═════════════════════════════════════════════════════════════════════════════
class AntiRaid(commands.Cog):
    """
    Sistema Defcon de Seguridad Perimetral y Anti-Sabotaje.
    Implementa Threat Scoring, Velocity Tracking, y Posturas Tácticas.
    """
    def __init__(self, bot):
        self.bot = bot
        
        # ─── CACHÉS DE MEMORIA RAM (VELOCITY TRACKING) ───
        self.joins_cache = defaultdict(list)
        self.recent_joiners = defaultdict(list)
        
        # ─── CACHÉS ANTI-NUKE (RASTREO DE ACCIONES DE STAFF) ───
        self.nuke_channels = defaultdict(lambda: defaultdict(list))
        self.nuke_roles = defaultdict(lambda: defaultdict(list))
        self.nuke_bans = defaultdict(lambda: defaultdict(list))
        self.nuke_kicks = defaultdict(lambda: defaultdict(list))
        self.nuke_webhooks = defaultdict(lambda: defaultdict(list))
        
        # ─── ESTADOS DE EMERGENCIA ───
        self.lockdown_state = defaultdict(list)
        self.server_tension = defaultdict(int) # Nivel de tensión del servidor (0-100)
        
        # Iniciar tareas de mantenimiento
        self.limpieza_cache.start()
        self.enfriamiento_tension.start()

    def cog_unload(self):
        self.limpieza_cache.cancel()
        self.enfriamiento_tension.cancel()

    # ─── TAREAS EN SEGUNDO PLANO ───
    @tasks.loop(minutes=2)
    async def limpieza_cache(self):
        """Libera memoria RAM limpiando los registros antiguos."""
        ahora = datetime.now(timezone.utc)
        
        # Limpiar Joins
        for gid in list(self.joins_cache.keys()):
            self.joins_cache[gid] = [ts for ts in self.joins_cache[gid] if (ahora - ts).total_seconds() < 60]
            if not self.joins_cache[gid]: del self.joins_cache[gid]
            
        # Limpiar cachés Anti-Nuke
        caches = [self.nuke_channels, self.nuke_roles, self.nuke_bans, self.nuke_kicks, self.nuke_webhooks]
        for cache in caches:
            for gid in list(cache.keys()):
                for uid in list(cache[gid].keys()):
                    cache[gid][uid] = [ts for ts in cache[gid][uid] if (ahora - ts).total_seconds() < 60]
                    if not cache[gid][uid]: del cache[gid][uid]

    @tasks.loop(minutes=15)
    async def enfriamiento_tension(self):
        """Reduce gradualmente el nivel de tensión del servidor si no hay ataques."""
        for gid in list(self.server_tension.keys()):
            if self.server_tension[gid] > 0:
                self.server_tension[gid] = max(0, self.server_tension[gid] - 10)

    # ─── FUNCIONES HEURÍSTICAS INTERNAS ───
    def _obtener_modo(self, guild_id: int) -> str:
        cfg = obtener_guild_config(guild_id)
        return cfg.get("antiraid_mode", "intermedio").lower()

    def _calcular_entropia(self, texto: str) -> float:
        """Calcula la aleatoriedad del nombre (detecta nombres como 'xkqwjehqwe')."""
        if not texto: return 0.0
        probabilidades = [float(texto.count(c)) / len(texto) for c in dict.fromkeys(list(texto))]
        return - sum(p * math.log(p) / math.log(2.0) for p in probabilidades)

    def _calcular_threat_score(self, member: discord.Member) -> dict:
        """
        Motor de Evaluación de Amenazas (Threat Score).
        Devuelve un diccionario con el puntaje total y las razones.
        """
        score = 0
        razones = []
        ahora = datetime.now(timezone.utc)
        
        # 1. Antigüedad de la cuenta
        dias_creacion = (ahora - member.created_at).days
        if dias_creacion < 1:
            score += 60
            razones.append("Cuenta creada hace menos de 24 horas")
        elif dias_creacion < 7:
            score += 30
            razones.append("Cuenta muy reciente (< 7 días)")
        elif dias_creacion < 30:
            score += 10
            
        # 2. Foto de perfil (Avatar)
        if not member.avatar:
            score += 25
            razones.append("Sin foto de perfil (Default Avatar)")
            
        # 3. Análisis del nombre de usuario
        if REGEX_SUSPICIOUS_NAMES.search(member.name):
            score += 80
            razones.append("Nombre de usuario en lista negra (Scam/Spam)")
            
        entropia_nombre = self._calcular_entropia(member.name)
        if entropia_nombre > 3.8: # Nombres muy aleatorios
            score += 20
            razones.append("Nombre de usuario con alta entropía (Posible Bot)")
            
        # 4. Tensión actual del servidor
        if self.server_tension[member.guild.id] > 50:
            score += 20
            razones.append("Servidor bajo alta tensión (Ataque reciente)")

        return {"total": score, "razones": razones}

    # ═════════════════════════════════════════════════════════════════════════════
    #  NÚCLEO ANTI-RAID (CONTROL DE INGRESO Y THREAT SCORING)
    # ═════════════════════════════════════════════════════════════════════════════
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        cfg = obtener_guild_config(guild.id)
        if not cfg.get("antiraid_enabled", True): return

        modo = self._obtener_modo(guild.id)
        ahora = datetime.now(timezone.utc)
        
        # ─── 1. EVALUACIÓN INDIVIDUAL (THREAT SCORE) ───
        threat_data = self._calcular_threat_score(member)
        score = threat_data["total"]
        
        if modo == "hard" and score >= 70:
            # En modo Hardcore, si la cuenta es muy sospechosa, se banea al instante (0ms)
            try:
                await member.ban(reason=f"Anti-Raid (Hard Mode): Threat Score Crítico ({score}/100)")
                self._log_incidente(guild, "🛡️ PREVENCIÓN ACTIVA", f"Cuenta neutralizada antes de ingresar.\n**Sujeto:** {member.mention}\n**Threat Score:** `{score}/100`\n**Motivos:** {', '.join(threat_data['razones'])}", 0xEF4444)
                return # Detenemos la ejecución aquí
            except Exception: pass
            
        elif modo == "intermedio" and score >= 85:
            # En modo intermedio, somos un poco más tolerantes, pero expulsamos si es obvio
            try:
                await member.kick(reason=f"Anti-Raid (Intermedio): Threat Score Alto ({score}/100)")
                self._log_incidente(guild, "⚠️ INGRESO RECHAZADO", f"Cuenta expulsada preventivamente.\n**Sujeto:** {member.mention}\n**Threat Score:** `{score}/100`\n**Motivos:** {', '.join(threat_data['razones'])}", 0xF59E0B)
                return
            except Exception: pass

        # ─── 2. VELOCITY TRACKING (DETECCIÓN DE RÁFAGAS) ───
        ventana_segundos = cfg.get("antiraid_join_seconds", 10)
        limite_ingresos = cfg.get("antiraid_join_limit", 5)
        
        if modo == "hard": limite_ingresos = max(2, limite_ingresos - 2) # Más sensible en Hard

        self.joins_cache[guild.id] = [ts for ts in self.joins_cache[guild.id] if (ahora - ts).total_seconds() < ventana_segundos]
        self.joins_cache[guild.id].append(ahora)
        
        self.recent_joiners[guild.id].append(member)
        if len(self.recent_joiners[guild.id]) > 30: 
            self.recent_joiners[guild.id].pop(0)

        # ¿Hay un Raid en progreso?
        if len(self.joins_cache[guild.id]) >= limite_ingresos:
            self.joins_cache[guild.id].clear()
            self.server_tension[guild.id] = 100 # Tensión al máximo
            atacantes = list(self.recent_joiners[guild.id][-limite_ingresos:])
            await self._ejecutar_contencion_raid(guild, atacantes, modo)

    async def _ejecutar_contencion_raid(self, guild: discord.Guild, atacantes: list, modo: str):
        print(f"[ALERTA RAID] Incursión masiva detectada en {guild.name}. Modo: {modo.upper()}")

        if modo == "pacifico":
            # Solo avisa, no toma acciones destructivas
            self._log_incidente(guild, "🚨 ALERTA DE RAID (MODO PACÍFICO)", f"Se ha detectado una ráfaga de `{len(atacantes)}` ingresos en pocos segundos.\n*El sistema no tomará acciones automáticas debido a la postura táctica actual.*", 0xF59E0B)
            return

        # ─── ACCIONES DE CONTENCIÓN (INTERMEDIO Y HARD) ───
        expulsados = 0
        baneados = 0
        
        # 1. Elevar nivel de verificación del servidor (Defcon 2)
        try: await guild.edit(verification_level=discord.VerificationLevel.highest, reason="Sentinel Anti-Raid: Cuarentena Automática")
        except Exception: pass

        # 2. Pausar invitaciones si es posible (Defcon 1)
        if "COMMUNITY" in guild.features:
            try: await guild.edit(invites_disabled=True, reason="Sentinel Anti-Raid: Bloqueo de Incursión")
            except Exception: pass

        # 3. Neutralizar atacantes
        for m in atacantes:
            try:
                if m.top_role < guild.me.top_role and m.id != guild.owner_id:
                    if modo == "hard":
                        await m.ban(reason="Anti-Raid Sentinel: Cuenta neutralizada por ataque de ráfaga (Hard Mode)")
                        baneados += 1
                    else:
                        await m.kick(reason="Anti-Raid Sentinel: Cuenta expulsada por ataque de ráfaga")
                        expulsados += 1
            except Exception: pass

        # 4. Reporte Forense IA
        prompt = (
            f"Alerta Crítica: Se detectó un RAID en el servidor '{guild.name}'. "
            f"Se neutralizaron {expulsados} cuentas (Kick) y {baneados} cuentas (Ban). "
            f"Redacta un reporte militar formal de 2 líneas informando que el perímetro fue cerrado y asegurado."
        )
        dictamen_ia = await preguntar_ia(prompt)

        accion_txt = f"`{baneados}` Baneos" if modo == "hard" else f"`{expulsados}` Expulsiones"
        
        alerta = (
            f"### 🚨 CONTENCIÓN ANTI-RAID EJECUTADA // PERÍMETRO BLINDADO\n"
            f"✦ ────────────────────────────────────────── ✦\n"
            f"> **Incidente:** Ráfaga anómala de ingresos masivos (Raid).\n"
            f"> **Postura Táctica:** `{modo.upper()}`\n"
            f"> **Contramedida:** {accion_txt} ejecutadas.\n"
            f"> **Defensa Pasiva:** Nivel de verificación elevado al MÁXIMO.\n\n"
            f"**🧠 Dictamen Forense (Cerebras AI):**\n"
            f"> *{dictamen_ia}*\n"
            f"✦ ────────────────────────────────────────── ✦"
        )
        
        cfg = obtener_guild_config(guild.id)
        ch_id = cfg.get("audit_channel") or cfg.get("log_channel")
        if ch_id:
            ch = guild.get_channel(int(ch_id))
            if ch: await ch.send(alerta)

    # ═════════════════════════════════════════════════════════════════════════════
    #  NÚCLEO ANTI-NUKE (PROTECCIÓN DE INFRAESTRUCTURA INTERNA)
    # ═════════════════════════════════════════════════════════════════════════════
    async def _procesar_evento_antinuke(self, guild: discord.Guild, action_type, cache_dict, tipo_accion: str, limite: int):
        cfg = obtener_guild_config(guild.id)
        if not cfg.get("antinuke_enabled", True): return

        modo = self._obtener_modo(guild.id)
        if modo == "pacifico": return # El Anti-Nuke no actúa en modo pacífico para evitar falsos positivos

        ahora = datetime.now(timezone.utc)
        ventana = cfg.get("antinuke_seconds", 10)
        
        if modo == "hard": limite = max(2, limite - 1) # Más estricto en Hard

        async for entry in guild.audit_logs(limit=1, action=action_type):
            responsable = entry.user
            if not responsable or responsable.id == self.bot.user.id or responsable.id == guild.owner_id: return

            cache_dict[guild.id][responsable.id] = [ts for ts in cache_dict[guild.id][responsable.id] if (ahora - ts).total_seconds() < ventana]
            cache_dict[guild.id][responsable.id].append(ahora)

            if len(cache_dict[guild.id][responsable.id]) >= limite:
                cache_dict[guild.id][responsable.id].clear()
                await self._neutralizar_saboteador(guild, responsable, tipo_accion, modo)
            break

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        await self._procesar_evento_antinuke(channel.guild, discord.AuditLogAction.channel_delete, self.nuke_channels, "Eliminación Masiva de Canales", limite=3)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        await self._procesar_evento_antinuke(role.guild, discord.AuditLogAction.role_delete, self.nuke_roles, "Eliminación Masiva de Roles", limite=3)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        await self._procesar_evento_antinuke(guild, discord.AuditLogAction.ban, self.nuke_bans, "Baneos Masivos (Abuso de Poder)", limite=4)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        # Detectar Kicks masivos
        await self._procesar_evento_antinuke(member.guild, discord.AuditLogAction.kick, self.nuke_kicks, "Expulsiones Masivas (Abuso de Poder)", limite=4)

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.abc.GuildChannel):
        # Detectar creación masiva de Webhooks (Vector común para inyectar Spam/Pornografía)
        await self._procesar_evento_antinuke(channel.guild, discord.AuditLogAction.webhook_create, self.nuke_webhooks, "Creación Masiva de Webhooks", limite=3)

    async def _neutralizar_saboteador(self, guild: discord.Guild, usuario: discord.User, accion: str, modo: str):
        miembro = guild.get_member(usuario.id)
        roles_removidos = []
        castigo_extra = "Ninguno"

        if miembro and miembro.top_role < guild.me.top_role:
            # 1. Quitar todos los permisos peligrosos (Strip-Roles)
            roles_peligrosos = [r for r in miembro.roles if r.permissions.administrator or r.permissions.manage_guild or r.permissions.manage_channels or r.permissions.ban_members or r.permissions.manage_webhooks]
            if roles_peligrosos:
                try:
                    await miembro.remove_roles(*roles_peligrosos, reason="Anti-Nuke: Neutralización por sabotaje")
                    roles_removidos = [r.name for r in roles_peligrosos]
                except Exception: pass

            # 2. Castigo adicional en modo Hard
            if modo == "hard":
                try:
                    await miembro.ban(reason="Anti-Nuke (Hard Mode): Sabotaje de Infraestructura")
                    castigo_extra = "Baneo Permanente"
                except Exception: pass

        prompt = (
            f"Alerta Crítica: El administrador '{usuario.name}' ejecutó '{accion}' de forma masiva. "
            f"El sistema Anti-Nuke le revocó los permisos instantáneamente. "
            f"Redacta un reporte de incidente de 2 líneas para el dueño del servidor."
        )
        dictamen_ia = await preguntar_ia(prompt)

        alerta = (
            f"### 🛑 PROTOCOLO ANTI-NUKE // SABOTAJE NEUTRALIZADO\n"
            f"✦ ────────────────────────────────────────── ✦\n"
            f"> **Responsable:** {usuario.mention} (`{usuario.id}`)\n"
            f"> **Infracción Detectada:** `{accion}`\n"
            f"> **Contención Táctica:** Roles revocados: `{', '.join(roles_removidos) if roles_removidos else 'Sin roles modificables'}`.\n"
            f"> **Castigo Adicional:** `{castigo_extra}`\n\n"
            f"**🧠 Dictamen Forense (IA):**\n> *{dictamen_ia}*\n"
            f"✦ ────────────────────────────────────────── ✦"
        )
        
        cfg = obtener_guild_config(guild.id)
        ch_id = cfg.get("audit_channel") or cfg.get("log_channel")
        if ch_id:
            ch = guild.get_channel(int(ch_id))
            if ch: await ch.send(alerta)

    def _log_incidente(self, guild: discord.Guild, titulo: str, descripcion: str, color: int):
        """Función auxiliar para enviar embeds limpios al canal de logs."""
        cfg = obtener_guild_config(guild.id)
        ch_id = cfg.get("audit_channel") or cfg.get("log_channel")
        if not ch_id: return
        
        log_ch = guild.get_channel(int(ch_id))
        if not log_ch: return

        embed = discord.Embed(title=titulo, description=descripcion, color=color, timestamp=datetime.now(timezone.utc))
        embed.set_footer(text="Elixyr Sentinel • Security Operations")
        asyncio.create_task(log_ch.send(embed=embed))

    # ═════════════════════════════════════════════════════════════════════════════
    #  COMANDOS DE CONFIGURACIÓN Y CONTROL
    # ═════════════════════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="antiraid-mode", description="Cambia la postura táctica del Anti-Raid y Anti-Nuke")
    @app_commands.describe(modo="Selecciona el nivel de agresividad defensiva")
    @app_commands.choices(modo=[
        app_commands.Choice(name="🟢 Pacífico (Solo observa y reporta)", value="pacifico"),
        app_commands.Choice(name="🟡 Intermedio (Expulsiones y Cuarentena)", value="intermedio"),
        app_commands.Choice(name="🔴 Hardcore (Baneos instantáneos y Tolerancia Cero)", value="hard")
    ])
    @commands.has_permissions(administrator=True)
    async def antiraid_mode(self, ctx, modo: str):
        await ctx.defer(ephemeral=True)
        actualizar_guild_config(ctx.guild.id, "antiraid_mode", modo)
        
        mensajes = {
            "pacifico": "🟢 **Modo Pacífico Activado:** El Anti-Raid y Anti-Nuke solo observarán y enviarán alertas al Staff. No se expulsará ni se quitarán roles a nadie automáticamente.",
            "intermedio": "🟡 **Modo Intermedio Activado:** Postura estándar. Se expulsará a los raiders, se activará el lockdown automático y se quitarán roles a los saboteadores.",
            "hard": "🔴 **Modo HARDCORE Activado:** Paranoia Total. Cuentas nuevas sin foto serán baneadas al entrar. Los saboteadores serán baneados. Límites de detección reducidos al mínimo."
        }
        await ctx.send(mensajes[modo], ephemeral=True)

    @commands.hybrid_command(name="antiraid", description="Configura el cortafuegos perimetral Anti-Raid")
    @commands.has_permissions(administrator=True)
    async def antiraid(self, ctx, estado: bool, limite_ingresos: int = 5, segundos: int = 10):
        await ctx.defer(ephemeral=True)
        actualizar_guild_config(ctx.guild.id, "antiraid_enabled", estado)
        actualizar_guild_config(ctx.guild.id, "antiraid_join_limit", max(2, min(limite_ingresos, 20)))
        actualizar_guild_config(ctx.guild.id, "antiraid_join_seconds", max(3, min(segundos, 30)))
        await ctx.send(f"🛡️ **Anti-Raid:** {'OPERATIVO 🟢' if estado else 'SUSPENDIDO 🔴'}.", ephemeral=True)

    @commands.hybrid_command(name="antinuke", description="Activa o desactiva la protección anti-sabotaje")
    @commands.has_permissions(administrator=True)
    async def antinuke(self, ctx, estado: bool):
        await ctx.defer(ephemeral=True)
        actualizar_guild_config(ctx.guild.id, "antinuke_enabled", estado)
        await ctx.send(f"🛑 **Anti-Nuke:** {'ACTIVO ⚔️' if estado else 'DESACTIVADO ⚠️'}.", ephemeral=True)

    @commands.hybrid_command(name="threat-scan", description="Escanea a un usuario para calcular su Threat Score (Nivel de Amenaza)")
    @app_commands.describe(usuario="Miembro a escanear")
    @commands.has_permissions(manage_messages=True)
    async def threat_scan(self, ctx, usuario: discord.Member):
        await ctx.defer()
        data = self._calcular_threat_score(usuario)
        score = data["total"]
        razones = "\n".join([f"▸ {r}" for r in data["razones"]]) if data["razones"] else "▸ Ninguna anomalía detectada."
        
        color = 0x10B981 if score < 30 else 0xF59E0B if score < 70 else 0xEF4444
        riesgo = "BAJO" if score < 30 else "MODERADO" if score < 70 else "CRÍTICO"
        
        embed = discord.Embed(title=f"🔍 ESCÁNER BIOMÉTRICO // {usuario.name}", color=color)
        embed.add_field(name="Threat Score", value=f"`{score}/100` (Riesgo {riesgo})", inline=False)
        embed.add_field(name="Factores de Riesgo", value=razones, inline=False)
        embed.set_thumbnail(url=usuario.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="antiraid-status", description="Muestra la telemetría y configuración actual del perímetro")
    @commands.has_permissions(manage_guild=True)
    async def antiraid_status(self, ctx):
        await ctx.defer()
        cfg = obtener_guild_config(ctx.guild.id)
        
        estado_ar = "🟢 Activo" if cfg.get("antiraid_enabled", True) else "🔴 Apagado"
        estado_an = "🟢 Activo" if cfg.get("antinuke_enabled", True) else "🔴 Apagado"
        modo = cfg.get("antiraid_mode", "intermedio").upper()
        
        limite = cfg.get("antiraid_join_limit", 5)
        segundos = cfg.get("antiraid_join_seconds", 10)
        tension = self.server_tension[ctx.guild.id]
        
        panel = (
            f"### 🛡️ TELEMETRÍA PERIMETRAL // DEFCON V5\n"
            f"✦ ────────────────────────────────────────── ✦\n"
            f"> **Postura Táctica:** `{modo}`\n"
            f"> **Escudo Anti-Raid:** {estado_ar} (`{limite}` joins / `{segundos}s`)\n"
            f"> **Escudo Anti-Nuke:** {estado_an} (Protege Canales, Roles, Bans, Kicks, Webhooks)\n"
            f"> **Tensión del Servidor:** `{tension}%` (Aumenta durante ataques)\n"
            f"> **Motores Activos:** `Threat Scoring`, `Velocity Tracking`, `Entropy Analysis`\n"
            f"✦ ────────────────────────────────────────── ✦\n"
            f"-# Usa /antiraid-mode para cambiar la agresividad del sistema."
        )
        await ctx.send(panel)

    @commands.hybrid_command(name="lockdown", description="Botón de Pánico: Bloquea todos los canales públicos")
    @commands.has_permissions(administrator=True)
    async def lockdown(self, ctx, *, motivo: str = "Ataque en progreso"):
        await ctx.defer()
        guild = ctx.guild
        canales_bloqueados = 0
        self.lockdown_state[guild.id].clear()

        for canal in guild.text_channels:
            ow = canal.overwrites_for(guild.default_role)
            if ow.send_messages is not False:
                try:
                    ow.send_messages = False
                    await canal.set_permissions(guild.default_role, overwrite=ow, reason=f"Lockdown: {motivo}")
                    self.lockdown_state[guild.id].append(canal.id)
                    canales_bloqueados += 1
                except Exception: pass

        await ctx.send(f"🔒 **LOCKDOWN PERIMETRAL:** `{canales_bloqueados}` canales asegurados por: *{motivo}*")

    @commands.hybrid_command(name="unlockdown", description="Restaura la comunicación en los canales asegurados")
    @commands.has_permissions(administrator=True)
    async def unlockdown(self, ctx):
        await ctx.defer()
        guild = ctx.guild
        canales_restaurados = 0
        for cid in self.lockdown_state[guild.id]:
            canal = guild.get_channel(cid)
            if canal:
                try:
                    ow = canal.overwrites_for(guild.default_role)
                    ow.send_messages = None
                    await canal.set_permissions(guild.default_role, overwrite=ow, reason="Unlockdown")
                    canales_restaurados += 1
                except Exception: pass

        self.lockdown_state[guild.id].clear()
        await ctx.send(f"🔓 **Perímetro restaurado:** `{canales_restaurados}` canales desbloqueados.")

async def setup(bot):
    await bot.add_cog(AntiRaid(bot))