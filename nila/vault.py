"""Authenticated encryption for local content; Windows key uses CurrentUser DPAPI."""
import ctypes
import os
import time
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken

PREFIX = 'enc:v1:'

def dpapi(data: bytes, decrypt=False) -> bytes:
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_ = [('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_byte))]
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_byte)))
    output = Blob()
    fn = ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    if not fn(ctypes.byref(source),None,None,None,None,1,ctypes.byref(output)):
        raise OSError('NILA-010: Windows could not unlock the local encryption key.')
    try: return ctypes.string_at(output.pbData,output.cbData)
    finally: ctypes.windll.kernel32.LocalFree(output.pbData)

class Vault:
    def __init__(self,root:Path):
        path=root/'vault.key'
        lock=root/'vault-key.lock'
        for attempt in range(100):
            try:
                fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
                os.close(fd)
                break
            except FileExistsError:
                time.sleep(.05)
        else: raise RuntimeError('NILA-010: Key creation is busy. If no Nila process is running, remove vault-key.lock and retry.')
        try:
            if not path.exists():
                # Do not silently replace a missing key for an encrypted database.
                db=root/'nila.db'
                if any(p.exists() and PREFIX.encode() in p.read_bytes() for p in (db,root/'nila.db-wal')):
                    raise RuntimeError('NILA-010: Encryption key is missing. Restore vault.key; do not reset your database.')
                key=Fernet.generate_key()
                payload=(b'DPAPI1:'+dpapi(key)) if os.name=='nt' else b'FILE1:'+key
                with os.fdopen(os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'wb') as f:
                    f.write(payload)
            payload=path.read_bytes()
            if payload.startswith(b'DPAPI1:'):
                if os.name!='nt': raise RuntimeError('NILA-010: This key is bound to the original Windows account.')
                key=dpapi(payload[7:],True)
            elif payload.startswith(b'FILE1:'): key=payload[6:]
            else: raise RuntimeError('NILA-010: Unknown encryption key format.')
            self.fernet=Fernet(key)
        finally: lock.unlink(missing_ok=True)
    def seal(self,value):
        return PREFIX+self.fernet.encrypt(str(value).encode()).decode()
    def open(self,value):
        if not value.startswith(PREFIX): return value
        try: return self.fernet.decrypt(value[len(PREFIX):].encode()).decode()
        except InvalidToken as exc: raise RuntimeError('NILA-010: Cannot decrypt local data. Restore the original vault.key.') from exc
