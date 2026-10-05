import asyncio,json,time
import httpx
from fastapi.testclient import TestClient
from nila.storage import Store
from nila import telegram_bot as tg,conversation
from nila.server import create_app
from nila.terminal import plain_text
from test_app import mock_ollama

TOKEN='123456:abcdefghijklmnopqrstuvwxyzABCDEF'

def test_telegram_private_authorization_encryption_and_disable(tmp_path,monkeypatch):
    s=Store(tmp_path);s.save_settings({'auto_update':False})
    result=tg.save(s,TOKEN,'123',True)
    assert TOKEN not in json.dumps(result)
    with s.db() as db:assert TOKEN not in db.execute("SELECT value FROM secrets WHERE name='telegram'").fetchone()[0]
    sent=[];prompts=[]
    async def call(token,method,payload):sent.append((method,payload));return {}
    async def reply(store,cid,text,**kw):prompts.append((text,kw));yield '**Hello**'
    monkeypatch.setattr(tg,'call',call);monkeypatch.setattr(tg,'reply',reply)
    b=tg.Bridge(s);c=tg.config(s)
    def update(uid=123,kind='private'):
        return {'message':{'chat':{'type':kind,'id':uid},'from':{'id':uid},'date':time.time(),'text':'Hi'}}
    async def run():
        await b.handle(c,update(456));await b.handle(c,update(kind='group'))
        assert not sent and not prompts
        await b.handle(c,update())
        assert prompts[0][0]=='Hi'
        assert prompts[0][1]['personal_context'] is False
        assert prompts[0][1]['search_mode']=='off'
        assert all(p['chat_id']=='123' for m,p in sent)
        assert sent[-1][1]['text']=='Hello'
        tg.disable(s);before=len(sent);await b.send(c,'must not send');assert len(sent)==before
    asyncio.run(run())

def test_telegram_credentials_not_backed_up_and_restore_disables(tmp_path):
    from nila.backup import export_backup,restore_backup
    s=Store(tmp_path);tg.save(s,TOKEN,'123',True)
    raw=export_backup(s,'correct horse battery staple')
    restore_backup(s,raw,'correct horse battery staple',True)
    assert not tg.status(s)['enabled']
    assert tg.config(s)['token']==TOKEN

def test_thinking_capability_mapping(monkeypatch):
    original=httpx.AsyncClient
    def handler(request):
        name=json.loads(request.content)['model']
        return httpx.Response(200,json={'capabilities':[] if name=='llama3.2:1b' else ['thinking']})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    async def run():
        assert await conversation.thinking_options('llama3.2:1b','high')=={}
        assert await conversation.thinking_options('gpt-oss:20b','medium')=={'think':'medium'}
        assert await conversation.thinking_options('qwen3:4b','low')=={'think':False}
        assert await conversation.thinking_options('qwen3:4b','high')=={'think':True}
    asyncio.run(run())
    assert [conversation.effort(x)[1] for x in ['low','medium','high']]==[512,1024,2048]

def test_terminal_markdown_is_rendered():
    rendered=plain_text('## Hello\n\n**Bold** and *italic* and ++underline++')
    assert 'Hello' in rendered and 'Bold' in rendered and 'italic' in rendered
    assert '#' not in rendered and '*' not in rendered and '++' not in rendered

def test_followups_are_contextual_local_and_release_lease(tmp_path,monkeypatch):
    s=Store(tmp_path);cid=s.create_chat()['id'];s.add_message(cid,'user','What are Python dictionaries?');s.add_message(cid,'assistant','Mappings of keys to values')
    seen=[];original=httpx.AsyncClient
    def handler(request):
        seen.append(request)
        return httpx.Response(200,json={'message':{'content':json.dumps({'questions':['How do I add a dictionary key?']})}})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    assert asyncio.run(conversation.followups(s,cid))==['How do I add a dictionary key?']
    assert seen[0].url.host=='127.0.0.1' and b'Python dictionaries' in seen[0].content
    token=s.acquire();s.release(token)

def test_temporary_attachment_and_current_model(tmp_path,monkeypatch):
    import base64
    s=Store(tmp_path);s.save_settings({'auto_update':False,'auto_memory':False})
    seen=mock_ollama(monkeypatch);c=TestClient(create_app(s));cid=c.post('/api/chats',json={'temporary':True}).json()['id']
    r=c.post(f'/api/chats/{cid}/attachments',json={'name':'test.txt','data':base64.b64encode(b'ATTACHMENT_REFERENCE blue moon').decode()})
    assert r.status_code==200,r.text
    c.post(f'/api/chats/{cid}/reply',json={'content':'What is the blue moon reference?','thinking_level':'high'})
    assert 'ATTACHMENT_REFERENCE' in json.dumps(seen)
    assert seen[0]['options']['num_predict']==2048
    with s.db() as db:assert db.execute('SELECT COUNT(*) FROM documents').fetchone()[0]==0

def test_new_message_cancels_suggestion_generation(tmp_path,monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    s=Store(tmp_path);s.save_settings({'auto_update':False,'auto_memory':False})
    mock_ollama(monkeypatch);cid=s.create_chat()['id'];started=threading.Event()
    async def pending(store,cid):
        token=store.acquire();started.set()
        try:await asyncio.sleep(30)
        finally:store.release(token)
    monkeypatch.setattr(conversation,'followups',pending)
    with TestClient(create_app(s)) as client,ThreadPoolExecutor() as pool:
        future=pool.submit(client.post,f'/api/chats/{cid}/followups')
        assert started.wait(2)
        result=client.post(f'/api/chats/{cid}/reply',json={'content':'A new question'})
        assert 'Hello' in result.text and future.result(timeout=2).json()==[]
