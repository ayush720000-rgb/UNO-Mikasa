#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Telegram bot to play UNO in group chats
# Copyright (c) 2016 Jannes Höke <uno@jhoeke.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

# Startup sequence.
#
# Startup sequence.
#
# On Render (free tier) the bot runs in WEBHOOK mode: Telegram pushes each update to
# our public URL, so a message wakes a sleeping instance. The instance sleeps after
# 15 minutes without incoming requests, so it costs no hours while idle.
#
# Without a public URL (local runs) the bot uses long polling instead.
#
#   * one small HTTP server on $PORT serving GET /health and the webhook
#   * the command menu is set automatically from commandlist.txt

import hashlib
import hmac
import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from telegram import BotCommand, Update

from config import PORT, TOKEN, WEBHOOK_URL, SMALL_CAPS
from smallcaps import small_caps

logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/telegram"
HEALTH_PATH = "/health"
SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"


class _RequestHandler(BaseHTTPRequestHandler):
    def _send(self, code, body=b"", send_body=True):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if send_body:
            self.wfile.write(body)

    def do_GET(self):
        if self.path.split("?", 1)[0] == HEALTH_PATH:
            self._send(200, b"UNO bot is running")
        else:
            self._send(404, b"Not found")

    def do_HEAD(self):
        if self.path.split("?", 1)[0] == HEALTH_PATH:
            self._send(200, b"UNO bot is running", send_body=False)
        else:
            self._send(404, b"Not found", send_body=False)

    def do_POST(self):
        # The webhook route only exists in webhook mode.
        if self.server.secret is None or self.path.split("?", 1)[0] != WEBHOOK_PATH:
            self._send(404, b"Not found")
            return

        # Only requests that carry the secret we registered with Telegram are accepted.
        given = self.headers.get(SECRET_HEADER, "")
        if not hmac.compare_digest(given, self.server.secret):
            self._send(403, b"Forbidden")
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
            update = Update.de_json(data, self.server.bot)
        except Exception:
            logger.exception("Could not parse webhook update")
            self._send(400, b"Bad request")
            return

        if update is not None:
            self.server.update_queue.put(update)
        self._send(200, b"ok")

    def log_message(self, *args):  # keep the logs clean
        pass


def _serve_http(updater, port, secret=None):
    """Serve /health on $PORT (Render needs an open port). With a secret, also the webhook."""
    server = ThreadingHTTPServer(("0.0.0.0", port), _RequestHandler)
    server.secret = secret
    server.bot = updater.bot
    server.update_queue = updater.update_queue
    threading.Thread(target=server.serve_forever, name="http", daemon=True).start()
    logger.info("HTTP server listening on 0.0.0.0:%s", port)
    # Updater.stop() shuts this server down on SIGTERM (Render stops/redeploys with it).
    updater.httpd = server
    return server


def _set_command_menu(bot):
    """Fill the Telegram command menu from commandlist.txt (no BotFather needed)"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "commandlist.txt")
    try:
        commands = []
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if " - " not in line:
                    continue
                name, description = line.split(" - ", 1)
                description = description.strip()
                if SMALL_CAPS:
                    description = small_caps(description)
                commands.append(BotCommand(name.strip(), description[:256]))
        bot.set_my_commands(commands)
        logger.info("Command menu set (%d commands)", len(commands))
    except Exception:
        logger.exception("Could not set the command menu")


def _start_webhook(updater, port):
    """Webhook mode: Telegram pushes updates to us. Note that every message wakes the bot."""
    secret = hashlib.sha256(TOKEN.encode("utf-8")).hexdigest()
    _serve_http(updater, port, secret=secret)

    # Process updates from the queue, and run the job queue (turn timers).
    updater.running = True
    updater.job_queue.start()
    threading.Thread(target=updater.dispatcher.start, name="dispatcher", daemon=True).start()

    # Pending updates are kept on purpose: the update that woke a sleeping instance is
    # queued on Telegram's side, and dropping it here would lose that first command.
    url = WEBHOOK_URL.rstrip("/") + WEBHOOK_PATH
    for attempt in range(1, 6):
        try:
            updater.bot.set_webhook(url=url, secret_token=secret, drop_pending_updates=False)
            logger.info("Webhook set to %s", url)
            return
        except Exception as e:
            logger.warning("set_webhook attempt %d failed: %s", attempt, e)
            time.sleep(5)
    raise RuntimeError("Could not register the Telegram webhook")


def start_bot(updater):
    _set_command_menu(updater.bot)

    if WEBHOOK_URL and PORT:
        _start_webhook(updater, int(PORT))
    else:
        if PORT:
            # Long polling; the HTTP server only exists so Render can wake the bot
            # when UptimeRobot (or anyone) calls its URL.
            _serve_http(updater, int(PORT))
        logger.info("Using long polling")
        # Updates that piled up while the bot was offline are dropped, so players
        # don't get a flood of old commands after a restart.
        updater.start_polling(drop_pending_updates=True)
