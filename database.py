#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import logging
import os
from urllib.parse import urlparse, parse_qs, unquote

from pony.orm import Database

logger = logging.getLogger(__name__)

# Database singleton
db = Database()


def _postgres_kwargs(url):
    """Turn a postgres:// URL (e.g. Neon) into keyword arguments for psycopg2."""
    parts = urlparse(url)
    query = parse_qs(parts.query)
    kwargs = {
        'user': unquote(parts.username or ''),
        'password': unquote(parts.password or ''),
        'host': parts.hostname or query.get('host', [None])[0],
        'port': parts.port or 5432,
        'database': parts.path.lstrip('/'),
        'sslmode': query.get('sslmode', ['require'])[0],
    }
    return kwargs


def bind_database():
    """Use Postgres when DATABASE_URL is set and reachable, otherwise the local SQLite file.

    The connection is tested before binding because Pony cannot be bound twice.
    """
    url = os.getenv('DATABASE_URL', '').strip()
    if url:
        try:
            import psycopg2
            kwargs = _postgres_kwargs(url)
            psycopg2.connect(connect_timeout=10, **kwargs).close()
            db.bind('postgres', **kwargs)
            logger.info('Using Postgres (DATABASE_URL).')
            return
        except Exception as e:
            logger.error('Postgres unavailable, falling back to SQLite: %s', e)

    db.bind('sqlite', os.getenv('UNO_DB', 'uno.sqlite3'), create_db=True)
