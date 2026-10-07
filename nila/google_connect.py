"""Opt-in, read-only Google access. Tokens are never part of model context."""
import asyncio
import json
import re
import secrets
import time
from urllib.parse import urlsplit, quote
import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

SERVICES = {
    'gmail': ('Gmail', 'gmail.readonly', 'Recent messages or one message'),
    'drive': ('Drive', 'drive.metadata.readonly', 'File names and metadata'),
    'docs': ('Docs', 'documents.readonly', 'Read a document by ID'),
    'sheets': ('Sheets', 'spreadsheets.readonly', 'Read spreadsheet cells by ID and range'),
    'classroom': ('Classroom', 'classroom.courses.readonly', 'Your courses'),
    'youtube': ('YouTube', 'youtube.readonly', 'Your channel and playlists'),
    'meet': ('Meet', 'meetings.space.readonly', 'Conference history'),
}
PREFIX = 'https://www.googleapis.com/auth/'


def get(store, name):
    with store.db() as db:
        db.execute('CREATE TABLE IF NOT EXISTS google_private(name TEXT PRIMARY KEY,value TEXT NOT NULL)')
        row = db.execute('SELECT value FROM google_private WHERE name=?', (name,)).fetchone()
    return json.loads(store.open(row[0])) if row else None


def put(store, name, value):
    get(store, name)
    with store.db() as db:
        if value is None:
            db.execute('DELETE FROM google_private WHERE name=?', (name,))
        else:
            db.execute('INSERT OR REPLACE INTO google_private VALUES (?,?)', (name, store.seal(json.dumps(value))))


def normalize_broker_url(value):
    value = value.strip()
    if not value or len(value) > 1000 or any(c.isspace() for c in value) or '\\' in value:
        raise ValueError('Enter your trusted OAuth website domain or HTTPS URL.')
    if '://' not in value:
        value = 'https://' + value
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Use an HTTPS domain without a query, fragment or embedded credentials.')
    try:
        port = parsed.port
        hostname = parsed.hostname.encode('idna').decode('ascii').lower()
    except (ValueError, UnicodeError):
        raise ValueError('Enter a valid HTTPS domain.') from None
    if not re.fullmatch(r'[a-z0-9.-]+', hostname) or '..' in hostname or hostname.startswith('.') or hostname.endswith('.'):
        raise ValueError('Enter a valid website hostname.')
    authority = hostname + (':' + str(port) if port and port != 443 else '')
    path = parsed.path.rstrip('/')
    if not path.endswith('.php'):
        path += '/index.php'
    if '%' in path or any(segment in {'.', '..'} for segment in path.split('/')):
        raise ValueError('Use a direct path to your PHP endpoint.')
    return 'https://' + authority + path


def configure(store, url, key):
    url = normalize_broker_url(url)
    if len(key) < 32 or len(key) > 256 or any(c.isspace() for c in key):
        raise ValueError('Enter the private deployment pairing key (32–256 characters).')
    current = get(store, 'config')
    if current and current['url'] != url:
        with store.db() as db:
            db.execute("DELETE FROM google_private WHERE name != 'config'")
    put(store, 'config', {'url': url, 'key': key})
    return status(store)


def write_scopes():
    from .google_actions import WRITE_SCOPES
    return WRITE_SCOPES

def status(store):
    config = get(store, 'config')
    return {'writes_enabled':bool(get(store,'writes_enabled')), 'configured': bool(config), 'url': config['url'] if config else '', 'callback_url': config['url'] + '?action=callback' if config else '', 'services': [
        {'id': key, 'name': meta[0], 'description': meta[2], 'scope': PREFIX + meta[1],
         'write_scope': PREFIX+write_scopes()[key] in (get(store,'token:'+key) or {}).get('scope','').split(),
         'connected': bool(get(store, 'token:' + key)), 'email': (get(store, 'token:' + key) or {}).get('email', '')}
        for key, meta in SERVICES.items()]}


async def broker(store, action, body):
    config = get(store, 'config')
    if not config:
        raise ValueError('Configure your trusted PHP OAuth broker first.')
    async with httpx.AsyncClient(timeout=40, follow_redirects=False) as client:
        try:
            response = await client.post(config['url'], params={'action': action}, json=body,
                                         headers={'Authorization': 'Bearer ' + config['key']})
            if 'text/html' in response.headers.get('content-type','').lower():
                raise ValueError('Your host returned a browser-only HTML page instead of the OAuth API. InfinityFree free hosting blocks app/API calls. Use an API-capable PHP host and upload the OAuth ZIP.')
            if response.status_code != 200:
                raise ValueError('OAuth broker rejected the request. Check the pairing key, server configuration or reconnect.')
            return response.json()
        except (httpx.HTTPError, json.JSONDecodeError):
            raise ValueError('OAuth broker is unavailable. Check its HTTPS URL and server configuration.') from None


async def check_connection(store):
    result = await broker(store, 'health', {})
    expected = get(store, 'config')['url'] + '?action=callback'
    if result.get('protocol') != 'nila-google-oauth' or result.get('version') != 1:
        raise ValueError('This website is not the compatible Nila OAuth ZIP. Upload the latest PHP package.')
    if result.get('redirect_uri') != expected:
        raise ValueError('Website domain mismatch. Set NILA_BROKER_URL on your PHP host to match the saved endpoint, and register its callback in Google Cloud.')
    return {'message': 'OAuth website connected. Choose a service and sign in with Google.', 'callback_url': expected}


def service_name(service):
    if service not in SERVICES and service not in {'all','all-write'}:
        raise ValueError('Choose one of the supported Google services.')


async def connect(store, service):
    service_name(service)
    secret = secrets.token_urlsafe(32)
    result = await broker(store, 'start', {'service': service, 'claim_secret': secret})
    url = urlsplit(result.get('url', ''))
    configured = urlsplit(get(store, 'config')['url'])
    if (url.scheme, url.netloc, url.path) != (configured.scheme, configured.netloc, configured.path):
        raise ValueError('Broker returned an unexpected login URL.')
    put(store, 'pending:' + service, {'id': result['id'], 'secret': secret, 'expires': time.time() + 600})
    return {'url': result['url'], 'expires_in': 600}


async def poll(store, service):
    service_name(service)
    pending = get(store, 'pending:' + service)
    if not pending or pending['expires'] < time.time():
        put(store, 'pending:' + service, None)
        raise ValueError('Connection expired. Select Connect again.')
    result = await broker(store, 'claim', {'id': pending['id'], 'claim_secret': pending['secret']})
    if result.get('status') == 'pending':
        return {'status': 'pending'}
    current = get(store, 'pending:' + service)
    if not current or current['id'] != pending['id']:
        raise ValueError('Connection was cancelled or replaced.')
    if result.get('status') != 'ready':
        put(store, 'pending:' + service, None)
        raise ValueError('Google sign-in was denied or expired. Select Connect to retry.')
    token = result['tokens']
    required=[PREFIX+v[1] for v in SERVICES.values()] if service.startswith('all') else [PREFIX+SERVICES[service][1]]
    if service=='all-write':
        from .google_actions import WRITE_SCOPES
        required += [PREFIX+x for x in WRITE_SCOPES.values()]
    if not set(required).issubset(token.get('scope', '').split()):
        raise ValueError('The requested permission was not granted. Reconnect and allow this service.')
    if not token.get('access_token') or not token.get('refresh_token'):
        raise ValueError('Offline permission was not returned. Reconnect with consent.')
    # User identity comes from Google, never an unverified JWT or the login URL.
    async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
        response = await client.get('https://openidconnect.googleapis.com/v1/userinfo', headers={'Authorization': 'Bearer ' + token['access_token']})
    if response.status_code != 200:
        raise ValueError('Could not verify the connected Google account. Reconnect.')
    identity = response.json()
    if not identity.get('sub') or not identity.get('email_verified'):
        raise ValueError('Google did not return a verified account.')
    token.update(email=identity['email'], expires_at=time.time() + int(token.get('expires_in', 3600)))
    current = get(store, 'pending:' + service)
    if not current or current['id'] != pending['id']:
        raise ValueError('Connection was cancelled or replaced.')
    put(store, 'pending:' + service, None)
    # Hold for an explicit local account confirmation before enabling reads.
    put(store, 'confirm:' + service, {'token': token, 'expires': time.time() + 600})
    return {'status': 'confirm', 'email': identity['email']}


def confirm(store, service):
    service_name(service)
    value = get(store, 'confirm:' + service)
    if not value or value['expires'] < time.time():
        put(store, 'confirm:' + service, None)
        raise ValueError('Account confirmation expired. Reconnect.')
    for key in SERVICES if service.startswith('all') else [service]:
        put(store, 'token:' + key, value['token'])
    put(store, 'confirm:' + service, None)
    return status(store)


def disconnect(store, service):
    service_name(service)
    for key in list(SERVICES)+['all','all-write'] if service.startswith('all') else [service]:
        for prefix in ('token:', 'pending:', 'confirm:'):
            put(store, prefix + key, None)
    return status(store)


async def access_token(store, service, force=False):
    token = get(store, 'token:' + service)
    if not token:
        raise ValueError('Connect and confirm this Google service first.')
    if force or token['expires_at'] < time.time() + 90:
        updated = await broker(store, 'refresh', {'refresh_token': token['refresh_token']})
        if not updated.get('access_token'):
            raise ValueError('Google permission expired or was revoked. Reconnect this service.')
        token.update(access_token=updated['access_token'], expires_at=time.time() + int(updated.get('expires_in', 3600)))
        # A concurrent Disconnect must not resurrect a connection.
        if (get(store, 'token:' + service) or {}).get('refresh_token') != token['refresh_token']:
            raise ValueError('Google connection was disconnected.')
        put(store, 'token:' + service, token)
    return token['access_token']


def endpoint(service, item='', cell_range='A1:Z100', page_token='', gmail_query=''):
    if service not in SERVICES:raise ValueError('Choose an individual service to read')
    service_name(service)
    item_pattern = r'(?:(?:video|playlist):)?[A-Za-z0-9_-]{1,180}' if service == 'youtube' else r'[A-Za-z0-9_-]{1,180}'
    if item and not re.fullmatch(item_pattern, item):
        raise ValueError('Enter the item ID, not its full URL.')
    params = {}
    if service == 'gmail':
        url = 'https://gmail.googleapis.com/gmail/v1/users/me/messages'
        if item:
            url += '/' + item
            params = {'format': 'full'}
        else:
            params = {'maxResults': 20, 'labelIds': 'INBOX'}
            if gmail_query:
                if not re.fullmatch(r'(?:after:[0-9]{1,12})(?: is:unread)?|is:unread',gmail_query):raise ValueError('Unsupported Gmail filter')
                params['q']=gmail_query
    elif service == 'drive':
        url = 'https://www.googleapis.com/drive/v3/files' + ('/' + item if item else '')
        params = {'fields': 'id,name,mimeType,webViewLink,modifiedTime,size'} if item else {'pageSize': 20, 'q': 'trashed = false', 'fields': 'nextPageToken,files(id,name,mimeType,webViewLink,modifiedTime)', 'orderBy': 'modifiedTime desc'}
    elif service == 'docs':
        if not item: raise ValueError('Enter a Google document ID.')
        url = 'https://docs.googleapis.com/v1/documents/' + item
        params = {'includeTabsContent': 'true'}
    elif service == 'sheets':
        if not item: raise ValueError('Enter a spreadsheet ID and cell range.')
        if not cell_range or len(cell_range) > 200: raise ValueError('Enter a cell range of at most 200 characters.')
        url = 'https://sheets.googleapis.com/v4/spreadsheets/' + item + '/values/' + quote(cell_range, safe='')
    elif service == 'classroom':
        url = 'https://classroom.googleapis.com/v1/courses' + ('/' + item if item else '')
        params = {} if item else {'pageSize': 20}
    elif service == 'youtube':
        resource = 'videos' if item.startswith('video:') else 'playlists' if item == 'playlists' or item.startswith('playlist:') else 'channels'
        url = 'https://www.googleapis.com/youtube/v3/' + resource
        params = {'part': 'snippet,contentDetails' + (',statistics' if resource in {'channels','videos'} else '')}
        if resource != 'videos': params['maxResults'] = 20
        params.update({'id': item.split(':',1)[-1]} if item and item != 'playlists' else {'mine': 'true'})
    else:
        url = 'https://meet.googleapis.com/v2/conferenceRecords' + ('/' + item if item else '')
        params = {} if item else {'pageSize': 20}
    if page_token and not item and service not in {'docs', 'sheets'}: params['pageToken'] = page_token
    return url, params


async def read(store, service, item='', cell_range='A1:Z100', page_token='', gmail_query=''):
    url, params = endpoint(service, item, cell_range, page_token, gmail_query)
    for attempt in range(2):
        token = await access_token(store, service, force=attempt > 0)
        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
            async with client.stream('GET', url, params=params, headers={'Authorization': 'Bearer ' + token}) as response:
                if response.status_code == 401 and not attempt: continue
                if response.status_code != 200:
                    raise ValueError('Google could not read this item. Check its ID, account permission, enabled API and quota.')
                raw = bytearray()
                async for part in response.aiter_bytes():
                    raw.extend(part)
                    if len(raw) > 2_000_000: raise ValueError('Result is too large. Read a smaller item or cell range.')
        if (get(store, 'token:' + service) or {}).get('access_token') != token: raise ValueError('Google connection changed. Read again.')
        result = json.loads(raw)
        if service == 'gmail' and item:
            import base64
            def text_parts(part):
                text = []
                if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
                    encoded = part['body']['data']
                    try: text.append(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)).decode('utf-8', 'replace'))
                    except (ValueError, TypeError): pass
                for child in part.get('parts', []): text.extend(text_parts(child))
                return text
            headers = [h['name'] + ': ' + h['value'] for h in result.get('payload', {}).get('headers', []) if h['name'].lower() in {'from','to','subject','date'}]
            result['readable_text'] = '\n'.join(headers + text_parts(result.get('payload', {}))) or result.get('snippet', '')
        elif service == 'docs':
            def doc_text(value):
                if isinstance(value, dict):
                    if 'textRun' in value: return value['textRun'].get('content', '')
                    return ''.join(doc_text(v) for v in value.values())
                if isinstance(value, list): return ''.join(doc_text(v) for v in value)
                return ''
            result['readable_text'] = result.get('title', 'Document') + '\n' + doc_text(result.get('tabs', result.get('body', {})))
        elif service == 'sheets':
            result['readable_text'] = result.get('range', '') + '\n' + '\n'.join('\t'.join(str(c) for c in row) for row in result.get('values', []))
        # Deliberately no memory write, Gemini call or model invocation here.
        return result
    raise ValueError('Reconnect this Google service.')


def register(app, store):
    class Config(BaseModel):
        url: str = Field(max_length=1000)
        key: str = Field(min_length=32, max_length=256)
    class Read(BaseModel):
        item: str = Field(default='', max_length=180)
        cell_range: str = Field(default='A1:Z100', max_length=200)
        page_token: str = Field(default='', max_length=2048)
    class Import(BaseModel):
        text: str = Field(min_length=1, max_length=450000)
        service: str
    async def guarded(fn, *args):
        try: return await fn(*args)
        except (ValueError, KeyError, httpx.HTTPError):
            # ValueError messages are controlled; network exceptions can contain sensitive URLs.
            import sys
            error = sys.exception()
            raise HTTPException(400, str(error) if isinstance(error, ValueError) and not isinstance(error, json.JSONDecodeError) else 'Google connection failed. Reconnect and retry.') from None
    class WritePermission(BaseModel):
        enabled:bool
    @app.put('/api/google/write-permission')
    async def write_permission(body:WritePermission):
        put(store,'writes_enabled',body.enabled)
        return status(store)
    @app.get('/api/google')
    async def google_status(): return status(store)
    @app.put('/api/google/config')
    async def google_config(body: Config):
        try: return configure(store, body.url, body.key)
        except ValueError as e: raise HTTPException(400, str(e)) from None
    @app.post('/api/google/check')
    async def google_check(): return await guarded(check_connection, store)
    @app.post('/api/google/{service}/connect')
    async def google_connect(service: str): return await guarded(connect, store, service)
    @app.post('/api/google/{service}/poll')
    async def google_poll(service: str): return await guarded(poll, store, service)
    @app.post('/api/google/{service}/confirm')
    async def google_confirm(service: str):
        try: return confirm(store, service)
        except ValueError as e: raise HTTPException(400, str(e)) from None
    @app.delete('/api/google/{service}')
    async def google_disconnect(service: str):
        try: return disconnect(store, service)
        except ValueError as e: raise HTTPException(400, str(e)) from None
    @app.post('/api/google/{service}/read')
    async def google_read(service: str, body: Read): return await guarded(read, store, service, body.item, body.cell_range, body.page_token)
    @app.post('/api/google/import/chat')
    async def google_import(body: Import):
        from . import workspace as ws
        try:
            service_name(body.service)
            # Import only on this explicit click; raw provider text is treated as untrusted document content.
            iid = ws.ingest(store, 'Google-' + body.service + '.txt', body.text.encode())
            chat = store.create_chat()
            ws.attach(store, chat['id'], [iid])
            return {'chat_id': chat['id']}
        except ValueError as e: raise HTTPException(400, str(e)) from None
