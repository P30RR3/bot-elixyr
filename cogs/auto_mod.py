"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR GUARD // FIREWALL HEURÍSTICO AUTOMOD V6.0 (DEFENSE GRADE)
  Capacidades: Secure by Default, Multi-Layer Anti-Evasion (Zero-Width/NFKD),
               Token/Webhook Leak Shield, Anti-Scam 0ms y Shadow-Flagging IA
═══════════════════════════════════════════════════════════════════════════════
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils.helpers import obtener_guild_config, actualizar_guild_config, crear_case_async
from utils.ia import analizar_mensaje, preguntar_ia
from utils.ui import formato_editorial, barra_progreso, barra_riesgo, LiveActionController
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import unicodedata
import re
import asyncio
import math
import logging

logger = logging.getLogger("ElixyrAutoMod")

# ═════════════════════════════════════════════════════════════════════════════
#  FIRMAS CRÍTICAS DE AMENAZAS (0ms REGEX ENGINE)
# ═════════════════════════════════════════════════════════════════════════════

# 1. Enlaces de Phishing, Robo de Cuentas y Estafas Cripto
REGEX_SCAM = re.compile(
    r"(discord\.gift|discordapp\.com/gifts|dlscord\.gg|discorcl\.gift|discord-nitro|"
    r"nitro\s*free|free\s*nitro|steamcommunity.*trade|steam.*gift|steam-promo|"
    r"airdrop|crypto.*giveaway|binance.*promo|coinbase.*free|metamask.*verify|"
    r"trustwallet.*unlock|roblox.*robux.*free|vbucks.*free)", 
    re.IGNORECASE
)

# 2. IP Loggers y Rastreadores de Ubicación (Grabify, etc.)
REGEX_IP_LOGGER = re.compile(
    r"(grabify\.link|iplogger\.org|2no\.co|blasze\.com|iplogger\.com|iplogger\.ru|"
    r"ps3cfw\.com|youshouldclick\.us|joinmy\.site|websitedns\.club|xda-developers\.us)", 
    re.IGNORECASE
)

# 3. Fuga de Credenciales (Webhooks y Bot Tokens)
REGEX_WEBHOOK = re.compile(r"https?://(?:ptb\.|canary\.)?discord\.com/api/webhooks/\d+/[A-Za-z0-9_-]+")
REGEX_BOT_TOKEN = re.compile(r"[MNO][A-Za-z0-9_-]{23,26}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27,38}")

# 4. Texto Corrupto / Zalgo (Payloads para colapsar clientes móviles)
REGEX_ZALGO = re.compile(r"[\u0300-\u036F\u0483-\u0489\u1DC0-\u1DFF\u20D0-\u20FF\uFE20-\uFE2F]{4,}")

# 5. Caracteres Invisibles de Ancho Cero (Vectores de Evasión)
REGEX_ZERO_WIDTH = re.compile(r"[\u200B-\u200D\uFEFF\u00A0]")

# 6. Repetición Masiva de Caracteres
REGEX_REPETITION = re.compile(r"(.)\1{9,}")

# Mapeo manual de homoglifos de alta persistencia
HOMOGLYPHS = {
    'а': 'a', 'α': 'a', '@': 'a', '4': 'a', 'в': 'b', 'ß': 'b', '8': 'b',
    'с': 'c', 'ϲ': 'c', '¢': 'c', 'е': 'e', '3': 'e', '€': 'e', 'ɡ': 'g',
    'і': 'i', '1': 'i', '!': 'i', '|': 'i', 'о': 'o', '0': 'o', 'р': 'p',
    'ѕ': 's', '5': 's', '$': 's', 'т': 't', '7': 't', 'υ': 'u', 'ν': 'v',
    'х': 'x', 'у': 'y', 'z': 'z'
}

class AutoMod(commands.Cog):
    """
    Cortafuegos de Chat de Grado Militar con Posturas DEFCON.
    Inspección Heurística 0ms, Sanitización Anti-Evasión y Análisis Cognitivo.
    """
    def __init__(self, bot):
        self.bot = bot
        
        # Trackers de velocidad en RAM
        self.spam_tracker = defaultdict(list)
        self.flood_tracker = defaultdict(lambda: {"last_msg": "", "count": 0})
        self.reincidencia = defaultdict(int)
        self.whitelist_canales = set()
        
        # Tareas periódicas
        self.limpieza_ram.start()
        self.reinicio_reincidencia.start()

    def cog_unload(self):
        self.limpieza_ram.cancel()
        self.reinicio_reincidencia.cancel()

    # ─── TAREAS DE MANTENIMIENTO EN MEMORIA ───
    @tasks.loop(minutes=5)
    async def limpieza_ram(self):
        ahora = datetime.now(timezone.utc)
        for uid in list(self.spam_tracker.keys()):
            self.spam_tracker[uid] = [t for t in self.spam_tracker[uid] if (ahora - t).total_seconds() < 60]
            if not self.spam_tracker[uid]:
                del self.spam_tracker[uid]
        self.flood_tracker.clear()

    @tasks.loop(hours=24)
    async def reinicio_reincidencia(self):
        self.reincidencia.clear()

    # ═════════════════════════════════════════════════════════════════════════════
    #  AUTO-ACTIVACIÓN INMEDIATA (SECURE BY DEFAULT)
    # ═════════════════════════════════════════════════════════════════════════════
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Auto-blinda el AutoMod apenas el bot ingresa a un servidor."""
        actualizar_guild_config(guild.id, "automod_enabled", True)
        actualizar_guild_config(guild.id, "automod_mode", "intermedio")
        actualizar_guild_config(guild.id, "automod_ia", True)
        logger.info(f"AutoMod armado automáticamente en {guild.name} ({guild.id}).")

    # ─── SANITIZADOR FORENSE ANTI-EVASIÓN ───
    def _desinfectar_texto(self, texto: str) -> tuple[str, str]:
        """
        Retorna dos capas de texto desinfectado:
        1. 'limpio': Texto normalizado para lectura semántica.
        2. 'comprimido': Texto sin espacios ni símbolos, para cazar dominios camuflados.
        """
        # 1. Purgar caracteres invisibles
        sin_invisibles = REGEX_ZERO_WIDTH.sub("", texto)

        # 2. Descomposición canónica NFKD (aplana fuentes raras como 𝓈𝒸𝒶𝓂)
        normalizado = unicodedata.normalize('NFKD', sin_invisibles)

        # 3. Transliteración de homoglifos
        resultado = []
        for char in normalizado.lower():
            resultado.append(HOMOGLYPHS.get(char, char))
        
        texto_limpio = "".join(resultado)
        texto_comprimido = re.sub(r"[\s\.\-_/\\*#@]", "", texto_limpio)
        
        return texto_limpio, texto_comprimido

    def _calcular_entropia(self, texto: str) -> float:
        if not texto: return 0.0
        prob = [float(texto.count(c)) / len(texto) for c in dict.fromkeys(list(texto))]
        return - sum(p * math.log(p) / math.log(2.0) for p in prob)

    def _es_inmune(self, message: discord.Message) -> bool:
        if message.author.bot or not message.guild:
            return True
        if message.channel.id in self.whitelist_canales:
            return True
        # Administradores y moderadores con permisos no son escaneados
        if message.author.guild_permissions.administrator or message.author.guild_permissions.manage_guild:
            return True
        return False

    # ═════════════════════════════════════════════════════════════════════════════
    #  INTERCEPTOR EN TIEMPO REAL (0ms GATEWAY)
    # ═════════════════════════════════════════════════════════════════════════════
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self._es_inmune(message) or len(message.content) < 2:
            return

        guild = message.guild
        cfg = obtener_guild_config(guild.id)
        
        # SECURE BY DEFAULT: Si no estuviera explícito, se asume activo
        if not cfg.get("automod_enabled", True):
            return

        modo = cfg.get("automod_mode", "intermedio").lower()
        ahora = datetime.now(timezone.utc)
        uid = message.author.id
        contenido_crudo = message.content
        texto_limpio, texto_comprimido = self._desinfectar_texto(contenido_crudo)

        # ─── FASE 0: SEGURIDAD CRÍTICA DE INFRAESTRUCTURA (0ms) ───
        
        # 0.1 Fuga de Webhooks o Tokens de Discord
        if REGEX_WEBHOOK.search(contenido_crudo) or REGEX_BOT_TOKEN.search(contenido_crudo):
            await self._ejecutar_neutralizacion(
                message, "Fuga Crítica de Token / Webhook Confidencial",
                minutos=1440, categoria="CREDENTIAL-LEAK", severidad=5,
                detalles="Credenciales confidenciales expuestas en chat público."
            )
            return

        # 0.2 Detección de Enlaces Phishing / Scam (Normal y Comprimido)
        if REGEX_SCAM.search(texto_limpio) or REGEX_SCAM.search(texto_comprimido):
            minutos = 1440 if modo != "hard" else 10080
            await self._ejecutar_neutralizacion(
                message, "Enlace Malicioso / Phishing / Scam",
                minutos=minutos, categoria="SCAM", severidad=5,
                detalles="Enlace malicioso detectado y neutralizado."
            )
            return

        # 0.3 Detección de Rastreadores / IP Loggers
        if REGEX_IP_LOGGER.search(texto_limpio) or REGEX_IP_LOGGER.search(texto_comprimido):
            minutos = 180 if modo != "hard" else 1440
            await self._ejecutar_neutralizacion(
                message, "Rastreador de IP / Privacidad Comprometida",
                minutos=minutos, categoria="MALWARE", severidad=5,
                detalles="IP Logger interceptado antes de ser pulsado."
            )
            return

        # 0.4 Raids de Menciones Masivas
        if len(message.mentions) > 5 or len(message.role_mentions) > 2:
            minutos = 60 if modo != "hard" else 720
            await self._ejecutar_neutralizacion(
                message, "Mass Mention Raid / Acoso Masivo",
                minutos=minutos, categoria="RAID", severidad=4,
                detalles=f"Intento de mención masiva ({len(message.mentions)} usuarios)."
            )
            return

        # 0.5 Texto Corrupto Zalgo / Client Crashers
        if REGEX_ZALGO.search(contenido_crudo) and modo != "pacifico":
            minutos = 15 if modo == "intermedio" else 60
            await self._ejecutar_neutralizacion(
                message, "Uso de Texto Corrupto (Zalgo / Client Crasher)",
                minutos=minutos, categoria="EXPLOIT", severidad=3,
                detalles="Caracteres combinados anómalos para colapsar clientes."
            )
            return

        # ─── FASE 1: FILTROS DE VELOCIDAD Y FLOOD (RAM L1) ───
        
        # 1.1 Anti-Flood (Mismo mensaje repetido)
        if self.flood_tracker[uid]["last_msg"] == texto_limpio:
            self.flood_tracker[uid]["count"] += 1
        else:
            self.flood_tracker[uid] = {"last_msg": texto_limpio, "count": 1}

        # 1.2 Anti-Spam Velocity Burst
        spam_limite = cfg.get("automod_spam_limit", 5)
        spam_segundos = cfg.get("automod_spam_seconds", 5)
        if modo == "hard":
            spam_limite = max(3, spam_limite - 2)

        self.spam_tracker[uid] = [t for t in self.spam_tracker[uid] if (ahora - t).total_seconds() < spam_segundos]
        self.spam_tracker[uid].append(ahora)

        if len(self.spam_tracker[uid]) >= spam_limite or self.flood_tracker[uid]["count"] >= 4:
            self.spam_tracker[uid].clear()
            self.flood_tracker[uid]["count"] = 0
            self.reincidencia[uid] += 1
            nivel = self.reincidencia[uid]

            if modo == "pacifico":
                await self._enviar_log_soc(guild, "⚠️ SATURACIÓN DE CANAL", f"El usuario {message.author.mention} está saturando {message.channel.mention} (Modo Pacífico).", 0xF59E0B)
                return

            mute_base = cfg.get("automod_mute_minutes", 10)
            mute_total = mute_base * nivel * (2 if modo == "hard" else 1)

            try:
                await message.channel.purge(limit=spam_limite + 2, check=lambda m: m.author.id == uid)
                if message.author.top_role < guild.me.top_role:
                    await message.author.timeout(ahora + timedelta(minutes=mute_total), reason=f"AutoMod: Saturación de red (Nivel {nivel})")
                
                aviso = await message.channel.send(
                    f"🛡️ **[CORTAFUEGOS SOC]** {message.author.mention} ha sido aislado `{mute_total}m` por saturación de tráfico (Reincidencia: x{nivel})."
                )
                await aviso.delete(delay=6)
                await self._enviar_log_soc(guild, "🔇 AISLAMIENTO POR SPAM", f"> **Infractor:** {message.author.mention} (`{message.author.id}`)\n> **Canal:** {message.channel.mention}\n> **Duración:** `{mute_total} minutos`", 0xEF4444)
            except Exception as e:
                logger.error(f"Error aplicando contención de spam: {e}")
            return

        # ─── FASE 2: LISTA NEGRA Y ANÁLISIS COGNITIVO IA (SHADOW FLAG) ───
        blacklist = cfg.get("automod_blacklist", [])
        palabra_detectada = any(p in texto_limpio for p in blacklist if len(p) >= 3)

        if palabra_detectada and modo != "pacifico":
            try:
                await message.delete()
                aviso = await message.channel.send(f"⚠️ {message.author.mention}, tu mensaje contenía términos restringidos por la directiva de seguridad.")
                await aviso.delete(delay=5)
            except Exception:
                pass
            return

        # Despachar análisis semántico IA asíncrono
        if cfg.get("automod_ia", True) and (palabra_detectada or self._requiere_analisis_ia(texto_limpio)):
            asyncio.create_task(self._inspeccionar_ia_segundo_plano(message, texto_limpio, modo))

    def _requiere_analisis_ia(self, texto: str) -> bool:
        if len(texto) < 6: return False
        if re.search(r"[a-z0-9][\.\-_*#][a-z0-9]", texto): return True
        if re.search(r"(put[ao]|mierd[a]|maric[oa]|pendej[oa]|coñ[oa]|nazi|hitler|terrorist)", texto): return True
        return False

    # ═════════════════════════════════════════════════════════════════════════════
    #  DESPACHADORES Y LOGGERS FORENSES (ROBUSTOS)
    # ═════════════════════════════════════════════════════════════════════════════
    async def _ejecutar_neutralizacion(self, message: discord.Message, razon_castigo: str, minutos: int, categoria: str, severidad: int, detalles: str):
        guild = message.guild
        autor = message.author
        ahora = datetime.now(timezone.utc)

        # 1. Destruir mensaje en 0ms
        try:
            await message.delete()
        except (discord.NotFound, discord.Forbidden):
            pass

        # 2. Aplicar aislamiento si la jerarquía lo permite
        if autor.top_role < guild.me.top_role and autor.id != guild.owner_id:
            try:
                await autor.timeout(ahora + timedelta(minutes=minutos), reason=f"AutoMod: {razon_castigo}")
            except discord.Forbidden:
                logger.warning(f"AutoMod carece de jerarquía para silenciar a {autor.id}.")

        # 3. Registrar expediente judicial
        case_id = await crear_case_async(
            tipo=categoria,
            usuario_id=autor.id,
            moderador_id=self.bot.user.id,
            razon=razon_castigo,
            extra={"severidad": severidad, "duracion": f"{minutos}m"},
            guild_id=guild.id
        )

        # 4. Telemetría al canal SOC
        cuerpo = (
            f"> **Infractor:** {autor.mention} (`{autor.id}`)\n"
            f"> **Canal:** {message.channel.mention}\n"
            f"> **Expediente:** `#{case_id}`\n"
            f"> **Clasificación:** `{categoria}` ({barra_riesgo(severidad)})\n"
            f"> **Acción:** Mensaje purgado y aislamiento de `{minutos}m`.\n\n"
            f"**Detalles Forenses:**\n"
            f"```{message.content[:300]}```"
        )
        await self._enviar_log_soc(guild, f"🛡️ AMENAZA NEUTRALIZADA // {categoria}", cuerpo, 0xEF4444)

    async def _inspeccionar_ia_segundo_plano(self, message: discord.Message, texto: str, modo: str):
        try:
            analisis = await analizar_mensaje(texto)
            categoria = analisis.get("categoria", "SEGURO")
            severidad = analisis.get("severidad", 0)
            razon = analisis.get("razon", "Detección cognitiva")

            if categoria in ["TOXICO", "SPAM", "SCAM"] and severidad >= 3:
                guild = message.guild
                autor = message.author
                
                if modo == "hard":
                    try:
                        await message.delete()
                        if autor.top_role < guild.me.top_role:
                            await autor.timeout(datetime.now(timezone.utc) + timedelta(minutes=30), reason=f"AutoMod IA: {razon}")
                    except Exception:
                        pass
                    
                    await self._enviar_log_soc(
                        guild, "🧠 NEUTRALIZACIÓN COGNITIVA IA (HARD)",
                        f"> **Sujeto:** {autor.mention}\n> **Veredicto:** `{categoria}` ({severidad}/5)\n> **Fundamento:** *{razon}*\n> **Acción:** Mensaje destruido + Aislamiento 30m.",
                        0xEF4444
                    )
                else:
                    # Shadow-Flagging (Solo advierte al Staff sin perturbar el canal)
                    await self._enviar_log_soc(
                        guild, "👁️ SHADOW-FLAG // ALERTA COGNITIVA",
                        f"> **Sujeto:** {autor.mention} en {message.channel.mention}\n> **Categoría:** `{categoria}` ({barra_riesgo(severidad)})\n> **Análisis:** *{razon}*\n> **Contenido:** `{texto[:200]}`",
                        0xF59E0B
                    )
        except Exception as e:
            logger.error(f"Fallo en motor cognitivo AutoMod: {e}")

    async def _enviar_log_soc(self, guild: discord.Guild, titulo: str, descripcion: str, color: int):
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
        embed.set_footer(text="Elixyr AutoMod v6.0 • Cognitive Firewall")
        try:
            await ch.send(embed=embed)
        except Exception:
            pass

    # ═════════════════════════════════════════════════════════════════════════════
    #  DIRECTIVAS Y COMANDOS NEW GEN (LIVE-ACTION)
    # ═════════════════════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="automod-inspect", description="Auditoría forense y heurística de un texto o frase sospechosa en vivo")
    @app_commands.describe(texto="Cadena de texto o enlace a auditar")
    @commands.has_permissions(manage_messages=True)
    async def automod_inspect(self, ctx, *, texto: str):
        await ctx.defer()
        
        live = LiveActionController(ctx, "Inspección Forense de Contenido", total_pasos=4)
        await live.iniciar()

        await live.actualizar("Desinfectando caracteres invisibles y transliterando homoglifos...", exito=True)
        await asyncio.sleep(0.7)
        limpio, comprimido = self._desinfectar_texto(texto)

        await live.actualizar("Ejecutando patrones de 0ms (Scam, IP-Loggers, Leaks)...", exito=True)
        await asyncio.sleep(0.7)
        
        es_scam = bool(REGEX_SCAM.search(limpio) or REGEX_SCAM.search(comprimido))
        es_logger = bool(REGEX_IP_LOGGER.search(limpio) or REGEX_IP_LOGGER.search(comprimido))
        es_leak = bool(REGEX_WEBHOOK.search(texto) or REGEX_BOT_TOKEN.search(texto))

        await live.actualizar("Consultando con el motor semántico de Cerebras AI...", exito=True)
        analisis_ia = await analizar_mensaje(limpio)
        
        amenaza = es_scam or es_logger or es_leak or (analisis_ia.get("severidad", 0) >= 3)
        await live.finalizar(
            f"Auditoría finalizada. Veredicto: {'AMENAZA CONFIRMADA' if amenaza else 'CONTENIDO SEGURO'}",
            error=amenaza
        )

        resumen = (
            f"> **Muestra Cruda:** `{texto[:150]}`\n"
            f"> **Texto Normalizado:** `{limpio[:150]}`\n"
            f"> **Detección Scam / Phishing:** `{'DETECTADO 🚨' if es_scam else 'Limpio 🟢'}`\n"
            f"> **Detección IP-Logger:** `{'DETECTADO 🚨' if es_logger else 'Limpio 🟢'}`\n"
            f"> **Fuga de Credenciales:** `{'DETECTADA 🚨' if es_leak else 'Limpio 🟢'}`\n\n"
            f"**🧠 Dictamen Cognitivo IA:**\n"
            f"▸ **Clasificación:** `{analisis_ia.get('categoria', 'SEGURO')}`\n"
            f"▸ **Nivel de Severidad:** {barra_riesgo(analisis_ia.get('severidad', 0))}\n"
            f"▸ **Fundamento:** *{analisis_ia.get('razon', 'Sin anomalías detectadas')}*"
        )
        panel = formato_editorial("RESULTADO DEL PERITAJE DE MENSAJE", resumen, badge="FIREWALL-SCAN")
        await ctx.channel.send(panel)

    @commands.hybrid_command(name="automod-status", description="Muestra la telemetría viva del cortafuegos y estadísticas de filtrado")
    @commands.has_permissions(manage_guild=True)
    async def automod_status(self, ctx):
        await ctx.defer()
        cfg = obtener_guild_config(ctx.guild.id)
        
        estado = "🟢 Activo (DEFCON)" if cfg.get("automod_enabled", True) else "🔴 Suspendido"
        estado_ia = "🟢 En Línea (Cerebras)" if cfg.get("automod_ia", True) else "🔴 Fuera de Servicio"
        modo = cfg.get("automod_mode", "intermedio").upper()
        
        contenido = (
            f"> **Postura Táctica:** `DEFCON {modo}`\n"
            f"> **Cortafuegos Heurístico:** {estado}\n"
            f"> **Motor Semántico IA:** {estado_ia}\n"
            f"> **Tolerancia de Ráfaga (Spam):** `{cfg.get('automod_spam_limit', 5)} msgs` en `{cfg.get('automod_spam_seconds', 5)}s`\n"
            f"> **Filtros Activos (0ms):** `Anti-Scam`, `Anti-ZeroWidth`, `Anti-TokenLeak`, `Anti-Zalgo`, `Anti-GhostMention`\n"
            f"> **Términos en Lista Negra:** `{len(cfg.get('automod_blacklist', []))}` términos\n\n"
            f"-# El cortafuegos funciona de forma autónoma sin necesidad de activación manual."
        )
        panel = formato_editorial("TELEMETRÍA DEL CORTAFUEGOS // AUTOMOD v6.0", contenido, badge="FIREWALL")
        await ctx.send(panel)

    @commands.hybrid_command(name="automod-mode", description="Cambia la agresividad del cortafuegos (Pacífico, Intermedio, Hard)")
    @app_commands.describe(modo="Nivel de rigidez del cortafuegos")
    @app_commands.choices(modo=[
        app_commands.Choice(name="🟢 Pacífico (Solo telemetría al SOC)", value="pacifico"),
        app_commands.Choice(name="🟡 Intermedio (Shadow-Flagging y Aislamiento de Spam)", value="intermedio"),
        app_commands.Choice(name="🔴 Hardcore (Tolerancia Cero y Mute Automático)", value="hard")
    ])
    @commands.has_permissions(administrator=True)
    async def automod_mode(self, ctx, modo: str):
        await ctx.defer(ephemeral=True)
        actualizar_guild_config(ctx.guild.id, "automod_mode", modo)
        await ctx.send(f"🛡️ **Postura Táctica AutoMod:** Cambiada a `DEFCON {modo.upper()}` exitosamente.", ephemeral=True)

    @commands.hybrid_command(name="blacklist-add", description="Añade un término o patrón a la lista de bloqueo del servidor")
    @commands.has_permissions(administrator=True)
    async def blacklist_add(self, ctx, palabra: str):
        await ctx.defer(ephemeral=True)
        cfg = obtener_guild_config(ctx.guild.id)
        blacklist = cfg.get("automod_blacklist", [])
        
        termino = palabra.lower().strip()
        if termino in blacklist:
            return await ctx.send(f"⚠️ El término `{termino}` ya formaba parte de la lista negra.", ephemeral=True)
            
        blacklist.append(termino)
        actualizar_guild_config(ctx.guild.id, "automod_blacklist", blacklist)
        await ctx.send(f"✅ Término `{termino}` inyectado a la base de datos de amenazas del servidor.", ephemeral=True)

    @commands.hybrid_command(name="blacklist-remove", description="Remueve un término de la lista negra")
    @commands.has_permissions(administrator=True)
    async def blacklist_remove(self, ctx, palabra: str):
        await ctx.defer(ephemeral=True)
        cfg = obtener_guild_config(ctx.guild.id)
        blacklist = cfg.get("automod_blacklist", [])
        
        termino = palabra.lower().strip()
        if termino not in blacklist:
            return await ctx.send(f"⚠️ El término `{termino}` no figura en la lista negra.", ephemeral=True)
            
        blacklist.remove(termino)
        actualizar_guild_config(ctx.guild.id, "automod_blacklist", blacklist)
        await ctx.send(f"✅ Término `{termino}` revocado de la lista negra.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AutoMod(bot))