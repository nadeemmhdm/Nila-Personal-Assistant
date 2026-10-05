import asyncio
import json
import re
from contextlib import suppress, asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator
from . import __version__
from .storage import Store
from .engine import models, reply, NilaError
from .model_manager import DEFAULT_PROFILES

class Settings(BaseModel):
    model_profiles: dict[str,str] = Field(default_factory=lambda: DEFAULT_PROFILES.copy())
    model_mode: Literal["fast","medium","current","custom"] = "current"
    @field_validator("model_profiles")
    @classmethod
    def valid_profiles(cls,value):
        from .model_manager import profiles
        return profiles(value)
    goals: str = Field(default="",max_length=1000)
    response_style: Literal["Concise","Balanced","Detailed"] = "Balanced"
    thinking_level: Literal["low","medium","high"] = "medium"
    memory_review: bool = True
    setup_complete: bool = False
    assistant_name: str = Field(default="Nila", min_length=1, max_length=40)
    user_name: str = Field(default="", max_length=60)
    model: str = Field(default=DEFAULT_PROFILES["current"], min_length=1,max_length=120,pattern=r"^[a-zA-Z0-9_.:/-]+$")
    language: Literal["Auto","English","Malayalam"] = "Auto"
    temperature: float = Field(default=0.7,ge=0,le=1.5)
    num_ctx: Literal[2048,4096,8192] = 2048
    memory_enabled: bool = True
    auto_memory: bool = True
    auto_update: bool = True
    description: str = Field(default="", max_length=1000)
    position: Literal["Student","Employee","Self-employed","Other","Prefer not to say"] = "Other"
    completion_year: str = Field(default="",pattern=r"^(|[0-9]{4})$")
    company: str = Field(default="",max_length=150)
    job_role: str = Field(default="",max_length=150)
    knowledge_enabled: bool = True
    course: str = Field(default="", max_length=150)
    interests: str = Field(default="", max_length=500)
    tone: Literal["Friendly","Professional","Concise"] = "Friendly"
    @model_validator(mode="after")
    def role_fields(self):
        if self.position != "Student": self.course="";self.completion_year=""
        if self.position not in {"Employee","Self-employed"}: self.company="";self.job_role=""
        return self
    @field_validator("assistant_name", "user_name")
    @classmethod
    def clean_name(cls, v):
        if "\n" in v or "\r" in v:
            raise ValueError("Use a single line name")
        return v.strip()

class Feedback(BaseModel):
    rating: Literal[-1,0,1]
    reason: str = Field(default='',max_length=500)

class NewChat(BaseModel):
    temporary: bool = False
    project_id: str | None = None

class Prompt(BaseModel):
    thinking_level: Literal["low","medium","high"] | None = None
    regenerate_id: int | None = Field(default=None,gt=0)
    instruction: str = Field(default='',max_length=2000)
    preserve_branch: bool = True
    search_mode: Literal['off','quick','deep'] = 'off'
    search_query: str | None = Field(default=None,min_length=1,max_length=500)
    edit_message_id: int | None = Field(default=None,gt=0)
    content: str = Field(min_length=1,max_length=12000)
    @field_validator("content")
    @classmethod
    def nonempty(cls,v):
        if not v.strip(): raise ValueError("Please enter a message")
        return v.strip()

class Item(BaseModel):
    content: str = Field(min_length=1,max_length=2000)
    done: bool = False
    @field_validator("content")
    @classmethod
    def nonempty(cls,v):
        if not v.strip(): raise ValueError("Please enter some text")
        return v.strip()

Kind = Literal["memories","notes","tasks"]

def create_app(store=None):
    store = store or Store()
    from .telegram_bot import Bridge
    from .extensions import register
    from .updater import start_auto_update
    bridge = Bridge(store)
    @asynccontextmanager
    async def lifespan(app):
        worker = asyncio.create_task(bridge.loop())
        start_auto_update(store)
        try: yield
        finally:
            pending=list(running.values())+list(app.state.followups.values())
            for task in pending:task.cancel()
            await asyncio.gather(*pending,return_exceptions=True)
            await lab.close()
            worker.cancel()
            with suppress(asyncio.CancelledError): await worker
            for ram in temporary.values():ram._ram.close()
    app = FastAPI(lifespan=lifespan,title="Nila Personal Assistant",version=__version__,docs_url=None,redoc_url=None)
    app.state.followups={}
    running = {}
    temporary={}
    def scope(cid):return temporary.get(cid,store)
    from .workspace_api import register as workspace_routes
    workspace_routes(app,store,scope,running)
    from .skills import register as skill_routes
    skill_routes(app,store)
    from .model_manager import register as model_routes
    model_routes(app,store)
    register(app,store,None)
    from .learning_api import register as register_learning
    lab=register_learning(app,store)

    @app.middleware("http")
    async def local_only(request, call_next):
        if request.url.path.startswith('/api/automations') or request.url.path in {'/api/items/notes','/api/items/tasks'} or request.url.path.startswith(('/api/items/notes/','/api/items/tasks/')):
            return JSONResponse({'detail':'Notes, tasks and automation features have been removed.'},status_code=410)
        host = request.url.hostname
        if host not in {"127.0.0.1","localhost","::1","testserver"}:
            return JSONResponse({"detail":"Local access only"},status_code=403)
        origin = request.headers.get("origin")
        if origin:
            parsed = urlparse(origin)
            if parsed.scheme != "http" or parsed.netloc not in {request.headers.get("host"),"localhost:5173","127.0.0.1:5173"}:
                return JSONResponse({"detail":"Origin blocked"},status_code=403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail":"Cross-site access blocked"},status_code=403)
        response = await call_next(request)
        if request.url.path.startswith("/api/"):response.headers["Cache-Control"]="no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        return response

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({"detail":"Conversation not found"},status_code=404)

    @app.get("/api/status")
    async def status():
        try:
            items = await models()
            return {"online":True,"models":items,"version":__version__,"model_ready":store.settings()["model"] in [m["name"] for m in items]}
        except NilaError as exc:
            return {"online":False,"models":[],"version":__version__,"model_ready":False,"error":str(exc)}

    @app.get("/api/settings")
    def get_settings(): return store.settings()

    @app.put("/api/settings")
    def put_settings(value:Settings): return store.save_settings(value.model_dump(exclude_unset=True))

    @app.get("/api/chats")
    def chats(): return store.chats()

    @app.post("/api/chats")
    def create(value:NewChat=Body(default=NewChat())):
        if value.temporary:
            if len(temporary)>=10:raise HTTPException(400,'Close an existing temporary chat first (limit 10)')
            ram=Store(ephemeral=True)
            ram.save_settings({k:v for k,v in store.settings().items() if k in {'assistant_name','model','language','temperature','num_ctx','thinking_level'}}|{'auto_memory':False,'memory_enabled':False,'knowledge_enabled':False,'auto_update':False})
            ram.acquire=store.acquire;ram.release=store.release
            chat=ram.create_chat();temporary[chat['id']]=ram
            return chat|{'temporary':True}
        chat=store.create_chat()
        if value.project_id:
            from .workspace import assign_project
            assign_project(store,chat['id'],value.project_id)
        return chat

    @app.get("/api/chats/{cid}")
    def chat(cid:str): return scope(cid).chat(cid)|{"temporary":cid in temporary}

    @app.delete("/api/chats/{cid}")
    def delete(cid:str):
        # The shared lease also protects deletion during CLI generation.
        try: token = store.acquire()
        except RuntimeError as exc: raise HTTPException(409,str(exc))
        try:
            scope(cid).delete_chat(cid)
            ram=temporary.pop(cid,None)
            if ram:ram._ram.close()
        finally: store.release(token)
        return {"ok":True}

    @app.get("/api/items/{kind}")
    def items(kind:Kind): return store.items(kind)

    @app.post("/api/items/{kind}")
    def add_item(kind:Kind,value:Item):
        try: iid = store.add_item(kind,value.content)
        except ValueError as exc: raise HTTPException(400,str(exc))
        return {"id":iid}

    @app.put("/api/items/{kind}/{iid}")
    def update_item(kind:Kind,iid:str,value:Item):
        store.update_item(kind,iid,value.content,value.done)
        return {"ok":True}

    @app.delete("/api/items/{kind}/{iid}")
    def remove_item(kind:Kind,iid:str):
        store.delete_item(kind,iid)
        return {"ok":True}

    @app.put("/api/chats/{cid}/messages/{mid}/feedback")
    def feedback(cid:str,mid:int,value:Feedback):
        if cid in temporary:raise HTTPException(400,"Temporary chats do not save feedback")
        store.feedback(cid,mid,value.rating,value.reason)
        return {"ok":True}

    @app.post("/api/chats/{cid}/stop")
    async def stop(cid:str):
        task = running.get(cid)
        if task: task.cancel()
        return {"ok":True}

    @app.post("/api/chats/{cid}/reply")
    async def answer(cid:str, value:Prompt, request:Request):
        pending=list(app.state.followups.values())
        for task in pending:task.cancel()
        await asyncio.gather(*pending,return_exceptions=True)
        chat_store=scope(cid)
        if cid in temporary:chat_store.save_settings({"model":store.settings()["model"]})
        chat_store.chat(cid)
        if value.thinking_level:chat_store.save_settings({'thinking_level':value.thinking_level})
        if value.regenerate_id is not None and value.edit_message_id is not None:raise HTTPException(400,"Choose edit or regenerate")
        if cid in running: raise HTTPException(409,"A response is already running")
        if value.edit_message_id is not None and not any(m['id']==value.edit_message_id and m['role']=='user' for m in chat_store.chat(cid)['messages']):
            raise HTTPException(404,"Prompt not found")
        if value.regenerate_id is not None and not any(m['id']==value.regenerate_id and m['role']=='assistant' for m in chat_store.chat(cid)['messages']):raise HTTPException(404,'Response not found')
        queue = asyncio.Queue()
        async def produce():
            try:
                async for part in reply(chat_store,cid,value.content,search_mode=value.search_mode,search_query=value.search_query,edit_message_id=value.edit_message_id,regenerate_id=value.regenerate_id,instruction=value.instruction,preserve_branch=value.preserve_branch,progress=lambda label:queue.put_nowait({"progress":label})):
                    await queue.put({"token":part})
            except asyncio.CancelledError:
                await queue.put({"stopped":True})
            except (NilaError,RuntimeError) as exc:
                await queue.put({"error":str(exc)})
            except Exception:
                await queue.put({"error":"NILA-006: Internal error. Run nila doctor and retry."})
            finally:
                await queue.put({"done":True})
                running.pop(cid,None)
        task = asyncio.create_task(produce())
        running[cid] = task
        async def events():
            try:
                while True:
                    event = await queue.get()
                    yield json.dumps(event,ensure_ascii=False)+"\n"
                    if event.get("done"): break
            finally:
                if not task.done(): task.cancel()
                with suppress(asyncio.CancelledError): await task
        return StreamingResponse(events(),media_type="application/x-ndjson",headers={"Cache-Control":"no-store","X-Accel-Buffering":"no"})

    static = Path(__file__).parent / "static"
    if (static/"assets").exists():
        app.mount("/assets",StaticFiles(directory=static/"assets"),name="assets")
    @app.get("/")
    def index():
        if (static/"index.html").exists(): return FileResponse(static/"index.html")
        return JSONResponse({"detail":"Build the web interface: cd web && npm ci && npm run build"},status_code=503)
    return app
