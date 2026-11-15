#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import json

try:
    with open("config.json", "r") as f:
        config = json.load(f)
except FileNotFoundError:
    config = {}

TOKEN = os.getenv("TOKEN", config.get("token"))
WORKERS = int(os.getenv("WORKERS", config.get("workers", 32)))
ADMIN_LIST = os.getenv("ADMIN_LIST", config.get("admin_list", None))

if isinstance(ADMIN_LIST, str):
    ADMIN_LIST = set(int(x) for x in ADMIN_LIST.replace(",", " ").split())

OPEN_LOBBY = os.getenv("OPEN_LOBBY", config.get("open_lobby", True))

if isinstance(OPEN_LOBBY, str):
    OPEN_LOBBY = OPEN_LOBBY.lower() in ("yes", "true", "t", "1")


DEFAULT_GAMEMODE = os.getenv("DEFAULT_GAMEMODE", config.get("default_gamemode", "fast"))
WAITING_TIME = int(os.getenv("WAITING_TIME", config.get("waiting_time", 120)))
TIME_REMOVAL_AFTER_SKIP = int(os.getenv("TIME_REMOVAL_AFTER_SKIP", config.get("time_removal_after_skip", 20)))
MIN_FAST_TURN_TIME = int(os.getenv("MIN_FAST_TURN_TIME", config.get("min_fast_turn_time", 15)))
MIN_PLAYERS = int(os.getenv("MIN_PLAYERS", config.get("min_players", 2)))

# --- Extra options (all optional, set them as environment variables) ----------

def _as_bool(value, default):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).lower() in ("yes", "true", "t", "1", "on")


# Show every bot message in ꜱᴍᴀʟʟ ᴄᴀᴘꜱ
SMALL_CAPS = _as_bool(os.getenv("SMALL_CAPS", config.get("small_caps")), True)


# Render / free-tier hosting helpers
PORT = os.getenv("PORT")  # set automatically by Render
KEEPALIVE_URL = os.getenv("KEEPALIVE_URL", os.getenv("RENDER_EXTERNAL_URL"))
KEEPALIVE_INTERVAL = int(os.getenv("KEEPALIVE_INTERVAL", 600))  # seconds
