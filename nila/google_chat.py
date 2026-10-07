"""Bounded, read-only Google tools selected from the user's current request.

Provider text, memories and model output can never schedule a tool call.
"""
import json
import time
import httpx
import re
from urllib.parse import urlsplit, parse_qs
from . import google_connect as google

ALIASES = {
    'gmail': r'\b(gmail|inbox|emails?|mailbox)\b|ജിമെയിൽ|ഇമെയിൽ',
    'drive': r'\b(google\s+drive|drive\s+files?)\b|ഗൂഗിൾ\s*ഡ്രൈവ്',
    'docs': r'\b(google\s+docs?|docs?)\b|ഗൂഗിൾ\s*ഡോക്',
    'sheets': r'\b(google\s+sheets?|spreadsheet|sheets?)\b|സ്പ്രെഡ്ഷീറ്റ്|ഗൂഗിൾ\s*ഷീറ്റ്',
    'classroom': r'\b(classroom)\b|ക്ലാസ്\s*റൂം',
    'youtube': r'\b(youtube|you\s+tube)\b|യൂട്യൂബ്',
    'meet': r'\b(google\s+meet|meet\s+history|meet\s+meetings?|meeting\s+history)\b|ഗൂഗിൾ\s*മീറ്റ്|മീറ്റ്\s*ഹിസ്റ്ററി',
}
OWNER = r'\b(my|our|ente|enikku|enike|enik|nammude)\b|എന്റെ|എൻ്റെ|എനിക്ക്|നമ്മുടെ'
READ = r'\b(read|show|list|summari[sz]e|check|fetch|open|get|view|kanikk|kaanikk|kanich|nokk|vayikk|summary|details)\w*\b|കാണി|വായി|ചുരുക്കി|പരിശോധി|സംഗ്രഹി'
WRITE = r'^\s*(?:please\s+)?(?:send|delete|edit|update|create|schedule|join|publish|upload|write|remove)\b|\b(?:send|delete|edit|create|join|upload)\s+(?:my|a|an|the|this|that|ente)\b'


def previous_sources(store, history):
    for message in reversed(history):
        if message['role'] != 'assistant' or message['status'] != 'complete': continue
        with store.db() as db:
            row = db.execute('SELECT content FROM answer_sources WHERE message_id=?', (message['id'],)).fetchone()
        refs = json.loads(store.open(row[0])) if row else []
        return [r for r in refs if r.get('kind') == 'google' and r.get('service') in google.SERVICES]
    return []


def plan(prompt, previous=()):
    """Explicit service reads or supported URLs; ordinary product questions stay local."""
    from .google_actions import parse
    write=parse(prompt)
    if write:
        service,action,data=write
        return [{'service':service,'write_action':action,'write_data':data}]
    lower = prompt.lower()
    words = re.sub(r'https?://\S+', '', lower)
    mentions=re.findall(r'@([a-z]+)\b',words)
    services = [key for key, pattern in ALIASES.items() if re.search(pattern, words)]
    services=list(dict.fromkeys(services+[x for x in mentions if x in google.SERVICES]))
    read_intent=bool(re.search(READ,lower) or (mentions and re.search(r'\b(latest|recent|unread|last)\b',lower)))
    targets = {}
    for raw in re.findall(r'https?://[^\s<>"\)]+', prompt):
        parsed = urlsplit(raw.rstrip('.,;'))
        host = (parsed.hostname or '').lower()
        if parsed.username or parsed.password: continue
        path = parsed.path
        for kind, segment in [('docs','document'),('sheets','spreadsheets')]:
            match = re.search(r'^/'+segment+r'/d/([A-Za-z0-9_-]+)', path)
            if host == 'docs.google.com' and match: targets[kind] = match[1]
        if host == 'drive.google.com':
            match = re.search(r'^/file/d/([A-Za-z0-9_-]+)', path)
            if match: targets['drive'] = match[1]
        if host in {'www.youtube.com','youtube.com','m.youtube.com','youtu.be'}:
            query = parse_qs(parsed.query)
            if host == 'youtu.be': targets['youtube'] = 'video:' + path.strip('/')
            elif query.get('v'): targets['youtube'] = 'video:' + query['v'][0]
            elif query.get('list'): targets['youtube'] = 'playlist:' + query['list'][0]
            elif path.startswith('/shorts/'): targets['youtube'] = 'video:' + path.split('/')[2]
            elif path.startswith('/channel/'): targets['youtube'] = path.split('/')[2]
        if host == 'meet.google.com': targets['meet'] = 'meeting-link'
    if mentions and services and not targets and not (read_intent or re.search(WRITE,lower)):
        return [{'service':services[0],'error':'Specify what to read or write from the mentioned service.'}]
    if not targets and not (services and (re.search(OWNER,lower) or read_intent or re.search(WRITE,lower))):
        if len(previous)==1 and re.fullmatch(r'\s*(?:please\s+)?(?:summari[sz]e|read|explain|open)\s+(?:it|that|this)(?:\s+(?:again|in detail))?[.!?\s]*', lower):
            ref=previous[0];return [{'service':ref['service'],'item':ref.get('item',''),'cell_range':ref.get('cell_range','A1:Z100')}]
        return []
    if re.match(r'^\s*(what is|what are|how (?:do|does|can|to)|explain what|define)\b',lower) and not targets:
        return []
    services=list(dict.fromkeys(list(targets)+services))
    if len(services)>2:return [{'service':services[0], 'error':'Ask for at most two Google services in one request.'}]
    result=[]
    for service in services:
        item=targets.get(service,'')
        explicit=re.search(r'\b(?:document|spreadsheet|message|file|record|course)?\s*id\s*[:=]\s*([A-Za-z0-9_-]{1,180})\b',prompt,re.I)
        if not item and explicit:item=explicit[1]
        if service=='youtube' and not item and re.search(r'playlist|പ്ലേലിസ്റ്റ്',lower):item='playlists'
        cell_range='A1:Z100'
        match=re.search(r"(?:\b[A-Za-z0-9_]+!)?\$?[A-Z]{1,3}\$?[0-9]+:\$?[A-Z]{1,3}\$?[0-9]+",prompt)
        if match:cell_range=match[0]
        spec={'service':service,'item':item,'cell_range':cell_range}
        if service=='gmail' and not item:
            filters=[]
            window=re.search(r'\b(?:last|past)\s+(\d{1,4})\s*(minutes?|mins?|hours?|hrs?|days?)\b',lower)
            if window:
                amount=int(window[1]);unit=window[2]
                seconds=amount*(60 if unit.startswith('min') else 3600 if unit.startswith(('h','hr')) else 86400)
                if 0<seconds<=31*86400:filters.append('after:'+str(int(time.time())-seconds))
                else:spec['error']='Choose a time window greater than zero and at most 31 days.'
            if re.search(r'\bunread\b',lower):filters.append('is:unread')
            if filters:spec['gmail_query']=' '.join(filters)

        if re.search(r"\b(do not|don't|dont|never|without|avoid|venda|vayikkaruth)\b|വേണ്ട|വായിക്കരുത്|ഉപയോഗിക്കരുത്",lower):spec['error']='The user requested no Google access. No account data was read.'
        elif re.search(WRITE,lower) or re.search(r'അയക്കു|ഡിലീറ്റ്|എഡിറ്റ്|സൃഷ്ടി|ചേരുക',lower):spec['error']='Ordinary requests are read-only when write details are incomplete. Provide an explicit @Service action with complete quoted or JSON details. No email was sent, file edited, meeting created or call joined.'
        elif service in {'docs','sheets'} and not item:spec['error']='Ask the user for the Google document/spreadsheet URL or ID (id: ...). Do not guess an item.'
        elif service=='meet' and item=='meeting-link':spec['error']='A Meet invite link is not a conference record ID. Ask for Meet history or a conference record ID. Nila cannot join live calls.'
        elif service=='classroom' and re.search(r'assignment|coursework|homework',lower):spec['error']='This connection supports course metadata only, not assignments or coursework.'
        result.append(spec)
    return result


def compact(service, data):
    """Keep useful text, not base64 mail bodies or huge provider response trees."""
    if data.get('readable_text'):
        return {'text':data['readable_text'][:8000], 'truncated':len(data['readable_text'])>8000}
    if service=='youtube':
        return {'items':[{'id':r.get('id'),'title':r.get('snippet',{}).get('title'),'description':r.get('snippet',{}).get('description','')[:1200],'statistics':r.get('statistics',{}),'contentDetails':r.get('contentDetails',{})} for r in data.get('items',[])[:10]],'more_available':bool(data.get('nextPageToken'))}
    collection={'gmail':'messages','drive':'files','classroom':'courses','meet':'conferenceRecords'}.get(service)
    if collection and collection in data:return {collection:data[collection][:10], 'more_available':bool(data.get('nextPageToken'))}
    return data


def link(service,item):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,180}',item):return ''
    if service=='docs':return 'https://docs.google.com/document/d/'+item+'/edit'
    if service=='sheets':return 'https://docs.google.com/spreadsheets/d/'+item+'/edit'
    if service=='drive':return 'https://drive.google.com/file/d/'+item+'/view'
    return ''


async def gather(store, specs, allowed=True, progress=None, stop=None):
    evidence=[];sources=[]
    for spec in specs:
        if stop and stop.is_set():break
        service=spec['service'];name=google.SERVICES[service][0]
        error=spec.get('error')
        if not allowed:error='Google account reads are disabled on this channel. Use a normal local Web or CLI chat.'
        elif store.ephemeral:error='Connect Google in a normal saved chat. Temporary chats do not access saved Google credentials.'
        elif not error and not google.get(store,'token:'+service):error='Connect '+name+' first in Workspace → Google, or run nila google connect '+service+'.'
        if spec.get('write_action') and not error:
            from .google_actions import execute
            if spec.get('write_data') is None:error='Invalid write details. Provide a complete JSON object; no action was taken.'
            else:
                try:
                    result=await execute(store,service,spec['write_action'],spec['write_data'])
                    evidence.append({'service':name,'status':'written','action':spec['write_action'],'result':result})
                    continue
                except (ValueError, httpx.HTTPError):error='Write failed or permission missing. Enable writes and reconnect with write permissions. Check the service before retrying; no automatic retry was made.'
        if error:evidence.append({'service':name,'status':'not_read','reason':error});continue
        if progress:progress('Reading '+name+' securely')
        try:
            item=spec.get('item','');cell_range=spec.get('cell_range','A1:Z100')
            data=await google.read(store,service,item,cell_range,**({'gmail_query':spec['gmail_query']} if spec.get('gmail_query') else {}))
            if service=='gmail' and not item:
                # Bounded preview of the five messages returned by the inbox list, never an unrestricted mailbox crawl.
                previews=[]
                for row in data.get('messages',[])[:5]:
                    if stop and stop.is_set():break
                    message=await google.read(store,'gmail',row['id'])
                    previews.append({'id':row['id'],'text':message.get('readable_text',message.get('snippet',''))[:1600]})
                data={'messages':previews,'limited_to_first_five':True,'more_available':bool(data.get('nextPageToken'))}
            evidence.append({'service':name,'status':'read','data':compact(service,data), 'limits':'Read-only, bounded preview. Drive and Meet return metadata; YouTube returns metadata/description, NOT video audio or transcripts.'})
            source={'kind':'google','service':service,'item':item,'cell_range':cell_range,'label':name+' · connected account'}
            url=link(service,item)
            if url:source['url']=url
            if service=='youtube' and item.startswith('video:'):
                source['url']='https://www.youtube.com/watch?v='+item[6:]
            sources.append(source)
        except (ValueError, KeyError):
            evidence.append({'service':name,'status':'not_read','reason':'Google could not read this item. Check the connection, permission and item ID in Workspace → Google. No data was retrieved for this request.'})
        except Exception as exc:
            if not isinstance(exc,httpx.HTTPError):raise
            evidence.append({'service':name,'status':'not_read','reason':'Google is unavailable. Try again when online; do not invent account data.'})
    text=json.dumps(evidence,ensure_ascii=False)
    # Bound private context for small local models; clearly mark clipping.
    if len(text)>8000:text=text[:8000]+'\n[Preview truncated; remaining data was not included.]'
    return text,sources
