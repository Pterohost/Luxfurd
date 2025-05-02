# Copyright (c) 2025 Pterohost
# Licensed under the MIT License (https://opensource.org/licenses/MIT)

import discord
from discord.ext import commands
from ..bot import GuardianBot
from ..utils import is_admin
import json
import textwrap
from datetime import datetime, timezone

class AdminCog(commands.Cog):
    def __init__(self, bot: GuardianBot) -> None:
        self.bot = bot

    @discord.app_commands.command(name="set_threshold", description="Изменить параметр конфигурации")
    @discord.app_commands.guild_only()
    async def set_threshold(self, itx: discord.Interaction, key: str, value: str):
        if not is_admin(itx.user, itx.guild, self.bot.config.global_cfg()["owner_id"]):
            await itx.response.send_message("Нет прав", ephemeral=True)
            return
        cfg = self.bot.config.guild_cfg(itx.guild.id)
        node = cfg
        keys = key.split(".")
        for p in keys[:-1]:
            node = node.setdefault(p, {})
        node[keys[-1]] = int(value) if value.isdigit() else value.lower()
        self.bot.config.save_guild(itx.guild.id)
        await itx.response.send_message("Обновлено", ephemeral=True)

    @discord.app_commands.command(name="show_config", description="Показать конфигурацию сервера")
    @discord.app_commands.guild_only()
    async def show_config(self, itx: discord.Interaction):
        if not is_admin(itx.user, itx.guild, self.bot.config.global_cfg()["owner_id"]):
            await itx.response.send_message("Нет прав", ephemeral=True)
            return
        txt = json.dumps(self.bot.config.guild_cfg(itx.guild.id), ensure_ascii=False, indent=2)
        await itx.response.send_message(f"```json\n{textwrap.shorten(txt, 1900)}\n```", ephemeral=True)

    @discord.app_commands.command(name="show_incidents", description="Показать последние инциденты")
    @discord.app_commands.guild_only()
    async def show_incidents(self, itx: discord.Interaction):
        if not is_admin(itx.user, itx.guild, self.bot.config.global_cfg()["owner_id"]):
            await itx.response.send_message("Нет прав", ephemeral=True)
            return
        incidents = [i for i in self.bot.incidents if i["guild_id"] == itx.guild.id]
        if not incidents:
            await itx.response.send_message("Инцидентов нет", ephemeral=True)
            return
        txt = "\n".join(f"{i['timestamp']} | User: {i['user_id']} | {i['reason']}" for i in incidents[-10:])
        await itx.response.send_message(f"```log\n{txt}\n```", ephemeral=True)

    @discord.app_commands.command(name="stats", description="Показать статистику инцидентов")
    @discord.app_commands.guild_only()
    async def stats(self, itx: discord.Interaction):
        if not is_admin(itx.user, itx.guild, self.bot.config.global_cfg()["owner_id"]):
            await itx.response.send_message("Нет прав", ephemeral=True)
            return
        incidents = [i for i in self.bot.incidents if i["guild_id"] == itx.guild.id]
        embed = discord.Embed(
            title="Статистика инцидентов",
            description=f"Всего инцидентов: **{len(incidents)}**",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(
            name="Последние 5",
            value="\n".join(f"{i['timestamp']} | {i['reason']}" for i in incidents[-5:]) or "Нет данных",
            inline=False
        )
        await itx.response.send_message(embed=embed)

    @discord.app_commands.command(name="ignore_role", description="Добавить/удалить роль в игнор-лист")
    @discord.app_commands.guild_only()
    @discord.app_commands.describe(role="Роль", action="Добавить или удалить")
    async def ignore_role(self, itx: discord.Interaction, role: discord.Role, action: str):
        if not is_admin(itx.user, itx.guild, self.bot.config.global_cfg()["owner_id"]):
            await itx.response.send_message("Нет прав", ephemeral=True)
            return
        cfg = self.bot.config.guild_cfg(itx.guild.id)
        action = action.lower()
        if action == "add":
            if role.id not in cfg["ignore_roles"]:
                cfg["ignore_roles"].append(role.id)
                self.bot.config.save_guild(itx.guild.id)
                await itx.response.send_message(f"Роль {role.name} добавлена в игнор-лист", ephemeral=True)
            else:
                await itx.response.send_message(f"Роль {role.name} уже в игнор-листе", ephemeral=True)
        elif action == "remove":
            if role.id in cfg["ignore_roles"]:
                cfg["ignore_roles"].remove(role.id)
                self.bot.config.save_guild(itx.guild.id)
                await itx.response.send_message(f"Роль {role.name} удалена из игнор-листа", ephemeral=True)
            else:
                await itx.response.send_message(f"Роль {role.name} не в игнор-листе", ephemeral=True)
        else:
            await itx.response.send_message("Действие: 'add' или 'remove'", ephemeral=True)

    @discord.app_commands.command(name="ignore_user", description="Добавить/удалить пользователя в игнор-лист")
    @discord.app_commands.guild_only()
    @discord.app_commands.describe(user="Пользователь", action="Добавить или удалить")
    async def ignore_user(self, itx: discord.Interaction, user: discord.User, action: str):
        if not is_admin(itx.user, itx.guild, self.bot.config.global_cfg()["owner_id"]):
            await itx.response.send_message("Нет прав", ephemeral=True)
            return
        cfg = self.bot.config.guild_cfg(itx.guild.id)
        action = action.lower()
        if action == "add":
            if user.id not in cfg["ignore_users"]:
                cfg["ignore_users"].append(user.id)
                self.bot.config.save_guild(itx.guild.id)
                await itx.response.send_message(f"Пользователь {user.name} добавлен в игнор-лист", ephemeral=True)
            else:
                await itx.response.send_message(f"Пользователь {user.name} уже в игнор-листе", ephemeral=True)
        elif action == "remove":
            if user.id in cfg["ignore_users"]:
                cfg["ignore_users"].remove(user.id)
                self.bot.config.save_guild(itx.guild.id)
                await itx.response.send_message(f"Пользователь {user.name} удален из игнор-листа", ephemeral=True)
            else:
                await itx.response.send_message(f"Пользователь {user.name} не в игнор-листе", ephemeral=True)
        else:
            await itx.response.send_message("Действие: 'add' или 'remove'", ephemeral=True)

    @discord.app_commands.command(name="set_log", description="Установить канал для логов входов и выходов")
    @discord.app_commands.guild_only()
    @discord.app_commands.describe(channel="Канал для логов")
    async def set_log(self, itx: discord.Interaction, channel: discord.TextChannel):
        if not is_admin(itx.user, itx.guild, self.bot.config.global_cfg()["owner_id"]):
            await itx.response.send_message("Нет прав", ephemeral=True)
            return
        cfg = self.bot.config.guild_cfg(itx.guild.id)
        cfg["logging"]["join_leave_log_channel_id"] = channel.id
        self.bot.config.save_guild(itx.guild.id)
        await itx.response.send_message(f"Канал логов установлен на {channel.mention}", ephemeral=True)

    @discord.app_commands.command(name="lock", description="Заблокировать функции")
    @discord.app_commands.guild_only()
    @discord.app_commands.describe(type="Тип блокировки")
    @discord.app_commands.choices(type=[
        discord.app_commands.Choice(name="Webhooks", value="webhooks"),
        discord.app_commands.Choice(name="Bots", value="bots"),
    ])
    async def lock(self, itx: discord.Interaction, type: str):
        if not is_admin(itx.user, itx.guild, self.bot.config.global_cfg()["owner_id"]):
            await itx.response.send_message("Нет прав", ephemeral=True)
            return
        cfg = self.bot.config.guild_cfg(itx.guild.id)
        if type == "webhooks":
            if cfg["webhooks_locked"]:
                await itx.response.send_message("Веб-хуки уже заблокированы", ephemeral=True)
                return
            cfg["invites"]["webhook_whitelist"] = [str(h.id) for h in await itx.guild.webhooks()]
            cfg["webhooks_locked"] = True
            self.bot.config.save_guild(itx.guild.id)
            await itx.response.send_message("Веб-хуки заблокированы", ephemeral=True)
        elif type == "bots":
            if cfg["bots_locked"]:
                await itx.response.send_message("Боты уже заблокированы", ephemeral=True)
                return
            cfg["bots_allowed"] = [m.id for m in itx.guild.members if m.bot]
            cfg["bots_locked"] = True
            self.bot.config.save_guild(itx.guild.id)
            await itx.response.send_message("Боты заблокированы", ephemeral=True)

    @discord.app_commands.command(name="unlock", description="Разблокировать функции")
    @discord.app_commands.guild_only()
    @discord.app_commands.describe(type="Тип разблокировки")
    @discord.app_commands.choices(type=[
        discord.app_commands.Choice(name="Webhooks", value="webhooks"),
        discord.app_commands.Choice(name="Bots", value="bots"),
    ])
    async def unlock(self, itx: discord.Interaction, type: str):
        if not is_admin(itx.user, itx.guild, self.bot.config.global_cfg()["owner_id"]):
            await itx.response.send_message("Нет прав", ephemeral=True)
            return
        cfg = self.bot.config.guild_cfg(itx.guild.id)
        if type == "webhooks":
            if not cfg["webhooks_locked"]:
                await itx.response.send_message("Веб-хуки не заблокированы", ephemeral=True)
                return
            cfg["webhooks_locked"] = False
            self.bot.config.save_guild(itx.guild.id)
            await itx.response.send_message("Веб-хуки разблокированы", ephemeral=True)
        elif type == "bots":
            if not cfg["bots_locked"]:
                await itx.response.send_message("Боты не заблокированы", ephemeral=True)
                return
            cfg["bots_locked"] = False
            self.bot.config.save_guild(itx.guild.id)
            await itx.response.send_message("Боты разблокированы", ephemeral=True)