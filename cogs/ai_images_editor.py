import discord
from discord.ext import commands
from discord import app_commands
import os
import io
import json
import time
import asyncio
import tempfile
import aiohttp
import base64
import traceback
from gradio_client import Client, handle_file
from dotenv import load_dotenv
from utils.ia import preguntar_ia

load_dotenv()

# Cloudflare FLUX Schnell para Texto a Imagen puro
CF_MODEL_TEXT = "@cf/black-forest-labs/flux-1-schnell"

# Espacio ZeroGPU de alto rendimiento para Edición Conversacional tipo "Nano Banana"
QWEN_SPACE = "kulkas2pintu/QWEN_EDIT_IMAGE"


def _obtener_credenciales_limpias():
    raw_acc = os.getenv("CLOUDFLARE_ACCOUNT_ID") or ""
    raw_tok = os.getenv("CLOUDFLARE_API_TOKEN") or ""

    acc_id = raw_acc.strip().replace('"', '').replace("'", "")
    token = raw_tok.strip().replace('"', '').replace("'", "")

    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    return acc_id, token


async def _traducir_con_cerebras(prompt_usuario: str, es_edicion: bool) -> str:
    """Prepara el prompt en inglés claro para que el modelo lo entienda al 100%."""
    if es_edicion:
        prompt_ia = (
            f"You are an AI photo editor instruction rewriter.\n"
            f"Convert this edit request into a clear, direct English instruction for image editing while preserving identity: '{prompt_usuario}'.\n"
            f"Example: 'add stylish dark sunglasses to the person, maintain facial features and hairstyle'.\n"
            f"Return ONLY the final instruction in English, no quotes, no extra chat."
        )
    else:
        prompt_ia = (
            f"Translate and enhance this image prompt into English: '{prompt_usuario}'.\n"
            f"Return ONLY the final prompt text."
        )

    try:
        res = await preguntar_ia(prompt_ia)
        if res.startswith("❌") or res.startswith("⚠️"):
            return prompt_usuario
        return res.replace('"', '').strip()
    except Exception as e:
        print(f"[DEBUG-IA] Error en Cerebras: {e}. Usando orden original.")
        return prompt_usuario


async def _generar_texto_con_cloudflare(prompt_en: str) -> io.BytesIO | None:
    """Genera imágenes desde cero usando tu cuenta de Cloudflare."""
    acc_id, token = _obtener_credenciales_limpias()
    if not acc_id or not token:
        print("[SEC ERROR] Faltan credenciales de Cloudflare en .env")
        return None

    url = f"https://api.cloudflare.com/client/v4/accounts/{acc_id}/ai/run/{CF_MODEL_TEXT}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {"prompt": prompt_en, "steps": 4}

    print(f"[DEBUG-CF] Ejecutando FLUX Schnell Text2Img...")
    t0 = time.time()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=40)) as resp:
                raw_data = await resp.read()
                print(f"[DEBUG-CF] Cloudflare respondió en {time.time()-t0:.2f}s | HTTP {resp.status}")

                if raw_data.startswith(b'\x89PNG') or raw_data.startswith(b'\xff\xd8') or b'JFIF' in raw_data[:25]:
                    buf = io.BytesIO(raw_data)
                    buf.seek(0)
                    return buf

                try:
                    data = json.loads(raw_data.decode("utf-8"))
                    if "result" in data and "image" in data["result"]:
                        buf = io.BytesIO(base64.b64decode(data["result"]["image"]))
                        buf.seek(0)
                        return buf
                except Exception:
                    pass

                return None
    except Exception as err:
        print(f"[CF EXCEPTION] {err}")
        return None


def _editar_con_qwen_sync(temp_path: str, prompt_en: str) -> str | None:
    """
    Llama al cluster de Qwen-Image-Edit (equivalente libre a Nano Banana)
    conservando la fisonomía y el rostro original.
    """
    try:
        print(f"[DEBUG-QWEN] Conectando con nodo GPU de Qwen Image Edit...")
        client = Client(QWEN_SPACE)
        
        # Ejecuta la predicción del modelo
        result = client.predict(
            image=handle_file(temp_path),
            prompt=prompt_en,
            api_name="/edit"
        )
        
        # Gradio puede devolver una tupla (ruta_imagen, seed) o solo la ruta
        if isinstance(result, (list, tuple)):
            return result[0]
        return result
    except Exception as e:
        print(f"[DEBUG-QWEN ERROR] Falló la inferencia en Qwen: {e}")
        traceback.print_exc()
        return None


class AIImageEditor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _extraer_url_msg(self, msg: discord.Message) -> discord.Attachment | None:
        if msg.attachments:
            for a in msg.attachments:
                if a.content_type and a.content_type.startswith("image/"):
                    return a
        return None

    @commands.hybrid_command(
        name="edit",
        description="Genera una nueva imagen o modifícala conversacionalmente"
    )
    @app_commands.describe(
        prompt="Qué quieres cambiar (ej: ponle lentes oscuros, cambia el fondo, ponme una camisa roja)",
        imagen="Opcional: Adjunta la imagen que quieres modificar"
    )
    async def edit(self, ctx: commands.Context, prompt: str, imagen: discord.Attachment = None):
        await ctx.defer()

        target_bytes = None

        # 1. Resolver el archivo de la imagen
        if imagen and imagen.content_type and imagen.content_type.startswith("image/"):
            print(f"[DEBUG] Imagen adjuntada directamente ({imagen.size} bytes)")
            target_bytes = await imagen.read()
        elif ctx.message and ctx.message.attachments:
            att = self._extraer_url_msg(ctx.message)
            if att:
                print(f"[DEBUG] Imagen detectada en adjunto de mensaje")
                target_bytes = await att.read()
        elif ctx.message and ctx.message.reference and ctx.message.reference.message_id:
            try:
                ref = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                att = self._extraer_url_msg(ref)
                if att:
                    print(f"[DEBUG] Imagen detectada en mensaje citado")
                    target_bytes = await att.read()
            except Exception as e:
                print(f"[DEBUG] Error al buscar mensaje citado: {e}")

        # 2. Análisis y traducción de la instrucción
        es_edicion = (target_bytes is not None)
        print(f"[DEBUG] Prompt recibido: '{prompt}' | Modo Edición: {es_edicion}")
        prompt_en = await _traducir_con_cerebras(prompt, es_edicion=es_edicion)
        print(f"[DEBUG] Prompt optimizado: '{prompt_en}'")

        # 3. MODO EDICIÓN (Qwen-Image-Edit, estilo Nano Banana)
        if es_edicion:
            # Creamos un archivo temporal para que Gradio lo lea de forma segura
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_path = temp_file.name
            try:
                temp_file.write(target_bytes)
                temp_file.close()

                # Ejecutamos en un hilo separado para NO bloquear el bucle de Discord
                t0 = time.time()
                ruta_resultado = await asyncio.to_thread(_editar_con_qwen_sync, temp_path, prompt_en)
                print(f"[DEBUG] Proceso completado en {time.time()-t0:.2f}s")

                if not ruta_resultado or not os.path.exists(ruta_resultado):
                    return await ctx.send("❌ El motor de edición no pudo procesar la imagen en este momento.")

                file = discord.File(ruta_resultado, filename="editado.png")
                embed = discord.Embed(
                    description=f"🪄 **Orden:** `{prompt}`\n🧬 **pedido:** `Su pedido esta aca`",
                    color=0x2b2d31
                )
                embed.set_image(url="attachment://editado.png")
                await ctx.send(file=file, embed=embed)

            finally:
                if os.path.exists(temp_path):
                    try: os.remove(temp_path)
                    except Exception: pass

        # 4. MODO GENERACIÓN DESDE CERO (Cloudflare FLUX)
        else:
            buffer = await _generar_texto_con_cloudflare(prompt_en)
            if not buffer:
                return await ctx.send("❌ Error al generar la imagen desde Cloudflare.")

            file = discord.File(buffer, filename="render.png")
            embed = discord.Embed(
                description=f"🎨 **Prompt:** `{prompt}`\n⚡ **Motor:** `Cloudflare FLUX.1 Schnell`",
                color=0x2b2d31
            )
            embed.set_image(url="attachment://render.png")
            await ctx.send(file=file, embed=embed)


async def setup(bot):
    await bot.add_cog(AIImageEditor(bot))