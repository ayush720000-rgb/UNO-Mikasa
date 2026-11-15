#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from pony.orm import Optional, PrimaryKey
from database import db


class UserSetting(db.Entity):

    id = PrimaryKey(int, auto=False, size=64)  # Telegram User ID
    first_places = Optional(int, default=0)  # Nr. of games won in first place
    games_played = Optional(int, default=0)  # Nr. of games completed
    cards_played = Optional(int, default=0)  # Nr. of cards played total
    use_keyboards = Optional(bool, default=False)  # Use keyboards (unused)
