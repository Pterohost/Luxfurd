# Discord Guardian Bot 6.5 - Pterohost (https://pterohost.com)
# MIT License: https://github.com/Pterohost/Luxfurd
# Copyright (c) 2025 Pterohost

from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
import discord
from .utils import LOG

class WarningManager:
    def __init__(self):
        self.warnings = defaultdict(lambda: defaultdict(lambda: defaultdict(deque)))
        self.warning_messages = defaultdict(lambda: defaultdict(list))
        self._last_notified = defaultdict(lambda: defaultdict(lambda: datetime(1970, 1, 1, tzinfo=timezone.utc)))
        self._locks = defaultdict(lambda: defaultdict(lambda: datetime.min.replace(tzinfo=timezone.utc)))

    def add_warning(self, guild_id: int, user_id: int, reason: str) -> int:
        if self.is_locked(guild_id, user_id):
            return self.get_warning_count(guild_id, user_id, reason)
        now = datetime.now(timezone.utc)
        user_warnings = self.warnings[guild_id][user_id][reason]
        user_warnings.append((now, reason))
        while user_warnings and (now - user_warnings[0][0]).total_seconds() > 360:
            user_warnings.popleft()
        return len(user_warnings)

    def add_warning_message(self, guild_id: int, user_id: int, channel_id: int, message_id: int) -> None:
        self.warning_messages[guild_id][user_id].append((channel_id, message_id))

    async def delete_warning_messages(self, guild: discord.Guild, user_id: int) -> None:
        if user_id not in self.warning_messages[guild.id]:
            return
        for channel_id, message_id in self.warning_messages[guild.id][user_id]:
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            try:
                message = await channel.fetch_message(message_id)
                await message.delete()
            except discord.HTTPException as e:
                if e.code != 10008:
                    LOG.warning(f"Не удалось удалить сообщение {message_id}: {e}")
        self.warning_messages[guild.id][user_id].clear()

    def get_warning_count(self, guild_id: int, user_id: int, reason: str) -> int:
        now = datetime.now(timezone.utc)
        user_warnings = self.warnings[guild_id][user_id][reason]
        while user_warnings and (now - user_warnings[0][0]).total_seconds() > 360:
            user_warnings.popleft()
        return len(user_warnings)

    def reset_warnings(self, guild_id: int, user_id: int, reason: str) -> None:
        self.warnings[guild_id][user_id][reason].clear()

    def lock_user(self, guild_id: int, user_id: int, duration: float = 60.0) -> None:
        self._locks[guild_id][user_id] = datetime.now(timezone.utc) + timedelta(seconds=duration)

    def is_locked(self, guild_id: int, user_id: int) -> bool:
        now = datetime.now(timezone.utc)
        lock_time = self._locks[guild_id][user_id]
        if now >= lock_time:
            self._locks[guild_id].pop(user_id, None)
            return False
        return True

    def can_notify(self, guild_id: int, user_id: int, reason: str) -> bool:
        now = datetime.now(timezone.utc)
        key = (user_id, reason)
        if (now - self._last_notified[guild_id][key]).total_seconds() < 10:
            return False
        self._last_notified[guild_id][key] = now
        return True