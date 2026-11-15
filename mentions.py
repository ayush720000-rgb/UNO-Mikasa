#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clickable player mentions and bold notices, built as plain text + entities.

Every player is mentioned with a text_mention entity, which is the same mention Telegram
uses for members. It works for users without a username, which an "@name" cannot do.
Telegram measures entity offsets in UTF-16 code units, so lengths are measured that way
too. That keeps names with emoji or styled letters (for example 𝙳𝚊𝚣𝚊𝚒) correct.
"""

import re
from collections.abc import Mapping

from telegram import MessageEntity, User

_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def utf16_len(text):
    return len(str(text).encode("utf-16-le")) // 2


class Msg(Mapping):
    """Message text and entities. Behaves like a dict of send kwargs: ``**msg(...)``.

    Empty entity lists are left out so plain messages stay plain.
    """

    def __init__(self, text="", entities=None):
        self.text = text
        self.entities = list(entities or [])

    def __getitem__(self, key):
        if key == "text":
            return self.text
        if key == "entities" and self.entities:
            return self.entities
        raise KeyError(key)

    def __iter__(self):
        yield "text"
        if self.entities:
            yield "entities"

    def __len__(self):
        return 2 if self.entities else 1

    def __add__(self, other):
        if isinstance(other, Msg):
            shift = utf16_len(self.text)
            moved = [_shifted(e, shift) for e in other.entities]
            return Msg(self.text + other.text, self.entities + moved)
        return Msg(self.text + str(other), self.entities)

    def __radd__(self, other):
        return Msg(str(other) + self.text, [_shifted(e, utf16_len(other)) for e in self.entities])


def _shifted(entity, shift):
    copy = MessageEntity(type=entity.type, offset=entity.offset + shift, length=entity.length,
                         url=entity.url, user=entity.user, language=entity.language)
    return copy


def _label(user):
    return (user.first_name or "").strip() or "Player"


def _compose(template, values, icon=None):
    text_parts = []
    entities = []
    offset = 0

    def add(chunk):
        nonlocal offset
        text_parts.append(chunk)
        offset += utf16_len(chunk)

    if icon is not None:
        add(icon + " ")
    bold_from = offset

    position = 0
    for match in _PLACEHOLDER.finditer(template):
        add(template[position:match.start()])
        value = values[match.group(1)]
        if isinstance(value, User):
            label = _label(value)
            entities.append(MessageEntity(type=MessageEntity.TEXT_MENTION, offset=offset,
                                          length=utf16_len(label), user=value))
            add(label)
            if value.username:
                add(" (@%s)" % value.username)
        elif isinstance(value, Msg):
            shift = offset
            add(value.text)
            entities.extend(_shifted(e, shift) for e in value.entities)
        else:
            add(str(value))
        position = match.end()
    add(template[position:])

    text = "".join(text_parts)
    if icon is not None:
        entities.append(MessageEntity(type=MessageEntity.BOLD, offset=bold_from,
                                      length=utf16_len(text) - bold_from))
    return Msg(text, entities)


def msg(template, **values):
    """Plain message with clickable player mentions. ``{name}`` takes a telegram User."""
    return _compose(template, values)


def notice(icon, template, **values):
    """Bold notice with an icon, the mention-capable equivalent of the fmt.warn/ok/info blocks."""
    return _compose(template, values, icon=icon)


def join(separator, pieces):
    result = Msg()
    for index, piece in enumerate(pieces):
        if index:
            result = result + separator
        result = result + piece
    return result


def display_text(user):
    """Plain name for logs, never sent to players."""
    name = _label(user)
    return name + (" (@%s)" % user.username if user.username else "")
