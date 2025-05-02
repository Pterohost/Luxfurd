# Copyright (c) 2025 Pterohost
# Licensed under the MIT License (https://opensource.org/licenses/MIT)

import discord
from discord.ext import commands, tasks
from .config_manager import ConfigManager
from .warning_manager import WarningManager
from .violation_history import ViolationHistory
from .cogs.verification import VerificationCog
from .cogs.moderation import ModerationCog
from .cogs.invites import InviteCog
from .cogs.logging import LoggingCog
from .cogs.admin import AdminCog
from collections import defaultdict, deque
import logging
from datetime import datetime, timezone

LOG = logging.getLogger("guardian")

class GuardianBot(commands.Bot):
    def __init__(self, cfg: ConfigManager) -> None:
        self.config = cfg
        gl = cfg.global_cfg()
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.all(),
            owner_id=gl["owner_id"],
        )
        logging.getLogger().setLevel(gl["log_level"].upper())
        self.incidents = deque(maxlen=100)
        self.warning_manager = WarningManager()
        self.violation_history = ViolationHistory()
        self.join_times = defaultdict(dict)

    async def setup_hook(self) -> None:
        for cog in (VerificationCog, ModerationCog, InviteCog, LoggingCog, AdminCog):
            await self.add_cog(cog(self))
        self._presence.start()
        await self.tree.sync()
        LOG.info("Slash commands synchronized.")

    @tasks.loop(minutes=1)
    async def _presence(self) -> None:
        await self.wait_until_ready()
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"Incidents: {len(self.incidents)}"
            )
        )

    def add_incident(self, guild_id: int, user_id: int, reason: str) -> None:
        self.incidents.append({
            "timestamp": datetime.now(timezone.utc),
            "guild_id": guild_id,
            "user_id": user_id,
            "reason": reason,
        })

if __name__ == "__main__":
    cfg = ConfigManager()
    TOKEN = cfg.global_cfg()["token"]
    if not TOKEN or TOKEN.startswith("PASTE"):
        LOG.error("Token not specified or invalid in config.yaml")
        raise ValueError("Specify a valid token in config.yaml")
    bot = GuardianBot(cfg)
    bot.run(TOKEN)