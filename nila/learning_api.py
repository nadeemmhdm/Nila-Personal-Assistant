from fastapi import HTTPException
from pydantic import BaseModel,Field
from .learning import LearningLab,SessionConfig,LearningError,save_key,delete_key,key,gemini_models,sessions,session,knowledge

class KeyInput(BaseModel):value:str=Field(min_length=10,max_length=300)
class KnowledgeInput(BaseModel):
    content:str=Field(min_length=1,max_length=2000)
    enabled:bool=True

def register(app,store):
    lab=LearningLab(store)
    @app.get('/api/learning/key')
    def key_status():return {'configured':bool(key(store))}
    @app.put('/api/learning/key')
    def set_key(value:KeyInput):
        try:save_key(store,value.value)
        except ValueError as exc:raise HTTPException(400,str(exc))
        return {'configured':True}
    @app.delete('/api/learning/key')
    def remove_key():delete_key(store);return {'configured':False}
    @app.get('/api/learning/models')
    async def list_models():
        try:return await gemini_models(store)
        except LearningError as exc:raise HTTPException(400,str(exc))
    @app.get('/api/learning/sessions')
    def list_sessions():return sessions(store)
    @app.post('/api/learning/sessions')
    async def start(config:SessionConfig):
        try:return {'id':lab.start(config)}
        except ValueError as exc:raise HTTPException(400,str(exc))
    @app.get('/api/learning/sessions/{iid}')
    def get_session(iid:str):return session(store,iid)
    @app.post('/api/learning/sessions/{iid}/stop')
    async def stop(iid:str):lab.stop(iid);return {'status':'stopping'}
    @app.delete('/api/learning/sessions/{iid}')
    def remove_session(iid:str):
        if session(store,iid)['status']=='running':raise HTTPException(409,'Stop the session first')
        with store.db() as db:
            db.execute('DELETE FROM learning_sessions WHERE id=?',(iid,))
            db.execute('DELETE FROM knowledge WHERE session_id=?',(iid,))
        return {'ok':True}
    @app.get('/api/learning/knowledge')
    def learned():return knowledge(store)
    @app.put('/api/learning/knowledge/{iid}')
    def edit_lesson(iid:str,value:KnowledgeInput):
        if not value.content.strip():raise HTTPException(400,'Lesson cannot be blank')
        with store.db() as db:db.execute('UPDATE knowledge SET content=?,enabled=? WHERE id=?',(store.seal(value.content.strip()),int(value.enabled),iid))
        return {'ok':True}
    @app.delete('/api/learning/knowledge/{iid}')
    def forget_lesson(iid:str):
        with store.db() as db:db.execute('DELETE FROM knowledge WHERE id=?',(iid,))
        return {'ok':True}
    return lab
