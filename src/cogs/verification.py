# Discord Guardian Bot 6.5 - Pterohost (https://pterohost.com)
# MIT License: https://github.com/Pterohost/Luxfurd
# Copyright (c) 2025 Pterohost

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import random
import string
from ..bot import GuardianBot
from ..utils import apply_action, LOG

class VerificationCog(commands.Cog):
    def __init__(self, bot: GuardianBot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            self.bot.config.guild_cfg(guild.id)

    @commands.Cog.listener()
    async def on_member_join(self, m: discord.Member) -> None:
        cfg = self.bot.config.guild_cfg(m.guild.id)
        acts = cfg["actions"]

        if m.bot and cfg["bots_locked"] and m.id not in cfg["bots_allowed"]:
            await apply_action(self.bot, m, acts["bot_join"], "bot_join", guild=m.guild)
            return

        v = cfg["verification"]
        if (discord.utils.utcnow() - m.created_at).days < v["min_account_age_days"]:
            await apply_action(self.bot, m, acts["min_account_age"], "min_account_age", guild=m.guild)
            return

        if v["require_avatar"] and m.avatar is None:
            await apply_action(self.bot, m, acts["require_avatar"], "require_avatar", guild=m.guild)
            if acts["require_avatar"] in {"kick", "ban"}:
                return

        if v["captcha_mode"] != "none" and not await self._captcha(m, v["captcha_mode"]):
            await apply_action(self.bot, m, acts["captcha_fail"], "captcha_fail", guild=m.guild)

    async def _captcha(self, mem: discord.Member, mode: str) -> bool:
        try:
            if mode == "image":
                code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
                buf = self._img(code)
                await mem.send("Введите код:", file=discord.File(buf, "captcha.png"))
                def chk(m: discord.Message): return m.author == mem and m.content.upper() == code
                await self.bot.wait_for("message", check=chk, timeout=60)
                return True
            if mode == "reaction":
                em = random.choice(["👍", "✅", "🎉"])
                msg = await mem.send(f"Нажмите реакцию {em}")
                await msg.add_reaction(em)
                def chk(r: discord.Reaction, u: discord.User):
                    return u == mem and str(r.emoji) == em and r.message.id == msg.id
                await self.bot.wait_for("reaction_add", check=chk, timeout=60)
                return True
            return True
        except discord.utils.TimeoutError:
            return False
        except discord.HTTPException as e:
            LOG.error(f"Ошибка капчи для {mem}: {e}")
            return False

    @staticmethod
    def _img(t: str) -> BytesIO:
        im = Image.new("RGB", (220, 80), "white")
        draw = ImageDraw.Draw(im)
        font = ImageFont.load_default()
        draw.text((20, 25), t, font=font, fill="black")
        b = BytesIO()
        im.save(b, "PNG")
        b.seek(0)
        return b