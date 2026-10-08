"""Optional speech packages kept outside the Nila binary environment."""
import asyncio,json,os,shutil,sys
from pathlib import Path
from .local_runtime import root

def python_path():return root()/'speech-env'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
def status():return {'installed':python_path().is_file() and (root()/'speech'/'ready').is_file(),'stt':'Whisper base · multilingual','tts':'Piper Lessac · English'}
async def process(args,input=None,timeout=1800):
    p=await asyncio.create_subprocess_exec(*map(str,args),stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,creationflags=getattr(subprocess_flags(),'CREATE_NO_WINDOW',0))
    try:
        stdout,stderr=await asyncio.wait_for(p.communicate(input),timeout)
        if p.returncode:
            root().mkdir(parents=True,exist_ok=True)
            (root()/'speech-install.log').write_bytes(stderr[-16000:])
            raise ValueError('Speech component failed. Check runtime/speech-install.log for dependency or microphone details.')
        return stdout
    finally:
        if p.returncode is None:p.kill();await p.wait()
def subprocess_flags():
    import subprocess
    return subprocess
async def install(progress=None):
    if status()['installed']:return status()
    root().mkdir(parents=True,exist_ok=True)
    candidates=[[sys.executable]] if not getattr(sys,'frozen',False) else []
    if os.name=='nt' and shutil.which('py'):candidates += [['py','-3.12'],['py','-3']]
    candidates += [[p] for p in [shutil.which('python3'),shutil.which('python')] if p]
    chosen=None
    for cmd in candidates:
        try:await process(cmd+['-c','import sys; assert sys.version_info >= (3,10)'],timeout=20);chosen=cmd;break
        except (ValueError,OSError):pass
    if not chosen and os.name=='nt' and shutil.which('winget'):
        if progress:progress('Installing Python 3.12 for optional speech tools')
        await process(['winget','install','--id','Python.Python.3.12','-e','--scope','user','--silent','--accept-package-agreements','--accept-source-agreements'])
        path=Path(os.environ['LOCALAPPDATA'])/'Programs/Python/Python312/python.exe'
        if path.is_file():chosen=[str(path)]
    if not chosen:raise ValueError('Install Python 3.10+ to enable the optional speech pack')
    if progress:progress('Preparing isolated speech tools')
    await process(chosen+['-m','venv',str(root()/'speech-env')])
    await process([python_path(),'-m','pip','install','faster-whisper>=1.1,<2','piper-tts>=1.3,<2'])
    if progress:progress('Downloading Whisper base and Piper English voice')
    await worker({'action':'install'},timeout=1800)
    (root()/'speech'/'ready').touch();return status()
async def worker(payload,timeout=180):
    if payload['action']!='install' and not status()['installed']:raise ValueError('Install the Speech pack in Workspace → Engine & downloads first')
    # Copy the bundled worker from its importable source, including frozen distributions.
    import inspect
    from . import speech_worker
    target=root()/'speech-worker.py';target.write_text((Path(sys._MEIPASS)/'nila/speech_worker.py').read_text(encoding='utf-8') if getattr(sys,'frozen',False) else inspect.getsource(speech_worker),encoding='utf-8')
    raw=await process([python_path(),target],json.dumps(payload|{'root':str(root()/'speech')}).encode(),timeout)
    return json.loads(raw)
