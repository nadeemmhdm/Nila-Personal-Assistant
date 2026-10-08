"""Executed by an isolated optional Python environment, never by a shell."""
import json,sys,wave
from pathlib import Path

def main():
    data=json.load(sys.stdin);root=Path(data['root']);root.mkdir(parents=True,exist_ok=True)
    if data['action']=='install':
        from faster_whisper import WhisperModel
        WhisperModel('base',device='cpu',compute_type='int8',download_root=str(root/'whisper'))
        import subprocess
        subprocess.run([sys.executable,'-m','piper.download_voices','en_US-lessac-medium','--download-dir',str(root)],check=True,stdout=sys.stderr)
        print('{}')
    elif data['action']=='transcribe':
        from faster_whisper import WhisperModel
        model=WhisperModel('base',device='cpu',compute_type='int8',download_root=str(root/'whisper'),local_files_only=True)
        parts,_=model.transcribe(data['file'],language=data.get('language') or None,beam_size=3)
        print(json.dumps({'text':' '.join(p.text.strip() for p in parts)},ensure_ascii=False))
    elif data['action']=='speak':
        from piper import PiperVoice
        voice=PiperVoice.load(str(root/'en_US-lessac-medium.onnx'))
        with wave.open(data['file'],'wb') as f:voice.synthesize_wav(data['text'],f)
        print('{}')
if __name__=='__main__':main()
