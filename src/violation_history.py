# Discord Guardian Bot 6.5 - Pterohost (https://pterohost.com)
# MIT License: https://github.com/Pterohost/Luxfurd
# Copyright (c) 2025 Pterohost

import json
from datetime import datetime, timezone, timedelta

class ViolationHistory:
    def __init__(self, file_path: str = "violations.json"):
        self.file_path = file_path
        self._load()

    def _load(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except FileNotFoundError:
            self.data = {}

    def _save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False)

    def add_violation(self, guild_id: int, user_id: int, reason: str):
        key = f"{guild_id}:{user_id}"
        if key not in self.data:
            self.data[key] = []
        self.data[key].append({"timestamp": datetime.now(timezone.utc).isoformat(), "reason": reason})
        self._save()

    def get_violations(self, guild_id: int, user_id: int, days: int = 7):
        key = f"{guild_id}:{user_id}"
        if key not in self.data:
            return []
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return [v for v in self.data[key] if datetime.fromisoformat(v["timestamp"]) > cutoff]