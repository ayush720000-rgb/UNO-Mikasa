import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

from telegram import MessageEntity, User  # noqa: E402
from mentions import msg, notice, join, utf16_len  # noqa: E402


def user(uid, name, username=None):
    return User(id=uid, first_name=name, is_bot=False, username=username)


class MentionTests(unittest.TestCase):
    def test_mention_works_without_a_username(self):
        dazai = user(42, '太宰 |𝙳𝚊𝚣𝚊𝚒')
        m = msg('Next player: {name}', name=dazai)
        self.assertEqual(m['text'], 'Next player: 太宰 |𝙳𝚊𝚣𝚊𝚒')
        (ent,) = m['entities']
        self.assertEqual(ent.type, MessageEntity.TEXT_MENTION)
        self.assertEqual(ent.user.id, 42)
        self.assertEqual(ent.offset, len('Next player: '))
        self.assertEqual(ent.length, utf16_len('太宰 |𝙳𝚊𝚣𝚊𝚒'))

    def test_offsets_use_utf16_units_for_astral_characters(self):
        # 𝙳 is outside the BMP: 2 UTF-16 units, so the entity must cover the full name
        name = '𝙳𝚊𝚣𝚊𝚒'
        m = msg('{name} wins', name=user(1, name))
        self.assertEqual(m['entities'][0].length, 10)
        self.assertEqual(m['entities'][0].offset, 0)

    def test_username_is_shown_after_the_mention(self):
        m = msg('{name}', name=user(7, 'Lia', 'lia_x'))
        self.assertEqual(m['text'], 'Lia (@lia_x)')
        self.assertEqual(m['entities'][0].length, 3)

    def test_plain_messages_have_no_entities_key(self):
        m = msg('Game ended!')
        self.assertEqual(dict(m), {'text': 'Game ended!'})

    def test_notice_is_bold_after_the_icon(self):
        n = notice('⚠️', 'Only {name} can do that.', name=user(3, 'Ana'))
        bold = [e for e in n['entities'] if e.type == MessageEntity.BOLD][0]
        self.assertEqual(bold.offset, utf16_len('⚠️ '))
        self.assertEqual(bold.length, utf16_len(n['text']) - bold.offset)

    def test_join_keeps_offsets_of_later_mentions(self):
        a = msg('{name} (1 card)', name=user(1, '太宰 |𝙳𝚊𝚣𝚊𝚒'))
        b = msg('{name} (2 cards)', name=user(2, 'Lia'))
        j = join(' -> ', [a, b])
        self.assertEqual(j['text'], '太宰 |𝙳𝚊𝚣𝚊𝚒 (1 card) -> Lia (2 cards)')
        second = [e for e in j['entities'] if e.user and e.user.id == 2][0]
        self.assertEqual(second.offset, utf16_len('太宰 |𝙳𝚊𝚣𝚊𝚒 (1 card) -> '))


if __name__ == '__main__':
    unittest.main()
