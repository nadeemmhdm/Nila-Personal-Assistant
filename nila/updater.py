"""Commit-based Windows updates from the fixed upstream; no release dependency."""
import hashlib
import json
import os
import re
import subprocess
import tempfile
import sys
import threading
import time
from pathlib import Path
import httpx

REPO='nadeemmhdm/Nila-Personal-Assistant'
API='https://api.github.com/repos/'+REPO
_lock=threading.Lock()

def install_root():
    if os.name!='nt': return None
    root=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'NilaApp'
    return root if (root/'current.txt').exists() else None

def installed():
    root=install_root()
    if not root: return {'managed':False,'commit':None,'message':'Automatic installation updates require the Windows single-command installer.'}
    sha=(root/'current.txt').read_text().strip()
    if not re.fullmatch('[a-f0-9]{40}',sha):raise RuntimeError('NILA-020: Invalid installation pointer')
    return {'managed':True,'commit':sha,'root':str(root)}

def check():
    state=installed()
    try:
        with httpx.Client(timeout=10,follow_redirects=False,headers={'User-Agent':'Nila-Updater','Accept':'application/vnd.github+json'}) as c:
            r=c.get(API+'/commits/main');r.raise_for_status();data=r.json()
            sha=data['sha']
            if not re.fullmatch('[a-f0-9]{40}',sha): raise ValueError('Invalid commit')
        return state|{'latest':sha,'available':sha!=state['commit'],'online':True,'message':'Latest main-branch commit checked. Updates are applied to the next launch.'}
    except (httpx.HTTPError,ValueError,KeyError):
        return state|{'online':False,'available':False,'message':'Update check unavailable. Offline features remain available.'}

def apply_update():
    if not _lock.acquire(blocking=False): return {'status':'busy','message':'Update already running.'}
    try:
        state=check()
        if not state['managed']: return state|{'status':'unsupported'}
        if not state.get('online'): return state|{'status':'offline'}
        if not state.get('available'): return state|{'status':'current'}
        sha=state['latest']
        with httpx.Client(timeout=30,follow_redirects=False,headers={'User-Agent':'Nila-Updater'}) as c:
            # Verify installer bytes against the Git blob of the selected immutable commit.
            meta=c.get(API+'/contents/scripts/install.ps1',params={'ref':sha});meta.raise_for_status()
            raw=c.get(f'https://raw.githubusercontent.com/{REPO}/{sha}/scripts/install.ps1');raw.raise_for_status()
            data=raw.content
            if len(data)>100000 or hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=meta.json()['sha']:
                raise RuntimeError('NILA-020: Installer integrity check failed')
        root=Path(state['root']);fd,name=tempfile.mkstemp(prefix='nila-update-',suffix='.ps1',dir=root)
        with os.fdopen(fd,'wb') as f:f.write(data)
        try:
            result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',name,'-Commit',sha,'-UpdateOnly'],capture_output=True,text=True,timeout=1800,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            log=(result.stdout+'\n'+result.stderr)[-16000:]
            (root/'last-update.log').write_text(log,encoding='utf-8')
            if result.returncode: return {'status':'failed','message':'Update build failed; current installation retained. See last-update.log in NilaApp.'}
            return {'status':'updated','message':'Update installed. Restart Nila to use it.','commit':sha}
        finally: Path(name).unlink(missing_ok=True)
    except (httpx.HTTPError,ValueError,KeyError,OSError,subprocess.TimeoutExpired,RuntimeError):
        return {'status':'failed','message':'Update failed. Existing installation remains available; retry from System.'}
    finally:_lock.release()

def auto_update(store):
    if not store.settings()['auto_update'] or not install_root():return
    root=install_root();stamp=root/'last-check.txt'
    try:
        if stamp.exists() and time.time()-float(stamp.read_text())<86400:return
        stamp.write_text(str(time.time()))
        result=apply_update()
        (root/'update-status.json').write_text(json.dumps(result),encoding='utf-8')
    except (OSError,ValueError):pass

def start_auto_update(store):
    if not store.settings()['auto_update'] or not install_root() or not getattr(sys,'frozen',False): return
    root=install_root()
    try:
        stamp=root/'last-check.txt'
        if stamp.exists() and time.time()-float(stamp.read_text())<86400:return
        with open(root/'auto-update-launch.log','a',encoding='utf-8') as log:
            subprocess.Popen([sys.executable,'update','--auto'],stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'DETACHED_PROCESS',0),close_fds=True)
    except (OSError,ValueError):pass
