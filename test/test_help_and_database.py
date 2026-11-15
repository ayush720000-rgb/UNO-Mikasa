import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)
os.environ.setdefault('TOKEN', '123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef')
os.environ.setdefault('UNO_DB', os.path.join(tempfile.mkdtemp(), 'test.sqlite3'))
os.environ.setdefault('PORT', '')

import config  # noqa: E402
if not config.TOKEN:  # config may already be imported by another test module
    config.TOKEN = '123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef'

from telegram.error import TelegramError  # noqa: E402
import simple_commands as sc  # noqa: E402
from database import _postgres_kwargs  # noqa: E402


def make_context(chat_type, chat_id, user_id, private_send_fails=False):
    bot = MagicMock()
    bot.username = 'UnoTestBot'
    bot.first_name = 'UNO'
    if private_send_fails:
        bot.send_message.side_effect = [
            TelegramError("Forbidden: bot can't initiate conversation"),
            MagicMock(message_id=99),
        ]
    else:
        bot.send_message.return_value = MagicMock(message_id=99)
    update = MagicMock()
    update.message.chat.type = chat_type
    update.message.chat.id = chat_id
    update.message.message_id = 7
    update.message.from_user.id = user_id
    ctx = MagicMock()
    ctx.bot = bot
    ctx.job_queue = MagicMock()
    return update, ctx, bot


class HelpCommandTests(unittest.TestCase):
    def test_group_guide_is_ephemeral_to_the_sender_and_stays_in_the_group(self):
        update, ctx, bot = make_context('supergroup', -100, 555)
        sc.help_handler(update, ctx)
        self.assertEqual(bot.send_message.call_count, 1)
        kwargs = bot.send_message.call_args.kwargs
        self.assertEqual(kwargs['chat_id'], -100)
        self.assertEqual(kwargs['api_kwargs'],
                         {'ephemeral_message_parameters': {'receiver_user_id': 555}})
        bot.delete_message.assert_not_called()
        ctx.job_queue.run_once.assert_not_called()

    def test_group_guide_never_goes_to_a_private_chat(self):
        update, ctx, bot = make_context('group', -200, 556)
        sc.help_handler(update, ctx)
        for call in bot.send_message.call_args_list:
            self.assertNotEqual(call.kwargs['chat_id'], 556)

    def test_private_chat_sends_a_normal_guide(self):
        update, ctx, bot = make_context('private', 556, 556)
        sc.help_handler(update, ctx)
        self.assertEqual(bot.send_message.call_count, 1)
        kwargs = bot.send_message.call_args.kwargs
        self.assertEqual(kwargs['chat_id'], 556)
        self.assertNotIn('api_kwargs', kwargs)

    def test_guide_button_in_group_replaces_the_ephemeral_guide(self):
        bot = MagicMock()
        ctx = MagicMock()
        ctx.bot = bot
        query = MagicMock()
        query.data = sc.GUIDE_PREFIX + sc.GUIDE_SECTIONS[0]
        query.message.chat.type = 'supergroup'
        query.message.chat.id = -100
        query.id = 'cbq-1'
        update = MagicMock()
        update.callback_query = query
        sc.guide_callback(update, ctx)
        query.edit_message_text.assert_not_called()
        kwargs = bot.send_message.call_args.kwargs
        self.assertEqual(kwargs['chat_id'], -100)
        self.assertEqual(kwargs['api_kwargs'], {'ephemeral_message_parameters': {
            'callback_query_id': 'cbq-1', 'replace_callback_query_message': True}})

    def test_guide_button_in_private_chat_edits_in_place(self):
        bot = MagicMock()
        ctx = MagicMock()
        ctx.bot = bot
        query = MagicMock()
        query.data = sc.GUIDE_PREFIX + sc.GUIDE_SECTIONS[0]
        query.message.chat.type = 'private'
        update = MagicMock()
        update.callback_query = query
        sc.guide_callback(update, ctx)
        # PTB 22: the edit goes through the bot, so it works from a worker thread.
        bot.editMessageText.assert_called_once()
        self.assertEqual(bot.editMessageText.call_args.kwargs['message_id'], query.message.message_id)
        bot.send_message.assert_not_called()

    def test_help_and_guide_are_ephemeral_commands(self):
        import start_bot
        self.assertIn('help', start_bot.EPHEMERAL_COMMANDS)
        self.assertIn('guide', start_bot.EPHEMERAL_COMMANDS)

    def test_guide_image_is_gone(self):
        self.assertFalse(hasattr(sc, 'GUIDE_IMAGE'))


class PostgresUrlTests(unittest.TestCase):
    def test_neon_style_url_is_parsed(self):
        kw = _postgres_kwargs('postgresql://neon_user:p%40ss@ep-cool.eu-central-1.aws.neon.tech/neondb?sslmode=require')
        self.assertEqual(kw['user'], 'neon_user')
        self.assertEqual(kw['password'], 'p@ss')
        self.assertEqual(kw['host'], 'ep-cool.eu-central-1.aws.neon.tech')
        self.assertEqual(kw['port'], 5432)
        self.assertEqual(kw['database'], 'neondb')
        self.assertEqual(kw['sslmode'], 'require')

    def test_socket_host_passed_as_query_parameter(self):
        kw = _postgres_kwargs('postgresql://postgres:@/postgres?host=/tmp/pgdata')
        self.assertEqual(kw['host'], '/tmp/pgdata')
        self.assertEqual(kw['user'], 'postgres')


if __name__ == '__main__':
    unittest.main()
