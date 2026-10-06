import asyncio,base64,json,time
import httpx
from fastapi.testclient import TestClient
from nila.storage import Store
from nila.server import create_app
from nila import engine,skills,telegram_bot as tg
from nila.websearch import needs_search
from nila.knowledge_cache import remember_web,recall_web
from test_app import mock_ollama

def test_stable_questions_skip_search_and_developer_uses_identity(tmp_path,monkeypatch):
    seen=mock_ollama(monkeypatch);s=Store(tmp_path);s.save_settings({'auto_memory':False})
    from nila import websearch
    async def search(q,mode):assert mode=='off';return []
    monkeypatch.setattr(websearch,'search',search)
    async def run(prompt):return ''.join([p async for p in engine.reply(s,s.create_chat()['id'],prompt,search_mode='deep')])
    assert asyncio.run(run('Explain Python dictionaries'))
    asyncio.run(run('developer details'))
    assert 'github.com/nadeemmhdm' in str(seen[-1]['messages'])
    assert needs_search('What is the latest weather today?')
    assert not needs_search('What is a Python dictionary?')

def test_skills_encrypted_multiple_and_not_shared_without_personal_context(tmp_path,monkeypatch):
    seen=mock_ollama(monkeypatch);s=Store(tmp_path);s.save_settings({'auto_memory':False})
    assert len(skills.listing(s))==10
    iid=skills.save(s,'custom.md','SECRET_STYLE use a concise checklist')
    skills.enable(s,iid,True);assert 'SECRET_STYLE' in skills.active_context(s)
    cid=s.create_chat()['id']
    async def run():return ''.join([p async for p in engine.reply(s,cid,'Explain Python',personal_context=False)])
    asyncio.run(run());assert 'SECRET_STYLE' not in json.dumps(seen)
    with s.db() as db:assert 'SECRET_STYLE' not in db.execute('SELECT content FROM custom_skills WHERE id=?',(iid,)).fetchone()[0]
    skills.enable(s,skills.listing(s)[0]['id'],True)
    assert sum(x['enabled'] for x in skills.listing(s))==2

def test_attachments_reload_detach_and_actual_model_context(tmp_path,monkeypatch):
    seen=mock_ollama(monkeypatch);s=Store(tmp_path);s.save_settings({'auto_memory':False});c=TestClient(create_app(s));cid=s.create_chat()['id']
    r=c.post(f'/api/chats/{cid}/attachments',json={'name':'note.txt','data':base64.b64encode(b'UNIQUE_FILE_FACT: a dictionary maps keys to values').decode()});assert r.status_code==200
    iid=r.json()['id'];assert c.get(f'/api/chats/{cid}/attachments').json()[0]['id']==iid
    r=c.post(f'/api/chats/{cid}/reply',json={'content':'Summarize attached files'})
    assert 'UNIQUE_FILE_FACT' in json.dumps(seen)
    assert c.delete(f'/api/chats/{cid}/attachments/{iid}').status_code==200
    assert c.get(f'/api/chats/{cid}/attachments').json()==[]

def test_cache_offline_relevance_encryption_and_delete(tmp_path):
    s=Store(tmp_path);refs=[{'title':'Python docs','url':'https://docs.python.org/3/','snippet':'Dictionary reference'}]
    remember_web(s,'Python dictionary',refs,'UNIQUE_CACHE_FACT')
    text,sources=recall_web(s,'Explain Python dictionary');assert 'UNIQUE_CACHE_FACT' in text and sources[0]['url']==refs[0]['url']
    assert recall_web(s,'banana bread')==('',[])
    with s.db() as db:assert 'UNIQUE_CACHE_FACT' not in db.execute('SELECT payload FROM web_knowledge').fetchone()[0]
    c=TestClient(create_app(s));items=c.get('/api/knowledge-cache').json();assert c.delete('/api/knowledge-cache/'+items[0]['id']).status_code==200
    assert recall_web(s,'Python dictionary')==('',[])

def test_model_load_only_selects_after_success(tmp_path,monkeypatch):
    s=Store(tmp_path);c=TestClient(create_app(s));from nila import extensions
    async def models():return [{'name':'new:1b'}]
    monkeypatch.setattr(engine,'models',models);original=httpx.AsyncClient;seen=[]
    def handler(r):seen.append(json.loads(r.content));return httpx.Response(200,json={'done':True})
    monkeypatch.setattr(extensions.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    assert c.post('/api/models/load',json={'model':'new:1b'}).status_code==200
    assert s.settings()['model']=='new:1b' and seen[0]['prompt']==''
    assert c.post('/api/models/load',json={'model':'missing'}).status_code==400
    assert s.settings()['model']=='new:1b'

def test_telegram_modes_only_authorized_user(tmp_path,monkeypatch):
    s=Store(tmp_path);tg.save(s,'123456:abcdefghijklmnopqrstuvwxyzABCDEF','123',True);sent=[]
    async def call(token,method,payload):sent.append(payload);return {}
    monkeypatch.setattr(tg,'call',call);b=tg.Bridge(s)
    def event(text,user=123):return {'message':{'chat':{'type':'private','id':user},'from':{'id':user},'date':time.time(),'text':text}}
    asyncio.run(b.handle(tg.config(s),event('/search deep',456)));assert not sent
    asyncio.run(b.handle(tg.config(s),event('/search deep')));assert tg.config(s)['search_mode']=='deep'
    asyncio.run(b.handle(tg.config(s),event('/think high')));assert tg.config(s)['thinking_level']=='high'
