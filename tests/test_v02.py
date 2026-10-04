import asyncio
import json
import sqlite3
import time
import httpx
import pytest
from fastapi.testclient import TestClient
from nila.storage import Store
from nila.server import create_app
from nila.automation import Job,Scheduler,save_job,jobs,runs
from nila import memory,updater

@pytest.fixture
def store(tmp_path):return Store(tmp_path)

def test_encryption_and_existing_database_migration(tmp_path):
    db=sqlite3.connect(tmp_path/'nila.db')
    db.executescript("CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE memories(id TEXT PRIMARY KEY,content TEXT NOT NULL,created REAL NOT NULL);")
    db.execute('INSERT INTO settings VALUES (?,?)',('company',json.dumps('Example Company')))
    db.execute('INSERT INTO memories VALUES (?,?,?)',('old','Sensitive old memory',time.time()))
    db.commit();db.close()
    store=Store(tmp_path)
    assert store.settings()['company']=='Example Company'
    assert store.items('memories')[0]['content']=='Sensitive old memory'
    cid=store.create_chat()['id'];store.add_message(cid,'user','Private chat content')
    store.add_item('notes','Private note content')
    with store.db() as db:
        for table,column in [('settings','value'),('memories','content'),('notes','content'),('messages','content'),('chats','title')]:
            assert all(row[0].startswith('enc:v1:') for row in db.execute(f'SELECT {column} FROM {table}'))
    assert Store(tmp_path).chat(cid)['messages'][0]['content']=='Private chat content'
    assert b'Sensitive old memory' not in (tmp_path/'nila.db').read_bytes()

def test_wrong_key_fails_closed(store):
    from cryptography.fernet import Fernet
    store.save_settings({'user_name':'Nadeem'})
    (store.root/'vault.key').write_bytes(b'FILE1:'+Fernet.generate_key())
    with pytest.raises(RuntimeError,match='decrypt'):Store(store.root).settings()

def test_memory_dedup_and_forget(store):
    iid=store.add_item('memories','Interest: Python','automatic')
    assert store.add_item('memories','interest: python','automatic')==iid
    store.delete_item('memories',iid)
    assert store.add_item('memories','Interest: Python','automatic') is None
    assert store.add_item('memories','Interest: Python','manual')

def test_profile_and_auto_memory_switches(store):
    with TestClient(create_app(store)) as c:
        settings=c.get('/api/settings').json()|{'position':'Employee','company':'Example Company','description':'Learning web development','auto_memory':False,'tone':'Friendly'}
        assert c.put('/api/settings',json=settings).status_code==200
        assert c.get('/api/settings').json()['company']=='Example Company'
        assert c.put('/api/settings',json=settings|{'tone':'evil'}).status_code==422
    from nila.engine import context
    cid=store.create_chat()['id']
    assert 'Example Company' in context(store,cid,store.settings())[0]['content']

def test_memory_requires_verbatim_evidence_and_filters_secrets(store,monkeypatch):
    original=httpx.AsyncClient;calls=[]
    def handler(r):
        calls.append(r)
        return httpx.Response(200,json={'message':{'content':json.dumps({'facts':[{'category':'interest','value':'Python','evidence':'I like Python'},{'category':'college','value':'Imaginary College','evidence':'I study at Imaginary College'}]})}})
    monkeypatch.setattr(memory.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    assert asyncio.run(memory.learn(store,'I like Python'))==['Interest: Python']
    assert len(store.items('memories'))==1
    assert asyncio.run(memory.learn(store,'My password is abc123'))==[]
    assert len(calls)==1
    store.save_settings({'auto_memory':False})
    assert asyncio.run(memory.learn(store,'I like Python'))==[]
    assert len(calls)==1

def test_once_schedule_and_no_duplicate_claims(store):
    iid=save_job(store,Job(title='Save note',prompt='Review Python',kind='note',next_run=time.time()-1))
    async def run():await asyncio.gather(Scheduler(store).run(iid),Scheduler(Store(store.root)).run(iid))
    asyncio.run(run())
    assert len(store.items('notes'))==1
    assert not jobs(store)[0]['enabled']
    assert runs(store)[0]['status']=='complete'

def test_scheduler_pausing_preserves_disabled_state(store,monkeypatch):
    import nila.automation as module
    started=asyncio.Event()
    async def fake_reply(*args,**kwargs):
        yield 'Partial response'
        started.set()
        await asyncio.sleep(30)
    monkeypatch.setattr(module,'reply',fake_reply)
    iid=save_job(store,Job(title='AI',prompt='Write a tip',kind='ai',interval_minutes=5,next_run=time.time()-1))
    scheduler=Scheduler(store)
    async def run():
        task=asyncio.create_task(scheduler.run(iid))
        await started.wait();scheduler.pause(iid);await task
    asyncio.run(run())
    assert not jobs(store)[0]['enabled']
    assert runs(store)[0]['status']=='cancelled'
    assert 'Partial response' in runs(store)[0]['output']

def test_automation_api_validation_and_run_request(store):
    c=TestClient(create_app(store))
    data={'title':'Plan','prompt':'Make a study plan','kind':'ai','next_run':time.time()+500,'interval_minutes':0}
    assert c.post('/api/automations',json=data|{'kind':'shell'}).status_code==422
    assert c.post('/api/automations',json=data|{'interval_minutes':1}).status_code==422
    iid=c.post('/api/automations',json=data).json()['id']
    assert c.post('/api/automations/'+iid+'/run').json()['status']=='queued'
    assert c.post('/api/automations/'+iid+'/pause').status_code==200
    assert not c.get('/api/automations').json()['jobs'][0]['enabled']
    assert c.delete('/api/automations/'+iid).status_code==200

def test_update_checks_main_not_releases_and_handles_offline(monkeypatch):
    original=httpx.Client;urls=[]
    def handler(r):
        urls.append(str(r.url));return httpx.Response(200,json={'sha':'a'*40})
    monkeypatch.setattr(updater.httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    result=updater.check();assert result['latest']=='a'*40
    assert urls[0].endswith('/commits/main')
    def offline(r):raise httpx.ConnectError('offline')
    monkeypatch.setattr(updater.httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(offline),**kw))
    assert updater.check()['online'] is False

def test_update_rejects_modified_installer(store,monkeypatch):
    original=httpx.Client
    monkeypatch.setattr(updater,'check',lambda:{'managed':True,'online':True,'available':True,'latest':'b'*40,'root':str(store.root)})
    def handler(r):
        if '/contents/' in str(r.url):return httpx.Response(200,json={'sha':'0'*40})
        return httpx.Response(200,content=b'modified installer')
    monkeypatch.setattr(updater.httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    assert updater.apply_update()['status']=='failed'
    assert not (store.root/'current.txt').exists()
