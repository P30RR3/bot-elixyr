import os
import asyncio
import json
import logging
from dotenv import load_dotenv
from cerebras.cloud.sdk import Cerebras

load_dotenv()

# Logger de telemetría IA
logger = logging.getLogger("ElixyrIA")

CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

client = Cerebras(api_key=CEREBRAS_API_KEY) if CEREBRAS_API_KEY else None
CEREBRAS_MODEL = "llama3.1-70b"

MAX_REINTENTOS = 2
ESPERA_BASE = 2

# ═════════════════════════════════════════════════════════════
#  PROMPTS DEL SISTEMA
# ═════════════════════════════════════════════════════════════

# 1. MODO CHAT NATURAL (Para /ask y respuestas libres)
SYSTEM_PROMPT_CHAT = """Eres un asistente de inteligencia artificial conversacional, perspicaz, empático y versátil.

Directrices de conversación:
1. TONO Y ACTITUD:
   - Actúa de forma natural, amigable, humana y cercana, exactamente como un asistente conversacional estándar (estilo ChatGPT o Claude).
   - NO asumas un rol de ciberseguridad, militar o corporativo a menos que el usuario te pida hablar de eso.
   - Eres libre de hablar sobre cualquier tema: tecnología, charla casual, filosofía, código, anime, consejos, videojuegos, bromas o cualquier duda cotidiana.

2. MEMORIA Y CONTEXTO:
   - Tienes acceso al historial reciente de la conversación. Mantén la coherencia de lo que el usuario y tú han estado hablando, recordando detalles, nombres y referencias previas.
   - Adáptate al tono del usuario: si bromea, sigue el juego con buen humor; si hace una pregunta seria o técnica, responde con profundidad y claridad.

3. ESTILO DE ESCRITURA:
   - Usa un formato de Markdown limpio para Discord (negritas sutiles, listas con viñetas cuando amerite y bloques de código para código).
   - Evita respuestas excesivamente acartonadas, no uses introducciones vacías como '¡Hola! Claro que sí, con gusto te ayudo con...'. Ve directo a la conversación con fluidez y frescura."""

# 2. PROMPT IDS (Cortafuegos de moderación y filtrado semántico)
SYSTEM_PROMPT_MOD = """Eres el firewall de moderación y ciberseguridad de Elixyr Guard.
Tu trabajo es clasificar si un mensaje en Discord representa una AMENAZA REAL, ATAQUE O FRAUDE.

DIRECTRICES OBLIGATORIAS:
1. CLASIFICA COMO "SEGURO" (Severidad 0):
   - Desahogos personales, salud, comida o cansancio (ej: "no he comido hace una semana", "tengo hambre", "me duele la cabeza").
   - Expresiones coloquiales, bromas de videojuegos o frustración común (ej: "me mataron", "los voy a reventar en la partida").
   - Evasiones que resulten ser charlas inocentes.

2. CLASIFICA COMO "TOXICO" (Severidad 3 a 5):
   - Ataques personales directos, insultos camuflados/abreviados (ej: 'p t o', 'm4ldito'), humillación, acoso u odio hacia otros usuarios.

3. CLASIFICA COMO "SCAM" / "SPAM" (Severidad 5):
   - Enlaces sospechosos, phishing de Discord Nitro gratis, Steam, tokens, airdrops o saturación maliciosa.

Responde ÚNICAMENTE con un JSON válido de una sola línea con este formato:
{"categoria": "SEGURO"|"TOXICO"|"SPAM"|"SCAM", "severidad": 0 a 5, "razon": "breve explicacion"}"""


# ═════════════════════════════════════════════════════════════
#  CONEXIÓN Y CONTROL DEL MOTOR CEREBRAS
# ═════════════════════════════════════════════════════════════

async def verificar_conexion_ia() -> bool:
    """Verifica la conectividad y sincroniza el mejor modelo disponible en Cerebras."""
    global CEREBRAS_MODEL
    if not client:
        print("[!] ADVERTENCIA: CEREBRAS_API_KEY no detectada en el archivo .env")
        return False

    try:
        modelos = await asyncio.to_thread(client.models.list)
        print("=== MOTOR CEREBRAS AI EN LÍNEA ===")
        for m in modelos.data:
            print(f" [+] Modelo detectado: {m.id}")
        print("==================================")
        
        if modelos.data:
            nombres = [m.id for m in modelos.data]
            if "llama3.3-70b" in nombres:
                CEREBRAS_MODEL = "llama3.3-70b"
            elif "llama3.1-70b" in nombres:
                CEREBRAS_MODEL = "llama3.1-70b"
            else:
                CEREBRAS_MODEL = modelos.data[0].id
            print(f"[!] Enlazado al modelo principal: {CEREBRAS_MODEL}")
        return True

    except Exception as e:
        print(f"[!] Advertencia al conectar con Cerebras: {e}")
        return False


async def _llamar_cerebras(
    system_prompt: str, 
    user_prompt: str = None, 
    json_mode: bool = False, 
    mensajes_historial: list = None, 
    max_tokens: int = 1500
) -> str | None:
    """Llamada base asíncrona al SDK de Cerebras con control de reintentos."""
    if not client:
        return None

    if mensajes_historial:
        messages = [{"role": "system", "content": system_prompt}] + mensajes_historial
    else:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt or ""}
        ]

    kwargs = {
        "model": CEREBRAS_MODEL,
        "messages": messages,
        "temperature": 0.1 if json_mode else 0.6,
        "max_completion_tokens": max_tokens,
    }

    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    for intento in range(MAX_REINTENTOS):
        try:
            response = await asyncio.to_thread(client.chat.completions.create, **kwargs)
            if response and response.choices:
                return response.choices[0].message.content.strip()
            return None

        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "rate" in error_msg or "503" in error_msg:
                await asyncio.sleep(ESPERA_BASE * (intento + 1))
                continue
            logger.error(f"Error en inferencia Cerebras: {e}")
            return None
    return None


# ═════════════════════════════════════════════════════════════
#  FUNCIONES PÚBLICAS DE CONSULTA
# ═════════════════════════════════════════════════════════════

async def preguntar_ia(
    prompt: str = None, 
    contexto: str = None, 
    historial: list = None, 
    json_mode: bool = False, 
    system_prompt: str = None, 
    max_tokens: int = 1500
) -> str:
    """
    Función de propósito general para consultar a la IA.
    Soporta historial conversacional, JSON mode forzado y prompts de sistema personalizados.
    """
    sys_p = system_prompt or SYSTEM_PROMPT_CHAT

    if historial:
        respuesta = await _llamar_cerebras(
            sys_p, 
            mensajes_historial=historial, 
            json_mode=json_mode, 
            max_tokens=max_tokens
        )
    else:
        texto_final = prompt if not contexto else f"Contexto:\n{contexto}\n\nPetición:\n{prompt}"
        respuesta = await _llamar_cerebras(
            sys_p, 
            user_prompt=texto_final, 
            json_mode=json_mode, 
            max_tokens=max_tokens
        )

    if not respuesta:
        return "⚠️ *El enlace neuronal con Cerebras AI no respondió a tiempo. Intente nuevamente en unos segundos.*"
    return respuesta


async def resumir_texto(texto: str) -> str:
    """Genera una síntesis ejecutiva clara y limpia de un texto largo."""
    prompt = f"Genera un resumen ordenado, claro y con viñetas del siguiente contenido:\n\n{texto}"
    return await preguntar_ia(prompt)


async def analizar_mensaje(mensaje: str) -> dict:
    """
    Firewall semántico de ultra-baja latencia (máximo 80 tokens).
    Inspecciona si hay toxicidad camuflada o scam con timeout estricto para no colgar el chat.
    """
    prompt = f"""Clasifica el riesgo de este mensaje de Discord.
Mensaje: "{mensaje[:300]}"

Devuelve SOLO este JSON:
{{"categoria": "SEGURO"|"TOXICO"|"SPAM"|"SCAM", "severidad": 0 a 5, "razon": "breve explicacion"}}"""

    try:
        raw = await asyncio.wait_for(
            _llamar_cerebras(SYSTEM_PROMPT_MOD, user_prompt=prompt, json_mode=True, max_tokens=80),
            timeout=3.5
        )
        if not raw:
            return {"categoria": "SEGURO", "severidad": 0, "razon": "Paso libre"}

        data = json.loads(raw)
        return {
            "categoria": str(data.get("categoria", "SEGURO")).upper(),
            "severidad": int(data.get("severidad", 0)),
            "razon": str(data.get("razon", ""))[:80],
        }
    except Exception:
        # En caso de timeout o saturación de API, se declara SEGURO para nunca congelar los mensajes
        return {"categoria": "SEGURO", "severidad": 0, "razon": "Bypass preventivo"}


async def sugerir_respuesta_ticket(asunto: str, descripcion: str) -> str:
    """Genera una respuesta preliminar para el Staff ante un nuevo ticket."""
    return await preguntar_ia(
        f"Un usuario abrió un ticket de soporte en Discord.\n"
        f"Asunto: {asunto}\nDetalles: {descripcion}\n\n"
        f"Redacta una respuesta modelo para el staff: educada, empática, resolutiva y de máximo 3 líneas."
    )