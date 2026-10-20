import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils.helpers import obtener_guild_config, actualizar_guild_config, crear_case
from utils.ia import analizar_mensaje
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import re
import asyncio
import math

# ═════════════════════════════════════════════════════════════════════════════
#  BASE DE DATOS DE AMENAZAS Y MOTORES DE EXPRESIÓN REGULAR (0ms)
# ═════════════════════════════════════════════════════════════════════════════

# 1. Enlaces de Phishing, Robo de Cuentas y Estafas Cripto
REGEX_SCAM = re.compile(
    r"(discord\.gift|nitro\s*free|free\s*nitro|steamcommunity.*trade|steam.*gift|"
    r"airdrop|t\.me/|crypto.*giveaway|binance.*promo|coinbase.*free|metamask.*verify|"
    r"trustwallet.*unlock|roblox.*robux.*free|vbucks.*free)", 
    re.IGNORECASE
)

# 2. IP Loggers y Rastreadores de Ubicación (Grabify, etc.)
REGEX_IP_LOGGER = re.compile(
    r"(grabify\.link|iplogger\.org|2no\.co|blasze\.com|iplogger\.com|iplogger\.ru|"
    r"ps3cfw\.com|youshouldclick\.us|joinmy\.site|websitedns\.club|xda-developers\.us)", 
    re.IGNORECASE
)

# 3. Acortadores de Enlaces (Frecuentemente usados para ocultar malware)
REGEX_SHORTENERS = re.compile(
    r"(bit\.ly|tinyurl\.com|t\.co|goo\.gl|is\.gd|buff\.ly|adf\.ly|shorte\.st|cutt\.ly)", 
    re.IGNORECASE
)

# 4. Texto Corrupto / Zalgo (Crashea clientes de Discord en móviles)
REGEX_ZALGO = re.compile(
    r"[\u0300-\u036F\u0483-\u0489\u1DC0-\u1DFF\u20D0-\u20FF\uFE20-\uFE2F]{4,}"
)

# 5. Repetición masiva de caracteres (ej: hooooooooolaaaaaaa)
REGEX_REPETITION = re.compile(r"(.)\1{8,}")

# 6. Diccionario de Homoglifos (Letras cirílicas/griegas usadas para evadir filtros)
HOMOGLYPH_MAP = {
    'а': 'a', 'A': 'a', 'α': 'a', '@': 'a', '4': 'a',
    'В': 'b', 'Β': 'b', 'ß': 'b', '8': 'b',
    'с': 'c', 'С': 'c', 'ϲ': 'c', '¢': 'c', '(': 'c',
    'ԁ': 'd', 'ⅾ': 'd',
    'е': 'e', 'Е': 'e', 'Ε': 'e', '3': 'e', '€': 'e',
    'ɡ': 'g', 'ց': 'g', '9': 'g',
    'һ': 'h', 'Η': 'h', '#': 'h',
    'і': 'i', 'І': 'i', 'Ι': 'i', '1': 'i', '!': 'i', '|': 'i',
    'ј': 'j', 'Ј': 'j',
    'κ': 'k', 'Κ': 'k',
    'ӏ': 'l', '1': 'l', 'I': 'l',
    'м': 'm', 'Μ': 'm',
    'ո': 'n', 'Ν': 'n',
    'о': 'o', 'О': 'o', 'Ο': 'o', '0': 'o',
    'р': 'p', 'Р': 'p', 'Ρ': 'p',
    'ԛ': 'q',
    'г': 'r', 'Г': 'r',
    'ѕ': 's', 'Ѕ': 's', '5': 's', '$': 's',
    'т': 't', 'Т': 't', 'Τ': 't', '7': 't',
    'υ': 'u', 'υ': 'u', 'ν': 'u',
    'ν': 'v', 'Ѵ': 'v',
    'ԝ': 'w', 'Ԝ': 'w',
    'х': 'x', 'Х': 'x', 'Χ': 'x',
    'у': 'y', 'У': 'y', 'Υ': 'y',
    'z': 'z', 'Ζ': 'z', '2': 'z'
}


# ═════════════════════════════════════════════════════════════════════════════
#  CLASE PRINCIPAL DEL CORTAFUEGOS (AUTOMOD V5)
# ═════════════════════════════════════════════════════════════════════════════
class AutoMod(commands.Cog):
    """
    Firewall de Chat de Grado Militar con Posturas Tácticas (Pacífico, Intermedio, Hard).
    Implementa Shadow Flagging, Anti-Spam, Anti-Zalgo, Cálculo de Entropía 
    y Análisis Semántico Asíncrono con Cerebras AI.
    """
    def __init__(self, bot):
        self.bot = bot
        
        # Cachés de memoria RAM para Velocity Tracking
        self.spam_tracker = defaultdict(list)
        self.flood_tracker = defaultdict(lambda: {"last_msg": "", "count": 0})
        self.infraction_escalation = defaultdict(int) # Memoria de reincidencia
        
        # Whitelists en memoria (Canales donde el automod es más flexible)
        self.whitelist_channels = set()
        
        # Iniciar tareas en segundo plano
        self.limpieza_cache.start()
        self.telemetria_interna.start()

    def cog_unload(self):
        """Limpieza segura al apagar el módulo."""
        self.limpieza_cache.cancel()
        self.telemetria_interna.cancel()

    # ─── TAREAS EN SEGUNDO PLANO ───
    @tasks.loop(minutes=5)
    async def limpieza_cache(self):
        """Libera memoria RAM limpiando los trackers antiguos para evitar fugas de memoria."""
        ahora = datetime.now(timezone.utc)
        
        # Limpiar Spam Tracker
        for uid in list(self.spam_tracker.keys()):
            self.spam_tracker[uid] = [t for t in self.spam_tracker[uid] if (ahora - t).total_seconds() < 60]
            if not self.spam_tracker[uid]:
                del self.spam_tracker[uid]
                
        # Limpiar Flood Tracker
        self.flood_tracker.clear()

    @tasks.loop(hours=24)
    async def telemetria_interna(self):
        """Reinicia el nivel de escalada de infracciones cada 24 horas."""
        self.infraction_escalation.clear()

    # ─── FUNCIONES HEURÍSTICAS INTERNAS ───
    def _limpiar_homoglifos(self, texto: str) -> str:
        """Traduce caracteres extraños a letras latinas normales para evitar evasión."""
        texto_limpio = ""
        for char in texto:
            texto_limpio += HOMOGLYPH_MAP.get(char, char)
        return texto_limpio.lower()

    def _calcular_entropia(self, texto: str) -> float:
        """
        Calcula la entropía de Shannon del texto.
        Útil para detectar aporreos de teclado (ej: 'asdkjhasdkjh') o cadenas generadas por bots.
        """
        if not texto:
            return 0.0
        probabilidades = [float(texto.count(c)) / len(texto) for c in dict.fromkeys(list(texto))]
        entropia = - sum(p * math.log(p) / math.log(2.0) for p in probabilidades)
        return entropia

    def _requiere_analisis_ia(self, texto: str, blacklist: list) -> bool:
        """
        FAST-PATH: Filtro previo de 0ms. 
        Solo despierta a la IA si hay señales de evasión, toxicidad o palabras clave.
        """
        texto_lower = self._limpiar_homoglifos(texto)
        
        # 1. Coincidencia con la lista negra del servidor
        if any(p in texto_lower for p in blacklist if len(p) >= 3): 
            return True
            
        # 2. Intentos de evasión de filtros (ej: p.u.t.o, m4ld!t0, p_u_t_a)
        if re.search(r"[a-z0-9][\.\-_*#][a-z0-9]", texto_lower): 
            return True
            
        # 3. Insultos comunes camuflados
        if re.search(r"(put[ao]|mierd[a]|maric[oa]|pendej[oa]|coñ[oa])", texto_lower):
            return True
            
        return False

    def _es_bypass_valido(self, message: discord.Message) -> bool:
        """Verifica si el usuario o canal está exento de las reglas del AutoMod."""
        if message.author.bot:
            return True
        if message.channel.id in self.whitelist_channels:
            return True
        if message.author.guild_permissions.administrator or message.author.guild_permissions.manage_messages:
            return True
        return False

    def _obtener_modo(self, guild_id: int) -> str:
        """Obtiene la postura táctica actual: 'pacifico', 'intermedio', 'hard'."""
        cfg = obtener_guild_config(guild_id)
        return cfg.get("automod_mode", "intermedio").lower()

    # ═════════════════════════════════════════════════════════════════════════════
    #  NÚCLEO DEL FIREWALL: INTERCEPTOR DE MENSAJES
    # ═════════════════════════════════════════════════════════════════════════════
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 1. Verificaciones iniciales de seguridad
        if not message.guild or len(message.content) < 2:
            return

        cfg = obtener_guild_config(message.guild.id)
        if not cfg.get("automod_enabled", True):
            return

        if self._es_bypass_valido(message):
            return

        ahora = datetime.now(timezone.utc)
        uid = message.author.id
        contenido = message.content
        modo = self._obtener_modo(message.guild.id)

        # ─── FASE 1: FILTROS DE AMENAZA CRÍTICA (0ms) ───
        # Estos filtros actúan sin importar el modo, porque son amenazas a la infraestructura.
        
        # 1.1. Anti-Mass-Mention (Prevención de Raids de Menciones)
        if len(message.mentions) > 6 or len(message.role_mentions) > 3:
            minutos = 60 if modo != "hard" else 1440
            await self._ejecutar_sancion(message, "Mass Mention (Posible Raid)", minutos, "RAID", 5, "Menciones masivas detectadas", borrado=True)
            return

        # 1.2. Anti-IP-Logger (Protección de Privacidad)
        if REGEX_IP_LOGGER.search(contenido):
            minutos = 120 if modo != "hard" else 1440
            await self._ejecutar_sancion(message, "IP Logger / Rastreador", minutos, "MALWARE", 5, "Enlace de rastreo de IP detectado", borrado=True)
            return

        # 1.3. Anti-Scam y Phishing (Protección de Cuentas)
        if REGEX_SCAM.search(contenido):
            minutos = 1440 if modo != "hard" else 10080 # 1 semana en hard
            await self._ejecutar_sancion(message, "Enlace malicioso / Scam", minutos, "SCAM", 5, "Enlace de Phishing/Scam detectado", borrado=True)
            return

        # 1.4. Anti-Zalgo / Texto Corrupto
        if REGEX_ZALGO.search(contenido):
            if modo != "pacifico":
                minutos = 15 if modo == "intermedio" else 60
                await self._ejecutar_sancion(message, "Uso de texto Zalgo/Corrupto", minutos, "SPAM", 3, "Texto Zalgo detectado", borrado=True)
                return

        # ─── FASE 2: FILTROS DE COMPORTAMIENTO Y VELOCIDAD ───

        # 2.1. Anti-Wall of Text / Entropía Anormal
        if len(contenido) > 800 and modo != "pacifico":
            entropia = self._calcular_entropia(contenido)
            if entropia < 2.5 or REGEX_REPETITION.search(contenido):
                minutos = 10 if modo == "intermedio" else 60
                await self._ejecutar_sancion(message, "Wall of Text / Spam de caracteres", minutos, "SPAM", 3, "Texto repetitivo o aporreo de teclado", borrado=True)
                return

        # 2.2. Anti-Flood (Mensajes idénticos repetidos)
        if self.flood_tracker[uid]["last_msg"] == contenido.lower():
            self.flood_tracker[uid]["count"] += 1
        else:
            self.flood_tracker[uid] = {"last_msg": contenido.lower(), "count": 1}

        # 2.3. Anti-Spam (Velocidad de mensajes)
        spam_limite = cfg.get("automod_spam_limit", 5)
        spam_segundos = cfg.get("automod_spam_seconds", 5)
        
        # En modo HARD, el límite de spam es más estricto
        if modo == "hard":
            spam_limite = max(3, spam_limite - 2)

        self.spam_tracker[uid] = [t for t in self.spam_tracker[uid] if (ahora - t).total_seconds() < spam_segundos]
        self.spam_tracker[uid].append(ahora)

        if len(self.spam_tracker[uid]) >= spam_limite or self.flood_tracker[uid]["count"] >= 4:
            self.spam_tracker[uid].clear()
            self.flood_tracker[uid]["count"] = 0
            
            self.infraction_escalation[uid] += 1
            nivel = self.infraction_escalation[uid]
            
            if modo == "pacifico":
                # En modo pacífico solo avisa al staff, no silencia
                self._log_incidente(message.guild, message.author, message.channel, "Múltiples mensajes", "SPAM", 3, f"Saturación de canal detectada (Modo Pacífico)", borrado=False)
                return
                
            mute_mins = cfg.get("automod_mute_minutes", 10) * nivel
            if modo == "hard": mute_mins *= 3 # Castigo triple en modo Hard
            
            try:
                await message.channel.purge(limit=spam_limite + 2, check=lambda m: m.author.id == uid)
                await message.author.timeout(ahora + timedelta(minutes=mute_mins), reason=f"AutoMod: Saturación de canal (Nivel {nivel})")
                aviso = await message.channel.send(f"🛡️ **[CORTAFUEGOS]** {message.author.mention} ha sido aislado `{mute_mins}m` por saturación de red.")
                await aviso.delete(delay=6)
                self._log_incidente(message.guild, message.author, message.channel, "Múltiples mensajes", "SPAM", 4, f"Saturación de canal (Reincidencia: {nivel})", borrado=True)
            except Exception:
                pass
            return

        # ─── FASE 3: ANÁLISIS SEMÁNTICO CON IA (ASÍNCRONO) ───
        blacklist = cfg.get("automod_blacklist", [])
        if cfg.get("automod_ia", True) and self._requiere_analisis_ia(contenido, blacklist):
            asyncio.create_task(self._procesar_ia_shadow_flag(message, contenido, modo))

    # ═════════════════════════════════════════════════════════════════════════════
    #  MÉTODOS DE EJECUCIÓN Y TELEMETRÍA (REFACTORIZADOS)
    # ═════════════════════════════════════════════════════════════════════════════
    async def _ejecutar_sancion(self, message: discord.Message, razon_timeout: str, minutos: int, cat: str, sev: int, razon_log: str, borrado: bool):
        """Ejecuta la eliminación, el timeout y el registro con manejo estricto de errores."""
        ahora = datetime.now(timezone.utc)
        try:
            if borrado:
                await message.delete()
            await message.author.timeout(ahora + timedelta(minutes=minutos), reason=f"AutoMod: {razon_timeout}")
        except discord.Forbidden:
            logger.warning(f"AutoMod: Jerarquía insuficiente para sancionar a {message.author.id} en {message.guild.name}.")
        except discord.NotFound:
            pass # El mensaje ya fue borrado por otro bot o el usuario
        except Exception as e:
            logger.error(f"AutoMod: Fallo crítico al ejecutar sanción: {e}")
            
        self._log_incidente(message.guild, message.author, message.channel, message.content, cat, sev, razon_log, borrado)

    async def _procesar_ia_shadow_flag(self, message: discord.Message, contenido: str, modo: str):
        """Procesa el mensaje con Cerebras AI en segundo plano y aplica la postura táctica."""
        try:
            analisis = await analizar_mensaje(contenido)
            categoria = analisis.get("categoria", "SEGURO")
            severidad = analisis.get("severidad", 0)
            razon = analisis.get("razon", "Detección preventiva")

            if categoria in ["TOXICO", "SPAM", "SCAM"] and severidad >= 3:
                if modo == "pacifico":
                    self._log_incidente(message.guild, message.author, message.channel, contenido, categoria, severidad, razon, borrado=False)
                elif modo == "intermedio":
                    self._log_incidente(message.guild, message.author, message.channel, contenido, categoria, severidad, razon, borrado=False)
                elif modo == "hard":
                    try:
                        await message.delete()
                        await message.author.timeout(datetime.now(timezone.utc) + timedelta(minutes=30), reason=f"AutoMod IA (Hard Mode): {razon}")
                    except discord.Forbidden:
                        logger.warning(f"AutoMod IA: Sin permisos para aislar a {message.author.id}.")
                    except Exception as e:
                        logger.error(f"AutoMod IA: Error al aplicar Hard Mode: {e}")
                        
                    self._log_incidente(message.guild, message.author, message.channel, contenido, categoria, severidad, razon, borrado=True)

        except Exception as e:
            logger.error(f"Fallo en el motor semántico IA (Shadow Flag): {e}")
    # ═════════════════════════════════════════════════════════════════════════════
    #  COMANDOS DE CONFIGURACIÓN Y CONTROL
    # ═════════════════════════════════════════════════════════════════════════════
    @commands.hybrid_command(name="automod-mode", description="Cambia la postura táctica del AutoMod (Pacífico, Intermedio, Hard)")
    @app_commands.describe(modo="Selecciona el nivel de agresividad del filtro")
    @app_commands.choices(modo=[
        app_commands.Choice(name="🟢 Pacífico (Solo observa y reporta)", value="pacifico"),
        app_commands.Choice(name="🟡 Intermedio (Shadow Flagging y Anti-Spam)", value="intermedio"),
        app_commands.Choice(name="🔴 Hardcore (Tolerancia Cero, Borrado y Muteo IA)", value="hard")
    ])
    @commands.has_permissions(administrator=True)
    async def automod_mode(self, ctx, modo: str):
        await ctx.defer(ephemeral=True)
        actualizar_guild_config(ctx.guild.id, "automod_mode", modo)
        
        mensajes = {
            "pacifico": "🟢 **Modo Pacífico Activado:** El AutoMod ahora solo observará y reportará al Staff. No borrará mensajes ni silenciará usuarios (excepto enlaces de robo de cuentas).",
            "intermedio": "🟡 **Modo Intermedio Activado:** Postura estándar. El Shadow Flagging está activo. Se silenciará el spam y se marcará la toxicidad en secreto.",
            "hard": "🔴 **Modo HARDCORE Activado:** Tolerancia CERO. La IA actuará como verdugo. Cualquier toxicidad, evasión o spam resultará en borrado inmediato y aislamiento prolongado."
        }
        await ctx.send(mensajes[modo], ephemeral=True)

    @commands.hybrid_command(name="automod", description="Activa o desactiva el cortafuegos heurístico global")
    @commands.has_permissions(administrator=True)
    async def automod(self, ctx, estado: bool):
        await ctx.defer(ephemeral=True)
        actualizar_guild_config(ctx.guild.id, "automod_enabled", estado)
        await ctx.send(f"🛡️ **AutoMod Global:** {'OPERATIVO 🟢' if estado else 'SUSPENDIDO 🔴'}.", ephemeral=True)

    @commands.hybrid_command(name="automod-ia", description="Activa el análisis semántico con IA")
    @commands.has_permissions(administrator=True)
    async def automod_ia(self, ctx, estado: bool):
        await ctx.defer(ephemeral=True)
        actualizar_guild_config(ctx.guild.id, "automod_ia", estado)
        await ctx.send(f"🧠 **AutoMod IA:** {'ACTIVADO 🟢' if estado else 'DESACTIVADO 🔴'}.", ephemeral=True)

    @commands.hybrid_command(name="automod-whitelist", description="Excluye un canal de las reglas del AutoMod")
    @app_commands.choices(accion=[
        app_commands.Choice(name="Añadir a Whitelist", value="add"),
        app_commands.Choice(name="Remover de Whitelist", value="remove")
    ])
    @commands.has_permissions(administrator=True)
    async def automod_whitelist(self, ctx, canal: discord.TextChannel, accion: str):
        await ctx.defer(ephemeral=True)
        if accion == "add":
            self.whitelist_channels.add(canal.id)
            await ctx.send(f"✅ El canal {canal.mention} ha sido **excluido** de las inspecciones del AutoMod.", ephemeral=True)
        else:
            self.whitelist_channels.discard(canal.id)
            await ctx.send(f"❌ El canal {canal.mention} vuelve a estar **protegido** por el AutoMod.", ephemeral=True)

    @commands.hybrid_command(name="blacklist-add", description="Añade una palabra a la lista negra del servidor")
    @commands.has_permissions(administrator=True)
    async def blacklist_add(self, ctx, palabra: str):
        await ctx.defer(ephemeral=True)
        cfg = obtener_guild_config(ctx.guild.id)
        blacklist = cfg.get("automod_blacklist", [])
        
        palabra_limpia = palabra.lower().strip()
        if palabra_limpia in blacklist:
            return await ctx.send(f"⚠️ El término `{palabra_limpia}` ya se encuentra en la lista negra.", ephemeral=True)
            
        blacklist.append(palabra_limpia)
        actualizar_guild_config(ctx.guild.id, "automod_blacklist", blacklist)
        await ctx.send(f"✅ Término `{palabra_limpia}` añadido a la base de datos de amenazas.", ephemeral=True)

    @commands.hybrid_command(name="automod-status", description="Muestra la telemetría y configuración actual del AutoMod")
    @commands.has_permissions(manage_guild=True)
    async def automod_status(self, ctx):
        await ctx.defer()
        cfg = obtener_guild_config(ctx.guild.id)
        
        estado_am = "🟢 Activo" if cfg.get("automod_enabled", True) else "🔴 Apagado"
        estado_ia = "🟢 Activo" if cfg.get("automod_ia", True) else "🔴 Apagado"
        modo = cfg.get("automod_mode", "intermedio").upper()
        
        spam_lim = cfg.get("automod_spam_limit", 5)
        spam_sec = cfg.get("automod_spam_seconds", 5)
        
        canales_wl = len(self.whitelist_channels)
        palabras_bl = len(cfg.get("automod_blacklist", []))
        
        panel = (
            f"### 🛡️ TELEMETRÍA DEL CORTAFUEGOS // AUTOMOD V5\n"
            f"✦ ────────────────────────────────────────── ✦\n"
            f"> **Postura Táctica:** `{modo}`\n"
            f"> **Motor Heurístico Base:** {estado_am}\n"
            f"> **Motor Semántico IA:** {estado_ia}\n"
            f"> **Tolerancia Spam:** `{spam_lim} msgs` cada `{spam_sec}s`\n"
            f"> **Filtros Activos (0ms):** `Anti-Zalgo`, `Anti-Mass-Mention`, `Anti-Scam`, `Anti-IP-Logger`\n"
            f"> **Base de Datos:** `{palabras_bl}` términos vetados | `{canales_wl}` canales en whitelist\n"
            f"✦ ────────────────────────────────────────── ✦\n"
            f"-# Usa /automod-mode para cambiar la agresividad del sistema."
        )
        await ctx.send(panel)

async def setup(bot):
    await bot.add_cog(AutoMod(bot))