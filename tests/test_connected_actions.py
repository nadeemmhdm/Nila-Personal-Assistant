import json
import pytest
from nila import google_actions as actions, google_chat, skills
from nila.conversation import IDENTITY


def test_mentions_are_bounded_and_read_intent_required():
    assert google_chat.plan('@Gmail read my last email')[0]['service']=='gmail'
    assert google_chat.plan('@Docs')[0]['error']
    assert google_chat.plan('What is YouTube?')==[]
    assert google_chat.plan("Don't read @Gmail")[0]['error']


def test_explicit_actions_and_no_guessed_arguments():
    assert actions.parse('@Gmail send to friend@example.com subject "Hi" body "Hello"')[2]['text']=='Hello'
    assert actions.parse('@Meet create a meeting link')==('meet','create',{})
    assert actions.parse('Send an email to my friend') is None
    assert actions.parse('@Gmail send {"to":"friend@example.com","text":"Hi"}')[0]=='gmail'
    assert actions.parse('@Gmail send {"to":"unknown"}')[2] is None


def test_safe_fixed_write_endpoints():
    with pytest.raises(ValueError):actions.endpoint('gmail','send',{'to':'a@example.com\r\nBcc: x@example.com'})
    with pytest.raises(ValueError):actions.endpoint('docs','append',{'id':'../oops','text':'x'})
    with pytest.raises(ValueError):actions.endpoint('sheets','update',{'id':'abc','range':'A1','values':['oops']})
    method,url,body=actions.endpoint('sheets','update',{'id':'abc','range':'A1:B1','values':[['=IMPORTXML("https://x")',2]]})
    assert method=='PUT' and 'valueInputOption=RAW' in url
    assert body['values'][0][0].startswith('=')


def test_greeting_identity_does_not_supply_birthday_date():
    assert 'March 2' not in IDENTITY

def test_write_requires_local_permission_before_network(tmp_path,monkeypatch):
    from nila.storage import Store
    from nila import google_connect as g
    store=Store(tmp_path)
    g.put(store,'token:gmail',{'scope':g.PREFIX+'gmail.send'})
    with pytest.raises(ValueError,match='Enable Google writes'):
        import asyncio
        asyncio.run(actions.execute(store,'gmail','send',{'to':'person@example.com','text':'Hello'}))


def test_skills_remain_enabled_together(tmp_path):
    from nila.storage import Store
    store=Store(tmp_path)
    items=skills.listing(store)
    for item in items[:2]:skills.enable(store,item['id'],True)
    assert len([s for s in skills.listing(store) if s['enabled']])==2
    assert items[0]['content'] in skills.active_context(store)
    skills.enable(store,items[0]['id'],False)
    assert [s['id'] for s in skills.listing(store) if s['enabled']]==[items[1]['id']]


def test_bundled_confirmation_and_disconnect(tmp_path):
    import time
    from nila.storage import Store
    from nila import google_connect as g
    store=Store(tmp_path)
    g.put(store,'confirm:all',{'token':{'access_token':'secret','email':'user@example.com'},'expires':time.time()+600})
    status=g.confirm(store,'all')
    assert all(s['connected'] for s in status['services'])
    g.disconnect(store,'gmail')
    assert not g.get(store,'token:gmail') and g.get(store,'token:docs')
    g.disconnect(store,'all')
    assert not any(s['connected'] for s in g.status(store)['services'])


def test_telegram_unauthorized_attachment_never_downloads(tmp_path,monkeypatch):
    import asyncio,time
    from nila.storage import Store
    from nila import telegram_bot as tg
    store=Store(tmp_path)
    async def forbidden(*args):raise AssertionError('No request from unauthorized chat')
    monkeypatch.setattr(tg,'download',forbidden)
    asyncio.run(tg.Bridge(store).handle({'chat_id':'123','enabled':True},{'message':{'date':time.time(),'chat':{'id':999,'type':'private'},'from':{'id':999},'document':{'file_id':'bad'}}}))


def test_telegram_download_rejects_traversal_and_oversize(monkeypatch):
    import asyncio
    from nila import telegram_bot as tg
    async def fake(*args):return {'file_path':'../private.txt'}
    monkeypatch.setattr(tg,'call',fake)
    with pytest.raises(tg.TelegramError,match='Invalid Telegram file path'):asyncio.run(tg.download('fake',{'file_id':'1'}))
    with pytest.raises(ValueError,match='5 MB'):asyncio.run(tg.download('fake',{'file_id':'1','file_size':6*1024*1024}))


def test_regeneration_does_not_repeat_google_write(tmp_path,monkeypatch):
    import asyncio
    from nila.storage import Store
    from nila import google_connect as g,engine
    from test_app import mock_ollama
    seen=mock_ollama(monkeypatch);store=Store(tmp_path);store.save_settings({'auto_memory':False})
    g.put(store,'token:gmail',{'scope':g.PREFIX+'gmail.send'})
    calls=[]
    async def fake(*args):calls.append(args);return {'id':'sent_1'}
    monkeypatch.setattr(actions,'execute',fake)
    cid=store.create_chat()['id']
    async def ask(**kw):return ''.join([s async for s in engine.reply(store,cid,'@Gmail send {"to":"person@example.com","text":"Hello"}',**kw)])
    asyncio.run(ask());mid=store.chat(cid)['messages'][-1]['id']
    asyncio.run(ask(regenerate_id=mid))
    assert len(calls)==1
    assert 'Regeneration never repeats Google writes' in json.dumps(seen[-1])
