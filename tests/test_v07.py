import asyncio,json,time
import httpx,pytest
from fastapi.testclient import TestClient
from nila.storage import Store
from nila import engine,model_manager as mm,telegram_bot as tg
from nila.server import create_app
from nila.conversation import developer_question
from nila.knowledge_cache import backfill,recall_web
from test_app import mock_ollama

@pytest.mark.parametrize('mode',['fast','medium','current'])
def test_shared_profiles_persist_generate_and_select_through_api(tmp_path,monkeypatch,mode):
    seen=mock_ollama(monkeypatch)
    async def available():return [{'name':v} for v in mm.DEFAULT_PROFILES.values()]
    monkeypatch.setattr(engine,'models',available)
    store=Store(tmp_path);store.save_settings({'auto_memory':False});client=TestClient(create_app(store))
    assert client.post('/api/models/select',json={'value':mode}).status_code==200
    assert Store(tmp_path).settings()['model']==mm.DEFAULT_PROFILES[mode]
    cid=store.create_chat()['id'];client.post(f'/api/chats/{cid}/reply',json={'content':'Explain dictionaries'})
    assert seen[0]['model']==mm.DEFAULT_PROFILES[mode]
    assert client.get('/api/models/profiles').json()['mode']==mode

def test_legacy_custom_model_preserved_and_missing_selection_not_applied(tmp_path,monkeypatch):
    store=Store(tmp_path);store.save_settings({'model':'llama3.2:1b'})
    assert Store(tmp_path).settings()['model']=='llama3.2:1b'
    assert mm.selection(store)['mode']=='custom'
    async def empty():return []
    monkeypatch.setattr(engine,'models',empty)
    with pytest.raises(engine.NilaError,match='ollama pull qwen3:0.6b'):asyncio.run(mm.select(store,'fast'))
    assert store.settings()['model']=='llama3.2:1b'
    store.save_settings({'model_profiles':mm.DEFAULT_PROFILES|{'fast':'custom:1b'}})
    assert store.settings()['model_profiles']['fast']=='custom:1b'

@pytest.mark.parametrize('question',['Who developed Grok?','Grok AI founder','web search grok ai founder','Who created Grok, do you know?','Who is the creator of Python?'])
def test_external_developer_is_not_nila(question):assert not developer_question(question)

def test_public_search_excludes_profile_and_old_identity_and_caches(tmp_path,monkeypatch):
    seen=mock_ollama(monkeypatch);store=Store(tmp_path);store.save_settings({'user_name':'PRIVATE_OWNER','auto_memory':False})
    store.add_item('memories','PRIVATE_FACT');cid=store.create_chat()['id'];store.add_message(cid,'user','Who developed you?');store.add_message(cid,'assistant','Nadeem created Nila.')
    from nila import websearch
    monkeypatch.setattr(websearch,'lookup',lambda *a:[{'href':'https://example.org/grok','title':'Grok owner','body':'Public Grok information'}])
    c=TestClient(create_app(store));c.post(f'/api/chats/{cid}/reply',json={'content':'Grok AI founder','search_mode':'quick'})
    body=json.dumps(seen);assert 'PRIVATE_OWNER' not in body and 'PRIVATE_FACT' not in body and 'Nadeem' not in body
    overview=c.get('/api/memory-overview').json();assert overview['web']==1 and overview['personal']==1
    assert 'Previously saved' in recall_web(store,'Grok AI founder')[0]

def test_recover_old_web_evidence_once_and_forget(tmp_path):
    store=Store(tmp_path);cid=store.create_chat()['id'];store.add_message(cid,'user','Grok founder');mid=store.add_message(cid,'assistant','Older researched answer')
    with store.db() as db:db.execute('INSERT INTO answer_sources VALUES (?,?)',(mid,store.seal(json.dumps([{'kind':'web','label':'Grok reference','url':'https://example.org/grok'}]))))
    backfill(store);assert recall_web(store,'Grok founder')[0]
    with store.db() as db:db.execute('DELETE FROM web_knowledge')
    backfill(store);assert recall_web(store,'Grok founder')==('',[])

def test_telegram_one_indicator_replaced_and_shared_model(tmp_path,monkeypatch):
    store=Store(tmp_path);tg.save(store,'123456:abcdefghijklmnopqrstuvwxyzABCDEF','123',True);calls=[]
    async def call(token,method,payload):calls.append((method,payload));return {'message_id':88}
    async def available():return [{'name':v} for v in mm.DEFAULT_PROFILES.values()]
    async def reply(s,cid,text,**kw):
        s.add_message(cid,'user',text)
        await asyncio.sleep(.01);yield 'Answer';await asyncio.sleep(.01);yield ' text'
        s.add_message(cid,'assistant','Answer text')
    monkeypatch.setattr(tg,'call',call);monkeypatch.setattr(tg,'reply',reply);monkeypatch.setattr(engine,'models',available)
    def event(text):return {'message':{'chat':{'type':'private','id':123},'from':{'id':123},'date':time.time(),'text':text}}
    b=tg.Bridge(store);asyncio.run(b.handle(tg.config(store),event('/model fast')))
    assert store.settings()['model']==mm.DEFAULT_PROFILES['fast'];calls.clear()
    asyncio.run(b.handle(tg.config(store),event('Explain SQL')))
    assert len([x for x in calls if x[0]=='sendMessage'])==1
    assert calls[-1][0]=='editMessageText' and calls[-1][1]['text']=='Answer text'
    assert calls[-1][1]['message_id']==88
