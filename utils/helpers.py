import sqlite3
import json
import os
import logging
import threading
from datetime import datetime, timezone

# ═══════════════════════════════════════════
#  TELEMETRÍA Y LOGGING
# ═══════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [ELIXYR-DB] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ElixyrPublic")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DB_PATH = os.path.join(DATA_DIR, "elixyr_soc.db")

os.makedirs(DATA_DIR, exist_ok=True)

# Lock para evitar colisiones de escritura en hilos concurrentes
db_lock = threading.Lock()

DEFAULT_GUILD_CONFIG = {
    "audit_channel": None,
    "log_channel": None,
    "ticket_category": None,
    "ticket_log_channel": None,
    "staff_role": None,
    "verified_role": None,
    "guest_role": None,
    "welcome_channel": None,
    "verify_channel": None,
    "antiraid_enabled": True,
    "antinuke_enabled": True,
    "automod_enabled": True,
    "automod_ia": True,
    "antiraid_join_limit": 8,
    "antiraid_join_seconds": 10,
    "antinuke_channel_delete_limit": 3,
    "antinuke_seconds": 10
}

# ═══════════════════════════════════════════
#  INICIALIZACIÓN DE SQLITE (MODO WAL)
# ═══════════════════════════════════════════
def init_db():
    """Forja las tablas relacionales si no existen y activa el modo de alto rendimiento."""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        # WAL (Write-Ahead Logging) permite lecturas y escrituras simultáneas ultrarrápidas
        conn.execute("PRAGMA journal_mode=WAL;")
        
        conn.execute('''CREATE TABLE IF NOT EXISTS guild_config (
                        guild_id TEXT PRIMARY KEY, config_data TEXT)''')
                        
        conn.execute('''CREATE TABLE IF NOT EXISTS cases (
                        case_id TEXT PRIMARY KEY, guild_id TEXT, tipo TEXT, 
                        usuario_id TEXT, moderador_id TEXT, razon TEXT, 
                        fecha TEXT, extra TEXT)''')
                        
        conn.execute('''CREATE TABLE IF NOT EXISTS warns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT, 
                        usuario_id TEXT, moderador_id TEXT, razon TEXT, fecha TEXT)''')
                        
        conn.execute('''CREATE TABLE IF NOT EXISTS notes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT, 
                        usuario_id TEXT, autor_id TEXT, nota TEXT, fecha TEXT)''')
        conn.commit()
        conn.close()

# Auto-inicializar al importar
init_db()

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# ═══════════════════════════════════════════
#  CONFIGURACIÓN GLOBAL (Mantiene JSON para config.json)
# ═══════════════════════════════════════════
def cargar_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Fallo al leer config.json: {e}")
    return {"prefijo": "g!"}

def guardar_config(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Fallo al escribir config.json: {e}")

# ═══════════════════════════════════════════
#  CONFIGURACIÓN POR SERVIDOR (Migrado a SQLite)
# ═══════════════════════════════════════════
def obtener_guild_config(guild_id: int) -> dict:
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT config_data FROM guild_config WHERE guild_id = ?", (str(guild_id),))
    row = cursor.fetchone()
    conn.close()

    config_actual = DEFAULT_GUILD_CONFIG.copy()
    if row:
        try:
            db_config = json.loads(row["config_data"])
            config_actual.update(db_config)
        except json.JSONDecodeError:
            pass
    return config_actual

def actualizar_guild_config(guild_id: int, clave: str, valor):
    config_actual = obtener_guild_config(guild_id)
    config_actual[clave] = valor
    
    with db_lock:
        conn = get_conn()
        conn.execute("INSERT OR REPLACE INTO guild_config (guild_id, config_data) VALUES (?, ?)", 
                     (str(guild_id), json.dumps(config_actual)))
        conn.commit()
        conn.close()

# ═══════════════════════════════════════════
#  CASES / EXPEDIENTES (Migrado a SQLite)
# ═══════════════════════════════════════════
def cargar_cases():
    """Capa de compatibilidad: Devuelve un dict con todos los casos para no romper cogs antiguos."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cases")
    rows = cursor.fetchall()
    conn.close()

    cases_dict = {}
    for row in rows:
        cases_dict[row["case_id"]] = {
            "id": row["case_id"],
            "guild_id": row["guild_id"],
            "tipo": row["tipo"],
            "usuario_id": row["usuario_id"],
            "moderador_id": row["moderador_id"],
            "razon": row["razon"],
            "fecha": row["fecha"],
            "extra": json.loads(row["extra"]) if row["extra"] else {}
        }
    return cases_dict

def guardar_cases(data):
    """Capa de compatibilidad: Sobrescribe la tabla (Usado por el comando delcase)."""
    with db_lock:
        conn = get_conn()
        conn.execute("DELETE FROM cases")
        for case_id, c in data.items():
            conn.execute('''INSERT INTO cases (case_id, guild_id, tipo, usuario_id, moderador_id, razon, fecha, extra)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                         (case_id, c.get("guild_id", "global"), c.get("tipo"), c.get("usuario_id"), 
                          c.get("moderador_id"), c.get("razon"), c.get("fecha"), json.dumps(c.get("extra", {}))))
        conn.commit()
        conn.close()

def crear_case(*args, **kwargs):
    # Adaptador de argumentos para mantener compatibilidad con tu código anterior
    if len(args) >= 5 and isinstance(args[4], (str, int)) and not isinstance(args[4], dict):
        guild_id, tipo, usuario_id, moderador_id, razon = args[:5]
        extra = args[5] if len(args) > 5 else kwargs.get("extra", {})
    else:
        tipo, usuario_id, moderador_id, razon = args[:4]
        extra = args[4] if len(args) > 4 else kwargs.get("extra", {})
        guild_id = "global"

    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    with db_lock:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cases")
        numero = cursor.fetchone()[0] + 1
        case_id = f"CASE-{numero:05d}"
        
        cursor.execute('''INSERT INTO cases (case_id, guild_id, tipo, usuario_id, moderador_id, razon, fecha, extra)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                       (case_id, str(guild_id), tipo, str(usuario_id), str(moderador_id), razon, fecha, json.dumps(extra)))
        conn.commit()
        conn.close()
        
    return case_id

def historial_usuario(*args):
    usuario_id = str(args[-1])
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cases WHERE usuario_id = ?", (usuario_id,))
    rows = cursor.fetchall()
    conn.close()

    return {row["case_id"]: dict(row) for row in rows}

# ═══════════════════════════════════════════
#  ADVERTENCIAS (WARNS) (Migrado a SQLite)
# ═══════════════════════════════════════════
def agregar_warn(*args):
    if len(args) == 4:
        guild_id, usuario_id, mod_id, razon = args
    else:
        usuario_id, mod_id, razon = args
        guild_id = "global"

    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    with db_lock:
        conn = get_conn()
        conn.execute('''INSERT INTO warns (guild_id, usuario_id, moderador_id, razon, fecha)
                        VALUES (?, ?, ?, ?, ?)''', 
                     (str(guild_id), str(usuario_id), str(mod_id), razon, fecha))
        conn.commit()
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM warns WHERE usuario_id = ?", (str(usuario_id),))
        total = cursor.fetchone()[0]
        conn.close()
        
    return total

def obtener_warns(*args):
    usuario_id = str(args[-1])
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM warns WHERE usuario_id = ?", (usuario_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def limpiar_warns(*args):
    usuario_id = str(args[-1])
    with db_lock:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM warns WHERE usuario_id = ?", (usuario_id,))
        borrados = cursor.fetchone()[0]
        cursor.execute("DELETE FROM warns WHERE usuario_id = ?", (usuario_id,))
        conn.commit()
        conn.close()
    return borrados

# ═══════════════════════════════════════════
#  NOTAS INTERNAS DEL STAFF (Migrado a SQLite)
# ═══════════════════════════════════════════
def agregar_nota(*args):
    if len(args) == 4:
        guild_id, usuario_id, autor_id, nota = args
    else:
        usuario_id, autor_id, nota = args
        guild_id = "global"

    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    with db_lock:
        conn = get_conn()
        conn.execute('''INSERT INTO notes (guild_id, usuario_id, autor_id, nota, fecha)
                        VALUES (?, ?, ?, ?, ?)''', 
                     (str(guild_id), str(usuario_id), str(autor_id), nota, fecha))
        conn.commit()
        conn.close()

def obtener_notas(*args):
    usuario_id = str(args[-1])
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes WHERE usuario_id = ?", (usuario_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

obtener_notes = obtener_notas