import asyncio,hashlib,json
import httpx,pytest
from nila import local_runtime as runtime,inference
from nila.storage import Store

def test_queue_wait_and_cancel(tmp_path):
    async def run():
        store=Store(tmp_path);held=store.acquire();messages=[]
        waiting=asyncio.create_task(store.acquire_async(progress=messages.append))
        await asyncio.sleep(.02);assert not waiting.done();assert 'Queued' in messages[0]
        store.release(held);token=await asyncio.wait_for(waiting,1);store.release(token)
        held=store.acquire();stop=asyncio.Event();waiting=asyncio.create_task(store.acquire_async(stop))
        await asyncio.sleep(.02);stop.set()
        with pytest.raises(asyncio.CancelledError):await waiting
        store.release(held);store.release(store.acquire())
    asyncio.run(run())

def test_verified_download_reuse_and_failure(tmp_path,monkeypatch):
    content=b'model';digest=hashlib.sha256(content).hexdigest();path=tmp_path/'model.gguf'
    actual=httpx.AsyncClient
    monkeypatch.setattr(runtime.httpx,'AsyncClient',lambda **kw:actual(transport=httpx.MockTransport(lambda req:httpx.Response(200,content=content)),**kw))
    asyncio.run(runtime.download('https://example.com/model',path,digest));assert path.read_bytes()==content
    monkeypatch.setattr(runtime.httpx,'AsyncClient',lambda **kw:(_ for _ in ()).throw(AssertionError('must reuse')))
    asyncio.run(runtime.download('https://example.com/model',path,digest))
    monkeypatch.setattr(runtime.httpx,'AsyncClient',lambda **kw:actual(transport=httpx.MockTransport(lambda req:httpx.Response(200,content=b'bad')),**kw))
    with pytest.raises(ValueError,match='checksum'):asyncio.run(runtime.download('https://example.com/model',path,'0'*64))
    assert path.read_bytes()==content;assert not path.with_suffix('.gguf.part').exists()

def test_adapter_json_stream_and_privacy(monkeypatch):
    monkeypatch.setattr(runtime,'config',lambda:{'engine':'llama.cpp','model':'qwen3:0.6b','key':'private'})
    async def ready(c):pass
    monkeypatch.setattr(runtime,'ensure',ready)
    calls=[]
    def handle(req):
        calls.append(req);data=json.loads(req.content)
        assert req.url.host=='127.0.0.1';assert req.headers['authorization']=='Bearer private'
        assert data['messages'][0]['content']=='Hi'
        if data['stream']:return httpx.Response(200,content=b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\ndata: [DONE]\n\n')
        return httpx.Response(200,json={'choices':[{'message':{'content':'Hello'}}]})
    monkeypatch.setattr(inference.httpx,'AsyncHTTPTransport',lambda:httpx.MockTransport(handle))
    async def run():
        async with inference.client() as c:
            payload={'model':'qwen3:0.6b','messages':[{'role':'user','content':'Hi'}]}
            assert (await c.post('http://localhost:11434/api/chat',json=payload)).json()['message']['content']=='Hello'
            lines=(await c.post('http://localhost:11434/api/chat',json=payload|{'stream':True})).text.splitlines()
            assert json.loads(lines[0])['message']['content']=='Hello';assert json.loads(lines[-1])['done']
            with pytest.raises(ValueError,match='external'):await c.get('https://example.com/api/tags')
    asyncio.run(run());assert len(calls)==2

def test_switch_back_restores_ollama_model(tmp_path,monkeypatch):
    monkeypatch.setenv('NILA_DATA_DIR',str(tmp_path));monkeypatch.setattr(runtime,'stop_owned',lambda c:None)
    store=Store(tmp_path);store.save_settings({'model':'smolvlm:500m'})
    runtime.save({'engine':'llama.cpp','model':'smolvlm:500m','ollama_model':'llama3.2:1b','key':'secret'})
    result=asyncio.run(runtime.choose(store,'ollama'))
    assert result['engine']=='ollama';assert store.settings()['model']=='llama3.2:1b';assert 'secret' not in json.dumps(result)

def test_background_setup_and_audio_cleanup(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from nila.server import create_app
    from nila import speech_pack
    monkeypatch.setenv('NILA_DATA_DIR',str(tmp_path))
    seen=[]
    async def worker(payload,timeout=180):
        from pathlib import Path
        p=Path(payload['file']);seen.append(p)
        if payload['action']=='speak':p.write_bytes(b'RIFF-test');return {}
        assert p.read_bytes()==b'audio';return {'text':'Hello'}
    monkeypatch.setattr(speech_pack,'worker',worker)
    store=Store(tmp_path);store.save_settings({'auto_update':False})
    with TestClient(create_app(store)) as client:
        assert client.get('/api/runtime').status_code==200
        assert client.post('/api/runtime/setup',json={'component':'unknown'}).status_code==422
        assert client.post('/api/runtime/transcribe',json={'data':'!'}).status_code==400
        assert client.post('/api/runtime/transcribe',json={'data':'YXVkaW8='}).json()=={'text':'Hello'}
        r=client.post('/api/runtime/speak',json={'text':'Hello'});assert r.content==b'RIFF-test'
        assert 'blob:' in r.headers['content-security-policy']
    assert all(not p.exists() for p in seen)
