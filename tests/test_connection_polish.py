import asyncio
import pytest
import httpx
from nila import google_chat as chat,google_connect as google
from nila.storage import Store


def test_gmail_time_window_and_unread(monkeypatch):
    monkeypatch.setattr(chat.time,'time',lambda:2000000000)
    spec=chat.plan('@Gmail unread emails from the last 10 minutes')[0]
    assert spec['gmail_query']=='after:1999999400 is:unread'
    assert 'error' not in spec
    assert chat.plan('@Gmail last 0 minutes')[0]['error']
    assert chat.plan('@Gmail last 32 days')[0]['error']
    assert chat.plan('What are the latest Gmail features?')==[]
    assert chat.plan('latest Gmail news')==[]
    assert chat.plan("Don't read @Gmail last 10 minutes")[0]['error']
    _,params=google.endpoint('gmail',gmail_query=spec['gmail_query'])
    assert params['q']==spec['gmail_query'] and params['labelIds']=='INBOX'
    with pytest.raises(ValueError):google.endpoint('gmail',gmail_query='in:anywhere OR secret')


def test_filtered_read_still_requires_connection(tmp_path,monkeypatch):
    store=Store(tmp_path)
    async def forbidden(*a,**kw):raise AssertionError('Disconnected service must not be called')
    monkeypatch.setattr(google,'read',forbidden)
    text,refs=asyncio.run(chat.gather(store,chat.plan('@Gmail last 10 minutes')))
    assert 'Connect Gmail first' in text and refs==[]


def test_host_browser_page_has_actionable_error(tmp_path,monkeypatch):
    store=Store(tmp_path);google.configure(store,'https://example.com','K'*40)
    class Client:
        def __init__(self,*a,**kw):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*a):pass
        async def post(self,*a,**kw):return httpx.Response(403,headers={'content-type':'text/html'},text='<html>JavaScript required</html>')
    monkeypatch.setattr(google.httpx,'AsyncClient',Client)
    with pytest.raises(ValueError,match='browser-only HTML'):
        asyncio.run(google.broker(store,'health',{}))


def test_write_scope_status_has_no_tokens(tmp_path):
    store=Store(tmp_path);google.put(store,'token:gmail',{'access_token':'PRIVATE_TOKEN','scope':google.PREFIX+'gmail.send'})
    value=google.status(store)
    assert value['services'][0]['write_scope']
    assert 'PRIVATE_TOKEN' not in str(value)
    assert not value['writes_enabled']


def test_normal_greeting_has_no_birthday_or_calendar_context(tmp_path,monkeypatch):
    from datetime import date
    from nila import engine,conversation
    from test_app import mock_ollama
    seen=mock_ollama(monkeypatch);store=Store(tmp_path);store.save_settings({'auto_memory':False})
    monkeypatch.setattr(conversation,'local_today',lambda:date(2026,10,7))
    async def ask():return ''.join([p async for p in engine.reply(store,store.create_chat()['id'],'Hi')])
    asyncio.run(ask())
    context=seen[-1]['messages'][0]['content'].lower()
    assert 'birthday' not in context and 'march' not in context
    assert 'nila' in context
