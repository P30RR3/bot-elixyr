"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR GUARD // PERIMETER DEFENSE & ANTI-SABOTAGE (NEW GEN v6.0)
  Capacidades: Secure by Default, Autonomous 5-Min Briefing,
               Threat Scoring Heurístico, Anti-Nuke y Live-Action Defense
═══════════════════════════════════════════════════════════════════════════════
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils.helpers import obtener_guild_config, actualizar_guild_config, crear_case_async
from utils.ia import preguntar_ia
from utils.ui import barra_progreso, barra_riesgo, formato_editorial, LiveActionController
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import asyncio
import math
import re
import logging

logger = logging.getLogger("ElixyrAntiRaid")

# ═════════════════════════════════════════════════════════════════════════════
#  MOTORES HEURÍSTICOS Y PATRONES DE AMENAZA (0ms)
# ═════════════════════════════════════════════════════════════════════════════
REGEX_SUSPICIOUS_NAMES = re.compile(
    r"(discord\.gg|twitter\.com|twitch\.tv|youtube\.com|free.*nitro|nitro.*free|"
    r"steam.*promo|airdrop|giveaway|crypto|roblox|vbucks|official.*bot)", 
    re.IGNORECASE
)

class AntiRaid(commands.Cog):
    """
    Centinela Perimetral Autónomo.
    Blindaje contra Raids masivos, Sabotaje de Staff (Anti-Nuke) y Perfilado Forense.
    """
    def __init__(self, bot):
        self.bot = bot
        
        # ─── VELOCITY TRACKERS EN RAM ───
        self.joins_cache = defaultdict(list)
        self.recent_joiners = defaultdict(list)
        
        # ─── RASTREADORES ANTI-NUKE ───
        self.nuke_channels = defaultdict(lambda: defaultdict(list))
        self.nuke_roles = defaultdict(lambda: defaultdict(list))
        self.nuke_bans = defaultdict(lambda: defaultdict(list))
        self.nuke_kicks = defaultdict(lambda: defaultdict(list))
        self.nuke_webhooks = defaultdict(lambda: defaultdict(list))
        
        # ─── ESTADOS Y TENSIÓN ───
        self.lockdown_state = defaultdict(list)
        self.server_tension = defaultdict(int)
        
        # Iniciar tareas autónomas de memoria
        self.limpieza_cache.start()
        self.enfriamiento_tension.start()

    def cog_unload(self):
        self.limpieza_cache.cancel()
        self.enfriamiento_tension.cancel()

    # ─── TAREAS DE MANTENIMIENTO EN SEGUNDO PLANO ───
    @tasks.loop(minutes=3)
    async def limpieza_cache(self):
        ahora = datetime.now(timezone.utc)
        for gid in list(self.joins_cache.keys()):
            self.joins_cache[gid] = [ts for ts in self.joins_cache[gid] if (ahora - ts).total_seconds() < 60]
            if not self.joins_cache[gid]:
                del self.joins_cache[gid]
            
        caches = [self.nuke_channels, self.nuke_roles, self.nuke_bans, self.nuke_kicks, self.nuke_webhooks]
        for c in caches:
            for gid in list(c.keys()):
                for uid in list(c[gid].keys()):
                    c[gid][uid] = [ts for ts in c[gid][uid] if (ahora - ts).total_seconds() < 60]
                    if not c[gid][uid]:
                        del c[gid][uid]

    @tasks.loop(minutes=10)
    async def enfriamiento_tension(self):
        for gid in list(self.server_tension.keys()):
            if self.server_tension[gid] > 0:
                self.server_tension[gid] = max(0, self.server_tension[gid] - 15)

    # ═════════════════════════════════════════════════════════════════════════════
    #  AUTO-INFILTRACIÓN: PROTOCOLO AUTÓNOMO & DOSSIER A LOS 5 MINUTOS
    # ═════════════════════════════════════════════════════════════════════════════
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """
        SECURE BY DEFAULT:
        Apenas el bot ingresa, se blinda el perímetro sin esperar comandos humanos.
        """
        logger.info(f"Nuevo perímetro detectado: {guild.name} ({guild.id}). Auto-armando defensas...")

        # 1. Activación inmediata en memoria L1 y Base de Datos
        actualizar_guild_config(guild.id, "antiraid_enabled", True)
        actualizar_guild_config(guild.id, "antinuke_enabled", True)
        actualizar_guild_config(guild.id, "antiraid_mode", "intermedio")
        actualizar_guild_config(guild.id, "automod_enabled", True)
        
        # 2. Despachar informe de bienvenida tras 5 minutos de reconocimiento
        asyncio.create_task(self._cronometro_reconocimiento_5min(guild.id))

    async def _cronometro_reconocimiento_5min(self, guild_id: int):
        """Espera 300 segundos y remite el briefing de ciberseguridad al operador."""
        await asyncio.sleep(300)

        guild = self.bot.get_guild(guild_id)
        if not guild:
            return  # El bot fue expulsado antes de cumplir los 5 minutos

        # Rastrear quién invitó al bot mediante auditoría forense
        operador = None
        if guild.me.guild_permissions.view_audit_log:
            try:
                async for entry in guild.audit_logs(limit=10, action=discord.AuditLogAction.bot_add):
                    if entry.target.id == self.bot.user.id:
                        operador = entry.user
                        break
            except Exception as e:
                logger.warning(f"No se pudo consultar el registro de auditoría en {guild.name}: {e}")

        # Fallback al dueño si el invitador no puede ser determinado
        if not operador:
            operador = guild.owner

        # Generar telemetría en frío
        total_miembros = guild.member_count or len(guild.members)
        bots = len([m for m in guild.members if m.bot])
        canales = len(guild.channels)
        roles = len(guild.roles)
        mfa = "Activo (2FA Forzado)" if guild.mfa_level == 1 else "Inactivo (Riesgo Moderado)"

        dossier = (
            f"```ansi\n"
            f"\u001b[0;36m═══════════════════════════════════════════════════════════════\u001b[0m\n"
            f"\u001b[1;32m       ELIXYR SENTINEL SOC // INFORME DE DESPLIEGUE INICIAL\u001b[0m\n"
            f"\u001b[0;36m═══════════════════════════════════════════════════════════════\u001b[0m\n"
            f" [0;33m[SISTEMA]\u001b[0m Red Asegurada:     \u001b[0;37m{guild.name}\u001b[0m\n"
            f" [0;33m[ESTADO]\u001b[0m  Defensa Perimetral: \u001b[1;32mOPERATIVA (DEFCON 3 - INTERMEDIO)\u001b[0m\n"
            f" [0;33m[MODO]\u001b[0m    AutoMod Heurístico: \u001b[1;32mACTIVO CON SHADOW-FLAGGING\u001b[0m\n"
            f" [0;33m[AUDIT]\u001b[0m   Protección Anti-Nuke:\u001b[1;32mENLACE DIRECTO A ROLES Y CANALES\u001b[0m\n"
            f"```\n"
            f"### 🛡️ PERÍMETRO BLINDADO // CERTIFICADO DE OPERACIONES\n"
            f"> Estimado/a {operador.mention if operador else 'Comandante'}:\n"
            f"> Han transcurrido **5 minutos** desde mi integración a tu infraestructura. "
            f"He completado el reconocimiento preliminar y las defensas se han auto-armado por defecto. "
            f"**Tu servidor ya es inmune a ataques masivos no coordinados y sabotajes internos.**\n\n"
            f"**📊 Radiografía del Entorno Auditado:**\n"
            f"▸ **Población Monitoreada:** `{total_miembros}` miembros (`{bots}` entidades bot)\n"
            f"▸ **Infraestructura:** `{canales}` canales | `{roles}` roles estructurados\n"
            f"▸ **Seguridad de Servidor (2FA):** `{mfa}`\n\n"
            f"**⚔️ Directivas Operativas Recomendadas:**\n"
            f"• `/server-audit` — Ejecuta un pentest completo asistido por Inteligencia Artificial.\n"
            f"• `/terminal` — Abre el panel interactivo DEFCON para regular la agresividad del cortafuegos.\n"
            f"• `/threat-scan` — Realiza un análisis biométrico a cualquier cuenta sospechosa en vivo.\n"
            f"• `/lockdown` — Botón de pánico para congelar todos los canales en 0ms.\n\n"
            f"-# Elixyr Sentinel SOC • Autonomía Táctica Activa • Sin configuraciones requeridas."
        )

        enviado = False
        if operador:
            try:
                await operador.send(dossier)
                enviado = True
                logger.info(f"Dossier de 5 minutos enviado exitosamente a {operador} ({operador.id}).")
            except discord.Forbidden:
                logger.warning(f"Imposible enviar MD a {operador.name}. Canal directo bloqueado.")

        # Fallback de contingencia: si el operador tiene DMs cerrados, se notifica en el canal de auditoría o system
        if not enviado:
            cfg = obtener_guild_config(guild.id)
            canal_target = None
            if cfg.get("audit_channel"):
                canal_target = guild.get_channel(int(cfg["audit_channel"]))
            if not canal_target:
                canal_target = guild.system_channel

            if canal_target and canal_target.permissions_for(guild.me).send_messages:
                try:
                    await canal_target.send(dossier)
                except Exception:
                    pass

    # ─── HEURÍSTICA Y THREAT SCORING ───
    def _calcular_entropia(self, texto: str) -> float:
        if not texto: return 0.0
        probabilidades = [float(texto.count(c)) / len(texto) for c in dict.fromkeys(list(texto))]
        return - sum(p * math.log(p) / math.log(2.0) for p in probabilidades)

    def _calcular_threat_score(self, member: discord.Member) -> dict:
        score = 0
        razones = []
        ahora = datetime.now(timezone.utc)
        
        # 1. Antigüedad de la cuenta
        dias_creacion = (ahora - member.created_at).days
        if dias_creacion < 1:
            score += 65
            razones.append("Cuenta creada hace menos de 24 horas")
        elif dias_creacion < 7:
            score += 35
            razones.append("Cuenta muy reciente (< 7 días)")
        elif dias_creacion < 30:
            score += 15
            
        # 2. Firma visual (Avatar)
        if not member.avatar:
            score += 20
            razones.append("Sin avatar personalizado (Firma de bot desechable)")
            
        # 3. Análisis léxico y de entropía
        if REGEX_SUSPICIOUS_NAMES.search(member.name):
            score += 75
            razones.append("Nombre coincide con lista negra de Spam/Phishing")
            
        if self._calcular_entropia(member.name) > 3.8:
            score += 25
            razones.append("Alta entropía léxica (Posible generador aleatorio de cuentas)")
            
        # 4. Multiplicador de tensión de red
        if self.server_tension[member.guild.id] > 50:
            score += 25
            razones.append("Alerta de infiltración en curso (Tensión de servidor > 50%)")

        return {"total": min(score, 100), "razones": razones}

    # ═════════════════════════════════════════════════════════════════════════════
    #  INTERCEPTOR PERIMETRAL (ANTI-RAID GATEWAY)
    # ═════════════════════════════════════════════════════════════════════════════
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        cfg = obtener_guild_config(guild.id)
        
        # AUTO-DEFENSA: Si por algún motivo no estuviera activo, se auto-activa
        if not cfg.get("antiraid_enabled", True):
            return

        modo = cfg.get("antiraid_mode", "intermedio").lower()
        ahora = datetime.now(timezone.utc)
        
        # 1. Evaluación biométrica individual
        threat_data = self._calcular_threat_score(member)
        score = threat_data["total"]

        # Neutralización preventiva si el bot tiene jerarquía suficiente
        if member.top_role < guild.me.top_role and member.id != guild.owner_id:
            if modo == "hard" and score >= 65:
                try:
                    await member.ban(reason=f"Sentinel Defense (Hardcore): Threat Score Crítico ({score}/100)")
                    await self._registrar_incidente(
                        guild, "🚨 AMENAZA NEUTRALIZADA (0ms)",
                        f"> **Sujeto:** {member.mention} (`{member.id}`)\n"
                        f"> **Threat Score:** `{score}/100`\n"
                        f"> **Factores:** {', '.join(threat_data['razones'])}\n"
                        f"> **Acción:** Baneo Definitivo Inmediato.",
                        0xEF4444
                    )
                    return
                except discord.Forbidden:
                    pass
            elif modo == "intermedio" and score >= 85:
                try:
                    await member.kick(reason=f"Sentinel Defense: Threat Score Inaceptable ({score}/100)")
                    await self._registrar_incidente(
                        guild, "⚠️ ACCESO RECHAZADO",
                        f"> **Sujeto:** {member.mention} (`{member.id}`)\n"
                        f"> **Threat Score:** `{score}/100`\n"
                        f"> **Factores:** {', '.join(threat_data['razones'])}\n"
                        f"> **Acción:** Expulsión Perimetral.",
                        0xF59E0B
                    )
                    return
                except discord.Forbidden:
                    pass

        # 2. Velocity Tracking (Detección de ráfagas coordinadas)
        ventana_sec = cfg.get("antiraid_join_seconds", 10)
        limite_joins = cfg.get("antiraid_join_limit", 5)
        if modo == "hard":
            limite_joins = max(2, limite_joins - 2)

        self.joins_cache[guild.id] = [ts for ts in self.joins_cache[guild.id] if (ahora - ts).total_seconds() < ventana_sec]
        self.joins_cache[guild.id].append(ahora)

        self.recent_joiners[guild.id].append(member)
        if len(self.recent_joiners[guild.id]) > 40:
            self.recent_joiners[guild.id].pop(0)

        # Disparo del protocolo de incursión masiva
        if len(self.joins_cache[guild.id]) >= limite_joins:
            self.joins_cache[guild.id].clear()
            self.server_tension[guild.id] = 100
            sospechosos = list(self.recent_joiners[guild.id][-limite_joins:])
            await self._ejecutar_contencion_masiva(guild, sospechosos, modo)

    async def _ejecutar_contencion_masiva(self, guild: discord.Guild, sospechosos: list, modo: str):
        logger.warning(f"Incursión masiva (RAID) interceptada en {guild.name}. Modo: {modo.upper()}")

        if modo == "pacifico":
            await self._registrar_incidente(
                guild, "🚨 ALERTA ROJA // OLEADA DE INGRESOS",
                f"Ráfaga anómala de `{len(sospechosos)}` cuentas simultáneas detectada.\n"
                f"*Modo Pacífico: El sistema no expulsará a los involucrados de forma automática.*",
                0xF59E0B
            )
            return

        neutralizados = 0
        # Elevar verificación al máximo si hay permisos
        if guild.me.guild_permissions.manage_guild:
            try:
                await guild.edit(verification_level=discord.VerificationLevel.highest, reason="Sentinel Anti-Raid: Cuarentena Automática")
            except Exception:
                pass

        # Despachar neutralizaciones
        for m in sospechosos:
            if m.top_role < guild.me.top_role and m.id != guild.owner_id:
                try:
                    if modo == "hard":
                        await m.ban(reason="Anti-Raid Sentinel: Neutralizado por ataque de ráfaga")
                    else:
                        await m.kick(reason="Anti-Raid Sentinel: Expulsado preventivamente")
                    neutralizados += 1
                except Exception:
                    pass

        # Resumen cognitivo mediante Cerebras AI
        prompt = (
            f"Alerta Crítica: Un RAID fue contenido en el servidor '{guild.name}'. "
            f"Se neutralizaron {neutralizados} atacantes mediante {'baneo' if modo == 'hard' else 'expulsión'}. "
            f"Redacta un veredicto militar frío de 2 líneas informando que el perímetro fue cerrado."
        )
        dictamen_ia = await preguntar_ia(prompt)

        panel = (
            f"### 🚨 ATAQUE MASIVO CONTENIDO // LOCKDOWN PERIMETRAL\n"
            f"✦ ────────────────────────────────────────── ✦\n"
            f"> **Vector de Ataque:** Incursión masiva de bots/cuentas sincronizadas.\n"
            f"> **Postura de Combate:** `DEFCON {modo.upper()}`\n"
            f"> **Cuentas Mitigadas:** `{neutralizados}` atacantes erradicados.\n"
            f"> **Escudo Pasivo:** Nivel de verificación forzado a `MÁXIMO`.\n\n"
            f"**🧠 Dictamen Forense IA:**\n"
            f"> *{dictamen_ia}*\n"
            f"✦ ────────────────────────────────────────── ✦"
        )
        await self._registrar_incidente(guild, "🚨 INCIDENTE CRÍTICO: RAID CONTENIDO", panel, 0xEF4444)

    # ═════════════════════════════════════════════════════════════════════════════
    #  INTERCEPTOR ANTI-NUKE (PROTECCIÓN CONTRA ADMINISTRADORES CORRUPTOS)
    # ═════════════════════════════════════════════════════════════════════════════
    async def _procesar_evento_antinuke(self, guild: discord.Guild, action_type, cache_dict, tipo_accion: str, limite: int):
        cfg = obtener_guild_config(guild.id)
        if not cfg.get("antinuke_enabled", True):
            return

        modo = cfg.get("antiraid_mode", "intermedio").lower()
        if modo == "pacifico":
            return

        if not guild.me.guild_permissions.view_audit_log:
            logger.warning(f"Anti-Nuke sin permiso de Audit Log en {guild.name}.")
            return

        ahora = datetime.now(timezone.utc)
        ventana = cfg.get("antinuke_seconds", 10)
        if modo == "hard":
            limite = max(2, limite - 1)

        try:
            async for entry in guild.audit_logs(limit=1, action=action_type):
                responsable = entry.user
                if not responsable or responsable.id == self.bot.user.id or responsable.id == guild.owner_id:
                    return

                cache_dict[guild.id][responsable.id] = [ts for ts in cache_dict[guild.id][responsable.id] if (ahora - ts).total_seconds() < ventana]
                cache_dict[guild.id][responsable.id].append(ahora)

                if len(cache_dict[guild.id][responsable.id]) >= limite:
                    cache_dict[guild.id][responsable.id].clear()
                    await self._neutralizar_saboteador(guild, responsable, tipo_accion, modo)
                break
        except Exception as e:
            logger.error(f"Fallo en inspección de auditoría Anti-Nuke: {e}")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        await self._procesar_evento_antinuke(channel.guild, discord.AuditLogAction.channel_delete, self.nuke_channels, "Eliminación Masiva de Canales", 3)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        await self._procesar_evento_antinuke(role.guild, discord.AuditLogAction.role_delete, self.nuke_roles, "Eliminación Masiva de Roles", 3)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        await self._procesar_evento_antinuke(guild, discord.AuditLogAction.ban, self.nuke_bans, "Baneos Masivos Sospechosos", 4)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self._procesar_evento_antinuke(member.guild, discord.AuditLogAction.kick, self.nuke_kicks, "Expulsiones Masivas Sospechosas", 4)

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.abc.GuildChannel):
        await self._procesar_evento_antinuke(channel.guild, discord.AuditLogAction.webhook_create, self.nuke_webhooks, "Generación Masiva de Webhooks", 3)

    async def _neutralizar_saboteador(self, guild: discord.Guild, usuario: discord.User, accion: str, modo: str):
        miembro = guild.get_member(usuario.id)
        roles_revocados = []
        accion_final = "Revocación de Permisos"

        if miembro and miembro.top_role < guild.me.top_role:
            # Despojar de privilegios administrativos
            roles_peligrosos = [
                r for r in miembro.roles 
                if r.permissions.administrator or r.permissions.manage_guild or 
                   r.permissions.manage_channels or r.permissions.ban_members or 
                   r.permissions.manage_roles or r.permissions.manage_webhooks
            ]
            if roles_peligrosos:
                try:
                    await miembro.remove_roles(*roles_peligrosos, reason=f"Anti-Nuke: Abuso detectado ({accion})")
                    roles_revocados = [r.name for r in roles_peligrosos]
                except Exception:
                    pass

            if modo == "hard":
                try:
                    await miembro.ban(reason=f"Anti-Nuke (Hard Mode): Sabotaje de Servidor ({accion})")
                    accion_final = "Baneo Permanente y Roles Purgados"
                except Exception:
                    pass

        prompt = (
            f"Alerta Crítica: El usuario '{usuario.name}' cometió '{accion}' masivamente. "
            f"El sistema Anti-Nuke actuó y aplicó: {accion_final}. "
            f"Redacta un informe disciplinario de 2 líneas formal y severo."
        )
        dictamen_ia = await preguntar_ia(prompt)

        panel = (
            f"### 🛑 PROTOCOLO ANTI-NUKE ACTIVADO // SABOTAJE NEUTRALIZADO\n"
            f"✦ ────────────────────────────────────────── ✦\n"
            f"> **Sujeto Hostil:** {usuario.mention} (`{usuario.id}`)\n"
            f"> **Actividad Saboteadora:** `{accion}`\n"
            f"> **Roles Neutralizados:** `{', '.join(roles_revocados) if roles_revocados else 'Ninguno accesible'}`\n"
            f"> **Veredicto Ejecutado:** `{accion_final}`\n\n"
            f"**🧠 Dictamen Forense:**\n"
            f"> *{dictamen_ia}*\n"
            f"✦ ────────────────────────────────────────── ✦"
        )
        await self._registrar_incidente(guild, "🛑 SABOTAJE INTERNO NEUTRALIZADO", panel, 0xEF4444)

    async def _registrar_incidente(self, guild: discord.Guild, titulo: str, descripcion: str, color: int):
        cfg = obtener_guild_config(guild.id)
        ch_id = cfg.get("audit_channel") or cfg.get("log_channel")
        if not ch_id:
            return

        ch = guild.get_channel(int(ch_id))
        if not ch or not ch.permissions_for(guild.me).send_messages:
            return

        embed = discord.Embed(
            title=titulo,
            description=descripcion,
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="Elixyr Sentinel SOC • Protocolo Perimetral")
        try:
            await ch.send(embed=embed)
        except Exception:
            pass

    # ═════════════════════════════════════════════════════════════════════════════
    #  DIRECTIVAS Y COMANDOS TÁCTICOS (LIVE ACTION NEW GEN)
    # ═════════════════════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="threat-scan", description="Análisis biométrico y escaneo de Threat Score en vivo")
    @app_commands.describe(usuario="Entidad a examinar")
    @commands.has_permissions(moderate_members=True)
    async def threat_scan(self, ctx, usuario: discord.Member):
        await ctx.defer()
        
        # Iniciar controlador Live-Action
        live = LiveActionController(ctx, f"Escaneo Biométrico // {usuario.name}", total_pasos=4)
        await live.iniciar()

        await live.actualizar("Extrayendo telemetría de creación e identidad...", exito=True)
        await asyncio.sleep(0.8)

        await live.actualizar("Calculando entropía léxica del identificador...", exito=True)
        await asyncio.sleep(0.8)

        data = self._calcular_threat_score(usuario)
        score = data["total"]

        await live.actualizar("Analizando coincidencia de firmas en listas negras...", exito=True)
        await asyncio.sleep(0.8)

        nivel = "BAJO" if score < 35 else "MODERADO" if score < 70 else "CRÍTICO"
        await live.finalizar(f"Escaneo finalizado. Threat Score resultante: {score}/100 [{nivel}]", error=(score >= 70))

        # Panel final con barras dinámicas New Gen
        razones_txt = "\n".join([f"▸ {r}" for r in data["razones"]]) if data["razones"] else "▸ Sin anomalías detectadas en el perímetro."
        resultado = (
            f"> **Objetivo Auditado:** {usuario.mention} (`{usuario.id}`)\n"
            f"> **Antigüedad:** <t:{int(usuario.created_at.timestamp())}:R>\n"
            f"> **Índice de Amenaza:** {barra_riesgo(int(score / 20))}\n\n"
            f"**Factores de Riesgo Observados:**\n"
            f"{razones_txt}"
        )
        panel = formato_editorial("RESULTADO DE PERITAJE BIOMÉTRICO", resultado, badge=f"SCORE: {score}/100")
        await ctx.channel.send(panel)

    @commands.hybrid_command(name="lockdown", description="🚨 Botón de Pánico: Cierra todos los canales públicos en tiempo real")
    @commands.has_permissions(administrator=True)
    async def lockdown(self, ctx, *, motivo: str = "Ataque perimetral en curso"):
        await ctx.defer()
        guild = ctx.guild
        canales_texto = [c for c in guild.text_channels if c.permissions_for(guild.default_role).send_messages is not False]
        total = len(canales_texto)

        if total == 0:
            return await ctx.send("✦ El servidor ya se encuentra bajo aislamiento preventivo total.")

        live = LiveActionController(ctx, "Protocolo de Aislamiento General (Lockdown)", total_pasos=total)
        await live.iniciar()

        self.lockdown_state[guild.id].clear()
        bloqueados = 0

        for canal in canales_texto:
            try:
                ow = canal.overwrites_for(guild.default_role)
                ow.send_messages = False
                await canal.set_permissions(guild.default_role, overwrite=ow, reason=f"Lockdown por {ctx.author}: {motivo}")
                self.lockdown_state[guild.id].append(canal.id)
                bloqueados += 1
                await live.actualizar(f"Canal #{canal.name} asegurado", exito=True)
            except Exception:
                await live.actualizar(f"Fallo en #{canal.name}", exito=False)

        await live.finalizar(f"Lockdown completado: {bloqueados}/{total} canales públicos sellados.")

    @commands.hybrid_command(name="unlockdown", description="Restaura la transmisión en los canales bloqueados por Lockdown")
    @commands.has_permissions(administrator=True)
    async def unlockdown(self, ctx):
        await ctx.defer()
        guild = ctx.guild
        canales_a_restaurar = self.lockdown_state[guild.id]

        if not canales_a_restaurar:
            return await ctx.send("✦ No existen registros de canales confinados por este sistema.")

        live = LiveActionController(ctx, "Restauración de Red (Unlockdown)", total_pasos=len(canales_a_restaurar))
        await live.iniciar()

        restaurados = 0
        for cid in canales_a_restaurar:
            canal = guild.get_channel(cid)
            if canal:
                try:
                    ow = canal.overwrites_for(guild.default_role)
                    ow.send_messages = None
                    await canal.set_permissions(guild.default_role, overwrite=ow, reason=f"Unlockdown por {ctx.author}")
                    restaurados += 1
                    await live.actualizar(f"Canal #{canal.name} abierto", exito=True)
                except Exception:
                    await live.actualizar(f"Fallo en canal ID {cid}", exito=False)

        self.lockdown_state[guild.id].clear()
        await live.finalizar(f"Restauración finalizada: {restaurados} canales operativos.")

    @commands.hybrid_command(name="antiraid-mode", description="Regula la agresividad táctica del cortafuegos")
    @app_commands.describe(modo="Nivel de defensa táctica")
    @app_commands.choices(modo=[
        app_commands.Choice(name="🟢 Pacífico (Vigilancia pasiva y alertas)", value="pacifico"),
        app_commands.Choice(name="🟡 Intermedio (Expulsión de raiders y cuarentena)", value="intermedio"),
        app_commands.Choice(name="🔴 Hardcore (Baneo 0ms y Tolerancia Cero)", value="hard")
    ])
    @commands.has_permissions(administrator=True)
    async def antiraid_mode(self, ctx, modo: str):
        await ctx.defer(ephemeral=True)
        actualizar_guild_config(ctx.guild.id, "antiraid_mode", modo)
        
        descripciones = {
            "pacifico": "🟢 **DEFCON 5 (Pacífico):** Telemetría pasiva. Se registran incidentes pero no se expulsan cuentas automáticamente.",
            "intermedio": "🟡 **DEFCON 3 (Intermedio - Estándar):** Expulsiones de ráfaga automáticas, cuarentena perimetral y despojo de roles a saboteadores.",
            "hard": "🔴 **DEFCON 1 (Hardcore - Paranoia):** Baneos definitivos en 0ms para perfiles sospechosos y saboteadores internos."
        }
        await ctx.send(descripciones[modo], ephemeral=True)

    @commands.hybrid_command(name="antiraid-status", description="Muestra la telemetría operativa y nivel de tensión perimetral")
    @commands.has_permissions(manage_guild=True)
    async def antiraid_status(self, ctx):
        await ctx.defer()
        cfg = obtener_guild_config(ctx.guild.id)
        
        ar_activo = "🟢 Operativo" if cfg.get("antiraid_enabled", True) else "🔴 Suspendido"
        an_activo = "🟢 Operativo" if cfg.get("antinuke_enabled", True) else "🔴 Suspendido"
        modo = cfg.get("antiraid_mode", "intermedio").upper()
        tension = self.server_tension[ctx.guild.id]
        
        contenido = (
            f"> **Postura Táctica:** `DEFCON {modo}`\n"
            f"> **Escudo Anti-Raid:** {ar_activo}\n"
            f"> **Escudo Anti-Nuke:** {an_activo}\n"
            f"> **Índice de Tensión Perimetral:** `{tension}%`\n"
            f"> **Heurísticas en Vigilancia:** `Shannon Entropy`, `Threat Scoring`, `Velocity Burst Tracker`\n\n"
            f"**Parámetros de Tolerancia:**\n"
            f"▸ Ráfaga crítica: `{cfg.get('antiraid_join_limit', 5)} ingresos` en `{cfg.get('antiraid_join_seconds', 10)}s`\n"
            f"▸ Tolerancia Anti-Nuke: `{cfg.get('antinuke_channel_delete_limit', 3)} borrados` en `{cfg.get('antinuke_seconds', 10)}s`\n\n"
            f"-# El sistema opera de manera autónoma sin requerir activación manual."
        )
        panel = formato_editorial("TELEMETRÍA DEFCON // ESTADO DEL PERÍMETRO", contenido, badge="SENTINEL-v6")
        await ctx.send(panel)


async def setup(bot):
    await bot.add_cog(AntiRaid(bot))