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
        
        return f"{Fore.LIGHTBLACK_EX}[{self.formatTime(record, '%Y-%m-%d %H:%M:%S')}]{Style.RESET_ALL} {color}[{record.levelname}]{Style.RESET_ALL} {Fore.LIGHTBLUE_EX}[ELIXYR-CORE]{Style.RESET_ALL} {record.getMessage()}"

handler = logging.StreamHandler()
handler.setFormatter(SOCFormatter())
logger = logging.getLogger("ElixyrMain")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# ═══════════════════════════════════════════
#  INTENTS DE DISCORD (MÁXIMA VISIBILIDAD)
# ═══════════════════════════════════════════
intents = discord.Intents.all()

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
        self.config = CONFIG

    async def setup_hook(self):
        """Inicialización asíncrona: El corazón del sistema."""
        print(f"\n{Fore.MAGENTA}══════════════════════════════════════════════════{Style.RESET_ALL}")
        print(f"{Fore.CYAN}    🛡️  ELIXYR GUARD // AI SECURITY OPERATIONS   {Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}══════════════════════════════════════════════════{Style.RESET_ALL}\n")

        logger.info("Verificando enlace con Cerebras AI...")
        asyncio.create_task(verificar_conexion_ia())

        # Carga dinámica de módulos (Cogs) con manejo estricto de errores
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
                        logger.error(f"Falla crítica al cargar {cog_nombre}: {e}")

        if not self.cambiar_estado.is_running():
            self.cambiar_estado.start()

    async def on_ready(self):
        if not self.synced:
            try:
                comandos = await self.tree.sync()
                total_slash = len(comandos)
                self.synced = True
            except Exception as e:
                logger.error(f"Error sincronizando comandos Slash: {e}")
                total_slash = "Error"
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

    @tasks.loop(seconds=30)
    async def cambiar_estado(self):
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
        except Exception as e:
            logger.warning(f"No se pudo actualizar el estado: {e}")

bot = ElixyrBot()

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.MissingPermissions):
        perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
        msg = f"### ⛔ ACCESO DENEGADO\n> Pareces no tener la autorización requerida.\n▸ **Falta:** {perms}"
    elif isinstance(error, discord.app_commands.BotMissingPermissions):
        perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
        msg = f"### ⚠️ LIMITACIÓN DEL SISTEMA\n> Mis protocolos me impiden ejecutar esto.\n▸ **Requiere:** {perms}"
    elif isinstance(error, discord.app_commands.CommandOnCooldown):
        msg = f"### ⏳ ENFRIAMIENTO TÁCTICO\n> Sistemas saturados. Reintenta en `{error.retry_after:.1f}s`."
    else:
        msg = f"### ⚠️ ANOMALÍA DETECTADA\n> El motor encontró una interrupción.\n```yaml\nDetalle: {str(error)[:250]}\n```"
        logger.error(f"Error en comando /{interaction.command.name if interaction.command else 'Desconocido'}: {error}")

    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception as e:
        logger.error(f"Fallo al enviar mensaje de error al usuario: {e}")

if __name__ == "__main__":
    if not TOKEN:
        logger.error("Variable DISCORD_TOKEN no detectada en entorno.")
        sys.exit(1)

    try:
        bot.run(TOKEN, log_handler=None)
    except discord.errors.LoginFailure:
        logger.error("Token de Discord inválido o revocado.")
    except KeyboardInterrupt:
        logger.info("Subsistemas Elixyr Guard desconectados por el usuario.")
    except Exception as e:
        logger.error(f"Caída crítica del sistema: {e}")