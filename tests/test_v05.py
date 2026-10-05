import asyncio,base64,json,subprocess,sys,time
import pytest
from fastapi.testclient import TestClient
from nila.storage import Store
from nila.server import create_app
from nila import engine,workspace as ws
from nila.automation import Job,save_job,Scheduler,jobs
from nila.backup import export_backup,restore_backup
from test_app import mock_ollama

@pytest.fixture
def store(tmp_path):
    s=Store(tmp_path/'saved');s.save_settings({'auto_memory':False,'auto_update':False});return s

def seed(s):
    cid=s.create_chat()['id']
    for role,text in [('user','Explain a dictionary'),('assistant','Original answer'),('user','Later follow-up'),('assistant','Later answer')]:s.add_message(cid,role,text)
    return cid,s.chat(cid)['messages'][1]['id']

def test_regenerate_replaces_same_id_archives_branch_and_preserves_prompt(store,monkeypatch):
    requests=mock_ollama(monkeypatch);cid,mid=seed(store)
    c=TestClient(create_app(store))
    r=c.post(f'/api/chats/{cid}/reply',json={'content':'Regenerate','regenerate_id':mid,'instruction':'Use a clear worked example'})
    assert 'Hello' in r.text
    current=store.chat(cid)['messages']
    assert len(current)==2 and current[1]['id']==mid and current[0]['content']=='Explain a dictionary'
    other=next(x for x in store.chats() if x['id']!=cid)
    assert [x['content'] for x in store.chat(other['id'])['messages']]==['Explain a dictionary','Original answer','Later follow-up','Later answer']
    payload=json.dumps(requests[0]);assert 'Use a clear worked example' in payload and 'Original answer' in payload and 'Later follow-up' not in payload
    assert c.get(f'/api/chats/{cid}/messages/{mid}/sources').status_code==200

def test_regenerate_failure_keeps_original_and_does_not_create_branch(store,monkeypatch):
    mock_ollama(monkeypatch,broken=True);cid,mid=seed(store);before=store.chat(cid)
    r=TestClient(create_app(store)).post(f'/api/chats/{cid}/reply',json={'content':'Regenerate','regenerate_id':mid})
    assert 'NILA-004' in r.text and store.chat(cid)==before and len(store.chats())==1

def test_regenerate_cancellation_keeps_original(store,monkeypatch):
    cid,mid=seed(store);before=store.chat(cid)
    async def models():return [{'name':'qwen3:4b'},{'name':'llama3.2:1b'}]
    monkeypatch.setattr(engine,'models',models)
    class Response:
        status_code=200
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def aiter_lines(self):
            yield json.dumps({'message':{'content':'new partial'}})
            await asyncio.sleep(5)
    class Client:
        def __init__(self,**kw):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        def stream(self,*a,**kw):return Response()
    monkeypatch.setattr(engine.httpx,'AsyncClient',Client)
    async def run():
        got=asyncio.Event()
        async def consume():
            async for x in engine.reply(store,cid,'unused',regenerate_id=mid):got.set()
        task=asyncio.create_task(consume());await got.wait();task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
    asyncio.run(run());assert store.chat(cid)==before
    token=store.acquire();store.release(token)

def test_temporary_is_ram_only_excludes_profile_feedback_and_history(store,monkeypatch,tmp_path):
    seen=mock_ollama(monkeypatch);store.save_settings({'user_name':'PRIVATE_PROFILE'});store.add_item('memories','PRIVATE_MEMORY')
    c=TestClient(create_app(store));cid=c.post('/api/chats',json={'temporary':True}).json()['id']
    assert c.post(f'/api/chats/{cid}/reply',json={'content':'TEMPORARY_SENTINEL'}).status_code==200
    chat=c.get(f'/api/chats/{cid}').json();assert chat['temporary'] and len(chat['messages'])==2
    assert store.chats()==[] and c.get('/api/chats').json()==[]
    assert 'PRIVATE_' not in json.dumps(seen)
    assert c.put(f"/api/chats/{cid}/messages/{chat['messages'][1]['id']}/feedback",json={'rating':1}).status_code==400
    assert c.post(f'/api/chats/{cid}/branch').status_code==400
    with store.db() as db:assert db.execute('SELECT COUNT(*) FROM messages').fetchone()[0]==0
    isolated=Store(tmp_path/'must-not-exist',ephemeral=True);assert not (tmp_path/'must-not-exist').exists();isolated._ram.close()
    assert c.delete(f'/api/chats/{cid}').status_code==200
    assert c.get(f'/api/chats/{cid}').status_code==404

def test_memory_inbox_review_edit_reject_and_suppression(store):
    iid=ws.suggest_memory(store,'Interest: Python');assert not store.items('memories')
    assert ws.suggest_memory(store,'Interest: Python') is None
    ws.decide_memory(store,iid,True,'Interest: Python programming')
    assert store.items('memories')[0]['source']=='reviewed' and not ws.inbox(store)
    iid=ws.suggest_memory(store,'Goal: Rust');ws.decide_memory(store,iid,False)
    assert ws.suggest_memory(store,'Goal: Rust') is None

def test_documents_project_isolation_and_provenance(store,monkeypatch):
    seen=mock_ollama(monkeypatch);p=ws.save_project(store,'Study','Explain using examples')
    d=ws.ingest(store,'reference.txt',b'Python dictionaries use unique keys.',p)
    other=ws.save_project(store,'Unrelated');ws.ingest(store,'secret.txt',b'UNRELATED_PROJECT_SENTINEL',other)
    ws.save_project(store,'Study renamed','Be concise',p)
    assert len(ws.document_list(store))==2 # Editing a project must not cascade-delete its files.
    cid=store.create_chat()['id'];ws.assign_project(store,cid,p)
    c=TestClient(create_app(store));c.post(f'/api/chats/{cid}/reply',json={'content':'Explain Python dictionaries'})
    assert 'unique keys' in json.dumps(seen) and 'UNRELATED_PROJECT_SENTINEL' not in json.dumps(seen)
    mid=store.chat(cid)['messages'][-1]['id'];sources=ws.provenance(store,cid,mid)
    assert any(x['kind']=='document' and x['page']==1 for x in sources)
    b=ws.branch(store,cid)
    with store.db() as db:assert db.execute('SELECT project_id FROM chat_meta WHERE chat_id=?',(b,)).fetchone()[0]==p
    with pytest.raises(ValueError):ws.ingest(store,'code.exe',b'bad')

def test_password_backup_roundtrip_excludes_keys_pauses_jobs_and_wrong_password_safe(store,tmp_path):
    from nila.learning import save_key
    save_key(store,'PRIVATE_GEMINI_KEY');cid,mid=seed(store)
    store.feedback(cid,mid,-1,'Clearer please');ws.ingest(store,'notes.txt',b'Local file')
    save_job(store,Job(title='Task',prompt='Hello',kind='note',next_run=time.time()+60))
    raw=export_backup(store,'correct horse battery staple')
    assert b'PRIVATE_GEMINI_KEY' not in raw and b'Original answer' not in raw
    target=Store(tmp_path/'target');target.add_item('notes','Keep until success')
    with pytest.raises(ValueError):restore_backup(target,raw,'wrong password long')
    assert target.items('notes')[0]['content']=='Keep until success'
    preview=restore_backup(target,raw,'correct horse battery staple');assert preview['counts']['chats']==1
    assert target.chats()==[]
    restore_backup(target,raw,'correct horse battery staple',True)
    assert target.chat(cid)['messages'][1]['content']=='Original answer'
    assert not jobs(target)[0]['enabled'] and ws.feedback_list(target)[0]['reason']=='Clearer please'
    with target.db() as db:assert not db.execute('SELECT * FROM secrets').fetchall()
    assert target.items('notes')==[]

def test_restore_rejects_active_work_and_tampering(store):
    raw=export_backup(store,'correct horse battery staple')
    with pytest.raises(ValueError):restore_backup(store,raw[:-1]+b'X','correct horse battery staple',True)
    token=store.acquire()
    try:
        with pytest.raises(RuntimeError):restore_backup(store,raw,'correct horse battery staple',True)
    finally:store.release(token)

def test_missed_automation_ask_run_skip(store):
    sched=Scheduler(store)
    for policy in ['ask','run','skip']:
        iid=save_job(store,Job(title=policy,prompt=policy,kind='note',next_run=time.time()-600,missed_policy=policy))
        out=asyncio.run(sched.run(iid));assert out['status']=={'ask':'needs_decision','run':'complete','skip':'skipped'}[policy]
    assert [x['content'] for x in store.items('notes')]==['run']
    missed=next(x for x in jobs(store) if x['missed'])
    c=TestClient(create_app(store));assert c.post('/api/automations/'+missed['id']+'/recover',json={'action':'run'}).status_code==410

def test_preview_does_not_schedule_and_cli_workspace_commands(store,monkeypatch):
    client=TestClient(create_app(store))
    r=client.post('/api/automations/preview',json={'title':'Test','prompt':'Test','kind':'note','next_run':time.time()+60})
    assert r.status_code==410 and not jobs(store)
    monkeypatch.setenv('NILA_DATA_DIR',str(store.root))
    out=subprocess.run([sys.executable,'-m','nila','inbox'],capture_output=True,text=True)
    assert out.returncode==0 and '[]' in out.stdout
    assert client.get('/api/brief').headers['cache-control']=='no-store'
