"""Background component setup and bounded offline speech endpoints."""
import asyncio,base64,binascii,tempfile
from pathlib import Path
from typing import Literal
from fastapi import HTTPException
from fastapi.responses import Response
from pydantic import BaseModel,Field
from . import local_runtime as runtime,speech_pack

class Setup(BaseModel):
    component: Literal['ollama','llama.cpp','speech','vision']
    profile: Literal['fast','medium','smart','vision']='fast'
class Audio(BaseModel):
    data: str=Field(max_length=7_000_000)
class Speech(BaseModel):
    text: str=Field(min_length=1,max_length=12000)

def register(app,store):
    state={'running':False,'message':'','error':''}
    app.state.component_tasks=set()
    speech_lock=asyncio.Lock()
    @app.get('/api/runtime')
    async def status():return {'runtime':runtime.status(),'speech':speech_pack.status(),'job':state.copy()}
    @app.post('/api/runtime/setup')
    async def setup(body:Setup):
        if state['running']:raise HTTPException(409,'A component setup is already running')
        state.update(running=True,message='Preparing components',error='')
        def progress(message):state['message']=message
        async def run():
            try:
                if body.component=='speech':await speech_pack.install(progress)
                elif body.component=='vision':
                    if runtime.config().get('engine')=='llama.cpp':await runtime.choose(store,'llama.cpp','vision',progress)
                    else:
                        from .model_manager import select
                        await select(store,'moondream',progress=progress)
                else:await runtime.choose(store,body.component,body.profile,progress)
                state['message']='Ready'
            except asyncio.CancelledError:state['message']='Setup stopped';raise
            except Exception as exc:state['error']=str(exc)
            finally:state['running']=False
        task=asyncio.create_task(run());app.state.component_tasks.add(task);task.add_done_callback(app.state.component_tasks.discard)
        return state.copy()
    async def voice(action,payload):
        if speech_lock.locked():raise HTTPException(409,'Speech is busy; retry when it finishes')
        async with speech_lock:
            with tempfile.TemporaryDirectory(prefix='nila-speech-') as folder:
                file=Path(folder)/('audio.wav' if action=='speak' else 'audio.webm')
                if action=='transcribe':
                    try:data=base64.b64decode(payload,validate=True)
                    except (ValueError,binascii.Error):raise HTTPException(400,'Invalid audio')
                    if not data or len(data)>5*1024*1024:raise HTTPException(400,'Audio limit is 5 MB')
                    file.write_bytes(data)
                try:result=await speech_pack.worker({'action':action,'file':str(file),**({'text':payload} if action=='speak' else {})})
                except (ValueError,OSError,asyncio.TimeoutError) as exc:raise HTTPException(400,str(exc) or 'Speech timed out')
                return Response(file.read_bytes(),media_type='audio/wav') if action=='speak' else result
    @app.post('/api/runtime/transcribe')
    async def transcribe(body:Audio):return await voice('transcribe',body.data)
    @app.post('/api/runtime/speak')
    async def speak(body:Speech):return await voice('speak',body.text)
