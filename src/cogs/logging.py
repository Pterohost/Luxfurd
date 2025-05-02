# Copyright (c) 2025 Pterohost
# Licensed under the MIT License (https://opensource.org/licenses/MIT)

import discord
from discord.ext import commands
from ..bot import GuardianBot
from ..utils import is_admin
from datetime import datetime, timezone

class LoggingCog(commands.Cog):
    def __init__(self, bot: GuardianBot) -> None:
        self.bot = bot

    async def log_incident(self, g: discord.Guild, desc: str, user: discord.User = None) -> None:
        cid = self.bot.config.guild_cfg(g.id)["logging"]["log_channel_id"]
        if cid and (ch := g.get_channel(cid)):
            embed = discord.Embed(
                title="Инцидент",
                description=desc,
                color=discord.Color.orange(),
                timestamp=datetime.now(timezone.utc)
            )
            if user:
                embed.set_author(name=str(user), icon_url=user.display_avatar.url)
            await ch.send(embed=embed)

    async def alert(self, g: discord.Guild, txt: str) -> None:
        cid = self.bot.config.guild_cfg(g.id)["logging"]["alert_channel_id"]
        if cid and (ch := g.get_channel(cid)):
            embed = discord.Embed(
                title="Алерт",
                description=txt,
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            await ch.send(embed=embed)

    async def log_join_leave(self, guild: discord.Guild, user: discord.User, event_type: str):
        cfg = self.bot.config.guild_cfg(guild.id)
        cid = cfg["logging"]["join_leave_log_channel_id"]
        if cid and (ch := guild.get_channel(cid)):
            color = discord.Color.green() if event_type == "join" else discord.Color.red()
            embed = discord.Embed(
                title="Лог входа" if event_type == "join" else "Лог выхода",
                color=color,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Пользователь", value=user.name, inline=False)
            embed.add_field(name="ID", value=str(user.id), inline=False)
            embed.add_field(name="Дата создания", value=user.created_at.strftime("%d/%m/%Y %H:%M:%S"), inline=False)
            embed.add_field(name="Бот?", value="Да" if user.bot else "Нет", inline=False)
            embed.set_thumbnail(url=user.display_avatar.url)
            view = discord.ui.View(timeout=None)
            pass_button = discord.ui.Button(label="Пройти капчу", style=discord.ButtonStyle.green, custom_id=f"pass_captcha_{user.id}_{guild.id}")
            ban_button = discord.ui.Button(label="Бан", style=discord.ButtonStyle.red, custom_id=f"ban_{user.id}_{guild.id}")

            async def pass_callback(interaction: discord.Interaction):
                if not is_admin(interaction.user, interaction.guild, self.bot.config.global_cfg()["owner_id"]):
                    await interaction.response.send_message("Нет прав.", ephemeral=True)
                    return
                await interaction.response.send_message(f"Капча пройдена для {user.name}.", ephemeral=True)
                pass_button.disabled = True
                ban_button.disabled = True
                await interaction.message.edit(view=view)

            async def ban_callback(interaction: discord.Interaction):
                if not is_admin(interaction.user, interaction.guild, self.bot.config.global_cfg()["owner_id"]):
                    await interaction.response.send_message("Нет прав.", ephemeral=True)
                    return
                try:
                    await guild.ban(user, reason="Забанен через лог")
                    await interaction.response.send_message(f"Пользователь {user.name} забанен.", ephemeral=True)
                    pass_button.disabled = True
                    ban_button.disabled = True
                    await interaction.message.edit(view=view)
                except discord.Forbidden:
                    await interaction.response.send_message("Недостаточно прав для бана.", ephemeral=True)

            pass_button.callback = pass_callback
            ban_button.callback = ban_callback
            view.add_item(pass_button)
            view.add_item(ban_button)
            await ch.send(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_member_remove(self, m: discord.Member) -> None:
        await self.log_join_leave(m.guild, m, "leave")
        if m.id in self.bot.join_times[m.guild.id]:
            del self.bot.join_times[m.guild.id][m.id]