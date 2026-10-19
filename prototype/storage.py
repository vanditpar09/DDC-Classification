"""Small local repository. SQLite retains encoded images, never decoded buffers.

The prototype deliberately uses one serving process; Engine serializes writes.
Operation receipts survive a restart so an interrupted upload is not repeated.
"""
from __future__ import annotations

import json
import logging
import threading
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class MemoryStore:
    def __init__(self):
        self.sessions, self.images, self.operations = {}, {}, {}

    def get(self, sid):
        return self.sessions.get(sid)

    def save(self, session, image=None):
        sid = session['id']
        self.sessions[sid] = session
        if image:
            self.images[(sid, image[0])] = image[1]
        live = {p['id'] for p in session['pages']}
        for key in list(self.images):
            if key[0] == sid and key[1] not in live:
                del self.images[key]

    def list(self):
        return sorted(self.sessions.values(), key=lambda s: s['updated'], reverse=True)

    def image(self, sid, pid):
        return self.images.get((sid, pid))

    def delete(self, sid):
        self.sessions.pop(sid, None)
        for mapping in (self.images, self.operations):
            for key in list(mapping):
                if key[0] == sid:
                    del mapping[key]

    def receipt(self, sid, key):
        return self.operations.get((sid, key))

    def record(self, sid, key, value):
        self.operations[(sid, key)] = value


class SQLiteStore:
    def __init__(self, path):
        self.path = Path(path)
        self.export_root = self.path.with_name(self.path.stem+'-exports')
        self.export_error = None
        self.export_lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS images (
                    sid TEXT, pid TEXT, body BLOB NOT NULL, PRIMARY KEY(sid, pid),
                    FOREIGN KEY(sid) REFERENCES sessions(id) ON DELETE CASCADE);
                CREATE TABLE IF NOT EXISTS operations (
                    sid TEXT, key TEXT, body TEXT NOT NULL, PRIMARY KEY(sid, key),
                    FOREIGN KEY(sid) REFERENCES sessions(id) ON DELETE CASCADE);
            ''')
        self.refresh_outputs()

    def refresh_outputs(self, session=None, deleted=None, image=None):
        from prototype import collection_export
        with self.export_lock:
            try:
                if deleted is not None:
                    collection_export.remove_session(self, deleted)
                if session is not None:
                    collection_export.sync_session(self, session, image=image)
                    collection_export.sync_table(self)
                elif deleted is not None:
                    collection_export.sync_table(self)
                else:
                    collection_export.rebuild(self)
                self.export_error = None
            except (OSError, ValueError, TypeError) as error:
                self.export_error = str(error)
                logging.getLogger(__name__).warning('Capture is saved in SQLite; readable exports could not update: %s', error)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(str(self.path), timeout=30)
        db.execute('PRAGMA foreign_keys = ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, sid):
        with self.connect() as db:
            row = db.execute('SELECT body FROM sessions WHERE id=?', (sid,)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self):
        with self.connect() as db:
            return sorted((json.loads(r[0]) for r in db.execute('SELECT body FROM sessions')),
                          key=lambda s: s['updated'], reverse=True)

    def save(self, session, image=None):
        sid = session['id']
        with self.connect() as db:
            db.execute('INSERT INTO sessions VALUES (?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body',
                       (sid, json.dumps(session, ensure_ascii=False, allow_nan=False)))
            if image:
                db.execute('INSERT OR REPLACE INTO images VALUES (?,?,?)', (sid, image[0], image[1]))
            live = {p['id'] for p in session['pages']}
            for (pid,) in db.execute('SELECT pid FROM images WHERE sid=?', (sid,)).fetchall():
                if pid not in live:
                    db.execute('DELETE FROM images WHERE sid=? AND pid=?', (sid, pid))
        self.refresh_outputs(session=session, image=image)

    def image(self, sid, pid):
        with self.connect() as db:
            row = db.execute('SELECT body FROM images WHERE sid=? AND pid=?', (sid, pid)).fetchone()
        return row[0] if row else None

    def delete(self, sid):
        with self.connect() as db:
            db.execute('DELETE FROM sessions WHERE id=?', (sid,))
        self.refresh_outputs(deleted=sid)

    def receipt(self, sid, key):
        with self.connect() as db:
            row = db.execute('SELECT body FROM operations WHERE sid=? AND key=?', (sid, key)).fetchone()
        return json.loads(row[0]) if row else None

    def record(self, sid, key, value):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO operations VALUES (?,?,?)',
                       (sid, key, json.dumps(value, ensure_ascii=False)))
