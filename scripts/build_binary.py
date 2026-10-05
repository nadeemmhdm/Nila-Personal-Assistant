"""Build on the target OS. Windows produces nila.exe; Linux produces nila."""
import subprocess
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
static=root/'nila'/'static'
if not (static/'index.html').exists():
    raise SystemExit('Build Web UI first: cd web && npm ci && npm run build')
subprocess.run([sys.executable,'-m','PyInstaller','--clean','--noconfirm','--onefile','--name','nila','--collect-all','nila','--collect-all','uvicorn','--collect-all','ddgs','--collect-all','primp','--add-data',f'{static}:nila/static',str(root/'scripts'/'entry.py')],cwd=root,check=True)
