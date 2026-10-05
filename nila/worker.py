"""Per-user Telegram bridge worker; Windows installer registers this at login."""
import asyncio
import json
import os
import time
from contextlib import suppress
from .telegram_bot import Bridge
from .updater import start_auto_update

async def run_worker(store):
    lock=open(store.root/'worker.lock','a+b')
    try:
        if os.name=='nt':
            import msvcrt
            lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
            try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
            except OSError:return
        else:
            import fcntl
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:return
        bridge=Bridge(store)
        task=asyncio.create_task(bridge.loop())
        stamp=store.root/'worker-status.json'
        start_auto_update(store)
        try:
            while True:
                temp=store.root/'worker-status.pending'
                temp.write_text(json.dumps({'pid':os.getpid(),'heartbeat':time.time()}))
                os.replace(temp,stamp)
                await asyncio.sleep(3)
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):await task
            stamp.unlink(missing_ok=True)
    finally:lock.close()

def worker_status(store):
    try:
        data=json.loads((store.root/'worker-status.json').read_text())
        return data|{'running':time.time()-data['heartbeat']<12}
    except (OSError,ValueError,KeyError):return {'running':False}
