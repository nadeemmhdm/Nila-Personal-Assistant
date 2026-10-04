import asyncio
import json
import re
from contextlib import suppress, asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from . import __version__
from .storage import Store
from .engine import models, reply, NilaError

class Settings(BaseModel):
    assistant_name: str = Field(default="Nila", min_length=1, max_length=40)
    user_name: str = Field(default="", max_length=60)
    model: str = Field(default="llama3.2:1b", min_length=1,max_length=120,pattern=r"^[a-zA-Z0-9_.:/-]+$")
    language: Literal["Auto","English","Malayalam"] = "Auto"
    temperature: float = Field(default=0.7,ge=0,le=1.5)
    num_ctx: Literal[2048,4096,8192] = 2048
    memory_enabled: bool = True
    auto_memory: bool = True
    auto_update: bool = True
    description: str = Field(default="", max_length=1000)
    college: str = Field(default="", max_length=150)
    course: str = Field(default="", max_length=150)
    interests: str = Field(default="", max_length=500)
    tone: Literal["Friendly","Professional","Concise"] = "Friendly"
    @field_validator("assistant_name", "user_name")
    @classmethod
    def clean_name(cls, v):
        if "\n" in v or "\r" in v:
            raise ValueError("Use a single line name")
        return v.strip()

class Prompt(BaseModel):
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
    from .automation import Scheduler
    from .extensions import register
    from .updater import start_auto_update
    scheduler = Scheduler(store)
    @asynccontextmanager
    async def lifespan(app):
        worker = asyncio.create_task(scheduler.loop())
        start_auto_update(store)
        try: yield
        finally:
            worker.cancel()
            with suppress(asyncio.CancelledError): await worker
    app = FastAPI(lifespan=lifespan,title="Nila Personal Assistant",version=__version__,docs_url=None,redoc_url=None)
    running = {}
    register(app,store,scheduler)

    @app.middleware("http")
    async def local_only(request, call_next):
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
    def put_settings(value:Settings): return store.save_settings(value.model_dump())

    @app.get("/api/chats")
    def chats(): return store.chats()

    @app.post("/api/chats")
    def create(): return store.create_chat()

    @app.get("/api/chats/{cid}")
    def chat(cid:str): return store.chat(cid)

    @app.delete("/api/chats/{cid}")
    def delete(cid:str):
        # The shared lease also protects deletion during CLI generation.
        try: token = store.acquire()
        except RuntimeError as exc: raise HTTPException(409,str(exc))
        try: store.delete_chat(cid)
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

    @app.post("/api/chats/{cid}/stop")
    async def stop(cid:str):
        task = running.get(cid)
        if task: task.cancel()
        return {"ok":True}

    @app.post("/api/chats/{cid}/reply")
    async def answer(cid:str, value:Prompt, request:Request):
        store.chat(cid)
        if cid in running: raise HTTPException(409,"A response is already running")
        queue = asyncio.Queue()
        async def produce():
            try:
                async for part in reply(store,cid,value.content):
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
