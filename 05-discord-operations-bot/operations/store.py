"""Small, single-instance SQLite store. No message bodies or credentials are saved."""
import sqlite3
from pathlib import Path


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS tickets (
                channel_id INTEGER PRIMARY KEY, guild_id INTEGER NOT NULL,
                owner_id INTEGER NOT NULL, state TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE UNIQUE INDEX IF NOT EXISTS one_open_ticket
                ON tickets(guild_id, owner_id) WHERE state='open';
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY, action TEXT NOT NULL, guild_id INTEGER NOT NULL,
                actor_id INTEGER NOT NULL, channel_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        """)

    def active(self, guild_id, owner_id):
        return self.db.execute(
            "SELECT * FROM tickets WHERE guild_id=? AND owner_id=? AND state='open'",
            (guild_id, owner_id)).fetchone()

    def ticket(self, guild_id, channel_id):
        return self.db.execute(
            "SELECT * FROM tickets WHERE guild_id=? AND channel_id=? AND state='open'",
            (guild_id, channel_id)).fetchone()

    def opened(self, guild_id, owner_id, channel_id):
        with self.db:
            self.db.execute("INSERT INTO tickets(channel_id,guild_id,owner_id) VALUES(?,?,?)",
                            (channel_id, guild_id, owner_id))
            self._event("ticket_open", guild_id, owner_id, channel_id)

    def closed(self, guild_id, actor_id, channel_id, action="ticket_close"):
        with self.db:
            self.db.execute("UPDATE tickets SET state='closed' WHERE guild_id=? AND channel_id=?",
                            (guild_id, channel_id))
            self._event(action, guild_id, actor_id, channel_id)

    def event(self, action, guild_id, actor_id):
        with self.db:
            self._event(action, guild_id, actor_id, None)

    def _event(self, action, guild_id, actor_id, channel_id):
        self.db.execute("INSERT INTO events(action,guild_id,actor_id,channel_id) VALUES(?,?,?,?)",
                        (action, guild_id, actor_id, channel_id))

    def recent(self, guild_id):
        return [dict(row) for row in self.db.execute(
            "SELECT action,actor_id,channel_id,created_at FROM events WHERE guild_id=? ORDER BY id DESC LIMIT 10",
            (guild_id,))]

    def close(self):
        self.db.close()
