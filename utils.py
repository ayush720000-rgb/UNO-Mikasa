#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from smallcaps import themed
import logging
from telegram import InlineKeyboardButton

from fmt import HTMLText
from mwt import MWT
from bridge import run_in_background
from shared_vars import gm

logger = logging.getLogger(__name__)

TIMEOUT = 2.5


class StyledButton(InlineKeyboardButton):
    """Inline button that can carry Telegram's color style.

    style: 'primary' (blue), 'success' (green) or 'danger' (red). None keeps
    the default transparent look, which is what most buttons should use.
    """

    def __init__(self, text, style=None, **kwargs):
        super().__init__(text, **kwargs)
        # Stored via object.__setattr__: PTB warns about new public attributes on its objects.
        object.__setattr__(self, '_style', style)

    def to_dict(self, recursive=True):
        data = super().to_dict(recursive)
        if self._style:
            data['style'] = self._style
        return data


def display_name(user):
    """ Get the current players name including their username, if possible """
    user_name = user.first_name
    if user.username:
        user_name += ' (@' + user.username + ')'
    return user_name


def display_color(color):
    """ Convert a color code to actual color name """
    if color == "r":
        return themed("{emoji} Red").format(emoji='❤️')
    if color == "b":
        return themed("{emoji} Blue").format(emoji='💙')
    if color == "g":
        return themed("{emoji} Green").format(emoji='💚')
    if color == "y":
        return themed("{emoji} Yellow").format(emoji='💛')


def display_color_group(color, game):
    """ Convert a color code to actual color name """
    if color == "r":
        return "{emoji} Red".format(
            emoji='❤️')
    if color == "b":
        return "{emoji} Blue".format(
            emoji='💙')
    if color == "g":
        return "{emoji} Green".format(
            emoji='💚')
    if color == "y":
        return "{emoji} Yellow".format(
            emoji='💛')


def error(update, context, exc=None):
    """Simple error handler. ``exc`` lets helpers report an exception directly."""
    err = exc if exc is not None else getattr(context, 'error', None)
    logger.error("Unhandled error: %s", err, exc_info=err)


def send_async(bot, *args, **kwargs):
    """Send a message asynchronously"""
    if 'timeout' not in kwargs:
        kwargs['timeout'] = TIMEOUT
    if isinstance(kwargs.get('text'), HTMLText):
        kwargs.setdefault('parse_mode', 'HTML')

    try:
        run_in_background(bot.sendMessage, *args, **kwargs)
    except Exception as e:
        error(None, None, e)


def answer_async(bot, *args, **kwargs):
    """Answer an inline query asynchronously"""
    if 'timeout' not in kwargs:
        kwargs['timeout'] = TIMEOUT

    try:
        run_in_background(bot.answerInlineQuery, *args, **kwargs)
    except Exception as e:
        error(None, None, e)


def game_is_running(game):
    return game in gm.chatid_games.get(game.chat.id, list())


def user_is_creator(user, game):
    return user.id in game.owner


def user_is_admin(user, bot, chat):
    return user.id in get_admin_ids(bot, chat.id)


def user_is_creator_or_admin(user, game, bot, chat):
    return user_is_creator(user, game) or user_is_admin(user, bot, chat)


@MWT(timeout=60*60)
def get_admin_ids(bot, chat_id):
    """Returns a list of admin IDs for a given chat. Results are cached for 1 hour."""
    return [admin.user.id for admin in bot.get_chat_administrators(chat_id)]
