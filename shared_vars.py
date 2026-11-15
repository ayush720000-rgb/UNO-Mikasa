#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from config import TOKEN, WORKERS
from telegram.ext import Application

from game_manager import GameManager
from database import db, bind_database
from start_bot import post_init
# The UserSetting table must be defined before db.generate_mapping() runs below.
# Importing it later (e.g. from simple_commands) crashes startup with an ERDiagramError.
import user_setting  # noqa: F401

if not TOKEN:
    raise SystemExit(
        "TOKEN is not set. Get a token from @BotFather and set it as the "
        "TOKEN environment variable (on Render: Environment tab -> TOKEN).")

bind_database()
db.generate_mapping(create_tables=True)

gm = GameManager()
# Handlers are registered on this Application by the modules imported below.
# post_init (start_bot.post_init) runs on the event loop before polling starts.
application = (Application.builder().token(TOKEN).concurrent_updates(WORKERS)
               .post_init(post_init).build())
