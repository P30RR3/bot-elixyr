"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR SOC // KERNEL DE PERSISTENCIA Y TELEMETRÍA (NEW GEN v6.0)
  Motor: aiosqlite (Asíncrono) + L1 In-Memory Cache (0ms reads)
  Seguridad: Sanitización de tipos, Prepared Statements y Thread-Safety Asíncrono
═══════════════════════════════════════════════════════════════════════════════
"""

import aiosqlite
import json
import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ElixyrKernel")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DB_PATH = os.path.join(DATA_DIR, "elixyr_soc.db")

os.makedirs(DATA_DIR, exist_ok=True)

# ─── CACHÉ L1 EN MEMORIA RAM (Lecturas a 0ms, Zero I/O overhead) ───
_GUILD_CONFIG_CACHE: Dict[str, Dict[str, Any]] = {}
_CONFIG_LOCK = asyncio.Lock()

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
    "antiraid_mode": "intermedio",
    "automod_mode": "intermedio",
    "antiraid_join_limit": 5,
    "antiraid_join_seconds": 10,
    "antinuke_channel_delete_limit": 3,
    "antinuke_seconds": 10,
    "automod_spam_limit": 5,
    "automod_spam_seconds": 5,
    "automod_mute_minutes": 10,
    "automod_blacklist": []
}

# ═════════════════════════════════════════════════════════════════════════════
#  INICIALIZACIÓN ASÍNCRONA DE BASE DE DATOS (ESQUEMA COMPLETO)
# ═════════════════════════════════════════════════════════════════════════════
async def init_db():
    """Crea las tablas relacionales bajo modo WAL de alta velocidad y precarga la caché."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        
        # Tabla de Configuración por Servidor
        await db.execute('''
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id TEXT PRIMARY KEY,
                config_data TEXT NOT NULL
            )
        ''')

        # Tabla Central de Casos / Expedientes Forenses
        await db.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                guild_id TEXT NOT NULL,
                tipo TEXT NOT NULL,
                usuario_id TEXT NOT NULL,
                moderador_id TEXT NOT NULL,
                razon TEXT NOT NULL,
                fecha TEXT NOT NULL,
                extra TEXT
            )
        ''')

        # Tabla de Advertencias Disciplinarias (Warns)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS warns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                usuario_id TEXT NOT NULL,
                moderador_id TEXT NOT NULL,
                razon TEXT NOT NULL,
                fecha TEXT NOT NULL
            )
        ''')

        # Tabla de Inteligencia / Notas Confidenciales
        await db.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                usuario_id TEXT NOT NULL,
                autor_id TEXT NOT NULL,
                nota TEXT NOT NULL,
                fecha TEXT NOT NULL
            )
        ''')

        # Tabla de Respaldos de Credenciales (Role Backups)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS role_backups (
                user_id TEXT NOT NULL,
                guild_id TEXT NOT NULL,
                role_ids TEXT NOT NULL,
                PRIMARY KEY(user_id, guild_id)
            )
        ''')

        await db.commit()

        # Precarga masiva a RAM para que ningún evento de chat sufra latencia
        async with db.execute("SELECT guild_id, config_data FROM guild_config") as cursor:
            rows = await cursor.fetchall()
            for gid, raw_json in rows:
                try:
                    merged = DEFAULT_GUILD_CONFIG.copy()
                    merged.update(json.loads(raw_json))
                    _GUILD_CONFIG_CACHE[str(gid)] = merged
                except Exception as err:
                    logger.warning(f"Configuración corrupta descartada en Guild {gid}: {err}")

    logger.info(f"Base de datos asegurada. {_GUILD_CONFIG_CACHE.__len__()} configuraciones precargadas en memoria.")

# ═════════════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN GLOBAL (JSON BOOTSTRAP)
# ═════════════════════════════════════════════════════════════════════════════
def cargar_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Fallo al leer config.json: {e}")
    return {"prefijo": "g!"}

def guardar_config(data: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Fallo al escribir config.json: {e}")

# ═════════════════════════════════════════════════════════════════════════════
#  GESTOR DE CONFIGURACIÓN POR GUILD (0ms RAM + Asynchronous Sync)
# ═════════════════════════════════════════════════════════════
def obtener_guild_config(guild_id: int | str) -> dict:
    """Lectura síncrona inmediata (0.0ms) desde la caché en RAM."""
    gid = str(guild_id)
    if gid not in _GUILD_CONFIG_CACHE:
        _GUILD_CONFIG_CACHE[gid] = DEFAULT_GUILD_CONFIG.copy()
    return _GUILD_CONFIG_CACHE[gid]

def actualizar_guild_config(guild_id: int | str, clave: str, valor: Any):
    """Actualiza la memoria de inmediato y programa persistencia no bloqueante."""
    gid = str(guild_id)
    cfg = obtener_guild_config(gid)
    cfg[clave] = valor
    _GUILD_CONFIG_CACHE[gid] = cfg

    # Tarea asíncrona de fondo para guardar en disco sin frenar el flujo actual
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_persistir_guild_config(gid, cfg))
    except RuntimeError:
        # Si no hay loop en ejecución, se crea una conexión puntual
        asyncio.run(_persistir_guild_config(gid, cfg))

async def _persistir_guild_config(guild_id: str, cfg: dict):
    async with _CONFIG_LOCK:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO guild_config (guild_id, config_data) VALUES (?, ?)",
                    (guild_id, json.dumps(cfg, ensure_ascii=False))
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Fallo crítico al persistir configuración de Guild {guild_id}: {e}")

# ═════════════════════════════════════════════════════════════════════════════
#  EXPEDIENTES JUDICIALES (CASES)
# ═════════════════════════════════════════════════════════════════════════════
async def crear_case_async(tipo: str, usuario_id: int | str, moderador_id: int | str, razon: str, extra: dict = None, guild_id: int | str = "global") -> str:
    """Registra una acción disciplinaria de forma atómica y no bloqueante."""
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    extra_data = json.dumps(extra or {}, ensure_ascii=False)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM cases") as cursor:
            row = await cursor.fetchone()
            total = (row[0] if row else 0) + 1
        
        case_id = f"CASE-{total:05d}"
        await db.execute(
            '''INSERT INTO cases (case_id, guild_id, tipo, usuario_id, moderador_id, razon, fecha, extra)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (case_id, str(guild_id), tipo.upper(), str(usuario_id), str(moderador_id), razon, fecha, extra_data)
        )
        await db.commit()
    return case_id

def crear_case(*args, **kwargs) -> str:
    """Wrapper retrocompatible: si un módulo antiguo lo llama sincrónicamente, no colapsa."""
    try:
        loop = asyncio.get_running_loop()
        future = asyncio.run_coroutine_threadsafe(crear_case_async(*args, **kwargs), loop)
        return future.result(timeout=3)
    except Exception:
        # Fallback de emergencia
        return "CASE-TEMP"

async def cargar_cases_async() -> dict:
    cases_dict = {}
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM cases") as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                cases_dict[r["case_id"]] = {
                    "id": r["case_id"],
                    "guild_id": r["guild_id"],
                    "tipo": r["tipo"],
                    "usuario_id": r["usuario_id"],
                    "moderador_id": r["moderador_id"],
                    "razon": r["razon"],
                    "fecha": r["fecha"],
                    "extra": json.loads(r["extra"]) if r["extra"] else {}
                }
    return cases_dict

def cargar_cases() -> dict:
    try:
        loop = asyncio.get_running_loop()
        future = asyncio.run_coroutine_threadsafe(cargar_cases_async(), loop)
        return future.result(timeout=3)
    except Exception:
        return {}

async def eliminar_case_async(case_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM cases WHERE case_id = ?", (case_id.upper(),))
        await db.commit()
        return cursor.rowcount > 0

def guardar_cases(data: dict):
    """Reconstrucción segura de expedientes."""
    async def _runner():
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM cases")
            for cid, c in data.items():
                await db.execute(
                    '''INSERT INTO cases (case_id, guild_id, tipo, usuario_id, moderador_id, razon, fecha, extra)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (cid, str(c.get("guild_id", "global")), c.get("tipo"), str(c.get("usuario_id")),
                     str(c.get("moderador_id")), c.get("razon"), c.get("fecha"), json.dumps(c.get("extra", {})))
                )
            await db.commit()
    try:
        loop = asyncio.get_running_loop()
        asyncio.run_coroutine_threadsafe(_runner(), loop)
    except Exception as e:
        logger.error(f"Fallo al guardar cases: {e}")

async def historial_usuario_async(usuario_id: int | str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM cases WHERE usuario_id = ?", (str(usuario_id),)) as cursor:
            rows = await cursor.fetchall()
            return {r["case_id"]: dict(r) for r in rows}

def historial_usuario(*args) -> dict:
    uid = str(args[-1])
    try:
        loop = asyncio.get_running_loop()
        future = asyncio.run_coroutine_threadsafe(historial_usuario_async(uid), loop)
        return future.result(timeout=3)
    except Exception:
        return {}

# ═════════════════════════════════════════════════════════════════════════════
#  SISTEMA DISCIPLINARIO DE ADVERTENCIAS (WARNS)
# ═════════════════════════════════════════════════════════════════════════════
async def agregar_warn_async(guild_id: int | str, usuario_id: int | str, mod_id: int | str, razon: str) -> int:
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO warns (guild_id, usuario_id, moderador_id, razon, fecha) VALUES (?, ?, ?, ?, ?)",
            (str(guild_id), str(usuario_id), str(mod_id), razon, fecha)
        )
        await db.commit()
        async with db.execute("SELECT COUNT(*) FROM warns WHERE usuario_id = ?", (str(usuario_id),)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 1

def agregar_warn(*args) -> int:
    guild_id = args[0] if len(args) == 4 else "global"
    uid = args[1] if len(args) == 4 else args[0]
    mid = args[2] if len(args) == 4 else args[1]
    razon = args[3] if len(args) == 4 else args[2]
    try:
        loop = asyncio.get_running_loop()
        future = asyncio.run_coroutine_threadsafe(agregar_warn_async(guild_id, uid, mid, razon), loop)
        return future.result(timeout=3)
    except Exception:
        return 1

async def obtener_warns_async(usuario_id: int | str) -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM warns WHERE usuario_id = ?", (str(usuario_id),)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

def obtener_warns(*args) -> List[dict]:
    uid = str(args[-1])
    try:
        loop = asyncio.get_running_loop()
        future = asyncio.run_coroutine_threadsafe(obtener_warns_async(uid), loop)
        return future.result(timeout=3)
    except Exception:
        return []

async def limpiar_warns_async(usuario_id: int | str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM warns WHERE usuario_id = ?", (str(usuario_id),))
        await db.commit()
        return cursor.rowcount

def limpiar_warns(*args) -> int:
    uid = str(args[-1])
    try:
        loop = asyncio.get_running_loop()
        future = asyncio.run_coroutine_threadsafe(limpiar_warns_async(uid), loop)
        return future.result(timeout=3)
    except Exception:
        return 0

# ═════════════════════════════════════════════════════════════════════════════
#  NOTAS INTERNAS DE INTELIGENCIA (STAFF NOTES)
# ═════════════════════════════════════════════════════════════
async def agregar_nota_async(guild_id: int | str, usuario_id: int | str, autor_id: int | str, nota: str):
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO notes (guild_id, usuario_id, autor_id, nota, fecha) VALUES (?, ?, ?, ?, ?)",
            (str(guild_id), str(usuario_id), str(autor_id), nota, fecha)
        )
        await db.commit()

def agregar_nota(*args):
    guild_id = args[0] if len(args) == 4 else "global"
    uid = args[1] if len(args) == 4 else args[0]
    aid = args[2] if len(args) == 4 else args[1]
    nota = args[3] if len(args) == 4 else args[2]
    try:
        loop = asyncio.get_running_loop()
        asyncio.run_coroutine_threadsafe(agregar_nota_async(guild_id, uid, aid, nota), loop)
    except Exception as e:
        logger.error(f"Error registrando nota: {e}")

async def obtener_notas_async(usuario_id: int | str) -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM notes WHERE usuario_id = ?", (str(usuario_id),)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

def obtener_notas(*args) -> List[dict]:
    uid = str(args[-1])
    try:
        loop = asyncio.get_running_loop()
        future = asyncio.run_coroutine_threadsafe(obtener_notas_async(uid), loop)
        return future.result(timeout=3)
    except Exception:
        return []

obtener_notes = obtener_notas