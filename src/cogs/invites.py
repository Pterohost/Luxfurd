# Discord Guardian Bot 6.5 - Pterohost (https://pterohost.com)
# MIT License: https://github.com/Pterohost/Luxfurd
# Copyright (c) 2025 Pterohost

import discord
from discord.ext import commands
from discord import app_commands
from collections import defaultdict
from ..bot import GuardianBot
from ..utils import apply_action, is_admin, LOG

class InviteCog(commands.Cog):
    def __init__(self, bot: GuardianBot) -> None:
        self.bot = bot
        self._inv = defaultdict(dict)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for g in self.bot.guilds:
            try:
                self._inv[g.id] = await self._snap(g)
            except discord.HTTPException as e:
                LOG.error(f"Ошибка кэширования инвайтов для {g.name}: {e}")

    async def _snap(self, g: discord.Guild) -> dict[str, int]:
        return {i.code: i.uses for i in await g.invites()}

    @commands.Cog.listener()
    async def on_member_join(self, m: discord.Member) -> None:
        before, after = self._inv[m.guild.id], await self._snap(m.guild)
        used = next((cannon for cannon, u in after.items() if u > before.get(c, 0)), None)
        self._inv[m.guild.id] = after
        if used:
            lg = self.bot.get_cog("LoggingCog")
            if lg:
                await lg.log_incident(m.guild, f"Инвайт {used} использовал {m}", m)

    @app_commands.command(name="pause_invites", description="Удалить все активные инвайты")
    @app_commands.guild_only()
    async def pause_invites(self, itx: discord.Interaction):
        if not is_admin(itx.user, itx.guild, self.bot.config.global_cfg()["owner_id"]):
            await itx.response.send_message("Нет прав", ephemeral=True)
            return
        n = 0
        for inv in await itx.guild.invites():
            await inv.delete(reason="pause_invites")
            n += 1
        await itx.response.send_message(f"Удалено инвайтов: {n}", ephemeral=True)

    @app_commands.command(name="lock_webhooks", description="Запретить новые веб-хуки")
    @app_commands.guild_only()
    async def lock_hooks(self, itx: discord.Interaction):
        if not is_admin(itx.user, itx.guild, self.bot.config.global_cfg()["owner_id"]):
            await itx.response.send_message("Нет прав", ephemeral=True)
            return
        cfg = self.bot.config.guild_cfg(itx.guild.id)
        if cfg["webhooks_locked"]:
            await itx.response.send_message("Защита активна", ephemeral=True)
            return
        cfg["invites"]["webhook_whitelist"] = [str(h.id) for h in await itx.guild.webhooks()]
        cfg["webhooks_locked"] = True
        self.bot.config.save_guild(itx.guild.id)
        await itx.response.send_message("Веб-хуки зафиксированы", ephemeral=True)

    @app_commands.command(name="unlock_webhooks", description="Снять запрет на веб-хуки")
    @app_commands.guild_only()
    async def unlock_hooks(self, itx: discord.Interaction):
        if not is_admin(itx.user, itx.guild, self.bot.config.global_cfg()["owner_id"]):
            await itx.response.send_message("Нет прав", ephemeral=True)
            return
        cfg = self.bot.config.guild_cfg(itx.guild.id)
        if not cfg["webhooks_locked"]:
            await itx.response.send_message("Защита выключена", ephemeral=True)
            return
        cfg["webhooks_locked"] = False
        self.bot.config.save_guild(itx.guild.id)
        await itx.response.send_message("Защита снята", ephemeral=True)

    @commands.Cog.listener()
    async def on_webhooks_update(self, ch: discord.abc.GuildChannel) -> None:
        cfg = self.bot.config.guild_cfg(ch.guild.id)
        if not cfg["webhooks_locked"]:
            return
        allowed = set(cfg["invites"]["webhook_whitelist"])
        for hook in await ch.webhooks():
            if str(hook.id) not in allowed and hook.user:
                await apply_action(self.bot, hook.user, cfg["actions"]["webhook_new"], "webhook_new", guild=ch.guild)
                await hook.delete(reason="Unauthorized webhook")