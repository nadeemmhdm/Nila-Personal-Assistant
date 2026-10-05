"""Local workspace API; cloud reviewers never receive these objects."""
import asyncio,base64,time
from fastapi import HTTPException,Body
from fastapi.responses import Response
from pydantic import BaseModel,Field
from typing import Literal
from . import workspace as ws
from .automation import Job

class TelegramConfig(BaseModel):
    token:str=Field(default='',max_length=230)
    chat_id:str=Field(pattern=r'^[1-9][0-9]{0,18}$')
    enabled:bool=False
    share_memory:bool=False

class Project(BaseModel):
    name:str=Field(min_length=1,max_length=100)
    instructions:str=Field(default='',max_length=3000)
class Attachment(BaseModel):
    ids:list[str]=Field(default_factory=list,max_length=10)
class Upload(BaseModel):
    name:str=Field(min_length=1,max_length=160)
    data:str=Field(max_length=7000000)
    project_id:str|None=None
class BackupRequest(BaseModel):
    password:str=Field(min_length=12,max_length=256)
    data:str=Field(default='',max_length=28000000)
    apply:bool=False
class Decision(BaseModel):
    approve:bool
    content:str=Field(default='',max_length=2000)
class FeedbackEdit(BaseModel):
    reason:str=Field(max_length=500)
    rating:Literal[-1,1]=-1

async def setup_status(store):
    import psutil
    from .extensions import diagnostics
    status=await diagnostics(store);ram=psutil.virtual_memory()
    candidates=[]
    for m in status['models']:
        size=m.get('size',0);estimated=size*1.4+1024**3
        candidates.append({'name':m['name'],'size_gb':round(size/1024**3,2),'estimated_ram_gb':round(estimated/1024**3,2),'fits_available_ram':bool(size and estimated<ram.available*.85)})
    candidates.sort(key=lambda x:(not x['fits_available_ram'],x['size_gb']))
    return status|{'ram_gb':round(ram.total/1024**3,1),'available_ram_gb':round(ram.available/1024**3,1),'suggestions':candidates,'setup_complete':store.settings()['setup_complete']}


def register(app,store,scope,running):
    @app.exception_handler(ValueError)
    async def invalid(request,exc):return __import__('fastapi').responses.JSONResponse({'detail':str(exc)},status_code=400)

    @app.get('/api/brief')
    def brief():return ws.daily_brief(store)

    @app.get('/api/workspace')
    def workspace():
        return {'projects':ws.projects(store),'documents':ws.document_list(store),'inbox':ws.inbox(store),'memories':store.items('memories'),'brief':ws.daily_brief(store),'memory_review':store.settings()['memory_review']}

    @app.get('/api/setup')
    async def setup():return await setup_status(store)
    @app.post('/api/setup/complete')
    def complete():return store.save_settings({'setup_complete':True})
    @app.post('/api/memory-review')
    def review_mode(enabled:bool=Body(embed=True)):return store.save_settings({'memory_review':enabled})
    @app.post('/api/memory-inbox/{iid}')
    def decide(iid:str,value:Decision):ws.decide_memory(store,iid,value.approve,value.content);return {'ok':True}

    @app.post('/api/projects')
    def project(value:Project):return {'id':ws.save_project(store,value.name,value.instructions)}
    @app.put('/api/projects/{iid}')
    def edit_project(iid:str,value:Project):return {'id':ws.save_project(store,value.name,value.instructions,iid)}
    @app.delete('/api/projects/{iid}')
    def delete_project(iid:str):
        with store.db() as db:db.execute('DELETE FROM projects WHERE id=?',(iid,))
        return {'ok':True}
    @app.put('/api/chats/{cid}/project')
    def assign(cid:str,project_id:str|None=Body(embed=True)):
        if scope(cid).ephemeral:raise ValueError('Temporary chats do not load saved projects')
        if cid in running:raise HTTPException(409,'Wait for generation to finish')
        ws.assign_project(store,cid,project_id);return {'ok':True}

    @app.get('/api/chats/{cid}/workspace')
    def chat_workspace(cid:str):
        selected=scope(cid);selected.chat(cid)
        with selected.db() as db:
            meta=db.execute('SELECT project_id,parent_id FROM chat_meta WHERE chat_id=?',(cid,)).fetchone()
            ids=[x[0] for x in db.execute('SELECT document_id FROM chat_documents WHERE chat_id=?',(cid,))]
        return {'project_id':meta['project_id'] if meta else None,'parent_id':meta['parent_id'] if meta else None,'document_ids':ids}

    @app.post('/api/chats/{cid}/branch')
    def branch(cid:str):
        if scope(cid).ephemeral:raise ValueError('Temporary chats cannot create saved branches')
        token=store.acquire()
        try:return store.chat(ws.branch(store,cid))
        finally:store.release(token)

    @app.get('/api/chats/{cid}/messages/{mid}/sources')
    def sources(cid:str,mid:int):return ws.provenance(scope(cid),cid,mid)

    @app.post('/api/chats/{cid}/attachments')
    async def attachment(cid:str,value:Upload):
        if cid in running:raise HTTPException(409,'Wait for the current answer')
        selected=scope(cid);selected.chat(cid)
        try:raw=base64.b64decode(value.data,validate=True)
        except ValueError:raise HTTPException(400,'Invalid file encoding')
        with selected.db() as db:ids=[r[0] for r in db.execute('SELECT document_id FROM chat_documents WHERE chat_id=?',(cid,))]
        if len(ids)>=10:raise ValueError('Attach at most 10 files')
        iid=await asyncio.to_thread(ws.ingest,selected,value.name,raw)
        ws.attach(selected,cid,ids+[iid]);return {'id':iid,'name':value.name}

    @app.post('/api/documents')
    async def document(value:Upload):
        try:raw=base64.b64decode(value.data,validate=True)
        except ValueError:raise HTTPException(400,'Invalid file encoding')
        iid=await asyncio.to_thread(ws.ingest,store,value.name,raw,value.project_id)
        return {'id':iid}
    @app.delete('/api/documents/{iid}')
    def delete_document(iid:str):
        with store.db() as db:db.execute('DELETE FROM documents WHERE id=?',(iid,))
        return {'ok':True}
    @app.put('/api/chats/{cid}/documents')
    def attach(cid:str,value:Attachment):
        if scope(cid).ephemeral:raise ValueError('Temporary chats do not load saved documents')
        if cid in running:raise HTTPException(409,'Wait for generation to finish')
        ws.attach(store,cid,value.ids);return {'ok':True}

    @app.put('/api/feedback/{mid}')
    def feedback(mid:int,value:FeedbackEdit):
        with store.db() as db:row=db.execute('SELECT chat_id FROM messages WHERE id=?',(mid,)).fetchone()
        if not row:raise KeyError('Message not found')
        store.feedback(row[0],mid,value.rating,value.reason);return {'ok':True}
    @app.delete('/api/feedback')
    def reset_feedback():
        with store.db() as db:db.execute('DELETE FROM feedback')
        return {'ok':True}
    @app.delete('/api/feedback/{mid}')
    def clear_feedback(mid:int):
        with store.db() as db:db.execute('DELETE FROM feedback WHERE message_id=?',(mid,))
        return {'ok':True}

    @app.post('/api/backup/export')
    async def backup(value:BackupRequest):
        from .backup import export_backup
        blob=await asyncio.to_thread(export_backup,store,value.password)
        return Response(blob,media_type='application/octet-stream',headers={'Content-Disposition':'attachment; filename="nila-backup.nila"','Cache-Control':'no-store'})
    @app.post('/api/backup/restore')
    async def restore(value:BackupRequest):
        from .backup import restore_backup
        if running:raise HTTPException(409,'Stop chat generation before restoring')
        try:raw=base64.b64decode(value.data,validate=True)
        except ValueError:raise HTTPException(400,'Invalid backup encoding')
        return await asyncio.to_thread(restore_backup,store,raw,value.password,value.apply)

    @app.post('/api/update/rollback')
    async def rollback():
        from .updater import rollback
        return await asyncio.to_thread(rollback,store)


    @app.post('/api/chats/{cid}/followups')
    async def followups(cid:str):
        from .conversation import followups
        if running or cid in app.state.followups:return []
        task=asyncio.create_task(followups(scope(cid),cid))
        app.state.followups[cid]=task
        try:return await task
        except (RuntimeError,asyncio.CancelledError):return []
        finally:app.state.followups.pop(cid,None)

    @app.get('/api/telegram')
    def telegram_status():
        from .telegram_bot import status
        return status(store)
    @app.put('/api/telegram')
    def telegram_save(value:TelegramConfig):
        from .telegram_bot import save,config
        previous=config(store)
        token=value.token or (previous['token'] if previous else '')
        return save(store,token,value.chat_id,value.enabled,value.share_memory)
    @app.post('/api/telegram/test')
    async def telegram_test():
        from .telegram_bot import test,TelegramError
        try:return await test(store)
        except TelegramError as exc:raise HTTPException(400,str(exc))
    @app.delete('/api/telegram')
    def telegram_remove():
        from .telegram_bot import disable
        return disable(store,True)

    @app.get('/api/chats/{cid}/attachments')
    def attachments(cid:str):
        selected=scope(cid);selected.chat(cid)
        with selected.db() as db:
            return [{'id':r['id'],'name':selected.open(r['name'])} for r in db.execute('SELECT d.id,d.name FROM documents d JOIN chat_documents c ON c.document_id=d.id WHERE c.chat_id=?',(cid,))]
    @app.delete('/api/chats/{cid}/attachments/{iid}')
    def detach(cid:str,iid:str):
        if cid in running:raise HTTPException(409,'Wait for the current answer')
        selected=scope(cid);selected.chat(cid)
        with selected.db() as db:db.execute('DELETE FROM chat_documents WHERE chat_id=? AND document_id=?',(cid,iid))
        return {'ok':True}

    @app.get('/api/memory-overview')
    def memory_overview():
        from .learning import knowledge,sessions
        from .knowledge_cache import backfill
        backfill(store)
        lessons=knowledge(store);settings=store.settings()
        with store.db() as db:cached=db.execute('SELECT COUNT(*) FROM web_knowledge').fetchone()[0]
        recent=sessions(store)[:5]
        return {'personal':len(store.items('memories')),'pending':len(ws.inbox(store)),'lessons':len(lessons),'enabled_lessons':sum(bool(x['enabled']) for x in lessons),'web':cached,'total':len(store.items('memories'))+len(lessons)+cached,'memory_enabled':settings['memory_enabled'],'knowledge_enabled':settings['knowledge_enabled'],'memory_review':settings['memory_review'],'recent_learning':[{'status':x['status'],'error':x['error'],'topic':x['config']['topic'],'save_knowledge':x['config'].get('save_knowledge',True)} for x in recent]}
