"""Stable GitHub Release updates, pinned to the release tag commit."""
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
            r=c.get(API+'/releases/latest');r.raise_for_status();release=r.json()
            tag=release['tag_name']
            if release.get('draft') or release.get('prerelease') or not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+',tag):raise ValueError('Invalid stable release')
            r=c.get(API+'/commits/'+tag);r.raise_for_status();sha=r.json()['sha']
            from . import __version__
            newer=tuple(map(int,tag[1:].split('.')))>tuple(map(int,__version__.split('.')))
            if not re.fullmatch('[a-f0-9]{40}',sha): raise ValueError('Invalid commit')
        return state|{'latest':sha,'version':tag,'available':newer and sha!=state['commit'],'online':True,'message':'Latest stable GitHub Release checked. Updates take effect on restart.'}
    except (httpx.HTTPError,ValueError,KeyError):
        return state|{'online':False,'available':False,'message':'Update check unavailable. Offline features remain available.'}

def update_failure(log, root):
    """Report an OS policy denial without bypassing executable validation."""
    if 'another nila installation/update is running' in log.lower():
        return {'status':'busy','message':'Another Nila installation/update is running. Let it finish before retrying. Do not delete install.lock.', 'log_path':str(root/'last-update.log')}
    blocked = any(marker in log.lower() for marker in (
        'nila-021', 'application control policy has blocked',
        'blocked by group policy', 'blocked by your system administrator',
    ))
    result = {'status':'failed','log_path':str(root/'last-update.log')}
    if blocked:
        return result | {'error_code':'NILA-021','message':
            'NILA-021: Windows application-control policy blocked the new executable. '
            'The update was not activated. Ask the device/policy administrator to review '
            'CodeIntegrity events and approve a trusted build, or use a properly signed '
            'distribution accepted by that policy. Nila does not disable security controls.'}
    return result | {'message':'Release installation failed; current installation retained. See last-update.log in NilaApp.'}

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
            meta=c.get(API+'/contents/scripts/update-release.ps1',params={'ref':sha});meta.raise_for_status()
            raw=c.get(f'https://raw.githubusercontent.com/{REPO}/{sha}/scripts/update-release.ps1');raw.raise_for_status()
            data=raw.content
            if len(data)>100000 or hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=meta.json()['sha']:
                raise RuntimeError('NILA-020: Installer integrity check failed')
        root=Path(state['root']);fd,name=tempfile.mkstemp(prefix='nila-update-',suffix='.ps1',dir=root)
        with os.fdopen(fd,'wb') as f:f.write(data)
        try:
            result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',name,'-Commit',sha,'-ReleaseTag',state['version'],'-UpdateOnly'],capture_output=True,text=True,timeout=1800,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            log=(result.stdout+'\n'+result.stderr)[-16000:]
            (root/'last-update.log').write_text(log,encoding='utf-8')
            if result.returncode: return update_failure(log,root)
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

def rollback(store):
    """Select a previously installed binary under the same installer lock. No network."""
    root=install_root()
    if not root:raise ValueError('Rollback requires a managed Windows installation')
    # PowerShell holds the same Windows file-share lock used by install.ps1.
    script=r'''
$ErrorActionPreference='Stop'
$root=Join-Path $env:LOCALAPPDATA 'NilaApp'
$lock=[IO.File]::Open((Join-Path $root 'install.lock'),'OpenOrCreate','ReadWrite','None')
try {
  $previous=(Get-Content (Join-Path $root 'previous.txt') -Raw).Trim()
  if ($previous -notmatch '^[a-f0-9]{40}$') { throw 'Invalid previous installation' }
  $binary=Join-Path $root "versions\$previous\nila.exe"
  if (-not (Test-Path $binary)) { throw 'Previous binary is unavailable' }
  & $binary --version | Out-Null
  if ($LASTEXITCODE) { throw 'Previous binary failed its smoke check' }
  $pending=Join-Path $root 'rollback.pending'
  [IO.File]::WriteAllText($pending,$previous)
  [IO.File]::Replace($pending,(Join-Path $root 'current.txt'),(Join-Path $root 'previous.txt'))
} finally { $lock.Dispose() }
'''
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],capture_output=True,text=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise ValueError('Rollback failed. An update may be running or the previous binary is unavailable.')
    store.save_settings({'auto_update':False})
    return {'message':'Previous installation selected. Restart Nila and its worker. Automatic updates are paused until you re-enable them.'}
