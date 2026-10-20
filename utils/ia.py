import os
import asyncio
import json
import logging
import re
from dotenv import load_dotenv
from cerebras.cloud.sdk import Cerebras

load_dotenv()

logger = logging.getLogger("ElixyrIA")

CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
client = Cerebras(api_key=CEREBRAS_API_KEY) if CEREBRAS_API_KEY else None
CEREBRAS_MODEL = "llama3.1-70b"

MAX_REINTENTOS = 2
ESPERA_BASE = 2

SYSTEM_PROMPT_CHAT = """Eres un asistente de inteligencia artificial conversacional, perspicaz, empático y versátil.
Directrices: Actúa de forma natural, amigable y humana. Usa Markdown limpio. No uses introducciones robóticas."""

SYSTEM_PROMPT_MOD = """Eres el firewall de moderación y ciberseguridad de Elixyr Guard.
Clasifica si un mensaje es una AMENAZA.
1. SEGURO (0): Desahogos, bromas, quejas comunes.
2. TOXICO (3-5): Insultos, acoso, odio.
3. SCAM/SPAM (5): Phishing, links falsos, saturación.
Responde ÚNICAMENTE con un JSON válido: {"categoria": "SEGURO"|"TOXICO"|"SPAM"|"SCAM", "severidad": 0 a 5, "razon": "explicacion"}"""

# ─── NUEVO: EXTRACTOR QUIRÚRGICO DE JSON ───
def extraer_json(texto: str) -> dict:
    """Extrae y sanitiza un bloque JSON de una respuesta alucinada de la IA."""
    try:
        # Busca todo lo que esté entre llaves { }
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        clean_text = match.group(0) if match else texto
        return json.loads(clean_text)
    except json.JSONDecodeError:
        logger.error(f"Fallo al decodificar JSON de la IA. Texto crudo: {texto[:100]}...")
        return {}

async def verificar_conexion_ia() -> bool:
    global CEREBRAS_MODEL
    if not client:
        logger.warning("CEREBRAS_API_KEY no detectada en el archivo .env")
        return False
    try:
        modelos = await asyncio.to_thread(client.models.list)
        if modelos.data:
            nombres = [m.id for m in modelos.data]
            CEREBRAS_MODEL = "llama3.3-70b" if "llama3.3-70b" in nombres else ("llama3.1-70b" if "llama3.1-70b" in nombres else modelos.data[0].id)
            logger.info(f"Motor Cerebras AI en línea. Modelo: {CEREBRAS_MODEL}")
        return True
    except Exception as e:
        logger.error(f"Advertencia al conectar con Cerebras: {e}")
        return False

async def _llamar_cerebras(system_prompt: str, user_prompt: str = None, json_mode: bool = False, mensajes_historial: list = None, max_tokens: int = 1500) -> str | None:
    if not client: return None
    messages = [{"role": "system", "content": system_prompt}] + (mensajes_historial if mensajes_historial else [{"role": "user", "content": user_prompt or ""}])
    kwargs = {"model": CEREBRAS_MODEL, "messages": messages, "temperature": 0.1 if json_mode else 0.6, "max_completion_tokens": max_tokens}
    if json_mode: kwargs["response_format"] = {"type": "json_object"}

    for intento in range(MAX_REINTENTOS):
        try:
            response = await asyncio.to_thread(client.chat.completions.create, **kwargs)
            if response and response.choices: return response.choices[0].message.content.strip()
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                await asyncio.sleep(ESPERA_BASE * (intento + 1))
                continue
            logger.error(f"Error en inferencia Cerebras: {e}")
            return None
    return None

async def preguntar_ia(prompt: str = None, contexto: str = None, historial: list = None, json_mode: bool = False, system_prompt: str = None, max_tokens: int = 1500) -> str:
    sys_p = system_prompt or SYSTEM_PROMPT_CHAT
    if historial:
        respuesta = await _llamar_cerebras(sys_p, mensajes_historial=historial, json_mode=json_mode, max_tokens=max_tokens)
    else:
        texto_final = prompt if not contexto else f"Contexto:\n{contexto}\n\nPetición:\n{prompt}"
        respuesta = await _llamar_cerebras(sys_p, user_prompt=texto_final, json_mode=json_mode, max_tokens=max_tokens)
    return respuesta if respuesta else "⚠️ *El enlace neuronal con Cerebras AI no respondió a tiempo.*"

async def resumir_texto(texto: str) -> str:
    return await preguntar_ia(f"Genera un resumen ordenado, claro y con viñetas del siguiente contenido:\n\n{texto}")

async def analizar_mensaje(mensaje: str) -> dict:
    prompt = f"""Clasifica el riesgo de este mensaje de Discord.
Mensaje: "{mensaje[:300]}"
Devuelve SOLO este JSON:
{{"categoria": "SEGURO"|"TOXICO"|"SPAM"|"SCAM", "severidad": 0 a 5, "razon": "breve explicacion"}}"""
    try:
        raw = await asyncio.wait_for(_llamar_cerebras(SYSTEM_PROMPT_MOD, user_prompt=prompt, json_mode=True, max_tokens=80), timeout=3.5)
        if not raw: return {"categoria": "SEGURO", "severidad": 0, "razon": "Paso libre"}
        
        # Usamos el nuevo extractor blindado
        data = extraer_json(raw)
        if not data: return {"categoria": "SEGURO", "severidad": 0, "razon": "Fallo de parseo IA"}

        return {
            "categoria": str(data.get("categoria", "SEGURO")).upper(),
            "severidad": int(data.get("severidad", 0)),
            "razon": str(data.get("razon", "Sin razón"))[:80],
        }
    except Exception as e:
        logger.warning(f"Bypass preventivo en AutoMod IA (Timeout/Error): {e}")
        return {"categoria": "SEGURO", "severidad": 0, "razon": "Bypass preventivo"}

async def sugerir_respuesta_ticket(asunto: str, descripcion: str) -> str:
    return await preguntar_ia(f"Un usuario abrió un ticket de soporte.\nAsunto: {asunto}\nDetalles: {descripcion}\nRedacta una respuesta modelo para el staff: educada, empática, resolutiva y de máximo 3 líneas.")