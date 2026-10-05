"""Shared Web API operations for profiles, maintenance and automations."""
import asyncio
import json
import os
import platform
import shutil
import subprocess
import time
import httpx
from fastapi import HTTPException
from pydantic import BaseModel,Field
from . import __version__
from .automation import Job,jobs,runs,save_job,remove_job
from .engine import ollama_url,models,NilaError
from .worker import worker_status
from . import updater

async def diagnostics(store):
    try:
        installed=await models();online=True;error=None
    except NilaError as exc: installed=[];online=False;error=str(exc)
    return {'version':__version__,'python':platform.python_version(),'platform':platform.system(),'storage':str(store.root),'encrypted':True,'key_protection':'Windows CurrentUser DPAPI' if os.name=='nt' else 'Private local key file','model':store.settings()['model'],'ollama_online':online,'model_ready':store.settings()['model'] in [m['name'] for m in installed],'models':installed,'error':error,'worker':worker_status(store),'installation':updater.installed()}

class ModelPull(BaseModel):
    model:str=Field(min_length=1,max_length=120,pattern=r'^[a-zA-Z0-9_.:/-]+$')

async def pull_model(model,on_progress=None):
    async with httpx.AsyncClient(timeout=httpx.Timeout(600,connect=5),trust_env=False) as client:
        async with client.stream('POST',ollama_url()+'/api/pull',json={'model':model,'stream':True}) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line:continue
                data=json.loads(line)
                if data.get('error'):raise ValueError(str(data['error'])[:200])
                if on_progress:on_progress(data)

class Draft(BaseModel):
    instruction:str=Field(min_length=5,max_length=2000)

async def draft_job(store,instruction):
    schema={'type':'object','properties':{'title':{'type':'string'},'prompt':{'type':'string'},'kind':{'type':'string','enum':['ai','brief','note','task']},'interval_minutes':{'type':'integer'}},'required':['title','prompt','kind','interval_minutes'],'additionalProperties':False}
    async with httpx.AsyncClient(timeout=60,trust_env=False) as c:
        r=await c.post(ollama_url()+'/api/chat',json={'model':store.settings()['model'],'stream':False,'format':schema,'messages':[{'role':'system','content':'Draft a local automation. Allowed actions: ai (write text), brief (summarize local notes/tasks), note (save provided text), task (create to-do). No shell, browser, messaging or file access. Use interval_minutes 0 for one-time or >=5 for repeats. Return JSON matching '+json.dumps(schema)},{'role':'user','content':instruction}],'options':{'temperature':0,'num_predict':400}})
        r.raise_for_status();data=json.loads(r.json()['message']['content'])
    return Job(**data,next_run=time.time()+3600,enabled=False).model_dump()

def service(action):
    if os.name!='nt': raise ValueError('Windows login task controls are available on Windows. Run nila worker here.')
    args={'start':['/Run'],'stop':['/End'],'enable':['/Change','/ENABLE'],'disable':['/Change','/DISABLE']}
    if action not in args: raise ValueError('Unknown worker action')
    result=subprocess.run(['schtasks.exe',*args[action],'/TN','Nila Personal Assistant'],capture_output=True,text=True,timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode: raise ValueError('Windows task control failed. Run the installer to register the login task, or run nila worker manually.')
    return {'message':'Background task '+action+' request completed. Telegram also connects while the Web server is running.'}

def register(app,store,scheduler):
    maintenance={'update':{'status':'idle'},'pull':{'status':'idle'}}
    background=set()
    def launch(coro):
        task=asyncio.create_task(coro);background.add(task);task.add_done_callback(background.discard)

    @app.post('/api/worker/{action}')
    async def worker_action(action:str):
        try:return await asyncio.to_thread(service,action)
        except ValueError as exc:raise HTTPException(400,str(exc))

    @app.get('/api/system')
    async def system():return (await diagnostics(store))|{'telegram_worker':True,'maintenance':maintenance}
    @app.get('/api/update')
    async def check_update():return await asyncio.to_thread(updater.check)
    @app.post('/api/update')
    async def apply_update():
        if maintenance['update'].get('status')=='running':return maintenance['update']
        maintenance['update']={'status':'running','message':'Building update in the background. Current version remains active.'}
        async def work():maintenance['update']=await asyncio.to_thread(updater.apply_update)
        launch(work());return maintenance['update']
    @app.post('/api/models/pull')
    async def pull(value:ModelPull):
        if maintenance['pull'].get('status')=='running':raise HTTPException(409,'A model download is already running')
        maintenance['pull']={'status':'running','model':value.model}
        async def work():
            try:
                await pull_model(value.model,lambda d:maintenance['pull'].update({'progress':d}))
                maintenance['pull']['status']='complete'
            except Exception:maintenance['pull']={'status':'failed','message':'Model download failed. Check Ollama and internet access; retry to resume.'}
        launch(work());return maintenance['pull']

    @app.post('/api/models/load')
    async def load(value:ModelPull):
        token=store.acquire()
        try:
            if value.model not in [m['name'] for m in await models()]:raise HTTPException(400,'Download this model first')
            async with httpx.AsyncClient(timeout=180,trust_env=False) as client:
                r=await client.post(ollama_url()+'/api/generate',json={'model':value.model,'prompt':'','stream':False,'keep_alive':'5m'})
                r.raise_for_status()
                if r.json().get('error'):raise ValueError('Ollama could not load this model')
            return store.save_settings({'model':value.model})
        except httpx.HTTPError:raise HTTPException(400,'Model could not load. Check Ollama and available RAM.') from None
        finally:store.release(token)
