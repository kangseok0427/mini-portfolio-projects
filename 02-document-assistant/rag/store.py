import sqlite3
import json
import hashlib
from pathlib import Path
from uuid import uuid4
from .documents import extract, chunks


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,name TEXT,hash TEXT UNIQUE);
            CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY,document_id TEXT,page INTEGER,text TEXT);
            CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,session TEXT,role TEXT,text TEXT,sources TEXT);
            CREATE INDEX IF NOT EXISTS chunks_doc ON chunks(document_id);
            CREATE INDEX IF NOT EXISTS messages_session ON messages(session,id);""")

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def add(self, name, content):
        parsed = chunks(extract(name, content))
        digest = hashlib.sha256(content).hexdigest()
        with self.connect() as db:
            old = db.execute(
                "SELECT id FROM documents WHERE hash=?", (digest,)
            ).fetchone()
            if old:
                return {"id": old["id"], "duplicate": True, "chunks": 0}
            if db.execute("SELECT count(*) FROM documents").fetchone()[0] >= 30:
                raise ValueError("문서는 30개까지 등록할 수 있습니다")
            identifier = uuid4().hex
            db.execute(
                "INSERT INTO documents VALUES(?,?,?)", (identifier, name, digest)
            )
            db.executemany(
                "INSERT INTO chunks VALUES(?,?,?,?)",
                [(uuid4().hex, identifier, page, text) for page, text in parsed],
            )
        return {"id": identifier, "duplicate": False, "chunks": len(parsed)}

    def documents(self):
        with self.connect() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT d.id,d.name,count(c.id) AS chunks FROM documents d LEFT JOIN chunks c ON c.document_id=d.id GROUP BY d.id ORDER BY d.name"
                )
            ]

    def corpus(self):
        with self.connect() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT c.*,d.name FROM chunks c JOIN documents d ON d.id=c.document_id"
                )
            ]

    def remove(self, identifier=None):
        with self.connect() as db:
            if identifier:
                db.execute("DELETE FROM chunks WHERE document_id=?", (identifier,))
                db.execute("DELETE FROM documents WHERE id=?", (identifier,))
            else:
                db.execute("DELETE FROM chunks")
                db.execute("DELETE FROM documents")
            db.execute("DELETE FROM messages")

    def history(self, session):
        with self.connect() as db:
            return [
                {
                    "role": r["role"],
                    "text": r["text"],
                    "sources": json.loads(r["sources"]),
                }
                for r in db.execute(
                    "SELECT * FROM (SELECT * FROM messages WHERE session=? ORDER BY id DESC LIMIT 40) ORDER BY id",
                    (session,),
                )
            ]

    def save_exchange(self, session, question, answer, sources):
        with self.connect() as db:
            db.executemany(
                "INSERT INTO messages(session,role,text,sources) VALUES(?,?,?,?)",
                [
                    (session, "user", question, "[]"),
                    (
                        session,
                        "assistant",
                        answer,
                        json.dumps(sources, ensure_ascii=False),
                    ),
                ],
            )

    def clear_history(self, session):
        with self.connect() as db:
            db.execute("DELETE FROM messages WHERE session=?", (session,))
