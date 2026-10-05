import asyncio
import json
import httpx
import pytest
from fastapi.testclient import TestClient
from nila import engine, websearch, learning
from nila.storage import Store
from nila.server import create_app
from test_app import mock_ollama

@pytest.fixture
def store(tmp_path):
    s=Store(tmp_path);s.save_settings({'auto_memory':False});return s

def test_search_off_never_calls_provider(monkeypatch):
    def forbidden(*args):raise AssertionError('Network called')
    monkeypatch.setattr(websearch,'lookup',forbidden)
    assert asyncio.run(websearch.search('Private chat','off'))==[]

def test_deep_deduplicates_filters_and_bounds(monkeypatch):
    queries=[]
    def lookup(q,limit):
        queries.append(q)
        return [{'href':'http://127.0.0.1/private','body':'private'}, {'href':'javascript:alert(1)'}, {'href':'https://example.com/a','title':'A','body':'x'*2000}, {'href':'https://example.org/'+str(len(q)),'body':'evidence'}]
    monkeypatch.setattr(websearch,'lookup',lookup)
    results=asyncio.run(websearch.search('Python','deep'))
    assert len(queries)==3 and len(results)==4
    assert len({r['url'] for r in results})==4
    assert all(len(r['snippet'])<=350 and r['retrieved'] for r in results)

def test_search_failure_does_not_destroy_edited_branch(store,monkeypatch):
    mock_ollama(monkeypatch)
    monkeypatch.setattr(websearch,'lookup',lambda *args:[])
    cid=store.create_chat()['id'];store.add_message(cid,'user','Old');store.add_message(cid,'assistant','Keep')
    before=store.chat(cid)['messages']
    client=TestClient(create_app(store))
    result=client.post(f'/api/chats/{cid}/reply',json={'content':'New','edit_message_id':before[0]['id'],'search_mode':'quick'})
    assert 'NILA-020' in result.text and store.chat(cid)['messages']==before
    token=store.acquire();store.release(token)

def test_search_sends_only_explicit_query_and_persists_sources(store,monkeypatch):
    seen=mock_ollama(monkeypatch);queries=[]
    store.save_settings({'user_name':'PRIVATE_NAME'});store.add_item('memories','PRIVATE_MEMORY')
    def lookup(q,limit):
        queries.append(q);return [{'href':'https://example.com/evidence','title':'Reference','body':'Fact.'}]
    monkeypatch.setattr(websearch,'lookup',lookup)
    cid=store.create_chat()['id'];store.add_message(cid,'user','PRIVATE_HISTORY')
    client=TestClient(create_app(store))
    result=client.post(f'/api/chats/{cid}/reply',json={'content':'PRIVATE_PROMPT','search_mode':'quick','search_query':'public query'})
    assert queries==['public query']
    assert 'PRIVATE_MEMORY' in json.dumps(seen) # stays in local Ollama context only
    assert 'Web evidence' in json.dumps(seen)
    assert 'https://example.com/evidence' in store.chat(cid)['messages'][-1]['content']
    assert 'Sources' in result.text

def test_edit_regenerates_in_place_cascades_feedback_and_continues(store,monkeypatch):
    seen=mock_ollama(monkeypatch)
    cid=store.create_chat()['id']
    for role,text in [('user','First'),('assistant','Answer'),('user','Old prompt'),('assistant','Old answer'),('user','Dependent')]:store.add_message(cid,role,text)
    messages=store.chat(cid)['messages'];mid=messages[2]['id']
    store.feedback(cid,messages[3]['id'],-1,'Old guidance')
    client=TestClient(create_app(store))
    result=client.post(f'/api/chats/{cid}/reply',json={'content':'Changed prompt','edit_message_id':mid})
    assert 'Hello' in result.text
    updated=store.chat(cid)['messages']
    assert [m['content'] for m in updated]==['First','Answer','Changed prompt','Hello Nadeem.']
    assert updated[2]['id']==mid
    with store.db() as db: assert db.execute('SELECT COUNT(*) FROM feedback').fetchone()[0]==0
    client.post(f'/api/chats/{cid}/reply',json={'content':'Follow-up'})
    assert any(m['content']=='Changed prompt' for m in seen[-1]['messages'])
    assert client.post(f'/api/chats/{cid}/reply',json={'content':'x','edit_message_id':updated[-1]['id']}).status_code==404

def test_feedback_encrypted_used_locally_and_clearable(store,monkeypatch):
    cid=store.create_chat()['id'];store.add_message(cid,'user','Python dictionaries');store.add_message(cid,'assistant','A response')
    mid=store.chat(cid)['messages'][-1]['id'];client=TestClient(create_app(store))
    assert client.put(f'/api/chats/{cid}/messages/{mid}/feedback',json={'rating':-1,'reason':'Use worked examples'}).status_code==200
    with store.db() as db: assert 'worked' not in db.execute('SELECT reason FROM feedback').fetchone()[0]
    assert 'Use worked examples' in engine.context(store,cid,store.settings())[0]['content']
    assert client.put(f'/api/chats/{cid}/messages/{mid}/feedback',json={'rating':0}).status_code==200
    assert 'Use worked examples' not in engine.context(store,cid,store.settings())[0]['content']
    assert client.put(f'/api/chats/{cid}/messages/{mid}/feedback',json={'rating':2}).status_code==422
    other=store.create_chat()['id']
    assert client.put(f'/api/chats/{other}/messages/{mid}/feedback',json={'rating':1}).status_code==404

def test_learning_both_http_payloads_exclude_all_private_context(store,monkeypatch):
    store.save_settings({'user_name':'PRIVATE_NAME','description':'PRIVATE_PROFILE'})
    store.add_item('memories','PRIVATE_MEMORY');store.add_item('notes','PRIVATE_NOTE')
    cid=store.create_chat()['id'];store.add_message(cid,'user','PRIVATE_HISTORY');store.add_message(cid,'assistant','PRIVATE_ANSWER')
    store.feedback(cid,store.chat(cid)['messages'][-1]['id'],-1,'PRIVATE_FEEDBACK')
    learning.save_key(store,'fake-key-long-enough')
    requests=[];original=httpx.AsyncClient
    def handler(req):
        requests.append(req)
        if req.url.host=='127.0.0.1':return httpx.Response(200,text=json.dumps({'message':{'content':'Public answer'},'done':True})+'\n')
        return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':json.dumps({'verdict':'acceptable','feedback':'OK','lesson':'Public lesson'})}]}}]})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    def forbidden(*args,**kw):raise AssertionError('Private store method accessed')
    for name in ('settings','chat','items','feedback_context'):monkeypatch.setattr(store,name,forbidden)
    lab=learning.LearningLab(store)
    config=learning.SessionConfig(topic='Public topic',local_model='llama3.2:1b',gemini_model='test',max_rounds=1,consent=True)
    iid=lab.create(config);asyncio.run(lab.run(iid))
    assert learning.session(store,iid)['status']=='completed'
    assert len(requests)==2
    assert all('PRIVATE_' not in r.content.decode() for r in requests)
    assert all('fake-key' not in r.content.decode() for r in requests)
    with pytest.raises(ValueError):learning.SessionConfig(**config.model_dump(),include_memories=True)
