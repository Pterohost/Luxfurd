# Discord Guardian Bot 6.5 - Pterohost (https://pterohost.com)
# MIT License: https://github.com/Pterohost/Luxfurd
# Copyright (c) 2025 Pterohost

import discord
from discord.ext import commands
from discord import app_commands
import json
import textwrap
from ..bot import GuardianBot
from ..utils import is_admin

class AdminCog(commands.Cog):
    def __init__(self, bot: GuardianBot) -> None:
        self.bot = bot

    @app_commands.command(name="lock_bots", description="Запретить новых ботов")
    @app_commands.guild_only()
    async def lock_bots(self, itx: discord.Interaction):
        if not is_admin(itx.user, itx.guild, self.bot.config.global_cfg()["owner_id"]):
            await itx.response.send_message("Нет прав", ephemeral=True)
            return
        cfg = self.bot.config.guild_cfg(itx.guild.id)
        if cfg["bots_locked"]:
            await itx.response.send_message("Защита активна", ephemeral=True)
            return
        cfg["bots_allowed"] = [m.id for m in itx.guild.members if m.bot]
        cfg["bots_locked"] = True
        self.bot.config.save_guild(itx.guild.id)
        await itx.response.send_message("Боты заблокированы", ephemeral=True)

    @app_commands.command(name="unlock_bots", description="Снять запрет на ботов")
    @app_commands.guild_only()
    async def unlock_bots(self, itx: discord.Interaction):
        if not is_admin(itx.user, itx.guild, self.bot.config.global_cfg()["owner_id"]):
            await itx.response.send_message("Нет прав", ephemeral=True)
            return
        cfg = self.bot.config.guild_cfg(itx.guild.id)
        if not cfg["bots_locked"]:
            await itx.response.send_message("Защита выключена", ephemeral=True)
            return
        cfg["bots_locked"] = False
        self.bot.config.save_guild(itx.guild.id)
        await itx.response.send_message("Блокировка снята", ephemeral=True)

    @app_commands.command(name="set_threshold", description="Изменить параметр конфигурации")
    @app_commands.guild_only()
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

    @app_commands.command(name="show_config", description="Показать конфигурацию сервера")
    @app_commands.guild_only()
    async def show_config(self, itx: discord.Interaction):
        if not is_admin(itx.user, itx.guild, self.bot.config.global_cfg()["owner_id"]):
            await itx.response.send_message("Нет прав", ephemeral=True)
            return
        txt = json.dumps(self.bot.config.guild_cfg(itx.guild.id), ensure_ascii=False, indent=2)
        await itx.response.send_message(f"```json\n{textwrap.shorten(txt, 1900)}\n```", ephemeral=True)

    @app_commands.command(name="show_incidents", description="Показать последние инциденты")
    @app_commands.guild_only()
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

    @app_commands.command(name="stats", description="Показать статистику инцидентов")
    @app_commands.guild_only()
    async def stats(self, itx: discord.Interaction):
        if not is_admin(itx.user, itx.guild, self.bot.config.global_cfg()["owner_id"]):
            await itx.response.send_message("Нет прав", ephemeral=True)
            return
        incidents = [i for i in self.bot.incidents if i["guild_id"] == itx.guild.id]
        embed = discord.Embed(
            title="Статистика инцидентов", description=f"Всего инцидентов: **{len(incidents)}**",
            color=discord.Color.blue(), timestamp=discord.utils.utcnow()
        )
        embed.add_field(
            name="Последние 5 инцидентов",
            value="\n".join(f"{i['timestamp']} | {i['reason']}" for i in incidents[-5:]) or "Нет данных",
            inline=False
        )
        await itx.response.send_message(embed=embed)

    @app_commands.command(name="ignore_role", description="Добавить/удалить роль в игнор-лист")
    @app_commands.guild_only()
    @app_commands.describe(role="Роль", action="Добавить или удалить")
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

    @app_commands.command(name="ignore_user", description="Добавить/удалить пользователя в игнор-лист")
    @app_commands.guild_only()
    @app_commands.describe(user="Пользователь", action="Добавить или удалить")
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