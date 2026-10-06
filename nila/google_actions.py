"""Explicit user-authored, bounded Google writes. Never execute model-generated actions."""
import base64,json,re
from email.message import EmailMessage
from urllib.parse import quote
import httpx
from . import google_connect as g

WRITE_SCOPES={'gmail':'gmail.send','docs':'documents','sheets':'spreadsheets','drive':'drive.file','classroom':'classroom.courses','youtube':'youtube.force-ssl','meet':'meetings.space.created'}

def endpoint(service,action,data):
    item=data.get('id','')
    if item and not re.fullmatch(r'[A-Za-z0-9_-]{1,180}',item):raise ValueError('Invalid Google item ID')
    text=data.get('text','')
    if not isinstance(text,str) or len(text)>12000:raise ValueError('Text limit: 12,000 characters')
    if service=='gmail' and action=='send':
        recipient=data.get('to','');subject=data.get('subject','')
        if not isinstance(recipient,str) or not re.fullmatch(r'[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+',recipient):raise ValueError('Provide one exact recipient email in to')
        if not isinstance(subject,str) or '\n' in subject or '\r' in subject or len(subject)>200:raise ValueError('Invalid subject')
        mail=EmailMessage();mail['To']=recipient;mail['Subject']=subject;mail.set_content(text)
        return 'POST','https://gmail.googleapis.com/gmail/v1/users/me/messages/send',{'raw':base64.urlsafe_b64encode(mail.as_bytes()).decode()}
    if service=='docs' and action=='append' and item:
        return 'POST','https://docs.googleapis.com/v1/documents/'+item+':batchUpdate',{'requests':[{'insertText':{'endOfSegmentLocation':{},'text':text}}]}
    if service=='sheets' and action=='update' and item:
        cells=data.get('values');cell_range=data.get('range','A1')
        if not isinstance(cells,list) or not cells or len(cells)>100 or any(not isinstance(row,list) or len(row)>26 or any(not isinstance(v,(str,int,float,bool)) or len(str(v))>1000 for v in row) for row in cells):raise ValueError('Provide values as rows, up to 100 × 26 cells')
        if not isinstance(cell_range,str) or not re.fullmatch(r'(?:[A-Za-z0-9_]+!)?[A-Z]{1,3}[1-9][0-9]*(?::[A-Z]{1,3}[1-9][0-9]*)?',cell_range):raise ValueError('Provide an A1 range')
        return 'PUT','https://sheets.googleapis.com/v4/spreadsheets/'+item+'/values/'+quote(cell_range,safe='')+'?valueInputOption=RAW',{'values':cells}
    if service=='drive' and action=='create':
        name=data.get('name','')
        if not isinstance(name,str) or not name.strip() or len(name)>160:raise ValueError('Provide a file name')
        return 'POST','https://www.googleapis.com/drive/v3/files',{'name':name,'mimeType':'application/vnd.google-apps.document'}
    if service=='classroom' and action=='create':
        name=data.get('name','')
        if not isinstance(name,str) or not name.strip() or len(name)>160:raise ValueError('Provide a course name')
        return 'POST','https://classroom.googleapis.com/v1/courses',{'name':name,'ownerId':'me','courseState':'PROVISIONED'}
    if service=='youtube' and action=='comment' and item:
        return 'POST','https://www.googleapis.com/youtube/v3/commentThreads?part=snippet',{'snippet':{'videoId':item,'topLevelComment':{'snippet':{'textOriginal':text}}}}
    if service=='meet' and action=='create':return 'POST','https://meet.googleapis.com/v2/spaces',{}
    raise ValueError('Supported writes: Gmail send, Docs append, Sheets update, Drive create document, Classroom create course, YouTube comment, Meet create space.')

async def execute(store,service,action,data):
    token=g.get(store,'token:'+service) or {}
    if not token:raise ValueError('Connect this Google service first')
    if not g.get(store,'writes_enabled'):raise ValueError('Enable Google writes once in Google connections settings first')
    if g.PREFIX+WRITE_SCOPES[service] not in token.get('scope','').split():raise ValueError('Reconnect with read/write permission first')
    method,url,body=endpoint(service,action,data)
    access=await g.access_token(store,service)
    async with httpx.AsyncClient(timeout=30,follow_redirects=False) as client:
        response=await client.request(method,url,json=body,headers={'Authorization':'Bearer '+access})
    if response.status_code not in {200,201}:raise ValueError('Google rejected this write. No automatic retry was made; check the service before retrying.')
    result=response.json()
    return {k:result[k] for k in ('id','name','meetingUri','updatedCells') if k in result}

def parse(prompt):
    prompt=re.sub(r'^\s*(Gmail|Docs|Sheets|Drive|Classroom|YouTube|Meet)\b',r'@\1',prompt,flags=re.I)
    match=re.fullmatch(r'\s*@([A-Za-z]+)\s+(send|append|update|create|comment)\s+(\{.*\})\s*',prompt,re.S)
    if not match:
        # Extract only literal user-provided values; never invent a recipient or message.
        mail=re.fullmatch(r'\s*@Gmail\s+send\s+(?:email\s+)?to\s+([^\s]+)\s+subject\s+"([^"\r\n]*)"\s+(?:body|message)\s+"([\s\S]*)"\s*',prompt,re.I)
        if mail:return 'gmail','send',{'to':mail[1],'subject':mail[2],'text':mail[3]}
        doc=re.fullmatch(r'\s*@Docs\s+append\s+"([\s\S]*)"\s+(?:to\s+)?(?:https://docs.google.com/document/d/|id:\s*)([A-Za-z0-9_-]+)(?:/edit)?\s*',prompt,re.I)
        if doc:return 'docs','append',{'text':doc[1],'id':doc[2]}
        meet=re.fullmatch(r'\s*(?:@Meet|Google Meet)\s+create\s+(?:a\s+)?(?:meeting|space)(?:\s+link)?[.!\s]*',prompt,re.I)
        if meet:return 'meet','create',{}
        return None
    service,action,raw=match.groups();service=service.lower()
    if service not in WRITE_SCOPES:return None
    try:
        data=json.loads(raw)
        if not isinstance(data,dict):raise ValueError('Provide a JSON object')
        endpoint(service,action,data)
        return service,action,data
    except (ValueError,TypeError):return service,action,None
