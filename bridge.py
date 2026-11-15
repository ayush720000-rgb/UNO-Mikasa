#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runs the synchronous UNO game code on top of python-telegram-bot 22's asyncio loop.

The game, database and message code was written for the blocking PTB 13 API. PTB 22 is
asyncio-only, so instead of rewriting every function as ``async``:

* Every PTB callback (command, button, inline query, job, error) is wrapped with
  :func:`threaded`. The wrapper runs the original function on a worker thread, the same
  model PTB 13 used with its dispatcher workers. Pony's thread-local ``db_session`` keeps
  working unchanged.
* Calls made from those threads (``bot.sendMessage(...)``, ``job_queue.run_once(...)``)
  go through :class:`_SyncBot` / :class:`_SyncJobQueue`, which run the real PTB coroutine on
  the event loop and wait for the result.
* :func:`run_in_background` replaces PTB 13's ``dispatcher.run_async``.

This module also holds the PTB 13 -> 22 keyword translations (``timeout``,
``disable_web_page_preview``, ``switch_pm_*``) and the camelCase -> snake_case method names,
so the game code keeps its original call sites.
"""
import asyncio
import functools
import inspect
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor

from telegram import InlineQueryResultsButton, LinkPreviewOptions

from config import WORKERS

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=WORKERS, thread_name_prefix='uno-worker')
_loop = None
_loop_thread_id = None
_sync_bot = None


def set_loop(loop):
    """Called once on startup, from the event loop thread."""
    global _loop, _loop_thread_id
    _loop = loop
    _loop_thread_id = threading.get_ident()


def _snake(name):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


def _translate(kwargs):
    """Map PTB 13 keyword arguments onto their PTB 22 equivalents."""
    if 'timeout' in kwargs:
        kwargs.setdefault('read_timeout', kwargs.pop('timeout'))
    if kwargs.pop('disable_web_page_preview', False):
        kwargs.setdefault('link_preview_options', LinkPreviewOptions(is_disabled=True))
    if 'switch_pm_text' in kwargs:
        text = kwargs.pop('switch_pm_text')
        start = kwargs.pop('switch_pm_parameter', None)
        if text:
            kwargs.setdefault('button', InlineQueryResultsButton(text=text, start_parameter=start))
    return kwargs


def _run_on_loop(fn, *args, **kwargs):
    """Run ``fn`` (a PTB coroutine function or plain method) on the event loop and wait."""
    if threading.get_ident() == _loop_thread_id:
        raise RuntimeError("Blocking bot call made on the event loop thread would deadlock")

    async def runner():
        result = fn(*args, **kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result

    return asyncio.run_coroutine_threadsafe(runner(), _loop).result()


class _SyncBot:
    """Blocking facade over ``telegram.Bot``, with PTB 13 method names and kwargs."""

    def __init__(self, bot):
        self._bot = bot

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        target = getattr(self._bot, _snake(name))
        if not callable(target):
            return target

        def call(*args, **kwargs):
            return _run_on_loop(target, *args, **_translate(kwargs))
        return call


class _SyncJobQueue:
    """Blocking facade over ``JobQueue``. Scheduling happens on the loop thread."""

    def __init__(self, job_queue):
        self._job_queue = job_queue

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        target = getattr(self._job_queue, name)
        if not callable(target):
            return target
        return lambda *args, **kwargs: _run_on_loop(target, *args, **kwargs)


def sync_bot_for(bot):
    """One facade per process, so MWT caches keyed on the bot object keep working."""
    global _sync_bot
    if _sync_bot is None or _sync_bot._bot is not bot:
        _sync_bot = _SyncBot(bot)
    return _sync_bot


class _SyncContext:
    """Wraps a PTB ``CallbackContext`` so ``.bot`` and ``.job_queue`` are blocking."""

    def __init__(self, context):
        self._context = context

    @property
    def bot(self):
        return sync_bot_for(self._context.bot)

    @property
    def job_queue(self):
        job_queue = self._context.job_queue
        return _SyncJobQueue(job_queue) if job_queue is not None else None

    def __getattr__(self, name):
        return getattr(self._context, name)


def threaded(fn):
    """Adapt a blocking ``fn(update, context)`` (or ``fn(context)``) to a PTB async callback."""
    @functools.wraps(fn)
    async def wrapper(*args):
        *head, context = args
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            _executor, fn, *head, _SyncContext(context))
    return wrapper


def run_in_background(fn, *args, **kwargs):
    """Fire-and-forget, like PTB 13's ``dispatcher.run_async``. Errors are logged."""
    def job():
        try:
            return fn(*args, **kwargs)
        except Exception:
            logger.exception("Background call failed")
    return _executor.submit(job)
