#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""Defines helper functions to build the inline result list"""

from smallcaps import themed
from uuid import uuid4

from telegram import InlineQueryResultArticle, InputTextMessageContent, \
    InlineQueryResultCachedSticker as Sticker

import card as c
from utils import display_color, display_color_group, display_name
from mentions import msg, join


def add_choose_color(results, game):
    """Add choose color options"""
    for color in c.COLORS:
        results.append(
            InlineQueryResultArticle(
                id=color,
                title=themed("Choose Color"),
                description=display_color(color),
                input_message_content=
                InputTextMessageContent(display_color_group(color, game))
            )
        )


def add_other_cards(player, results, game):
    """Add hand cards when choosing colors"""

    results.append(
        InlineQueryResultArticle(
            "hand",
            title=themed("Card (tap for game state):" if len(player.cards) == 1 else "Cards (tap for game state):"),
            description=', '.join([repr(card) for card in player.cards]),
            input_message_content=game_info(game)
        )
    )


def player_list(game):
    """One clickable mention per player, e.g. "Name (2 cards)" """
    return [msg(themed("{name} ({number} card)" if len(player.cards) == 1 else "{name} ({number} cards)"),
                name=player.user, number=len(player.cards))
            for player in game.players]


def add_no_game(results):
    """Add text result if user is not playing"""
    results.append(
        InlineQueryResultArticle(
            "nogame",
            title=themed("You are not playing"),
            input_message_content=
            InputTextMessageContent(themed('Not playing right now. Use /new to '
                                      'start a game or /join to join the '
                                      'current game in this group'))
        )
    )


def add_not_started(results):
    """Add text result if the game has not yet started"""
    results.append(
        InlineQueryResultArticle(
            "nogame",
            title=themed("The game wasn't started yet"),
            input_message_content=
            InputTextMessageContent(themed('Start the game with /start'))
        )
    )


def add_mode_classic(results):
    """Change mode to classic"""
    results.append(
        InlineQueryResultArticle(
            "mode_classic",
            title=themed("🎻 Classic mode"),
            input_message_content=
            InputTextMessageContent(themed('Classic 🎻'))
        )
    )


def add_mode_fast(results):
    """Change mode to classic"""
    results.append(
        InlineQueryResultArticle(
            "mode_fast",
            title=themed("🚀 Sanic mode"),
            input_message_content=
            InputTextMessageContent(themed('Gotta go fast! 🚀'))
        )
    )


def add_mode_wild(results):
    """Change mode to classic"""
    results.append(
        InlineQueryResultArticle(
            "mode_wild",
            title=themed("🐉 Wild mode"),
            input_message_content=
            InputTextMessageContent(themed('Into the Wild~ 🐉'))
        )
    )


def add_mode_text(results):
    """Change mode to text"""
    results.append(
        InlineQueryResultArticle(
            "mode_text",
            title=themed("✍️ Text mode"),
            input_message_content=
            InputTextMessageContent(themed('Text ✍️'))
        )
    )
    
    
def add_draw(player, results):
    """Add option to draw"""
    n = player.game.draw_counter or 1

    results.append(
        Sticker(
            "draw", sticker_file_id=c.STICKERS['option_draw'],
            input_message_content=
            InputTextMessageContent(('Drawing {number} card' if n == 1 else 'Drawing {number} cards')
                                    .format(number=n))
        )
    )


def add_gameinfo(game, results):
    """Add option to show game info"""

    results.append(
        Sticker(
            "gameinfo",
            sticker_file_id=c.STICKERS['option_info'],
            input_message_content=game_info(game)
        )
    )


def add_pass(results, game):
    """Add option to pass"""
    results.append(
        Sticker(
            "pass", sticker_file_id=c.STICKERS['option_pass'],
            input_message_content=InputTextMessageContent(
                'Pass'
            )
        )
    )


def add_call_bluff(results, game):
    """Add option to call a bluff"""
    results.append(
        Sticker(
            "call_bluff",
            sticker_file_id=c.STICKERS['option_bluff'],
            input_message_content=
            InputTextMessageContent("I'm calling your bluff!")
        )
    )


def add_card(game, card, results, can_play):
    """Add an option that represents a card"""

    if can_play:
        if game.mode != "text":
            results.append(
                Sticker(str(card), sticker_file_id=c.STICKERS[str(card)])
        )
        if game.mode == "text":
            results.append(
                Sticker(str(card), sticker_file_id=c.STICKERS[str(card)], input_message_content=InputTextMessageContent("Card Played: {card}".format(card=repr(card).replace('Draw Four', '+4').replace('Draw', '+2').replace('Colorchooser', 'Color Chooser')))
        ))
    else:
        results.append(
            Sticker(str(uuid4()), sticker_file_id=c.STICKERS_GREY[str(card)],
                    input_message_content=game_info(game))
        )


def game_info(game):
    """Inline result text. Player names are clickable mentions (text_mention entities)."""
    players = join(" -> ", player_list(game))
    message = (msg(themed("Current player: {name}"), name=game.current_player.user)
               + "\n"
               + themed("Last card: {card}").format(card=repr(game.last_card))
               + "\n"
               + msg(themed("Player: {player_list}" if len(game.players) == 1 else "Players: {player_list}"),
                     player_list=players))
    return InputTextMessageContent(message.text, entities=message.entities or None)
