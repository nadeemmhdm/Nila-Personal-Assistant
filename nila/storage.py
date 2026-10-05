"""SQLite persistence shared by CLI, Web UI and the automation worker."""
import hashlib
import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from platformdirs import user_data_dir
from .vault import Vault, PREFIX

DEFAULTS = {'assistant_name':'Nila','user_name':'','model':'llama3.2:1b','language':'Auto','temperature':.7,'num_ctx':2048,'memory_enabled':True,'auto_memory':True,'auto_update':True,'description':'','position':'Other','completion_year':'','company':'','job_role':'','knowledge_enabled':True,'course':'','interests':'','tone':'Friendly'}

class Store:
    def __init__(self,root=None):
        self.root=Path(root or os.environ.get('NILA_DATA_DIR') or user_data_dir('Nila',appauthor=False))
        self.root.mkdir(parents=True,exist_ok=True)
        if os.name!='nt': self.root.chmod(0o700)
        self.vault=Vault(self.root)
        self.path=self.root/'nila.db'
        with self.db() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS chats (id TEXT PRIMARY KEY,title TEXT NOT NULL,updated REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT,chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,role TEXT NOT NULL,content TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'complete');
                CREATE TABLE IF NOT EXISTS memories (id TEXT PRIMARY KEY,content TEXT NOT NULL,created REAL NOT NULL,source TEXT NOT NULL DEFAULT 'manual',fingerprint TEXT);
                CREATE TABLE IF NOT EXISTS notes (id TEXT PRIMARY KEY,content TEXT NOT NULL,created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY,content TEXT NOT NULL,done INTEGER NOT NULL DEFAULT 0,created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS lease (id INTEGER PRIMARY KEY,token TEXT,expires REAL);
                CREATE TABLE IF NOT EXISTS feedback (message_id INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,rating INTEGER NOT NULL,reason TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS forgotten (fingerprint TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS automations (id TEXT PRIMARY KEY,title TEXT NOT NULL,prompt TEXT NOT NULL,kind TEXT NOT NULL,interval_minutes INTEGER NOT NULL,next_run REAL NOT NULL,enabled INTEGER NOT NULL DEFAULT 1,running_until REAL NOT NULL DEFAULT 0,claim TEXT);
                CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY,automation_id TEXT NOT NULL,started REAL NOT NULL,status TEXT NOT NULL,output TEXT NOT NULL);
            ''')
            cols={r[1] for r in db.execute('PRAGMA table_info(memories)')}
            if 'source' not in cols: db.execute("ALTER TABLE memories ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'")
            if 'fingerprint' not in cols: db.execute('ALTER TABLE memories ADD COLUMN fingerprint TEXT')
            migrated=False
            for table,columns in {'settings':['value'],'chats':['title'],'messages':['content'],'memories':['content'],'notes':['content'],'tasks':['content'],'automations':['title','prompt'],'runs':['output']}.items():
                for column in columns:
                    rows=db.execute(f'SELECT rowid,{column} FROM {table}').fetchall()
                    for row in rows:
                        if not row[1].startswith(PREFIX):
                            db.execute(f'UPDATE {table} SET {column}=? WHERE rowid=?',(self.seal(row[1]),row[0]))
                            migrated=True
        if migrated:
            with self.db() as db: db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            with sqlite3.connect(self.path) as db: db.execute('VACUUM')
        if os.name!='nt': self.path.chmod(0o600)
    def seal(self,v): return self.vault.seal(v)
    def open(self,v): return self.vault.open(v)
    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path,timeout=10)
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA secure_delete=ON')
        try:
            with db: yield db
        finally: db.close()
    def decode(self,row,fields):
        result=dict(row)
        for field in fields: result[field]=self.open(result[field])
        return result
    def settings(self):
        with self.db() as db: return DEFAULTS|{r['key']:json.loads(self.open(r['value'])) for r in db.execute('SELECT * FROM settings') if r['key'] in DEFAULTS}
    def save_settings(self,values):
        with self.db() as db: db.executemany('INSERT OR REPLACE INTO settings VALUES (?,?)',[(k,self.seal(json.dumps(v))) for k,v in values.items() if k in DEFAULTS])
        return self.settings()
    def create_chat(self):
        cid=str(uuid.uuid4())
        with self.db() as db: db.execute('INSERT INTO chats VALUES (?,?,?)',(cid,self.seal('New conversation'),time.time()))
        return self.chat(cid)
    def chats(self):
        with self.db() as db: return [self.decode(r,['title']) for r in db.execute('SELECT * FROM chats ORDER BY updated DESC')]
    def chat(self,cid):
        with self.db() as db:
            row=db.execute('SELECT * FROM chats WHERE id=?',(cid,)).fetchone()
            if row is None: raise KeyError('Conversation not found')
            return self.decode(row,['title'])|{'messages':[self.decode(r,['content']) for r in db.execute('SELECT messages.*,COALESCE(feedback.rating,0) AS rating FROM messages LEFT JOIN feedback ON feedback.message_id=messages.id WHERE chat_id=? ORDER BY messages.id',(cid,))]}
    def add_message(self,cid,role,content,status='complete'):
        with self.db() as db:
            db.execute('INSERT INTO messages(chat_id,role,content,status) VALUES (?,?,?,?)',(cid,role,self.seal(content),status))
            db.execute('UPDATE chats SET updated=? WHERE id=?',(time.time(),cid))
            count=db.execute("SELECT COUNT(*) FROM messages WHERE chat_id=? AND role='user'",(cid,)).fetchone()[0]
            if role=='user' and count==1: db.execute('UPDATE chats SET title=? WHERE id=?',(self.seal(content[:65]),cid))
    def delete_chat(self,cid):
        with self.db() as db: db.execute('DELETE FROM chats WHERE id=?',(cid,))
    def items(self,kind):
        assert kind in {'memories','notes','tasks'}
        with self.db() as db: return [self.decode(r,['content']) for r in db.execute(f'SELECT * FROM {kind} ORDER BY created DESC')]
    @staticmethod
    def fingerprint(content): return hashlib.sha256(' '.join(content.lower().split()).encode()).hexdigest()
    def add_item(self,kind,content,source='manual'):
        assert kind in {'memories','notes','tasks'}
        iid=str(uuid.uuid4());fingerprint=self.fingerprint(content)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if kind=='memories':
                if source=='automatic' and db.execute('SELECT 1 FROM forgotten WHERE fingerprint=?',(fingerprint,)).fetchone(): return None
                for existing in db.execute('SELECT id,content FROM memories'):
                    if self.fingerprint(self.open(existing['content']))==fingerprint: return existing['id']
            if db.execute(f'SELECT COUNT(*) FROM {kind}').fetchone()[0]>=500: raise ValueError('Limit of 500 items reached. Remove an older item first.')
            if kind=='memories': db.execute('INSERT INTO memories VALUES (?,?,?,?,?)',(iid,self.seal(content),time.time(),source,fingerprint))
            else: db.execute(f'INSERT INTO {kind}(id,content,created) VALUES (?,?,?)',(iid,self.seal(content),time.time()))
        return iid
    def update_item(self,kind,iid,content=None,done=None):
        assert kind in {'memories','notes','tasks'}
        with self.db() as db:
            if content is not None:
                if kind=='memories':
                    old=db.execute('SELECT content FROM memories WHERE id=?',(iid,)).fetchone()
                    if old: db.execute('INSERT OR IGNORE INTO forgotten VALUES (?)',(self.fingerprint(self.open(old[0])),))
                    db.execute("UPDATE memories SET fingerprint=?,source='manual' WHERE id=?",(self.fingerprint(content),iid))
                db.execute(f'UPDATE {kind} SET content=? WHERE id=?',(self.seal(content),iid))
            if done is not None and kind=='tasks': db.execute('UPDATE tasks SET done=? WHERE id=?',(int(done),iid))
    def delete_item(self,kind,iid):
        assert kind in {'memories','notes','tasks'}
        with self.db() as db:
            if kind=='memories':
                row=db.execute('SELECT content FROM memories WHERE id=?',(iid,)).fetchone()
                if row: db.execute('INSERT OR IGNORE INTO forgotten VALUES (?)',(self.fingerprint(self.open(row[0])),))
            db.execute(f'DELETE FROM {kind} WHERE id=?',(iid,))
    def acquire(self):
        token=str(uuid.uuid4())
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT expires FROM lease WHERE id=1').fetchone()
            if row and row[0]>time.time(): raise RuntimeError('NILA-003: Another request is running. Stop it or wait for completion.')
            db.execute('INSERT OR REPLACE INTO lease VALUES (1,?,?)',(token,time.time()+720))
        return token
    def release(self,token):
        with self.db() as db: db.execute('DELETE FROM lease WHERE token=?',(token,))

    def revise_prompt(self,cid,mid,content):
        """Caller holds generation lease. Replace this turn and discard its dependent branch."""
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute("SELECT id FROM messages WHERE id=? AND chat_id=? AND role='user'",(mid,cid)).fetchone()
            if not row: raise KeyError('Prompt not found')
            db.execute('DELETE FROM messages WHERE chat_id=? AND id>?',(cid,mid))
            db.execute("UPDATE messages SET content=?,status='complete' WHERE id=?",(self.seal(content),mid))
            first=db.execute("SELECT id FROM messages WHERE chat_id=? AND role='user' ORDER BY id LIMIT 1",(cid,)).fetchone()
            if first and first[0]==mid: db.execute('UPDATE chats SET title=? WHERE id=?',(self.seal(content[:65]),cid))
            db.execute('UPDATE chats SET updated=? WHERE id=?',(time.time(),cid))

    def feedback(self,cid,mid,rating,reason=''):
        if rating not in {-1,0,1}: raise ValueError('Invalid rating')
        if len(reason)>500: raise ValueError('Feedback must be at most 500 characters')
        with self.db() as db:
            if not db.execute("SELECT id FROM messages WHERE id=? AND chat_id=? AND role='assistant'",(mid,cid)).fetchone(): raise KeyError('Answer not found')
            if rating==0: db.execute('DELETE FROM feedback WHERE message_id=?',(mid,))
            else: db.execute('INSERT OR REPLACE INTO feedback VALUES (?,?,?)',(mid,rating,self.seal(reason.strip())))

    def feedback_context(self,query):
        # Local retrieval only: relevant rated examples and explicit recent guidance.
        import re
        words=set(re.findall(r'\w{4,}',query.lower()))
        selected=[]
        with self.db() as db:
            rows=db.execute("SELECT f.*,m.content,(SELECT content FROM messages u WHERE u.chat_id=m.chat_id AND u.role='user' AND u.id<m.id ORDER BY u.id DESC LIMIT 1) AS prompt FROM feedback f JOIN messages m ON m.id=f.message_id ORDER BY m.id DESC LIMIT 30").fetchall()
        for row in rows:
            reason=self.open(row['reason']);prompt=self.open(row['prompt']) if row['prompt'] else ''
            if reason or words.intersection(re.findall(r'\w{4,}',prompt.lower())):
                selected.append({'rating':'helpful' if row['rating']==1 else 'unhelpful','guidance':reason,'question':prompt[:180],'answer':self.open(row['content'])[:400]})
            if len(selected)==3: break
        return json.dumps(selected,ensure_ascii=False) if selected else ''
