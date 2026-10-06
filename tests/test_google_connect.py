import asyncio, json, time
import httpx, pytest
from fastapi.testclient import TestClient
from nila.storage import Store
from nila.server import create_app
from nila import google_connect as g


def config(store):
    return g.configure(store,'https://connect.example.test/index.php','K'*43)


def token(store, service='gmail', expired=False):
    g.put(store,'token:'+service,{'access_token':'ACCESS_SECRET','refresh_token':'REFRESH_SECRET','email':'user@example.test','expires_at':0 if expired else time.time()+3600})


def test_config_and_credentials_are_encrypted_and_absent_from_settings(tmp_path):
    store=Store(tmp_path);config(store);token(store)
    result=g.status(store)
    assert result['services'][0]['connected']
    assert 'ACCESS_SECRET' not in json.dumps(result) and 'K'*43 not in json.dumps(result)
    assert 'google' not in str(store.settings())
    with store.db() as db:
        raw=str([tuple(r) for r in db.execute('SELECT * FROM google_private')])
    assert 'ACCESS_SECRET' not in raw and 'REFRESH_SECRET' not in raw and 'K'*43 not in raw
    for url in ['http://localhost/a','https://user:password@example.test','https://example.test/a?q=secret']:
        with pytest.raises(ValueError):g.configure(store,url,'K'*43)
    g.configure(store,'https://other.example.test/index.php','K'*43)
    assert not g.status(store)['services'][0]['connected']


def test_confirm_account_before_any_read_and_remove_pending_on_disconnect(tmp_path,monkeypatch):
    store=Store(tmp_path);config(store)
    calls=[]
    async def broker(store,action,body):
        calls.append((action,body))
        if action=='start':return {'id':'abc','url':'https://connect.example.test/index.php?action=authorize&id=abc'}
        return {'status':'ready','tokens':{'access_token':'ACCESS','refresh_token':'REFRESH','scope':g.PREFIX+'gmail.readonly','expires_in':3600}}
    monkeypatch.setattr(g,'broker',broker)
    original=httpx.AsyncClient
    def handler(req):
        assert str(req.url)=='https://openidconnect.googleapis.com/v1/userinfo'
        return httpx.Response(200,json={'sub':'123','email':'me@example.test','email_verified':True})
    monkeypatch.setattr(g.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    asyncio.run(g.connect(store,'gmail'))
    assert len(calls[0][1]['claim_secret'])>=43
    result=asyncio.run(g.poll(store,'gmail'));assert result=={'status':'confirm','email':'me@example.test'}
    with pytest.raises(ValueError):asyncio.run(g.access_token(store,'gmail'))
    g.confirm(store,'gmail');assert g.status(store)['services'][0]['connected']
    g.disconnect(store,'gmail');assert not g.status(store)['services'][0]['connected']
    assert g.get(store,'pending:gmail') is None and g.get(store,'confirm:gmail') is None


def test_missing_scope_and_expired_connection_rejected(tmp_path,monkeypatch):
    store=Store(tmp_path);config(store)
    g.put(store,'pending:gmail',{'id':'id','secret':'secret','expires':time.time()-1})
    with pytest.raises(ValueError,match='expired'):asyncio.run(g.poll(store,'gmail'))
    g.put(store,'pending:gmail',{'id':'id','secret':'secret','expires':time.time()+100})
    async def broker(*a):return {'status':'ready','tokens':{'scope':g.PREFIX+'youtube.readonly'}}
    monkeypatch.setattr(g,'broker',broker)
    with pytest.raises(ValueError,match='permission'):asyncio.run(g.poll(store,'gmail'))
    assert g.get(store,'token:gmail') is None


def test_refresh_retry_readonly_and_no_automatic_memory_or_chat(tmp_path,monkeypatch):
    store=Store(tmp_path);config(store);token(store,'sheets');seen=[]
    async def broker(store,action,body):
        assert action=='refresh' and body=={'refresh_token':'REFRESH_SECRET'}
        return {'access_token':'NEW_ACCESS','expires_in':3600}
    monkeypatch.setattr(g,'broker',broker)
    original=httpx.AsyncClient
    def handler(req):
        seen.append(req)
        if len(seen)==1:return httpx.Response(401)
        assert req.method=='GET' and req.url.host=='sheets.googleapis.com'
        assert req.headers['authorization']=='Bearer NEW_ACCESS'
        return httpx.Response(200,json={'range':'A1:B1','values':[['PRIVATE_SHEET','hello']]})
    monkeypatch.setattr(g.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    result=asyncio.run(g.read(store,'sheets','spreadsheet_id','A1:B1'))
    assert 'PRIVATE_SHEET' in result['readable_text']
    assert len(seen)==2 and not store.chats() and not store.items('memories')
    with store.db() as db:assert db.execute('SELECT COUNT(*) FROM documents').fetchone()[0]==0
    with pytest.raises(ValueError):g.endpoint('docs','https://evil.test')
    with pytest.raises(ValueError):g.endpoint('write','abc')


def test_all_services_have_fixed_read_endpoints():
    for service in g.SERVICES:
        url,params=g.endpoint(service,'abc' if service in {'docs','sheets'} else '')
        assert url.startswith('https://') and urlsplit_host(url).endswith('googleapis.com')
    assert 'readonly' in str(g.SERVICES)


def urlsplit_host(url):
    from urllib.parse import urlsplit
    return urlsplit(url).hostname


def test_local_routes_never_expose_secrets_and_import_is_explicit(tmp_path):
    store=Store(tmp_path);config(store);token(store)
    client=TestClient(create_app(store))
    assert 'ACCESS_SECRET' not in client.get('/api/google').text
    assert client.post('/api/google/gmail/read',json={},headers={'Origin':'https://evil.test'}).status_code==403
    result=client.post('/api/google/import/chat',json={'service':'gmail','text':'PRIVATE_PREVIEW'}).json()
    assert store.chat(result['chat_id'])['id'] == result['chat_id']
    with store.db() as db:
        row=db.execute('SELECT pages FROM documents').fetchone()
        assert 'PRIVATE_PREVIEW' not in row[0] and 'PRIVATE_PREVIEW' in store.open(row[0])
    assert client.delete('/api/google/gmail').status_code==200
    assert client.get('/api/google').json()['services'][0]['connected'] is False


def test_disconnect_during_refresh_does_not_restore_token(tmp_path,monkeypatch):
    store=Store(tmp_path);config(store);token(store,expired=True)
    async def broker(*args):
        g.disconnect(store,'gmail');return {'access_token':'late','expires_in':3600}
    monkeypatch.setattr(g,'broker',broker)
    with pytest.raises(ValueError,match='disconnected'):asyncio.run(g.access_token(store,'gmail'))
    assert not g.get(store,'token:gmail')


def test_disconnect_during_poll_cannot_add_confirmation(tmp_path,monkeypatch):
    store=Store(tmp_path);config(store)
    g.put(store,'pending:gmail',{'id':'a','secret':'s','expires':time.time()+600})
    async def broker(*args):
        g.disconnect(store,'gmail')
        return {'status':'ready','tokens':{}}
    monkeypatch.setattr(g,'broker',broker)
    with pytest.raises(ValueError,match='cancelled'):asyncio.run(g.poll(store,'gmail'))
    assert g.get(store,'confirm:gmail') is None
