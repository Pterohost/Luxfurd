# Discord Guardian Bot 6.5 - Pterohost (https://pterohost.com)
# MIT License: https://github.com/Pterohost/Luxfurd
# Copyright (c) 2025 Pterohost

import discord
from discord.ext import commands, tasks
from .config_manager import ConfigManager
from .warning_manager import WarningManager
from .violation_history import ViolationHistory
from .cogs import VerificationCog, ModerationCog, InviteCog, LoggingCog, AdminCog

class GuardianBot(commands.Bot):
    def __init__(self, cfg: ConfigManager) -> None:
        self.config = cfg
        gl = cfg.global_cfg()
        super().__init__(command_prefix="!", intents=discord.Intents.all(), owner_id=gl["owner_id"])
        self.incidents = []
        self.warning_manager = WarningManager()
        self.violation_history = ViolationHistory()

    async def setup_hook(self) -> None:
        for cog in (VerificationCog, ModerationCog, InviteCog, LoggingCog, AdminCog):
            await self.add_cog(cog(self))
        self._presence.start()
        await self.tree.sync()

    @tasks.loop(minutes=1)
    async def _presence(self) -> None:
        await self.wait_until_ready()
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name=f"Инциденты: {len(self.incidents)}")
        )

    def add_incident(self, guild_id: int, user_id: int, reason: str) -> None:
        self.incidents.append({"timestamp": discord.utils.utcnow(), "guild_id": guild_id, "user_id": user_id, "reason": reason})

def main():
    cfg = ConfigManager()
    bot = GuardianBot(cfg)
    bot.run(cfg.global_cfg()["token"])

if __name__ == "__main__":
    main()