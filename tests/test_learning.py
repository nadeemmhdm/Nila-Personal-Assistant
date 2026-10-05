import asyncio
import json
import time
import subprocess
import sys
import httpx
import pytest
from fastapi.testclient import TestClient
from nila.storage import Store
from nila.server import create_app,Settings
from nila import learning as labmod
from nila.learning import SessionConfig,Review,LearningLab,save_key,session,knowledge

@pytest.fixture
def store(tmp_path,monkeypatch):
    async def question(*args):return "What are Python dictionaries?"
    monkeypatch.setattr(labmod,"gemini_question",question)
    s=Store(tmp_path);labmod.ensure(s);save_key(s,'test-key-not-a-real-google-key');return s

def config(**kw):return SessionConfig(topic='Python dictionaries',local_model='custom-model:latest',gemini_model='test-gemini',minutes=1,max_rounds=1,consent=True,**kw)

def test_secret_is_encrypted_and_never_in_api(store):
    client=TestClient(create_app(store))
    assert client.get('/api/learning/key').json()=={'configured':True}
    assert 'test-key' not in client.get('/api/settings').text
    with store.db() as db:assert db.execute('SELECT value FROM secrets').fetchone()[0].startswith('enc:v1:')
    assert client.post('/api/learning/sessions',json=config().model_dump()|{'consent':False}).status_code==400
    assert client.delete('/api/learning/key').json()=={'configured':False}

def test_review_saves_and_reuses_relevant_knowledge(store,monkeypatch):
    async def local(c,q,emit):emit('Dictionaries map keys to values.');return 'Dictionaries map keys to values.'
    async def review(*args):return Review(verdict='acceptable',feedback='Correct.',lesson='Python dictionaries map unique keys to values.',next_question='How do lookups work?')
    monkeypatch.setattr(labmod,'local_answer',local);monkeypatch.setattr(labmod,'gemini_review',review)
    lab=LearningLab(store);iid=lab.create(config());asyncio.run(lab.run(iid))
    result=session(store,iid)
    assert result['status']=='completed'
    assert [m['actor'] for m in result['messages'] if m['actor']!='system']==['question','ollama','gemini']
    assert knowledge(store)[0]['enabled']==1
    assert 'unique keys' in labmod.knowledge_context(store,'How do Python dictionaries work?')
    assert labmod.knowledge_context(store,'volcano geology')==''
    from nila.engine import context
    cid=store.create_chat()['id'];store.add_message(cid,'user','Explain Python dictionaries')
    assert 'Gemini-reviewed study notes' in context(store,cid,store.settings())[0]['content']
    assert 'Gemini-reviewed study notes' not in context(store,cid,store.settings()|{'knowledge_enabled':False})[0]['content']

def test_revision_feedback_returns_to_local_model(store,monkeypatch):
    prompts=[];count=0
    async def local(c,q,emit):prompts.append(q);return 'Candidate answer'
    async def review(*args):
        nonlocal count;count+=1
        return Review(verdict='revise' if count==1 else 'acceptable',feedback='Fix the missing key case.',lesson='' if count==1 else 'Use get for a fallback value.')
    monkeypatch.setattr(labmod,'local_answer',local);monkeypatch.setattr(labmod,'gemini_review',review);monkeypatch.setattr(labmod,'ROUND_PAUSE_SECONDS',0)
    c=config();c.max_rounds=2;lab=LearningLab(store);iid=lab.create(c);asyncio.run(lab.run(iid))
    assert 'Fix the missing key case' in prompts[1]
    assert len(knowledge(store))==1
    assert knowledge(store)[0]['round']==2

def test_stop_cancels_request_and_releases_generation(store,monkeypatch):
    started=asyncio.Event();cancelled=[]
    async def local(c,q,emit):
        started.set();emit('Partial answer')
        try:await asyncio.sleep(10)
        finally:cancelled.append(True)
    monkeypatch.setattr(labmod,'local_answer',local)
    async def run():
        lab=LearningLab(store);iid=lab.start(config());task=lab.tasks[iid]
        await started.wait();lab.stop(iid);await task
        return iid
    iid=asyncio.run(run());assert cancelled
    assert session(store,iid)['status']=='stopped'
    assert not knowledge(store)
    token=store.acquire();store.release(token)

def test_deadline_bounds_inflight_request(store,monkeypatch):
    async def local(*args):await asyncio.sleep(10)
    monkeypatch.setattr(labmod,'local_answer',local)
    lab=LearningLab(store);iid=lab.create(config())
    with store.db() as db:db.execute('UPDATE learning_sessions SET deadline=? WHERE id=?',(time.time()+.05,iid))
    asyncio.run(lab.run(iid));assert session(store,iid)['status']=='time_limit'

def test_gemini_quota_stops_without_retry_or_secret_leak(store,monkeypatch):
    original=httpx.AsyncClient;requests=[]
    def handler(r):requests.append(r);return httpx.Response(429,json={'error':{'message':'test-key-not-a-real-google-key'}})
    monkeypatch.setattr(labmod.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    async def local(*args):return 'Local answer'
    monkeypatch.setattr(labmod,'local_answer',local)
    lab=LearningLab(store);iid=lab.create(config());asyncio.run(lab.run(iid))
    result=session(store,iid)
    assert result['status']=='failed' and 'quota' in result['error']
    assert 'test-key' not in json.dumps(result)
    assert len(requests)==1 and not knowledge(store)

def test_remote_payload_excludes_profile_and_memory(store,monkeypatch):
    store.save_settings({'user_name':'Private Name','company':'Private Company'})
    store.add_item('memories','Private memory')
    original=httpx.AsyncClient;requests=[]
    def handler(r):
        requests.append(r)
        return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':json.dumps({'verdict':'acceptable','feedback':'Fine','lesson':'Dictionary lesson','next_question':''})}]}}]})
    monkeypatch.setattr(labmod.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    asyncio.run(labmod.gemini_review(store,config(),'Question','Answer'))
    body=requests[0].content.decode()
    assert 'Private' not in body and 'test-key' not in body
    assert requests[0].headers['x-goog-api-key']=='test-key-not-a-real-google-key'

def test_role_specific_profile_and_arbitrary_model():
    s=Settings(position='Student',course='BSc',completion_year='2027',company='Should clear',model='qwen-custom:7b')
    assert s.company=='' and s.course=='BSc' and s.completion_year=='2027'
    s=Settings(position='Employee',company='Example',job_role='Developer',course='Should clear')
    assert s.course=='' and s.company=='Example'
    with pytest.raises(ValueError):Settings(completion_year='tomorrow')

def test_plain_cli_input_and_interactive_quit(store,monkeypatch):
    monkeypatch.setenv('NILA_DATA_DIR',str(store.root))
    # CLI stdout is UTF-8; Windows subprocess defaults to the ANSI code page.
    monkeypatch.setenv('PYTHONIOENCODING','utf-8')
    p=subprocess.run([sys.executable,'-m','nila'],input='/help\n/exit\n',capture_output=True,text=True,encoding="utf-8")
    assert p.returncode==0 and 'Just type your message' in p.stdout
    p=subprocess.run([sys.executable,'-m','nila','Explain','Python','dictionaries'],capture_output=True,text=True,encoding="utf-8")
    assert 'invalid choice' not in p.stderr and 'NILA-001' in p.stderr
