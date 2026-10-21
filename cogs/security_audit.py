"""
═══════════════════════════════════════════════════════════════════════════════
  ELIXYR GUARD // RED TEAM VULNERABILITY PENTEST ENGINE (NEW GEN v6.0)
  Capacidades: Live-Action Penetration Audit, Zero-Trust Permission Analyzer,
               Algorithmic Attack Surface Scoring & Tactical Mitigation Playbook
═══════════════════════════════════════════════════════════════════════════════
"""

import discord
from discord.ext import commands
from discord import app_commands
from utils.ia import preguntar_ia
from utils.ui import formato_editorial, barra_progreso, LiveActionController
from datetime import datetime, timezone
import asyncio

class SecurityAudit(commands.Cog):
    """Módulo de evaluación de vulnerabilidades y pentesting simulado."""
    def __init__(self, bot):
        self.bot = bot

    def _auditar_jerarquia_roles(self, guild: discord.Guild) -> dict:
        roles_admin = []
        roles_peligrosos = []
        for role in guild.roles:
            if role.is_default():
                continue
            if role.permissions.administrator:
                roles_admin.append(role.name)
            elif (role.permissions.manage_guild or role.permissions.manage_roles or 
                  role.permissions.manage_webhooks or role.permissions.ban_members):
                roles_peligrosos.append(role.name)
        return {"admins": roles_admin, "peligrosos": roles_peligrosos}

    def _auditar_canales(self, guild: discord.Guild) -> dict:
        everyone = guild.default_role
        menciones_abiertas = 0
        escritura_publica = 0
        
        for canal in guild.text_channels:
            perms = canal.permissions_for(everyone)
            if perms.mention_everyone:
                menciones_abiertas += 1
            if perms.send_messages:
                escritura_publica += 1
                
        return {
            "menciones": menciones_abiertas,
            "escritura": escritura_publica,
            "total": len(guild.text_channels)
        }

    @commands.hybrid_command(
        name="server-audit",
        description="Ejecuta un pentest simulado del servidor con telemetría en vivo e informe IA"
    )
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_guild=True, manage_roles=True)
    async def server_audit(self, ctx):
        await ctx.defer()
        guild = ctx.guild
        
        # ─── LIVE ACTION CONTROLLER ───
        live = LiveActionController(ctx, f"Pentest de Red // {guild.name}", total_pasos=5)
        await live.iniciar()

        # Paso 1: Roles
        await live.actualizar("Auditando jerarquía de roles, escalada de privilegios y permisos Admin...", exito=True)
        await asyncio.sleep(0.9)
        roles_data = self._auditar_jerarquia_roles(guild)

        # Paso 2: Canales
        await live.actualizar("Analizando superficie de canales públicos y vectores de mención masiva...", exito=True)
        await asyncio.sleep(0.9)
        canales_data = self._auditar_canales(guild)

        # Paso 3: Webhooks e Integraciones
        await live.actualizar("Inspeccionando integraciones de webhooks y bots con privilegios elevados...", exito=True)
        await asyncio.sleep(0.9)
        
        admins_humanos = [m for m in guild.members if m.guild_permissions.administrator and not m.bot]
        bots_admins = [m for m in guild.members if m.guild_permissions.administrator and m.bot]
        
        try:
            webhooks = await guild.webhooks()
            total_webhooks = len(webhooks)
        except Exception:
            total_webhooks = 0

        # Paso 4: Políticas 2FA y Verificación
        await live.actualizar("Comprobando nivel de autenticación perimetral y 2FA obligatorio...", exito=True)
        await asyncio.sleep(0.9)

        mfa_activo = guild.mfa_level == 1
        verif_dict = {
            discord.VerificationLevel.none: "Ninguno (VULNERABLE)",
            discord.VerificationLevel.low: "Bajo (Email)",
            discord.VerificationLevel.medium: "Medio (> 5 min)",
            discord.VerificationLevel.high: "Alto (> 10 min)",
            discord.VerificationLevel.highest: "Máximo (Teléfono)"
        }
        nivel_verif = verif_dict.get(guild.verification_level, str(guild.verification_level))

        # ─── CÁLCULO ALGORÍTMICO DEL ÍNDICE DE BLINDAJE (0-100) ───
        puntaje = 100
        if not mfa_activo:
            puntaje -= 25
        if guild.verification_level in [discord.VerificationLevel.none, discord.VerificationLevel.low]:
            puntaje -= 20
        if canales_data["menciones"] > 0:
            puntaje -= 15
        if len(admins_humanos) > 5:
            puntaje -= 10
        if len(bots_admins) > 3:
            puntaje -= 10
        if len(roles_data["peligrosos"]) > 4:
            puntaje -= 10
        puntaje = max(10, min(puntaje, 100))

        # Paso 5: Consultoría Red Team con Cerebras AI
        await live.actualizar("Generando dictamen y vector de ataque con Cerebras Cognitive Engine...", exito=True)
        
        matriz_seguridad = (
            f"INFRAESTRUCTURA: {guild.name} (ID: {guild.id})\n"
            f"Población: {guild.member_count} usuarios | Roles Totales: {len(guild.roles)}\n"
            f"Admins Humanos: {len(admins_humanos)} | Bots con Administrador: {len(bots_admins)}\n"
            f"Roles Admin: {len(roles_data['admins'])} | Roles con Permisos Críticos: {len(roles_data['peligrosos'])}\n"
            f"Webhooks Activos: {total_webhooks}\n"
            f"Nivel de Verificación: {nivel_verif}\n"
            f"2FA Obligatorio Moderación: {'Activado' if mfa_activo else 'DESACTIVADO (Crítico)'}\n"
            f"Canales donde @everyone puede escribir: {canales_data['escritura']} de {canales_data['total']}\n"
            f"Canales donde @everyone puede usar @everyone/@here: {canales_data['menciones']}\n"
            f"PUNTAJE MATEMÁTICO BASE: {puntaje}/100"
        )

        prompt = (
            f"Actúa como un Lead Penetration Tester (Red Team Lead) de Ciberseguridad en Discord.\n"
            f"Analiza la siguiente matriz de telemetría extraída de un servidor:\n\n"
            f"{matriz_seguridad}\n\n"
            f"Entrega un informe ejecutivo formal estructurado estrictamente así:\n"
            f"• **PRINCIPAL VECTOR DE ATAQUE:** (Explica en 2 líneas cómo un atacante sabotearía este servidor hoy)\n"
            f"• **VULNERABILIDADES CRÍTICAS DETECTADAS:** (Señala los 2 puntos más débiles)\n"
            f"• **PLAN DE BLINDAJE INMEDIATO (3 PASOS):** (Acciones técnicas exactas que el staff debe aplicar ya)\n\n"
            f"Tono profesional, severo, frío y táctico. Sin saludos ni charlas de relleno."
        )

        dictamen_ia = await preguntar_ia(prompt)
        await live.finalizar(f"Pentest completado. Blindaje estimado: {puntaje}/100.", error=(puntaje < 60))

        # RENDERIZADO DEL INFORME FINAL (EDITORIAL DE ALTA COSTURA)
        calificacion = "A+ (BLINDADO)" if puntaje >= 90 else "B (ACEPTABLE)" if puntaje >= 75 else "C (VULNERABLE)" if puntaje >= 50 else "F (CRÍTICO)"
        
        cuerpo = (
            f"> **Índice de Blindaje General:** {barra_progreso(puntaje, 100)} `{puntaje}/100` **[{calificacion}]**\n"
            f"> **Superficie Administrativa:** `{len(admins_humanos)}` Admins Humanos | `{len(bots_admins)}` Bots Privilegiados\n"
            f"> **Fugas de Mención Pública:** `{canales_data['menciones']}` canales permiten @everyone masivo\n"
            f"> **2FA para Moderación:** `{'Activo 🟢' if mfa_activo else 'INACTIVO 🔴 (Vulnerabilidad Alta)'}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"### 🎯 EVALUACIÓN DE INTRUSIÓN (RED TEAM REPORT)\n\n"
            f"{dictamen_ia}"
        )

        panel = formato_editorial(f"MATRIZ FORENSE DE SEGURIDAD // {guild.name}", cuerpo, badge="PENTEST-V6")
        await ctx.channel.send(panel)


async def setup(bot):
    await bot.add_cog(SecurityAudit(bot))