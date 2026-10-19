import json
import os
import logging
import threading
from datetime import datetime, timezone
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [ELIXYR-DB] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ElixyrPublic")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

GUILDS_FILE = os.path.join(DATA_DIR, "guilds_config.json")
CASES_FILE = os.path.join(DATA_DIR, "cases.json")
WARNS_FILE = os.path.join(DATA_DIR, "warns.json")
NOTES_FILE = os.path.join(DATA_DIR, "notes.json")

os.makedirs(DATA_DIR, exist_ok=True)

# ═══════════════════════════════════════════
#  SISTEMA DE CACHÉ Y LOCKS (ANTI-RAID I/O)
# ═══════════════════════════════════════════
# Previene corrupción de JSON cuando cientos de 
# usuarios son sancionados al mismo tiempo.
_FILE_LOCKS = defaultdict(threading.Lock)
_MEMORY_CACHE = {}

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

def _cargar_json(path):
    if path in _MEMORY_CACHE:
        return _MEMORY_CACHE[path]

    with _FILE_LOCKS[path]:
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump({}, f)
            _MEMORY_CACHE[path] = {}
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                _MEMORY_CACHE[path] = data
                return data
        except json.JSONDecodeError:
            logger.error(f"Archivo corrupto detectado: {path}. Recreando.")
            _MEMORY_CACHE[path] = {}
            return {}

def _guardar_json(path, data):
    _MEMORY_CACHE[path] = data
    with _FILE_LOCKS[path]:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error escribiendo I/O en {os.path.basename(path)}: {e}")

# ═══════════════════════════════════════════
#  CONFIGURACIÓN GLOBAL
# ═══════════════════════════════════════════
def cargar_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"prefijo": "g!"}

def guardar_config(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def obtener_guild_config(guild_id: int) -> dict:
    data = _cargar_json(GUILDS_FILE)
    gid = str(guild_id)
    if gid not in data:
        data[gid] = DEFAULT_GUILD_CONFIG.copy()
        _guardar_json(GUILDS_FILE, data)
        return data[gid]

    for k, v in DEFAULT_GUILD_CONFIG.items():
        data[gid].setdefault(k, v)
    return data[gid]

def actualizar_guild_config(guild_id: int, clave: str, valor):
    data = _cargar_json(GUILDS_FILE)
    gid = str(guild_id)
    if gid not in data:
        data[gid] = DEFAULT_GUILD_CONFIG.copy()
    data[gid][clave] = valor
    _guardar_json(GUILDS_FILE, data)

# ═══════════════════════════════════════════
#  CASES / EXPEDIENTES (REGISTROS)
# ═══════════════════════════════════════════
def cargar_cases(): return _cargar_json(CASES_FILE)
def guardar_cases(data): _guardar_json(CASES_FILE, data)

def crear_case(*args, **kwargs):
    cases = cargar_cases()
    
    if len(args) >= 5 and isinstance(args[4], (str, int)) and not isinstance(args[4], dict):
        guild_id, tipo, usuario_id, moderador_id, razon = args[:5]
        extra = args[5] if len(args) > 5 else kwargs.get("extra", {})
    else:
        tipo, usuario_id, moderador_id, razon = args[:4]
        extra = args[4] if len(args) > 4 else kwargs.get("extra", {})
        guild_id = "global"

    numero = len(cases) + 1
    case_id = f"CASE-{numero:05d}" # Actualizado a 5 dígitos para alta escalabilidad

    cases[case_id] = {
        "id": case_id,
        "guild_id": str(guild_id),
        "tipo": tipo,
        "usuario_id": str(usuario_id),
        "moderador_id": str(moderador_id),
        "razon": razon,
        "fecha": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "extra": extra
    }
    guardar_cases(cases)
    return case_id

def historial_usuario(*args):
    cases = cargar_cases()
    usuario_id = str(args[-1])
    return {k: v for k, v in cases.items() if v.get("usuario_id") == usuario_id}

# ═══════════════════════════════════════════
#  ADVERTENCIAS (WARNS)
# ═══════════════════════════════════════════
def cargar_warns(): return _cargar_json(WARNS_FILE)
def guardar_warns(data): _guardar_json(WARNS_FILE, data)

def agregar_warn(*args):
    warns = cargar_warns()
    if len(args) == 4:
        guild_id, usuario_id, mod_id, razon = args
        uid = f"{guild_id}_{usuario_id}"
    else:
        usuario_id, mod_id, razon = args
        uid = str(usuario_id)

    if uid not in warns: warns[uid] = []

    warns[uid].append({
        "moderador_id": str(mod_id),
        "razon": razon,
        "fecha": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    })
    guardar_warns(warns)
    return len(warns[uid])

def obtener_warns(*args):
    warns = cargar_warns()
    uid = str(args[-1])
    if uid in warns: return warns[uid]
    for k, v in warns.items():
        if k.endswith(f"_{uid}"): return v
    return []

def limpiar_warns(*args):
    warns = cargar_warns()
    uid = str(args[-1])
    borrados = 0
    claves_a_borrar = [k for k in warns if k == uid or k.endswith(f"_{uid}")]
    for k in claves_a_borrar:
        borrados += len(warns[k])
        del warns[k]
    guardar_warns(warns)
    return borrados

# ═══════════════════════════════════════════
#  NOTAS INTERNAS DEL STAFF
# ═══════════════════════════════════════════
def cargar_notes(): return _cargar_json(NOTES_FILE)
def guardar_notes(data): _guardar_json(NOTES_FILE, data)

def agregar_nota(*args):
    notes = cargar_notes()
    if len(args) == 4:
        guild_id, usuario_id, autor_id, nota = args
        uid = f"{guild_id}_{usuario_id}"
    else:
        usuario_id, autor_id, nota = args
        uid = str(usuario_id)

    if uid not in notes: notes[uid] = []

    notes[uid].append({
        "autor_id": str(autor_id),
        "nota": nota,
        "fecha": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    })
    guardar_notes(notes)

def obtener_notas(*args):
    notes = cargar_notes()
    uid = str(args[-1])
    if uid in notes: return notes[uid]
    for k, v in notes.items():
        if k.endswith(f"_{uid}"): return v
    return []

obtener_notes = obtener_notas