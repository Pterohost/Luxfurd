# Discord Guardian Bot 6.5 - Pterohost (https://pterohost.com)
# MIT License: https://github.com/Pterohost/Luxfurd
# Copyright (c) 2025 Pterohost

import discord
from discord.ext import commands
from ..bot import GuardianBot

class LoggingCog(commands.Cog):
    def __init__(self, bot: GuardianBot) -> None:
        self.bot = bot

    async def log_incident(self, g: discord.Guild, desc: str, user: discord.User = None) -> None:
        cid = self.bot.config.guild_cfg(g.id)["logging"]["log_channel_id"]
        if cid and (ch := g.get_channel(cid)):
            embed = discord.Embed(
                title="Инцидент", description=desc, color=discord.Color.orange(), timestamp=discord.utils.utcnow()
            )
            if user:
                embed.set_author(name=str(user), icon_url=user.display_avatar.url)
            await ch.send(embed=embed)

    async def alert(self, g: discord.Guild, txt: str) -> None:
        cid = self.bot.config.guild_cfg(g.id)["logging"]["alert_channel_id"]
        if cid and (ch := g.get_channel(cid)):
            embed = discord.Embed(
                title="Алерт", description=txt, color=discord.Color.red(), timestamp=discord.utils.utcnow()
            )
            await ch.send(embed=embed)