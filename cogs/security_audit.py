import discord
from discord.ext import commands
from discord import app_commands
from utils.ia import preguntar_ia
from datetime import datetime, timezone
import asyncio

def partir_texto(texto: str, max_len: int = 1900):
    """Divide reportes largos para no exceder los límites de Discord."""
    if len(texto) <= max_len: return [texto]
    partes = []
    while len(texto) > max_len:
        corte = texto.rfind("\n", 0, max_len)
        if corte == -1: corte = max_len
        partes.append(texto[:corte].strip())
        texto = texto[corte:].strip()
    if texto: partes.append(texto)
    return partes

class SecurityAudit(commands.Cog):
    """
    Módulo de Evaluación de Vulnerabilidades (Vulnerability Assessment).
    Escanea la superficie de ataque del servidor y genera reportes con IA.
    """
    def __init__(self, bot):
        self.bot = bot

    def _scan_dangerous_roles(self, guild: discord.Guild) -> dict:
        """Escanea roles en busca de escalada de privilegios y permisos críticos."""
        peligrosos = []
        admin_roles = []
        for role in guild.roles:
            if role.is_default(): continue
            if role.permissions.administrator:
                admin_roles.append(role.name)
            elif role.permissions.manage_guild or role.permissions.manage_roles or role.permissions.manage_webhooks or role.permissions.ban_members:
                peligrosos.append(role.name)
        return {"admins": admin_roles, "peligrosos": peligrosos}

    def _scan_channel_risks(self, guild: discord.Guild) -> dict:
        """Busca canales mal configurados que puedan ser usados para Raids."""
        everyone = guild.default_role
        riesgo_mencion = 0
        riesgo_escritura = 0
        
        for canal in guild.text_channels:
            perms = canal.permissions_for(everyone)
            if perms.mention_everyone: riesgo_mencion += 1
            if perms.send_messages: riesgo_escritura += 1
            
        return {"mencion_everyone": riesgo_mencion, "escritura_publica": riesgo_escritura, "total": len(guild.text_channels)}

    @commands.hybrid_command(name="server-audit", description="Escaneo forense profundo de vulnerabilidades del servidor analizado por IA")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_guild=True, manage_roles=True)
    async def server_audit(self, ctx):
        await ctx.defer()
        guild = ctx.guild
        msg_estado = await ctx.send("📡 *Iniciando escaneo de superficie de ataque (Red Team Pentest)...*")

        # ─── 1. RECOLECCIÓN DE TELEMETRÍA FORENSE ───
        await msg_estado.edit(content="📡 *Analizando jerarquía de roles y permisos críticos...*")
        roles_data = self._scan_dangerous_roles(guild)
        
        await msg_estado.edit(content="📡 *Auditando configuraciones de canales y webhooks...*")
        canales_data = self._scan_channel_risks(guild)
        
        admins_humanos = [m for m in guild.members if m.guild_permissions.administrator and not m.bot]
        bots_admins = [m for m in guild.members if m.guild_permissions.administrator and m.bot]
        
        try:
            webhooks = await guild.webhooks()
            total_webhooks = len(webhooks)
        except Exception:
            total_webhooks = "No auditables (Falta permiso)"

        mfa_activo = "Activado (Seguro)" if guild.mfa_level == 1 else "DESACTIVADO (Vulnerabilidad Crítica)"
        
        verif_dict = {
            discord.VerificationLevel.none: "Ninguno (Peligro extremo)",
            discord.VerificationLevel.low: "Bajo (Email verificado)",
            discord.VerificationLevel.medium: "Medio (Registrado > 5 min)",
            discord.VerificationLevel.high: "Alto (Miembro > 10 min)",
            discord.VerificationLevel.highest: "Máximo (Teléfono verificado)"
        }
        nivel_verif = verif_dict.get(guild.verification_level, str(guild.verification_level))

        # ─── 2. CONSTRUCCIÓN DE LA MATRIZ DE DATOS ───
        matriz_seguridad = (
            f"INFRAESTRUCTURA: {guild.name} (ID: {guild.id})\n"
            f"Población: {guild.member_count} miembros | Roles totales: {len(guild.roles)}\n"
            f"Admins Humanos: {len(admins_humanos)}\n"
            f"Bots con Administrador Completo: {len(bots_admins)}\n"
            f"Roles con Admin: {len(roles_data['admins'])} | Roles Peligrosos (Ban/Manage): {len(roles_data['peligrosos'])}\n"
            f"Webhooks Activos: {total_webhooks}\n"
            f"Nivel de Verificación de Entrada: {nivel_verif}\n"
            f"2FA Obligatorio para Moderadores: {mfa_activo}\n"
            f"Canales con escritura de @everyone: {canales_data['escritura_publica']} de {canales_data['total']}\n"
            f"Canales donde @everyone puede usar @everyone/@here: {canales_data['mencion_everyone']}"
        )

        # ─── 3. EVALUACIÓN CON CEREBRAS COGNITIVE ENGINE ───
        await msg_estado.edit(content="🧠 *Procesando telemetría con Cerebras AI...*")
        
        prompt = (
            f"Actúa como un Auditor Principal de Ciberseguridad (Red Team) especializado en Discord.\n"
            f"Analiza la siguiente telemetría de seguridad extraída del servidor:\n\n"
            f"{matriz_seguridad}\n\n"
            f"Genera un informe técnico formal, estructurado estrictamente así:\n"
            f"• **PUNTAJE DE BLINDAJE:** [X/100] (Explica en 1 línea el motivo de la nota)\n"
            f"• **SUPERFICIE DE ATAQUE CRÍTICA:** (Menciona cuál de los datos representa el mayor vector de ataque o riesgo de raid/sabotaje)\n"
            f"• **VECTORES SECUNDARIOS:** (Analiza bots con admin, webhooks y permisos de @everyone)\n"
            f"• **PLAN DE MITIGACIÓN INMEDIATO (3 PASOS):** (Acciones claras y exactas que el administrador debe ejecutar ahora mismo)\n\n"
            f"Usa tono serio, profesional, frío y táctico. Eres una IA de seguridad, no un asistente amigable."
        )

        dictamen_ia = await preguntar_ia(prompt)
        await msg_estado.delete()

        # ─── 4. REPORTE VISUAL DE ALTA COSTURA ───
        cabecera = (
            f"# 🛡️ MATRIZ FORENSE DE SEGURIDAD // {guild.name.upper()}\n"
            f"> **Telemetría Operativa:** `{len(admins_humanos)} Admins` | `{len(bots_admins)} Bots Privilegiados` | `{total_webhooks} Webhooks`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        cuerpo = dictamen_ia + "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n-# Elixyr Sentinel Security Audit • Cerebras Cognitive Engine"
        
        texto_final = cabecera + cuerpo
        for parte in partir_texto(texto_final):
            await ctx.send(parte)

async def setup(bot):
    await bot.add_cog(SecurityAudit(bot))