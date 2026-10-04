import asyncio
import json
import subprocess
import sys
import httpx
import pytest
from fastapi.testclient import TestClient
from nila.storage import Store
from nila.server import create_app
from nila import engine

@pytest.fixture
def store(tmp_path): return Store(tmp_path)

@pytest.fixture
def client(store): return TestClient(create_app(store))

def test_persistence_and_cascade(store):
    cid=store.create_chat()['id']
    store.add_message(cid,'user','Hello')
    store.add_message(cid,'assistant','Hi')
    assert Store(store.root).chat(cid)['title']=='Hello'
    store.delete_chat(cid)
    with store.db() as db: assert db.execute('SELECT COUNT(*) FROM messages').fetchone()[0]==0

def test_settings_validation_and_memory_crud(client):
    s=client.get('/api/settings').json()
    s['user_name']='Nadeem'
    assert client.put('/api/settings',json=s).status_code==200
    assert client.get('/api/settings').json()['user_name']=='Nadeem'
    assert client.put('/api/settings',json=s|{'num_ctx':999999}).status_code==422
    assert client.put('/api/settings',json=s|{'model':'bad; command'}).status_code==422
    assert client.post('/api/items/memories',json={'content':'  '}).status_code==422
    iid=client.post('/api/items/memories',json={'content':'I like short answers'}).json()['id']
    client.put('/api/items/memories/'+iid,json={'content':'I prefer examples'})
    assert client.get('/api/items/memories').json()[0]['content']=='I prefer examples'
    client.delete('/api/items/memories/'+iid)
    assert client.get('/api/items/memories').json()==[]

def test_request_protection(client):
    assert client.post('/api/chats',headers={'Origin':'https://evil.example'}).status_code==403
    assert client.get('/api/settings',headers={'Host':'evil.example'}).status_code==403
    assert client.get('/api/settings',headers={'Sec-Fetch-Site':'cross-site'}).status_code==403
    assert client.post('/api/chats',headers={'Origin':'http://testserver'}).status_code==200
    assert client.get('/api/items/settings').status_code==422

def test_shared_generation_lease(store,client):
    cid=store.create_chat()['id']
    token=store.acquire()
    with pytest.raises(RuntimeError): Store(store.root).acquire()
    assert client.delete('/api/chats/'+cid).status_code==409
    store.release(token)
    assert client.delete('/api/chats/'+cid).status_code==200

def test_context_and_memory_switch(store):
    cid=store.create_chat()['id']
    store.add_item('memories','Prefers Malayalam')
    store.add_message(cid,'user','Who are you?')
    messages=engine.context(store,cid,store.settings())
    assert 'You are Nila' in messages[0]['content']
    assert 'Prefers Malayalam' in messages[0]['content']
    assert 'Prefers Malayalam' not in engine.context(store,cid,store.settings()|{'memory_enabled':False})[0]['content']

def mock_ollama(monkeypatch, missing=False, broken=False):
    original=httpx.AsyncClient
    seen=[]
    def handler(request):
        if request.url.path=='/api/tags': return httpx.Response(200,json={'models':[] if missing else [{'name':'llama3.2:1b'}]})
        seen.append(json.loads(request.content))
        lines=[{'message':{'content':'Hello '},'done':False},{'message':{'content':'Nadeem.'},'done':False}]
        if not broken: lines.append({'done':True})
        return httpx.Response(200,text='\n'.join(json.dumps(x) for x in lines)+'\n')
    monkeypatch.setattr(engine.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    return seen

def test_streaming_saves_history(store,client,monkeypatch):
    seen=mock_ollama(monkeypatch)
    cid=store.create_chat()['id']
    r=client.post('/api/chats/'+cid+'/reply',json={'content':'Hi'})
    events=[json.loads(x) for x in r.text.splitlines()]
    assert ''.join(x.get('token','') for x in events)=='Hello Nadeem.'
    assert events[-1]=={'done':True}
    assert store.chat(cid)['messages'][-1]['status']=='complete'
    assert seen[0]['model']=='llama3.2:1b'
    assert seen[0]['messages'][-1]['content']=='Hi'
    assert seen[0]['options']['num_ctx']==2048

def test_missing_model_does_not_add_message(store,client,monkeypatch):
    mock_ollama(monkeypatch,missing=True)
    cid=store.create_chat()['id']
    result=client.post('/api/chats/'+cid+'/reply',json={'content':'Hi'}).text
    assert 'NILA-002' in result
    assert store.chat(cid)['messages']==[]
    token=store.acquire();store.release(token)

def test_broken_stream_persists_partial_response(store,client,monkeypatch):
    mock_ollama(monkeypatch,broken=True)
    cid=store.create_chat()['id']
    assert 'NILA-004' in client.post('/api/chats/'+cid+'/reply',json={'content':'Hello'}).text
    message=store.chat(cid)['messages'][-1]
    assert message['status']=='interrupted'
    assert message['content']=='Hello Nadeem.'

def test_cancellation_releases_lease(store,monkeypatch):
    async def fake_models(): return [{'name':'llama3.2:1b'}]
    monkeypatch.setattr(engine,'models',fake_models)
    class Response:
        status_code=200
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def aiter_lines(self):
            yield json.dumps({'message':{'content':'Partial'}})
            await asyncio.sleep(10)
    class Client:
        def __init__(self,**kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        def stream(self,*args,**kwargs): return Response()
    monkeypatch.setattr(engine.httpx,'AsyncClient',Client)
    cid=store.create_chat()['id']
    async def run():
        received=asyncio.Event()
        async def consume():
            async for _ in engine.reply(store,cid,'Hi'): received.set()
        task=asyncio.create_task(consume())
        await received.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError): await task
    asyncio.run(run())
    assert store.chat(cid)['messages'][-1]['status']=='interrupted'
    token=store.acquire();store.release(token)

def test_remote_ollama_rejected(monkeypatch):
    monkeypatch.setenv('NILA_OLLAMA_URL','https://example.com')
    with pytest.raises(engine.NilaError): engine.ollama_url()

def test_cli_shared_storage(store,monkeypatch):
    monkeypatch.setenv('NILA_DATA_DIR',str(store.root))
    result=subprocess.run([sys.executable,'-m','nila','memory','add','Keep it simple'],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert store.items('memories')[0]['content']=='Keep it simple'
    result=subprocess.run([sys.executable,'-m','nila','--version'],capture_output=True,text=True)
    assert '0.3.0' in result.stdout
