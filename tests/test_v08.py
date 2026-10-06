import asyncio,base64,json
from datetime import date
from pathlib import Path
import httpx,pytest
from fastapi.testclient import TestClient
from nila import engine,model_manager as mm,extensions,conversation
from nila.storage import Store
from nila.server import create_app
from test_app import mock_ollama


def test_real_server_delivers_logo_and_bundled_landing(tmp_path):
    client=TestClient(create_app(Store(tmp_path)))
    response=client.get('/nila-logo.png')
    assert response.status_code==200 and response.headers['content-type']=='image/png'
    assert response.content.startswith(b'\x89PNG\r\n\x1a\n')
    about=client.get('/about/');assert about.status_code==200
    assert 'error-search' in about.text and 'March 2, 2026' in about.text
    assert client.get('/about/guide-license.html').status_code==200
    assert client.get('/about/../../vault.key').status_code!=200

@pytest.mark.parametrize('query',['Summarize the attached files: secret.txt','What does this say?'])
def test_attached_content_survives_search_mode_and_names_survive_reload(tmp_path,monkeypatch,query):
    seen=mock_ollama(monkeypatch);store=Store(tmp_path);store.save_settings({'auto_memory':False});client=TestClient(create_app(store));cid=store.create_chat()['id']
    doc=client.post(f'/api/chats/{cid}/attachments',json={'name':'secret.txt','data':base64.b64encode(b'PRIVATE_FILE_PAYLOAD').decode()}).json()
    from nila import websearch
    monkeypatch.setattr(websearch,'lookup',lambda *a:(_ for _ in ()).throw(AssertionError('Do not search file requests')))
    client.post(f'/api/chats/{cid}/reply',json={'content':query,'search_mode':'deep'})
    assert 'PRIVATE_FILE_PAYLOAD' in str(seen[-1]['messages'])
    chat=Store(tmp_path).chat(cid);assert chat['messages'][0]['attachments']==[{'id':doc['id'],'name':'secret.txt'}]
    client.delete(f'/api/chats/{cid}/attachments/{doc["id"]}')
    assert Store(tmp_path).chat(cid)['messages'][0]['attachments'][0]['name']=='secret.txt'


def test_birthday_context_remembers_once_per_year_and_retains_date(tmp_path,monkeypatch):
    seen=mock_ollama(monkeypatch);store=Store(tmp_path);store.save_settings({'auto_memory':False})
    monkeypatch.setattr(conversation,'local_today',lambda:date(2027,3,2))
    async def ask():return ''.join([x async for x in engine.reply(store,store.create_chat()['id'],'Hi')])
    asyncio.run(ask());assert 'Today is March 2' in seen[-1]['messages'][0]['content']
    assert Store(tmp_path).settings()['birthday_announced_year']==2027
    asyncio.run(ask());assert 'Today is March 2' not in seen[-1]['messages'][0]['content']
    assert 'March 2, 2026' not in seen[-1]['messages'][0]['content']
    async def birthday():return ''.join([x async for x in engine.reply(store,store.create_chat()['id'],'When is your birthday?')])
    asyncio.run(birthday());assert 'March 2, 2026' in seen[-1]['messages'][0]['content']
    monkeypatch.setattr(conversation,'local_today',lambda:date(2028,3,2));asyncio.run(ask());assert 'Today is March 2' in seen[-1]['messages'][0]['content']


def test_failed_reply_does_not_consume_birthday(tmp_path,monkeypatch):
    mock_ollama(monkeypatch,broken=True);store=Store(tmp_path)
    monkeypatch.setattr(conversation,'local_today',lambda:date(2027,3,2))
    async def ask():return [x async for x in engine.reply(store,store.create_chat()['id'],'Hi')]
    with pytest.raises(engine.NilaError):asyncio.run(ask())
    assert store.settings()['birthday_announced_year']==0


def test_model_download_once_then_reuse_and_load(tmp_path,monkeypatch):
    installed=[];downloads=[];loads=[]
    async def models():return [{'name':x} for x in installed]
    async def pull(name,progress):downloads.append(name);installed.append(name);progress({'status':'complete'})
    original=httpx.AsyncClient
    def handler(request):loads.append(json.loads(request.content));return httpx.Response(200,json={'done':True})
    monkeypatch.setattr(engine,'models',models);monkeypatch.setattr(extensions,'pull_model',pull)
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    store=Store(tmp_path)
    asyncio.run(mm.select(store,'fast'));asyncio.run(mm.select(store,'fast'))
    assert downloads==['qwen3:0.6b'] and len(loads)==2
    assert store.settings()['model_mode']=='fast'


def test_failed_activation_retains_model_and_releases_lease(tmp_path,monkeypatch):
    store=Store(tmp_path);old=store.settings()['model']
    async def models():return []
    async def pull(*a):raise ValueError('Network failed')
    monkeypatch.setattr(engine,'models',models);monkeypatch.setattr(extensions,'pull_model',pull)
    with pytest.raises(ValueError):asyncio.run(mm.select(store,'fast'))
    assert store.settings()['model']==old
    store.release(store.acquire())


def test_streaming_model_activation_has_progress_and_final_selection(tmp_path,monkeypatch):
    mock_ollama(monkeypatch)
    async def models():return [{'name':'qwen3:0.6b'}]
    monkeypatch.setattr(engine,'models',models)
    c=TestClient(create_app(Store(tmp_path)));events=[json.loads(line) for line in c.post('/api/models/activate',json={'value':'fast'}).text.splitlines()]
    assert any(x.get('progress','').startswith('Loading') for x in events)
    assert any(x.get('selection',{}).get('mode')=='fast' for x in events)
    assert events[-1]=={'done':True}


def test_unqualified_installed_model_does_not_download(tmp_path,monkeypatch):
    mock_ollama(monkeypatch)
    async def models():return [{'name':'my-model:latest'}]
    async def forbidden(*a):raise AssertionError('Installed model must not download')
    monkeypatch.setattr(engine,'models',models);monkeypatch.setattr(extensions,'pull_model',forbidden)
    s=Store(tmp_path);result=asyncio.run(mm.select(s,'my-model'));assert result['model']=='my-model:latest'


def test_birthday_question_uses_local_identity_even_when_search_enabled(tmp_path,monkeypatch):
    seen=mock_ollama(monkeypatch);s=Store(tmp_path);s.save_settings({'auto_memory':False})
    from nila import websearch
    async def search(q,mode):assert mode=='off';return []
    monkeypatch.setattr(websearch,'search',search)
    async def ask():return [x async for x in engine.reply(s,s.create_chat()['id'],'When is your birthday?',search_mode='deep')]
    asyncio.run(ask());assert 'March 2, 2026' in seen[0]['messages'][0]['content']


def test_explicit_web_request_keeps_file_context_out_of_public_cache(tmp_path,monkeypatch):
    seen=mock_ollama(monkeypatch);s=Store(tmp_path);s.save_settings({'auto_memory':False})
    from nila import workspace,websearch
    from nila.knowledge_cache import recall_web
    cid=s.create_chat()['id'];iid=workspace.ingest(s,'private.txt',b'PRIVATE_ATTACHMENT_FACT');workspace.attach(s,cid,[iid])
    monkeypatch.setattr(websearch,'lookup',lambda *a:[{'href':'https://example.org/public','title':'Public reference','body':'Public facts'}])
    async def ask():return [x async for x in engine.reply(s,cid,'Compare with attached details',search_mode='quick',search_query='public topic')]
    asyncio.run(ask());assert 'PRIVATE_ATTACHMENT_FACT' in str(seen[-1]['messages'])
    assert recall_web(s,'Compare with attached details')==('',[])


def test_windows_microphone_stop_terminates_capture(tmp_path,monkeypatch):
    from nila import voice
    from types import SimpleNamespace
    monkeypatch.setattr(voice,'os',SimpleNamespace(name='nt'))
    started=asyncio.Event();killed=[]
    class Process:
        returncode=None
        async def communicate(self,payload):
            assert json.loads(payload)['language']=='en-US'
            started.set();await asyncio.sleep(30)
        def kill(self):self.returncode=-1;killed.append(True)
        async def wait(self):return self.returncode
    async def spawn(*args,**kwargs):return Process()
    monkeypatch.setattr(asyncio,'create_subprocess_exec',spawn)
    app=create_app(Store(tmp_path))
    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://testserver') as c:
            task=asyncio.create_task(c.post('/api/voice/listen',json={'id':'capture-test','language':'en-US'}))
            await started.wait()
            assert (await c.delete('/api/voice/listen/capture-test')).json()['stopped']
            assert (await task).json()['stopped']
    asyncio.run(check());assert killed and not app.state.voice_tasks
