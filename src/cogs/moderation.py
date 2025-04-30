# Discord Guardian Bot 6.5 - Pterohost (https://pterohost.com)
# MIT License: https://github.com/Pterohost/Luxfurd
# Copyright (c) 2025 Pterohost

import discord
from discord.ext import commands
from collections import defaultdict, deque
import re
from ..bot import GuardianBot
from ..utils import apply_action

class ModerationCog(commands.Cog):
    def __init__(self, bot: GuardianBot) -> None:
        self.bot = bot
        self._burst = defaultdict(lambda: deque(maxlen=50))
        self._repeat = defaultdict(lambda: deque(maxlen=10))
        self._last = defaultdict(str)
        self._mentions = defaultdict(lambda: deque(maxlen=50))

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        if msg.author.bot or not msg.guild or msg.type is not discord.MessageType.default:
            return

        cfg = self.bot.config.guild_cfg(msg.guild.id)
        if any(role.id in cfg["ignore_roles"] for role in msg.author.roles) or msg.author.id in cfg["ignore_users"]:
            return

        mod, acts = cfg["moderation"], cfg["actions"]
        now = discord.utils.utcnow()
        key = (msg.guild.id, msg.author.id)

        burst = self._burst[key]
        burst.append(now)
        while burst and (now - burst[0]).total_seconds() > mod["spam"]["interval_seconds"]:
            burst.popleft()
        if len(burst) >= mod["spam"]["max_messages"]:
            await apply_action(self.bot, msg.author, acts["spam"], "spam", guild=msg.guild, delete_msg=msg, channel=msg.channel)
            return

        if msg.content == self._last[key]:
            rep = self._repeat[key]
            rep.append(now)
            while rep and (now - rep[0]).total_seconds() > mod["repeat"]["interval_seconds"]:
                rep.popleft()
            if len(rep) >= mod["repeat"]["max_repeats"]:
                await apply_action(self.bot, msg.author, acts["repeat"], "repeat", guild=msg.guild, delete_msg=msg, channel=msg.channel)
                return
        else:
            self._repeat[key].clear()
        self._last[key] = msg.content

        if mod["links"]["block"] and re.search(r"https?://", msg.content):
            await apply_action(self.bot, msg.author, acts["links"], "links", guild=msg.guild, delete_msg=msg, channel=msg.channel)
            return

        if mod["attachments"]["max"] == 0 and msg.attachments:
            await apply_action(self.bot, msg.author, acts["attachments"], "attachments", guild=msg.guild, delete_msg=msg, channel=msg.channel)
            return

        if (cnt := len(re.findall(r"[\U00010000-\U0010ffff]", msg.content))) > mod["emoji"]["max"] >= 0:
            await apply_action(self.bot, msg.author, acts["emoji"], "emoji", guild=msg.guild, delete_msg=msg, channel=msg.channel)
            return

        mentions_count = len(msg.mentions)
        if mentions_count > mod["mentions"]["max_per_message"]:
            await apply_action(self.bot, msg.author, acts["mentions"], "mentions", guild=msg.guild, delete_msg=msg, channel=msg.channel)
            return
        self._mentions[key].append((now, mentions_count))
        while self._mentions[key] and (now - self._mentions[key][0][0]).total_seconds() > mod["mentions"]["interval_seconds"]:
            self._mentions[key].popleft()
        total_mentions = sum(count for _, count in self._mentions[key])
        if total_mentions > mod["mentions"]["max_total"]:
            await apply_action(self.bot, msg.author, acts["mentions"], "mentions", guild=msg.guild, delete_msg=msg, channel=msg.channel)