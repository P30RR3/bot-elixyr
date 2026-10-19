import os
import sys
import time
import asyncio
import logging
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from colorama import Fore, Style, init

# Inicializar colores en terminal
init(autoreset=True)

# Importaciones locales seguras
from utils.helpers import cargar_config
from utils.ia import verificar_conexion_ia

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CONFIG = cargar_config()

# ═══════════════════════════════════════════
#  CONFIGURACIÓN DE LOGS DE TERMINAL (ESTILO SOC)
# ═══════════════════════════════════════════
class SOCFormatter(logging.Formatter):
    def format(self, record):
        color = Fore.WHITE
        if record.levelno == logging.WARNING: color = Fore.YELLOW
        elif record.levelno == logging.ERROR: color = Fore.RED
        elif record.levelno == logging.INFO: color = Fore.CYAN
        
        # Formato de consola táctico
        return f"{Fore.LIGHTBLACK_EX}[{self.formatTime(record, '%Y-%m-%d %H:%M:%S')}]{Style.RESET_ALL} {color}[{record.levelname}]{Style.RESET_ALL} {Fore.LIGHTBLUE_EX}[ELIXYR-CORE]{Style.RESET_ALL} {record.getMessage()}"

handler = logging.StreamHandler()
handler.setFormatter(SOCFormatter())
logger = logging.getLogger("ElixyrMain")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# ═══════════════════════════════════════════
#  INTENTS DE DISCORD (MÁXIMA VISIBILIDAD)
# ═══════════════════════════════════════════
intents = discord.Intents.all() # Activamos todos directamente para análisis IA profundo

# ═══════════════════════════════════════════
#  CLASE PRINCIPAL DEL MOTOR ELIXYR
# ═══════════════════════════════════════════
class ElixyrBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=CONFIG.get("prefijo", "g!"),
            intents=intents,
            help_command=None
        )
        self.synced = False
        self.estado_index = 0
        self.start_time = time.time()
        self.config = CONFIG  # Almacenado en caché para los cogs

    async def setup_hook(self):
        """Inicialización asíncrona: El corazón del sistema."""
        print(f"\n{Fore.MAGENTA}══════════════════════════════════════════════════{Style.RESET_ALL}")
        print(f"{Fore.CYAN}    🛡️  ELIXYR GUARD // AI SECURITY OPERATIONS   {Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}══════════════════════════════════════════════════{Style.RESET_ALL}\n")

        # 1. Conexión con Motor de IA
        logger.info("Verificando enlace con Cerebras AI...")
        asyncio.create_task(verificar_conexion_ia())

        # 2. Carga dinámica de módulos (Cogs)
        cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
        if os.path.exists(cogs_dir):
            for archivo in sorted(os.listdir(cogs_dir)):
                if archivo.endswith(".py") and not archivo.startswith("__"):
                    cog_nombre = f"cogs.{archivo[:-3]}"
                    try:
                        t_start = time.perf_counter()
                        await self.load_extension(cog_nombre)
                        t_end = time.perf_counter()
                        ms = (t_end - t_start) * 1000
                        print(f"{Fore.GREEN} [+] Módulo cargado:{Style.RESET_ALL} {archivo[:-3]:<15} {Fore.LIGHTBLACK_EX}({ms:.1f}ms){Style.RESET_ALL}")
                    except Exception as e:
                        print(f"{Fore.RED} [!] Falla crítica en {cog_nombre}:{Style.RESET_ALL} {e}")

        # 3. Encender presencia
        if not self.cambiar_estado.is_running():
            self.cambiar_estado.start()

    async def on_ready(self):
        """Disparado al enlazar exitosamente con los servidores de Discord."""
        if not self.synced:
            try:
                comandos = await self.tree.sync()
                total_slash = len(comandos)
                self.synced = True
            except Exception as e:
                total_slash = f"Error: {e}"
        else:
            total_slash = len(self.tree.get_commands())

        uptime = round(time.time() - self.start_time, 2)
        print(f"\n{Fore.MAGENTA}══════════════════════════════════════════════════{Style.RESET_ALL}")
        print(f" {Fore.CYAN}[SYSTEM]{Style.RESET_ALL} IDENTIDAD:     {Fore.WHITE}{self.user} {Fore.LIGHTBLACK_EX}({self.user.id}){Style.RESET_ALL}")
        print(f" {Fore.CYAN}[SYSTEM]{Style.RESET_ALL} REDES ACTIVAS: {Fore.WHITE}{len(self.guilds)}{Style.RESET_ALL}")
        print(f" {Fore.CYAN}[SYSTEM]{Style.RESET_ALL} COMANDOS:      {Fore.WHITE}{total_slash} directivas{Style.RESET_ALL}")
        print(f" {Fore.CYAN}[SYSTEM]{Style.RESET_ALL} ARRANQUE:      {Fore.WHITE}{uptime}s{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}══════════════════════════════════════════════════{Style.RESET_ALL}\n")
        logger.info("Elixyr SOC en línea y monitoreando.")

    # ═══════════════════════════════════════════
    #  SISTEMA DE ESTADOS DINÁMICOS
    # ═══════════════════════════════════════════
    @tasks.loop(seconds=30)
    async def cambiar_estado(self):
        """Rotación de presencia. Información táctica en tiempo real."""
        await self.wait_until_ready()
        if self.is_closed(): return

        usuarios_vigilados = sum(g.member_count or 0 for g in self.guilds)
        
        estados = [
            discord.Streaming(name="/help • AI Security v2.0", url="https://twitch.tv/discord"),
            discord.Activity(type=discord.ActivityType.watching, name=f"{len(self.guilds)} redes protegidas 🛡️"),
            discord.Activity(type=discord.ActivityType.listening, name="telemetría Cerebras AI 🧠"),
            discord.Activity(type=discord.ActivityType.competing, name="Protocolo Defensa Activo ⚔️"),
            discord.Activity(type=discord.ActivityType.watching, name=f"{usuarios_vigilados:,} usuarios vigilados 👥")
        ]

        try:
            await self.change_presence(activity=estados[self.estado_index], status=discord.Status.online)
            self.estado_index = (self.estado_index + 1) % len(estados)
        except Exception:
            pass

bot = ElixyrBot()

# ═══════════════════════════════════════════
#  MANEJADOR GLOBAL DE ERRORES (RESPUESTAS IA-LIKE)
# ═══════════════════════════════════════════
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Intercepta errores y responde con estética de ciberseguridad profesional."""
    
    if isinstance(error, discord.app_commands.MissingPermissions):
        perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
        msg = (
            f"### ⛔ ACCESO DENEGADO\n"
            f"> Pareces no tener la autorización requerida para esta directiva.\n"
            f"▸ **Credenciales faltantes:** {perms}\n\n"
            f"-# El intento ha sido registrado. Mantengamos la seguridad."
        )
    elif isinstance(error, discord.app_commands.BotMissingPermissions):
        perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
        msg = (
            f"### ⚠️ LIMITACIÓN DEL SISTEMA\n"
            f"> Mis protocolos de seguridad me impiden ejecutar esto. Necesito más permisos.\n"
            f"▸ **Requiere:** {perms}\n\n"
            f"-# Por favor, eleva los privilegios de mi rol en la configuración."
        )
    elif isinstance(error, discord.app_commands.CommandOnCooldown):
        msg = (
            f"### ⏳ ENFRIAMIENTO TÁCTICO\n"
            f"> Mis sistemas están procesando demasiadas solicitudes. \n"
            f"▸ **Reintenta en:** `{error.retry_after:.1f} segundos`."
        )
    else:
        # Error no manejado
        msg = (
            f"### ⚠️ ANOMALÍA DETECTADA\n"
            f"> El motor de IA encontró una interrupción al procesar tu instrucción.\n"
            f"```yaml\nDetalle: {str(error)[:250]}\n```\n"
            f"-# Nuestros registros de telemetría han capturado este evento."
        )
        logger.error(f"Error en comando /{interaction.command.name if interaction.command else 'Desconocido'}: {error}")

    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception as e:
        logger.error(f"Fallo al enviar mensaje de error al usuario: {e}")

# ═══════════════════════════════════════════
#  BOOTLOADER DEL SISTEMA
# ═══════════════════════════════════════════
if __name__ == "__main__":
    if not TOKEN:
        print(f"\n{Fore.RED}[CRÍTICO]{Style.RESET_ALL} Variable DISCORD_TOKEN no detectada en entorno.")
        sys.exit(1)

    try:
        bot.run(TOKEN, log_handler=None) # Desactivamos logger default de discord para usar el nuestro
    except discord.errors.LoginFailure:
        print(f"\n{Fore.RED}[CRÍTICO]{Style.RESET_ALL} Token de Discord inválido o revocado.")
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[APAGADO]{Style.RESET_ALL} Subsistemas Elixyr Guard desconectados.")
    except Exception as e:
        print(f"\n{Fore.RED}[FATAL]{Style.RESET_ALL} Caída crítica del sistema: {e}")