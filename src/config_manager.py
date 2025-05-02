# Copyright (c) 2025 Pterohost
# Licensed under the MIT License (https://opensource.org/licenses/MIT)

import os
import yaml
from schema import Schema, And, Or
from typing import Any, MutableMapping

class ConfigManager:
    def __init__(self, g_path: str = "config.yaml", dir_: str = "guilds") -> None:
        self.g_path, self.dir = g_path, dir_
        os.makedirs(dir_, exist_ok=True)
        self._global = self._validate_global(self._load_yaml(g_path, self._default_global()))
        self._guilds: dict[int, dict[str, Any]] = {}

    @staticmethod
    def _default_global() -> dict[str, Any]:
        return {
            "token": "YOUR_TOKEN_HERE",
            "owner_id": 0,
            "log_level": "INFO",
        }

    @staticmethod
    def _validate_global(config):
        schema = Schema({
            "token": And(str, len),
            "owner_id": And(int, lambda n: n >= 0),
            "log_level": Or("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        })
        return schema.validate(config)

    @staticmethod
    def _default_guild() -> dict[str, Any]:
        return {
            "verification": {
                "captcha_mode": "none",
                "quarantine_minutes": 0,
                "min_account_age_days": 0,
                "require_avatar": False,
            },
            "moderation": {
                "spam": {"max_messages": 8, "interval_seconds": 4},
                "repeat": {"max_repeats": 3, "interval_seconds": 10},
                "links": {"block": False},
                "attachments": {"max": 5},
                "emoji": {"max": 20},
                "mentions": {"max_per_message": 5, "max_total": 10, "interval_seconds": 60},
            },
            "invites": {"webhook_whitelist": []},
            "bots_locked": False,
            "bots_allowed": [],
            "webhooks_locked": False,
            "actions": {
                "spam": "timeout",
                "repeat": "timeout",
                "links": "kick",
                "attachments": "kick",
                "emoji": "timeout",
                "mentions": "timeout",
                "require_avatar": "warn",
                "min_account_age": "kick",
                "bot_join": "ban",
                "webhook_new": "ban",
                "captcha_fail": "kick",
            },
            "logging": {
                "log_channel_id": 0,
                "alert_channel_id": 0,
                "join_leave_log_channel_id": 0,
            },
            "ignore_roles": [],
            "ignore_users": [],
        }

    @staticmethod
    def _validate_guild(config):
        schema = Schema({
            "verification": {
                "captcha_mode": Or("none", "image", "reaction"),
                "quarantine_minutes": And(int, lambda n: n >= 0),
                "min_account_age_days": And(int, lambda n: n >= 0),
                "require_avatar": bool,
            },
            "moderation": {
                "spam": {"max_messages": int, "interval_seconds": int},
                "repeat": {"max_repeats": int, "interval_seconds": int},
                "links": {"block": bool},
                "attachments": {"max": int},
                "emoji": {"max": int},
                "mentions": {"max_per_message": int, "max_total": int, "interval_seconds": int},
            },
            "invites": {"webhook_whitelist": [str]},
            "bots_locked": bool,
            "bots_allowed": [int],
            "webhooks_locked": bool,
            "actions": {
                key: Or("warn", "timeout", "kick", "ban") for key in [
                    "spam", "repeat", "links", "attachments", "emoji", "mentions",
                    "require_avatar", "min_account_age", "bot_join", "webhook_new", "captcha_fail"
                ]
            },
            "logging": {
                "log_channel_id": int,
                "alert_channel_id": int,
                "join_leave_log_channel_id": int,
            },
            "ignore_roles": [int],
            "ignore_users": [int],
        })
        return schema.validate(config)

    @staticmethod
    def _load_yaml(path: str, default: dict[str, Any]) -> dict[str, Any]:
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f) or default
        yaml.safe_dump(default, open(path, "w", encoding="utf-8"), allow_unicode=True)
        return default

    @staticmethod
    def _dump_yaml(path: str, data: dict[str, Any]) -> None:
        yaml.safe_dump(data, open(path, "w", encoding="utf-8"), allow_unicode=True)

    @staticmethod
    def merge_defaults(config: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
        if isinstance(defaults, dict):
            if not isinstance(config, dict):
                config = {}
            for key, value in defaults.items():
                if key not in config:
                    config[key] = value
                else:
                    config[key] = ConfigManager.merge_defaults(config[key], value)
        return config

    def global_cfg(self) -> dict[str, Any]:
        return self._global

    def guild_cfg(self, gid: int) -> MutableMapping[str, Any]:
        if gid not in self._guilds:
            p = os.path.join(self.dir, f"{gid}.yaml")
            loaded = self._load_yaml(p, self._default_guild())
            validated = self._validate_guild(loaded)
            self._guilds[gid] = self.merge_defaults(validated, self._default_guild())
            self.save_guild(gid)
        return self._guilds[gid]

    def save_global(self) -> None:
        self._dump_yaml(self.g_path, self._global)

    def save_guild(self, gid: int) -> None:
        self._dump_yaml(os.path.join(self.dir, f"{gid}.yaml"), self._guilds[gid])