"""Managed CPU llama.cpp runtime. Downloads are explicit, verified and reusable."""
import asyncio,hashlib,json,os,platform,secrets,subprocess,tarfile,time,zipfile
import re
from pathlib import Path
import httpx
from platformdirs import user_data_dir

CATALOG={'fast':('ggml-org/Qwen3-0.6B-GGUF','Qwen3-0.6B-Q4_0.gguf','qwen3:0.6b'),'medium':('Qwen/Qwen3-1.7B-GGUF','Qwen3-1.7B-Q8_0.gguf','qwen3:1.7b'),'smart':('Qwen/Qwen3-4B-GGUF','Qwen3-4B-Q8_0.gguf','qwen3:4b')}
CATALOG['vision']=('ggml-org/SmolVLM-500M-Instruct-GGUF','SmolVLM-500M-Instruct-Q8_0.gguf','smolvlm:500m')
_PROCESS=None
_LOCK=None

def root():return Path(os.environ.get('NILA_DATA_DIR') or user_data_dir('Nila',appauthor=False))/'runtime'
def config():
    try:return json.loads((root()/'engine.json').read_text())
    except (FileNotFoundError,ValueError):return {'engine':'ollama'}
def save(value):
    root().mkdir(parents=True,exist_ok=True)
    p=root()/'engine.json';tmp=p.with_suffix('.tmp')
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as f:json.dump(value,f)
    tmp.replace(p)
def status():
    c=config();return {'engine':c['engine'],'profile':c.get('profile','fast'),'model':c.get('model',''),'installed':bool(c.get('binary') and Path(c['binary']).is_file()),'profiles':list(CATALOG)}

async def download(url,path,digest,progress=None):
    if not re.fullmatch(r'[0-9a-f]{64}',digest):raise ValueError('Download has no trusted SHA-256 checksum')
    if path.is_file():
        with path.open('rb') as existing:
            if hashlib.file_digest(existing,'sha256').hexdigest()==digest:return
    if len(digest)!=64:raise ValueError('Download has no trusted SHA-256 checksum')
    path.parent.mkdir(parents=True,exist_ok=True);part=path.with_suffix(path.suffix+'.part');h=hashlib.sha256()
    try:
        async with httpx.AsyncClient(timeout=120,follow_redirects=True) as client:
            async with client.stream('GET',url) as response:
                response.raise_for_status();total=int(response.headers.get('content-length',0));done=0;last=0
                with part.open('wb') as f:
                    async for chunk in response.aiter_bytes(1024*1024):
                        f.write(chunk);h.update(chunk);done+=len(chunk)
                        if done-last>8*1024*1024:
                            if progress:progress('Downloading '+path.name+': '+str(done//1048576)+' MB'+(' / '+str(total//1048576)+' MB' if total else ''))
                            last=done
        if h.hexdigest()!=digest:raise ValueError('Download checksum mismatch; retry the installation')
        part.replace(path)
    finally:part.unlink(missing_ok=True)

async def install(profile='fast',progress=None):
    if profile not in CATALOG:raise ValueError('Choose fast, medium, smart or vision')
    if platform.machine().lower() not in {'amd64','x86_64'}:raise ValueError('Automatic llama.cpp installation currently supports Windows/Linux x64')
    if platform.system() not in {'Windows','Linux'}:raise ValueError('Automatic installation supports Windows and Linux')
    if progress:progress('Checking official llama.cpp CPU release')
    async with httpx.AsyncClient(timeout=30,follow_redirects=True) as client:
        r=await client.get('https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=10');r.raise_for_status()
        asset=None
        for release in r.json():
            for a in release.get('assets',[]):
                n=a['name'].lower()
                match=('win-cpu-x64' in n and n.endswith('.zip')) if os.name=='nt' else bool(re.fullmatch(r'llama-b[0-9]+-bin-ubuntu-x64\.tar\.gz',n))
                if match and a.get('digest','').startswith('sha256:'):asset=a;break
            if asset:break
        if not asset:raise ValueError('No verified CPU binary is available for this OS. Retry later.')
        archive=root()/asset['name'];await download(asset['browser_download_url'],archive,asset['digest'][7:],progress)
        dest=root()/'llama-bin'/asset['name'].replace('.tar.gz','').replace('.zip','')
        dest.mkdir(parents=True,exist_ok=True)
        executable='llama-server.exe' if os.name=='nt' else 'llama-server'
        binaries=list(dest.rglob(executable))
        if not binaries:
            if archive.suffix=='.zip':
                with zipfile.ZipFile(archive) as z:
                    for member in z.infolist():
                        if not (dest/member.filename).resolve().is_relative_to(dest.resolve()):raise ValueError('Unsafe runtime archive')
                    z.extractall(dest)
            else:
                with tarfile.open(archive) as tar:tar.extractall(dest,filter='data')
            binaries=list(dest.rglob(executable))
        if not binaries:raise ValueError('Runtime archive did not include llama-server')
        binary=binaries[0]
        if os.name!='nt':binary.chmod(0o700)
        repo,filename,name=CATALOG[profile]
        r=await client.get('https://huggingface.co/api/models/'+repo+'/tree/main?blobs=true');r.raise_for_status()
        meta=next((x for x in r.json() if x.get('path')==filename),None)
        if not meta or not meta.get('lfs'):raise ValueError('Verified GGUF model unavailable')
        model=root()/'models'/filename
        await download('https://huggingface.co/'+repo+'/resolve/main/'+filename,model,meta['lfs']['oid'],progress)
        projector=None
        if profile=='vision':
            filename='mmproj-SmolVLM-500M-Instruct-Q8_0.gguf'
            meta=next(x for x in r.json() if x.get('path')==filename)
            projector=root()/'models'/filename
            await download('https://huggingface.co/'+repo+'/resolve/main/'+filename,projector,meta['lfs']['oid'],progress)
    return {'mmproj':str(projector) if projector else '', 'engine':'llama.cpp','profile':profile,'binary':str(binary),'gguf':str(model),'model':name,'key':secrets.token_urlsafe(32)}

async def ensure(c=None):
    global _PROCESS,_LOCK
    c=c or config()
    if c.get('engine')!='llama.cpp':return
    async with httpx.AsyncClient(timeout=2,trust_env=False) as client:
        try:
            r=await client.get('http://127.0.0.1:11436/v1/models',headers={'Authorization':'Bearer '+c['key']})
            if r.status_code==200:return
        except httpx.HTTPError:pass
    if _PROCESS is None or _PROCESS.poll() is not None:
        if not Path(c['binary']).is_file() or not Path(c['gguf']).is_file():raise ValueError('Install the llama.cpp runtime in Workspace → Engine & downloads')
        log=(root()/'llama-server.log').open('ab')
        try:_PROCESS=subprocess.Popen([c['binary'],'-m',c['gguf'],'--host','127.0.0.1','--port','11436','--api-key',c['key'],'--alias',c['model'],'-c','4096','-np','1','-t',str(max(1,min(4,os.cpu_count() or 2))),'--jinja']+(['--mmproj',c['mmproj']] if c.get('mmproj') else []),stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        finally:log.close()
    for _ in range(120):
        await asyncio.sleep(.5)
        if _PROCESS.poll() is not None:raise ValueError('llama.cpp could not start. See runtime/llama-server.log; verify CPU support and free RAM.')
        try:
            async with httpx.AsyncClient(timeout=2,trust_env=False) as client:
                r=await client.get('http://127.0.0.1:11436/v1/models',headers={'Authorization':'Bearer '+c['key']})
                if r.status_code==200:
                    if config().get('key')==c.get('key'):save(c|{'pid':_PROCESS.pid})
                    return
        except httpx.HTTPError:pass
    raise ValueError('llama.cpp model load timed out')

def stop_owned(c):
    import psutil
    try:
        p=psutil.Process(c.get('pid',0))
        if Path(p.exe()).resolve()==Path(c.get('binary','')).resolve() and c.get('key') in p.cmdline():p.terminate();p.wait(10)
    except (psutil.Error,OSError,ValueError):pass

async def choose(store,engine,profile='fast',progress=None):
    global _PROCESS
    if engine not in {'ollama','llama.cpp'}:raise ValueError('Choose Ollama or llama.cpp')
    token=await store.acquire_async(progress=progress)
    report=progress
    def progress(message):
        with store.db() as db:db.execute('UPDATE lease SET expires=? WHERE token=?',(time.time()+720,token))
        if report:report(message)
    try:
        previous=config()
        ollama_model=previous.get('ollama_model') or (store.settings()['model'] if previous.get('engine')=='ollama' else 'qwen3:0.6b')
        if engine=='ollama':
            stop_owned(previous)
            save({'engine':'ollama','ollama_model':ollama_model,**({'cached':previous} if previous.get('engine')=='llama.cpp' else {})})
            store.save_settings({'model':ollama_model})
            if _PROCESS and _PROCESS.poll() is None:_PROCESS.terminate()
            _PROCESS=None
        else:
            old=config();cached=old.get('cached',old)
            c=cached if cached.get('profile')==profile and cached.get('binary') and Path(cached['binary']).is_file() and Path(cached.get('gguf','')).is_file() else await install(profile,progress)
            stop_owned(previous)
            if _PROCESS and _PROCESS.poll() is None:_PROCESS.terminate();_PROCESS.wait(timeout=10)
            _PROCESS=None
            if progress:progress('Loading local GGUF model')
            c=dict(c);c['ollama_model']=ollama_model
            await ensure(c);c['pid']=_PROCESS.pid if _PROCESS else c.get('pid');save(c);store.save_settings({'model':c['model']})
        return status()
    except httpx.HTTPError as exc:
        raise ValueError('Component download failed. Check internet access to GitHub and Hugging Face, then retry.') from exc
    finally:store.release(token)
