"""Run against the real PHP router when PHP/cURL/SQLite/Sodium are available."""
import base64,hashlib,json,os,shutil,socket,sqlite3,subprocess,time
from pathlib import Path
import httpx,pytest

pytestmark = pytest.mark.skipif(os.name == 'nt', reason='PHP hosting is tested on Linux; Windows runs the local Nila client suite')

@pytest.fixture
def broker(tmp_path):
    php=shutil.which('php')
    if not php:pytest.skip('PHP runtime is not installed here; Linux CI runs this test')
    modules=subprocess.check_output([php,'-m'],text=True).lower()
    if any(x not in modules for x in ['pdo_sqlite','sodium','curl']):pytest.fail('PHP broker requires curl, pdo_sqlite and sodium')
    public=Path(__file__).resolve().parents[1]/'oauth-broker/public'
    subprocess.run([php,'-l',str(public/'index.php')],check=True,capture_output=True)
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    env=os.environ|{'GOOGLE_CLIENT_ID':'test.apps.googleusercontent.com','GOOGLE_CLIENT_SECRET':'fake-secret','NILA_BROKER_URL':'https://connect.example.test/index.php','NILA_PAIRING_KEY':'K'*43,'NILA_ENCRYPTION_KEY':base64.b64encode(b'E'*32).decode(),'NILA_DB_PATH':str(tmp_path/'sessions.sqlite')}
    process=subprocess.Popen([php,'-S',f'127.0.0.1:{port}','-t',str(public)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    client=httpx.Client(base_url=f'http://127.0.0.1:{port}/index.php',headers={'Authorization':'Bearer '+'K'*43},follow_redirects=False)
    try:
        for _ in range(100):
            try:
                if client.get('').status_code==200:break
            except httpx.HTTPError:pass
            time.sleep(.05)
        else:raise AssertionError('PHP did not start')
        yield client,env,php
    finally:client.close();process.terminate();process.wait(timeout=5)


def test_broker_auth_scope_state_denial_and_replay(broker):
    client,env,php=broker
    assert client.post('?action=start',json={},headers={'Authorization':'bad'}).status_code==401
    assert client.post('?action=start',json={'service':'admin','claim_secret':'C'*43}).status_code==400
    start=client.post('?action=start',json={'service':'gmail','claim_secret':'C'*43}).json();sid=start['id']
    assert 'K'*43 not in start['url'] and 'C'*43 not in start['url']
    assert client.post('?action=claim',json={'id':sid,'claim_secret':'WRONG'}).status_code==400
    assert client.post('?action=claim',json={'id':sid,'claim_secret':'C'*43}).json()=={'status':'pending'}
    auth=client.get('?action=authorize&id='+sid)
    assert auth.status_code==302 and auth.headers['location'].startswith('https://accounts.google.com/')
    from urllib.parse import urlsplit,parse_qs
    fields=parse_qs(urlsplit(auth.headers['location']).query)
    assert fields['state']==[sid] and 'gmail.readonly' in fields['scope'][0] and 'youtube' not in fields['scope'][0]
    assert 'httponly' in auth.headers['set-cookie'].lower() and 'secure' in auth.headers['set-cookie'].lower()
    assert client.get('?action=callback&state='+sid+'&error=access_denied').status_code==400
    cookie=auth.headers['set-cookie'].split(';')[0]
    denied=client.get('?action=callback&state='+sid+'&error=access_denied',headers={'Cookie':cookie})
    assert denied.status_code==200
    assert client.post('?action=claim',json={'id':sid,'claim_secret':'C'*43}).json()=={'status':'denied'}
    assert client.post('?action=claim',json={'id':sid,'claim_secret':'C'*43}).status_code==400
    assert 'no-store' in denied.headers['cache-control']


def test_encrypted_one_time_handoff_and_expiry(broker):
    client,env,php=broker
    start=client.post('?action=start',json={'service':'drive','claim_secret':'C'*43}).json();sid=start['id']
    script='$n=random_bytes(24); echo base64_encode($n.sodium_crypto_secretbox(json_encode(["access_token"=>"TEST_ACCESS","refresh_token"=>"TEST_REFRESH"]),$n,base64_decode(getenv("NILA_ENCRYPTION_KEY"))));'
    payload=subprocess.check_output([php,'-r',script],env=env,text=True)
    with sqlite3.connect(env['NILA_DB_PATH']) as db:
        db.execute("UPDATE sessions SET status='ready',payload=? WHERE id=?",(payload,sid))
    result=client.post('?action=claim',json={'id':sid,'claim_secret':'C'*43})
    assert result.json()['tokens']['access_token']=='TEST_ACCESS'
    assert client.post('?action=claim',json={'id':sid,'claim_secret':'C'*43}).status_code==400
    start=client.post('?action=start',json={'service':'drive','claim_secret':'C'*43}).json()
    with sqlite3.connect(env['NILA_DB_PATH']) as db:db.execute('UPDATE sessions SET expires=1')
    assert client.post('?action=claim',json={'id':start['id'],'claim_secret':'C'*43}).status_code==400
    assert b'TEST_ACCESS' not in Path(env['NILA_DB_PATH']).read_bytes()
