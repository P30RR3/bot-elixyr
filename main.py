"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR GUARD // AI-SOC COMMAND CORE (BOOTSTRAP v6.0)
  Arquitectura: Zero-Blocking Async Event Loop, Auto-Discovery & Healthcheck
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import time
import asyncio
import logging
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from colorama import Fore, Style, init

init(autoreset=True)
load_dotenv()

from utils.helpers import cargar_config, init_db
from utils.ia import verificar_conexion_ia

TOKEN = os.getenv("DISCORD_TOKEN")
CONFIG = cargar_config()

# ═════════════════════════════════════════════════════════════════════════════
#  LOGGING ESTILO MILITAR / SOC
# ═════════════════════════════════════════════════════════════════════════════
class SOCFormatter(logging.Formatter):
    def format(self, record):
        color = Fore.WHITE
        if record.levelno == logging.WARNING:
            color = Fore.YELLOW
        elif record.levelno == logging.ERROR:
            color = Fore.RED
        elif record.levelno == logging.INFO:
            color = Fore.CYAN

        timestamp = self.formatTime(record, '%H:%M:%S')
        return (
            f"{Fore.LIGHTBLACK_EX}[{timestamp}]{Style.RESET_ALL} "
            f"{color}[{record.levelname:<7}]{Style.RESET_ALL} "
            f"{Fore.BLUE}[SOC-CORE]{Style.RESET_ALL} {record.getMessage()}"
        )

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(SOCFormatter())
logger = logging.getLogger("ElixyrKernel")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# ═════════════════════════════════════════════════════════════════════════════
#  INTENTS DE VISIBILIDAD TOTAL
# ═════════════════════════════════════════════════════════════════════════════
intents = discord.Intents.all()

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

    async def setup_hook(self):
        """Inicialización atómica de infraestructura."""
        print(f"\n{Fore.CYAN}╔════════════════════════════════════════════════════════════╗{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║     🛡️  ELIXYR GUARD // AI SECURITY OPERATIONS CORE        ║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}╚════════════════════════════════════════════════════════════╝{Style.RESET_ALL}\n")

        # 1. Base de datos asíncrona
        logger.info("Verificando integridad del almacén SQLite (WAL Mode)...")
        await init_db()

        # 2. Enlace neuronal
        logger.info("Estableciendo enlace con el motor de inferencia Cerebras AI...")
        asyncio.create_task(verificar_conexion_ia())

        # 3. Autodescubrimiento de Cogs
        cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
        if os.path.exists(cogs_dir):
            for archivo in sorted(os.listdir(cogs_dir)):
                if archivo.endswith(".py") and not archivo.startswith("__"):
                    cog_ext = f"cogs.{archivo[:-3]}"
                    try:
                        t0 = time.perf_counter()
                        await self.load_extension(cog_ext)
                        elapsed_ms = (time.perf_counter() - t0) * 1000
                        logger.info(f"Módulo acoplado: {archivo[:-3]:<18} [{elapsed_ms:.1f}ms]")
                    except Exception as e:
                        logger.error(f"Falla crítica cargando [{cog_ext}]: {e}")

        # Iniciar ciclo de presencia
        if not self.presencia_soc.is_running():
            self.presencia_soc.start()

    async def on_ready(self):
        if not self.synced:
            try:
                comandos = await self.tree.sync()
                total_slash = len(comandos)
                self.synced = True
            except Exception as e:
                logger.error(f"Error sincronizando comandos Slash globales: {e}")
                total_slash = "Error"
        else:
            total_slash = len(self.tree.get_commands())

        uptime = round(time.time() - self.start_time, 2)
        print(f"\n{Fore.GREEN}✦ RED OPERATIVA ACTIVA ✦{Style.RESET_ALL}")
        print(f" ▸ Identidad:    {self.user} ({self.user.id})")
        print(f" ▸ Perímetros:   {len(self.guilds)} servidores monitoreados")
        print(f" ▸ Directivas:   {total_slash} comandos slash listos")
        print(f" ▸ Despliegue:   {uptime}s en inicialización\n")

    @tasks.loop(seconds=30)
    async def presencia_soc(self):
        await self.wait_until_ready()
        if self.is_closed():
            return

        total_users = sum(g.member_count or 0 for g in self.guilds)
        estados = [
            discord.CustomActivity(name="🛡️ Monitoreando tráfico en busca de anomalías"),
            discord.Activity(type=discord.ActivityType.watching, name=f"{len(self.guilds)} redes aseguradas"),
            discord.Activity(type=discord.ActivityType.listening, name="telemetría Cerebras AI"),
            discord.Activity(type=discord.ActivityType.watching, name=f"{total_users:,} identidades protegidas")
        ]

        try:
            await self.change_presence(activity=estados[self.estado_index], status=discord.Status.online)
            self.estado_index = (self.estado_index + 1) % len(estados)
        except Exception:
            pass

bot = ElixyrBot()

# ═════════════════════════════════════════════════════════════════════════════
#  CORTAFUEGOS GLOBAL DE ERRORES (SLASH COMMANDS)
# ═════════════════════════════════════════════════════════════════════════════
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.MissingPermissions):
        perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
        msg = f"### ⛔ AUTORIZACIÓN INSUFICIENTE\n> Tu jerarquía actual carece de los siguientes privilegios:\n▸ {perms}"
    elif isinstance(error, discord.app_commands.BotMissingPermissions):
        perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
        msg = f"### ⚠️ IMPEDIMENTO TÁCTICO\n> El bot no cuenta con los permisos necesarios en este canal/servidor:\n▸ {perms}"
    elif isinstance(error, discord.app_commands.CommandOnCooldown):
        msg = f"### ⏳ ENFRIAMIENTO DE CANAL\n> Operación saturada. Reintento disponible en `{error.retry_after:.1f}s`."
    else:
        cmd = interaction.command.name if interaction.command else "desconocido"
        msg = f"### 🚨 ANOMALÍA EN EJECUCIÓN\n> Error interno registrado en la directiva `/{cmd}`.\n```yaml\nDetalle: {str(error)[:200]}\n```"
        logger.error(f"Fallo en /{cmd} ejecutado por {interaction.user.id}: {error}")

    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass

if __name__ == "__main__":
    if not TOKEN:
        logger.error("Token de autenticación DISCORD_TOKEN no detectado en variables de entorno.")
        sys.exit(1)

    try:
        bot.run(TOKEN, log_handler=None)
    except discord.LoginFailure:
        logger.error("El token de Discord es inválido o ha sido revocado.")
    except KeyboardInterrupt:
        logger.info("Cierre manual autorizado por el operador.")
    except Exception as e:
        logger.error(f"Falla catastrófica en el proceso principal: {e}")