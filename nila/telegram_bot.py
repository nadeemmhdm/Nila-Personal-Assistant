"""Opt-in Telegram private-chat bridge. Fixed API origin, encrypted token, one allowed user."""
import asyncio,json,re,time,uuid
import httpx
from .engine import reply,NilaError

class TelegramError(RuntimeError):pass

def ensure(store):
    from .learning import ensure as learning_tables
    learning_tables(store)
    with store.db() as db:db.execute('CREATE TABLE IF NOT EXISTS telegram_state(id INTEGER PRIMARY KEY,offset INTEGER NOT NULL DEFAULT 0,chat_id TEXT,owner TEXT,expires REAL NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT \'disabled\')')

def config(store):
    ensure(store)
    with store.db() as db:r=db.execute("SELECT value FROM secrets WHERE name='telegram'").fetchone()
    return json.loads(store.open(r[0])) if r else None

def status(store):
    c=config(store)
    with store.db() as db:r=db.execute('SELECT * FROM telegram_state WHERE id=1').fetchone()
    return {'configured':bool(c),'enabled':bool(c and c['enabled']),'chat_id':c['chat_id'] if c else '', 'share_memory':bool(c and c.get('share_memory')),'status':r['status'] if r else 'disabled','running':bool(r and r['expires']>time.time())}

def save(store,token,chat_id,enabled=False,share_memory=False):
    if not re.fullmatch(r'[0-9]{5,20}:[A-Za-z0-9_-]{20,200}',token.strip()):raise ValueError('Enter a valid bot token from BotFather')
    if not re.fullmatch(r'[1-9][0-9]{0,18}',str(chat_id)):raise ValueError('Use your positive numeric private Telegram chat ID (groups are not supported)')
    previous=config(store)
    value={'token':token.strip(),'chat_id':str(chat_id),'enabled':enabled,'share_memory':share_memory}
    with store.db() as db:
        db.execute("INSERT OR REPLACE INTO secrets VALUES ('telegram',?)",(store.seal(json.dumps(value)),))
        if not previous or previous['token']!=value['token'] or previous['chat_id']!=value['chat_id'] or previous.get('share_memory')!=share_memory:
            db.execute("INSERT INTO telegram_state VALUES (1,0,NULL,NULL,0,'configured') ON CONFLICT(id) DO UPDATE SET offset=0,chat_id=NULL,status='configured'")
    return status(store)

def disable(store,remove=False):
    c=config(store)
    with store.db() as db:
        if remove:db.execute("DELETE FROM secrets WHERE name='telegram'")
        elif c:
            c['enabled']=False;db.execute("UPDATE secrets SET value=? WHERE name='telegram'",(store.seal(json.dumps(c)),))
        db.execute("UPDATE telegram_state SET status='disabled' WHERE id=1")
    return status(store)

async def call(token,method,payload):
    if method not in {'getMe','getUpdates','sendMessage','sendChatAction'}:raise TelegramError('Unsupported Telegram operation')
    try:
        async with httpx.AsyncClient(timeout=30,follow_redirects=False) as c:
            r=await c.post('https://api.telegram.org/bot'+token+'/'+method,json=payload)
        if r.status_code==409:raise TelegramError('Telegram polling conflict. Stop another bot process or remove its webhook before connecting Nila.')
        if r.status_code in {401,403}:raise TelegramError('Telegram rejected the token or chat access. Check the connection details.')
        if r.status_code==429:raise TelegramError('Telegram rate limit reached. Waiting before retry.')
        r.raise_for_status();data=r.json()
        if not data.get('ok'):raise TelegramError('Telegram request failed. Check token, chat ID and bot permissions.')
        return data.get('result')
    except (httpx.HTTPError,ValueError):raise TelegramError('Telegram connection unavailable. Check internet and retry.') from None

async def test(store):
    c=config(store)
    if not c:raise ValueError('Save the bot token first')
    me=await call(c['token'],'getMe',{})
    return {'connected':True,'username':me.get('username',''),'message':'Token accepted. Start the bot in Telegram, then enable the connection. Only your configured private chat can use it.'}

class Bridge:
    def __init__(self,store):self.store=store;self.owner=str(uuid.uuid4());self.active=None
    def state(self,text):
        with self.store.db() as db:db.execute('UPDATE telegram_state SET status=? WHERE id=1 AND owner=?',(text,self.owner))
    async def send(self,c,text):
        # Disabling or replacing credentials prevents subsequent sends.
        if config(self.store)!=c or not c['enabled']:return
        from .terminal import plain_text
        text=plain_text(text)
        for i in range(0,len(text),1800):
            if config(self.store)!=c:return
            await call(c['token'],'sendMessage',{'chat_id':c['chat_id'],'text':text[i:i+1800],'link_preview_options':{'is_disabled':True}})
    async def handle(self,c,update):
        msg=update.get('message',{});chat=msg.get('chat',{});sender=msg.get('from',{})
        if chat.get('type')!='private' or str(chat.get('id'))!=c['chat_id'] or str(sender.get('id'))!=c['chat_id'] or sender.get('is_bot'):return
        if time.time()-msg.get('date',0)>300:return # Do not replay stale requests after laptop sleep.
        text=msg.get('text','').strip()
        if not text or len(text)>12000:return
        if text in {'/start','/help'}:
            await self.send(c,'I’m Nila. Send a message to chat. /new starts a fresh conversation. Keep Nila running on your laptop.');return
        with self.store.db() as db:r=db.execute('SELECT chat_id FROM telegram_state WHERE id=1').fetchone()
        cid=r[0] if r else None
        try:
            if cid:self.store.chat(cid)
        except KeyError:cid=None
        if not cid or text=='/new':
            cid=self.store.create_chat()['id']
            with self.store.db() as db:db.execute('UPDATE telegram_state SET chat_id=? WHERE id=1',(cid,))
        if text=='/new':await self.send(c,'New conversation ready.');return
        self.state('Thinking')
        await call(c['token'],'sendChatAction',{'chat_id':c['chat_id'],'action':'typing'})
        answer=''
        try:
            async for part in reply(self.store,cid,text,learn_memory=False,personal_context=c.get('share_memory',False)):answer+=part
        except (NilaError,RuntimeError):answer='Nila could not answer right now. Check Ollama on your laptop or wait for the current local request to finish.'
        await self.send(c,answer or 'No answer was generated. Try again.')
    async def loop(self):
        ensure(self.store)
        while True:
            c=config(self.store)
            if not c or not c['enabled']:await asyncio.sleep(2);continue
            with self.store.db() as db:
                db.execute('BEGIN IMMEDIATE');r=db.execute('SELECT * FROM telegram_state WHERE id=1').fetchone()
                if r and r['expires']>time.time() and r['owner']!=self.owner:claim=False
                else:
                    db.execute("INSERT INTO telegram_state(id,owner,expires,status) VALUES (1,?,?,'connecting') ON CONFLICT(id) DO UPDATE SET owner=excluded.owner,expires=excluded.expires,status='connecting'",(self.owner,time.time()+45));claim=True
            if not claim:await asyncio.sleep(3);continue
            current=asyncio.current_task()
            async def guard():
                while True:
                    if config(self.store)!=c:
                        if self.active:self.active.cancel()
                        return
                    with self.store.db() as db:db.execute('UPDATE telegram_state SET expires=? WHERE id=1 AND owner=?',(time.time()+45,self.owner))
                    await asyncio.sleep(2)
            watcher=asyncio.create_task(guard())
            try:
                while config(self.store)==c:
                    with self.store.db() as db:offset=db.execute('SELECT offset FROM telegram_state WHERE id=1').fetchone()[0]
                    self.state('Connected')
                    updates=await call(c['token'],'getUpdates',{'offset':offset,'timeout':20,'limit':10,'allowed_updates':['message']})
                    for update in updates:
                        if config(self.store)!=c:break
                        # Record before generation to avoid duplicate replies after restart.
                        with self.store.db() as db:db.execute('UPDATE telegram_state SET offset=? WHERE id=1',(int(update['update_id'])+1,))
                        self.active=asyncio.create_task(self.handle(c,update))
                        try:await self.active
                        except asyncio.CancelledError:
                            if current.cancelling():raise
                        finally:self.active=None
            except TelegramError as exc:self.state(str(exc));await asyncio.sleep(5)
            except (ValueError,KeyError,TypeError,OSError):
                self.state('Connection interrupted. Check Telegram settings and local Ollama.');await asyncio.sleep(5)
            finally:
                watcher.cancel()
                await asyncio.gather(watcher,return_exceptions=True)
                with self.store.db() as db:db.execute('UPDATE telegram_state SET owner=NULL,expires=0 WHERE id=1 AND owner=?',(self.owner,))
