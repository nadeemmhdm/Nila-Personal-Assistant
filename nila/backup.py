"""Portable, password-encrypted logical snapshots. No vault keys or API credentials."""
import base64,json,os,time,sqlite3
from cryptography.fernet import Fernet,InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

FIELDS={'settings':['value'],'projects':['name','instructions'],'chats':['title'],'messages':['content'],'memories':['content'],'notes':['content'],'tasks':['content'],'feedback':['reason'],'forgotten':[],'automations':['title','prompt'],'runs':['output'],'chat_meta':[],'documents':['name','pages'],'chat_documents':[],'memory_inbox':['content'],'answer_sources':['content'],'job_policy':[],'learning_sessions':['config','error'],'learning_messages':['content'],'knowledge':['topic','content']}
MAGIC=b'NILABACKUP1\0'
MAX=20*1024*1024

def cipher(password,salt):
    if not 12<=len(password)<=256:raise ValueError('Use a backup password of 12–256 characters')
    key=Scrypt(salt=salt,length=32,n=2**15,r=8,p=1).derive(password.encode())
    return Fernet(base64.urlsafe_b64encode(key))

def export_backup(store,password):
    from .learning import ensure
    ensure(store);tables={}
    with store.db() as db:
        db.execute('BEGIN')
        for name,fields in FIELDS.items():tables[name]=[store.decode(row,fields) for row in db.execute('SELECT * FROM '+name)]
    payload=json.dumps({'format':1,'created':time.time(),'tables':tables},ensure_ascii=False).encode()
    if len(payload)>14*1024*1024:raise ValueError('Backup exceeds 14 MB data limit; remove unused documents or chats')
    salt=os.urandom(16)
    return MAGIC+salt+cipher(password,salt).encrypt(payload)

def read_backup(store,raw,password):
    if len(raw)>MAX or not raw.startswith(MAGIC):raise ValueError('Unsupported or oversized backup')
    salt=raw[len(MAGIC):len(MAGIC)+16]
    try:data=json.loads(cipher(password,salt).decrypt(raw[len(MAGIC)+16:]))
    except (InvalidToken,ValueError,UnicodeError):raise ValueError('Incorrect password or damaged backup') from None
    if data.get('format')!=1 or set(data.get('tables',{}))!=set(FIELDS):raise ValueError('Backup format is incompatible with this version')
    from .learning import ensure
    ensure(store)
    total=0
    with store.db() as db:
        for name,rows in data['tables'].items():
            columns={r[1] for r in db.execute('PRAGMA table_info('+name+')')}
            if not isinstance(rows,list):raise ValueError('Invalid backup rows')
            total+=len(rows)
            if total>100000:raise ValueError('Too many backup records')
            for row in rows:
                if not isinstance(row,dict) or set(row)!=columns:raise ValueError('Backup schema mismatch')
                if any(not isinstance(row[k],str) for k in FIELDS[name]):raise ValueError('Invalid encrypted field')
                if any(not isinstance(v,(str,int,float,type(None))) for v in row.values()):raise ValueError('Invalid field type')
    from .server import Settings
    values={r['key']:json.loads(r['value']) for r in data['tables']['settings']}
    Settings(**values)
    return data

def restore_backup(store,raw,password,apply=False):
    data=read_backup(store,raw,password)
    counts={name:len(rows) for name,rows in data['tables'].items()}
    if not apply:return {'counts':counts,'created':data.get('created'),'notice':'Restore replaces saved workspace data. Back up current data first. API keys are excluded; legacy automations are paused. Telegram is disabled after restore.'}
    token=store.acquire()
    try:
        with store.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM automations WHERE running_until>?',(time.time(),)).fetchone() or db.execute("SELECT 1 FROM learning_sessions WHERE status='running'").fetchone():raise ValueError('Stop active automations and Learning Lab before restoring')
            tg=db.execute("SELECT value FROM secrets WHERE name='telegram'").fetchone()
            if tg:
                config=json.loads(store.open(tg[0]));config['enabled']=False
                db.execute("UPDATE secrets SET value=? WHERE name='telegram'",(store.seal(json.dumps(config)),))
            for name in reversed(FIELDS):db.execute('DELETE FROM '+name)
            for name,fields in FIELDS.items():
                for original in data['tables'][name]:
                    row=dict(original)
                    if name=='automations':row.update(enabled=0,running_until=0,claim=None)
                    if name=='runs' and row['status']=='running':row['status']='interrupted'
                    if name=='learning_sessions':row.update(stop=1,status='interrupted' if row['status']=='running' else row['status'])
                    if name=='settings' and row['key']=='auto_update':row['value']='false'
                    for field in fields:row[field]=store.seal(row[field])
                    db.execute('INSERT INTO '+name+'('+','.join(row)+') VALUES ('+','.join('?' for _ in row)+')',list(row.values()))
    except sqlite3.Error:raise ValueError('Backup relationships are invalid; existing workspace retained') from None
    finally:store.release(token)
    return {'restored':True,'counts':counts,'notice':'Workspace restored. Automations paused; restart Nila before resuming work.'}
