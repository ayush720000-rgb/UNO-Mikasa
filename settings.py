#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pony.orm import db_session
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, CallbackContext

from fmt import info
from shared_vars import application
from bridge import threaded
from smallcaps import themed
from utils import send_async


@db_session
def show_settings(update: Update, context: CallbackContext):
    """Handler for /settings: explains what is configurable (statistics are always on)"""
    chat = update.message.chat

    text = info(themed("Statistics are always on, so every game you play is counted."))
    send_async(context.bot, chat.id,
               text=text + "\n\n" + themed("See your numbers with /stats"),
               parse_mode=ParseMode.HTML)


def register():
    application.add_handler(CommandHandler('settings', threaded(show_settings)))
