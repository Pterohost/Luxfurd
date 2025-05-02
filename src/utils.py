# Copyright (c) 2025 Pterohost
# Licensed under the MIT License (https://opensource.org/licenses/MIT)

import discord
from typing import Union
from .bot import GuardianBot
import asyncio
from datetime import datetime, timezone, timedelta
import logging

LOG = logging.getLogger("guardian")

REASON_MAP = {
    "spam": "Спам",
    "repeat": "Повтор сообщений",
    "links": "Ссылки",
    "attachments": "Вложения",
    "emoji": "Много эмодзи",
    "mentions": "Спам упоминаний",
    "require_avatar": "Нет аватара",
    "min_account_age": "Молодой аккаунт",
    "bot_join": "Неавторизованный бот",
    "webhook_new": "Неавторизованный веб-хук",
    "captcha_fail": "Не пройдена капча",
}

def get_display_reason(internal_reason: str) -> str:
    return REASON_MAP.get(internal_reason, internal_reason)

def is_admin(user: discord.abc.User, guild: discord.Guild, owner_id: int) -> bool:
    return (
        getattr(user, "guild_permissions", None)
        and user.guild_permissions.administrator
        or user.id == owner_id
    )

async def apply_action(
    bot: GuardianBot,
    target: Union[discord.Member, discord.User],
    action: str,
    reason: str,
    *,
    guild: discord.Guild,
    delete_msg: discord.Message | None = None,
    channel: discord.TextChannel | None = None,
) -> None:
    if bot.warning_manager.is_locked(guild.id, target.id):
        return
    internal_reason = reason
    display_reason = get_display_reason(reason)
    if delete_msg:
        try:
            await delete_msg.delete()
        except discord.HTTPException:
            pass
    if channel is None:
        channel = guild.text_channels[0]
    
    async def delete_warning_after_delay(message: discord.Message, delay: float = 60.0):
        await asyncio.sleep(delay)
        try:
            await message.delete()
        except discord.HTTPException:
            pass

    warning_count = bot.warning_manager.get_warning_count(guild.id, target.id, internal_reason)
    if warning_count < 3:
        new_count = bot.warning_manager.add_warning(guild.id, target.id, internal_reason)
        if new_count == warning_count:
            return
        embed = discord.Embed(
            title="Предупреждение",
            description=f"{target.mention}, вы получили предупреждение за **{display_reason}**.",
            color=discord.Color.yellow(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Предупреждений", value=f"{new_count}/3", inline=False)
        try:
            message = await channel.send(embed=embed)
            bot.warning_manager.add_warning_message(guild.id, target.id, channel.id, message.id)
            asyncio.create_task(delete_warning_after_delay(message))
        except discord.HTTPException:
            pass
        if new_count == 3:
            try:
                await target.send(f"⚠️ Последнее предупреждение за **{display_reason}**!")
            except discord.HTTPException:
                pass
        return

    if bot.warning_manager.can_notify(guild.id, target.id, internal_reason):
        ok = True
        try:
            if action == "timeout" and isinstance(target, discord.Member):
                violations = bot.violation_history.get_violations(guild.id, target.id)
                violation_count = len([v for v in violations if v["reason"] == internal_reason])
                timeout_minutes = [5, 15, 30][min(violation_count, 2)]
                await target.timeout(timedelta(minutes=timeout_minutes), reason=display_reason)
            elif action == "kick" and isinstance(target, discord.Member):
                await target.kick(reason=display_reason)
            elif action == "ban":
                await guild.ban(target, reason=display_reason)
        except discord.Forbidden:
            ok = False
        except discord.HTTPException:
            ok = False

        if ok:
            bot.add_incident(guild.id, target.id, display_reason)
            bot.violation_history.add_violation(guild.id, target.id, internal_reason)
            bot.warning_manager.reset_warnings(guild.id, target.id, internal_reason)
            bot.warning_manager.lock_user(guild.id, target.id, 60.0)
            await bot.warning_manager.delete_warning_messages(guild, target.id)
            embed = discord.Embed(
                title="Наказание",
                description=f"{target.mention} наказан за **{display_reason}**. Действие: **{action}**.",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
        else:
            embed = discord.Embed(
                title="Ошибка",
                description=f"Не удалось применить {action} к {target.mention}.",
                color=discord.Color.orange(),
                timestamp=datetime.now(timezone.utc)
            )
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            pass
        lg = bot.get_cog("LoggingCog")
        if lg:
            await lg.log_incident(guild, f"{display_reason} → {action if ok else 'ошибка'}", target)