import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from platformdirs import user_data_dir

DEFAULTS = {"assistant_name": "Nila", "user_name": "", "model": "llama3.2:1b", "language": "Auto", "temperature": 0.7, "num_ctx": 2048, "memory_enabled": True}

class Store:
    def __init__(self, root=None):
        self.root = Path(root or os.environ.get("NILA_DATA_DIR") or user_data_dir("Nila", appauthor=False))
        self.root.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            self.root.chmod(0o700)
        self.path = self.root / "nila.db"
        with self.db() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS chats (id TEXT PRIMARY KEY, title TEXT NOT NULL, updated REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE, role TEXT NOT NULL, content TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'complete');
                CREATE TABLE IF NOT EXISTS memories (id TEXT PRIMARY KEY, content TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS notes (id TEXT PRIMARY KEY, content TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, content TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS lease (id INTEGER PRIMARY KEY, token TEXT, expires REAL);
            ''')
        if os.name != "nt":
            self.path.chmod(0o600)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def settings(self):
        with self.db() as db:
            return DEFAULTS | {r["key"]: json.loads(r["value"]) for r in db.execute("SELECT * FROM settings")}

    def save_settings(self, values):
        with self.db() as db:
            db.executemany("INSERT OR REPLACE INTO settings VALUES (?,?)", [(k, json.dumps(v)) for k,v in values.items() if k in DEFAULTS])
        return self.settings()

    def create_chat(self):
        cid = str(uuid.uuid4())
        with self.db() as db:
            db.execute("INSERT INTO chats VALUES (?,?,?)", (cid, "New conversation", time.time()))
        return self.chat(cid)

    def chats(self):
        with self.db() as db:
            return [dict(r) for r in db.execute("SELECT * FROM chats ORDER BY updated DESC")]

    def chat(self, cid):
        with self.db() as db:
            row = db.execute("SELECT * FROM chats WHERE id=?", (cid,)).fetchone()
            if row is None:
                raise KeyError("Conversation not found")
            return dict(row) | {"messages": [dict(r) for r in db.execute("SELECT * FROM messages WHERE chat_id=? ORDER BY id", (cid,))]}

    def add_message(self, cid, role, content, status="complete"):
        with self.db() as db:
            db.execute("INSERT INTO messages(chat_id,role,content,status) VALUES (?,?,?,?)", (cid,role,content,status))
            db.execute("UPDATE chats SET updated=? WHERE id=?", (time.time(),cid))
            if role == "user":
                db.execute("UPDATE chats SET title=? WHERE id=? AND title='New conversation'", (content[:65],cid))

    def delete_chat(self, cid):
        with self.db() as db:
            db.execute("DELETE FROM chats WHERE id=?", (cid,))

    def items(self, kind):
        assert kind in {"memories", "notes", "tasks"}
        with self.db() as db:
            return [dict(r) for r in db.execute(f"SELECT * FROM {kind} ORDER BY created DESC")]

    def add_item(self, kind, content):
        assert kind in {"memories", "notes", "tasks"}
        iid = str(uuid.uuid4())
        with self.db() as db:
            if db.execute(f"SELECT COUNT(*) FROM {kind}").fetchone()[0] >= 500:
                raise ValueError("Limit of 500 items reached. Remove an older item first.")
            db.execute(f"INSERT INTO {kind}(id,content,created) VALUES (?,?,?)", (iid,content,time.time()))
        return iid

    def update_item(self, kind, iid, content=None, done=None):
        assert kind in {"memories", "notes", "tasks"}
        with self.db() as db:
            if content is not None:
                db.execute(f"UPDATE {kind} SET content=? WHERE id=?", (content,iid))
            if done is not None and kind == "tasks":
                db.execute("UPDATE tasks SET done=? WHERE id=?", (int(done),iid))

    def delete_item(self, kind, iid):
        assert kind in {"memories", "notes", "tasks"}
        with self.db() as db:
            db.execute(f"DELETE FROM {kind} WHERE id=?", (iid,))

    def acquire(self):
        token = str(uuid.uuid4())
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT expires FROM lease WHERE id=1").fetchone()
            if row and row[0] > time.time():
                raise RuntimeError("NILA-003: Another request is running. Stop it or wait for completion.")
            db.execute("INSERT OR REPLACE INTO lease VALUES (1,?,?)", (token,time.time()+660))
        return token

    def release(self, token):
        with self.db() as db:
            db.execute("DELETE FROM lease WHERE token=?", (token,))
