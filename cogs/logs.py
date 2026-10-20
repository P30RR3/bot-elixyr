@commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot: return
        ch = self._canal_seguridad(message.guild)
        if not ch: return

        txt = message.content[:1000] if message.content else "*[Sin texto / Archivo]*"
        
        # ─── RADAR DE GHOST PINGS ───
        # Si el mensaje tenía menciones y fue borrado en menos de 3 minutos (180s)
        if message.mentions or message.role_mentions:
            tiempo_vida = (datetime.now(timezone.utc) - message.created_at).total_seconds()
            if tiempo_vida < 180:
                menciones = [m.mention for m in message.mentions] + [r.mention for r in message.role_mentions]
                alerta_ghost = (
                    f"### 👻 RADAR SOC // GHOST PING DETECTADO\n"
                    f"✦ ────────────────────────────────────────── ✦\n"
                    f"> **Infractor:** {message.author.mention} (`{message.author.id}`)\n"
                    f"> **Objetivos:** {', '.join(menciones)}\n"
                    f"> **Canal:** {message.channel.mention}\n"
                    f"> **Tiempo de vida:** `{int(tiempo_vida)} segundos`\n\n"
                    f"**Mensaje Original Capturado:**\n```{txt}```\n"
                    f"✦ ────────────────────────────────────────── ✦"
                )
                return await ch.send(alerta_ghost) # Retornamos para no enviar el log normal y duplicar

        # ─── LOG NORMAL DE BORRADO ───
        reporte = (
            f"### 🗑️ REGISTRO // MENSAJE DESTRUIDO\n"
            f"> **Autor:** {message.author.mention} `[{message.author.id}]`\n"
            f"> **Canal:** {message.channel.mention} • <t:{int(datetime.now(timezone.utc).timestamp())}:T>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{txt}"
        )
        await ch.send(reporte, view=IALogView(message.content) if message.content else None)