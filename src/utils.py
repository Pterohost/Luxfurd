# Discord Guardian Bot 6.5 - Pterohost (https://pterohost.com)
# MIT License: https://github.com/Pterohost/Luxfurd
# Copyright (c) 2025 Pterohost

import discord
import logging
import os
from datetime import datetime, timezone
from .bot import GuardianBot

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
fh = logging.FileHandler(os.path.join("logs", f"bot_{datetime.now().date()}.log"), "a", "utf-8")
fh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S"))
logging.getLogger().addHandler(fh)
LOG = logging.getLogger("guardian")

REASON_MAP = {
    "spam": "Спам", "repeat": "Повтор сообщений", "links": "Ссылки", "attachments": "Вложения",
    "emoji": "Много эмодзи", "mentions": "Много упоминаний", "require_avatar": "Нет аватара",
    "min_account_age": "Новый аккаунт", "bot_join": "Неавторизованный бот",
    "webhook_new": "Неавторизованный веб-хук", "captcha_fail": "Ошибка капчи"
}

def get_display_reason(internal_reason: str) -> str:
    return REASON_MAP.get(internal_reason, internal_reason)

def is_admin(user: discord.abc.User, guild: discord.Guild, owner_id: int) -> bool:
    return user.guild_permissions.administrator or user.id == owner_id

async def apply_action(
    bot: GuardianBot, target: discord.Member | discord.User, action: str, reason: str,
    *, guild: discord.Guild, delete_msg: discord.Message | None = None, channel: discord.TextChannel | None = None
) -> None:
    if bot.warning_manager.is_locked(guild.id, target.id):
        return

    display_reason = get_display_reason(reason)
    if delete_msg:
        try:
            await delete_msg.delete()
        except discord.HTTPException as e:
            LOG.warning(f"Не удалось удалить сообщение: {e}")

    if channel is None:
        channel = guild.text_channels[0]

    async def delete_warning_after_delay(message: discord.Message, delay: float = 60.0):
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.utils.timedelta(seconds=delay))
        try:
            await message.delete()
        except discord.HTTPException as e:
            if e.code != 10008:
                LOG.warning(f"Не удалось удалить сообщение {message.id}: {e}")

    warning_count = bot.warning_manager.get_warning_count(guild.id, target.id, reason)
    if warning_count < 3:
        new_count = bot.warning_manager.add_warning(guild.id, target.id, reason)
        if new_count == warning_count:
            return
        embed = discord.Embed(
            title="Предупреждение", description=f"{target.mention}, нарушение: **{display_reason}**.",
            color=discord.Color.yellow(), timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Предупреждений", value=f"{new_count}/3", inline=False)
        try:
            message = await channel.send(embed=embed)
            bot.warning_manager.add_warning_message(guild.id, target.id, channel.id, message.id)
            discord.utils.create_task(delete_warning_after_delay(message))
        except discord.HTTPException as e:
            LOG.error(f"Не удалось отправить предупреждение: {e}")
        if new_count == 3:
            try:
                await target.send(f"⚠️ Последнее предупреждение за **{display_reason}**!")
            except discord.HTTPException:
                LOG.warning(f"Не удалось отправить ЛС {target}")
        return

    if bot.warning_manager.can_notify(guild.id, target.id, reason):
        ok = True
        try:
            if action == "timeout" and isinstance(target, discord.Member):
                violations = bot.violation_history.get_violations(guild.id, target.id)
                violation_count = len([v for v in violations if v["reason"] == reason])
                timeout_minutes = [5, 15, 30][min(violation_count, 2)]
                await target.timeout(discord.utils.timedelta(minutes=timeout_minutes), reason=display_reason)
            elif action == "kick" and isinstance(target, discord.Member):
                await target.kick(reason=display_reason)
            elif action == "ban":
                await guild.ban(target, reason=display_reason)
        except discord.Forbidden:
            ok = False
            LOG.warning(f"Недостаточно прав для {action} на {target}")
        except discord.HTTPException as e:
            ok = False
            LOG.error(f"Ошибка {action} на {target}: {e}")

        if ok:
            bot.add_incident(guild.id, target.id, display_reason)
            bot.violation_history.add_violation(guild.id, target.id, reason)
            bot.warning_manager.reset_warnings(guild.id, target.id, reason)
            bot.warning_manager.lock_user(guild.id, target.id, 60.0)
            await bot.warning_manager.delete_warning_messages(guild, target.id)
            embed = discord.Embed(
                title="Наказание", description=f"{target.mention} наказан за **{display_reason}**. Действие: **{action}**.",
                color=discord.Color.red(), timestamp=discord.utils.utcnow()
            )
        else:
            embed = discord.Embed(
                title="Ошибка", description=f"Не удалось применить {action} к {target.mention}.",
                color=discord.Color.orange(), timestamp=discord.utils.utcnow()
            )
        try:
            await channel.send(embed=embed)
        except discord.HTTPException as e:
            LOG.error(f"Не удалось отправить сообщение о наказании: {e}")

        lg = bot.get_cog("LoggingCog")
        if lg:
            await lg.log_incident(guild, f"{display_reason} → {action if ok else 'ошибка'}", target)