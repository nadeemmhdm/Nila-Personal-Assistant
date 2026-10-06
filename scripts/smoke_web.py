"""Exercise the packaged HTTP server, not just files in the build directory."""
import os,socket,subprocess,tempfile,time,urllib.request
from pathlib import Path
from nila.storage import Store
with tempfile.TemporaryDirectory() as folder:
    Store(folder).save_settings({'auto_update':False})
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    binary=Path('dist')/('nila.exe' if os.name=='nt' else 'nila')
    process=subprocess.Popen([str(binary.resolve()),'web','--no-open','--port',str(port)],env=os.environ|{'NILA_DATA_DIR':folder},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for attempt in range(80):
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/nila-logo.png',timeout=1) as response:
                    assert response.headers['Content-Type']=='image/png'
                    assert response.read(8)==b'\x89PNG\r\n\x1a\n'
                break
            except OSError:
                if process.poll() is not None:raise RuntimeError('Packaged server exited')
                time.sleep(.5)
        else:raise RuntimeError('Packaged server did not become ready')
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/about/',timeout=5) as response:assert b'error-search' in response.read()
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/about/guide-license.html',timeout=5) as response:assert b'MIT License' in response.read()
        print('PASS packaged logo, About page and license guide')
    finally:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
