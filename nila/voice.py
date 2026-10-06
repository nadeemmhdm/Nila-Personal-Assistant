"""Windows offline speech using installed System.Speech voices/recognizers."""
import json,os,subprocess

SCRIPT=r'''
$ErrorActionPreference='Stop'
[Console]::InputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$value=[Console]::In.ReadToEnd() | ConvertFrom-Json
Add-Type -AssemblyName System.Speech
if ($value.action -eq 'speak') {
  $speech=New-Object System.Speech.Synthesis.SpeechSynthesizer
  try { $speech.Speak([string]$value.text) } finally { $speech.Dispose() }
} else {
  $installed=[System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers()
  $matching=$installed | Where-Object { $_.Culture.Name -eq $value.language } | Select-Object -First 1
  if (-not $matching -and $value.language -like 'en-*') { $matching=$installed | Where-Object { $_.Culture.Name -like 'en-*' } | Select-Object -First 1 }
  if ($value.language -and -not $matching) { throw 'Requested speech language is not installed' }
  if ($matching) { $recognizer=[System.Speech.Recognition.SpeechRecognitionEngine]::new($matching) }
  else { $recognizer=New-Object System.Speech.Recognition.SpeechRecognitionEngine }
  try {
    $recognizer.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
    $recognizer.SetInputToDefaultAudioDevice()
    $recognizer.InitialSilenceTimeout=[TimeSpan]::FromSeconds(10)
    $recognizer.EndSilenceTimeout=[TimeSpan]::FromSeconds(1)
    $result=$recognizer.Recognize([TimeSpan]::FromSeconds(20))
    if ($result) { [Console]::Write($result.Text) }
  } finally { $recognizer.Dispose() }
}
'''

def run(action,text=''):
    if os.name!='nt':raise ValueError('Native CLI voice currently requires Windows. Web voice depends on your browser’s on-device support.')
    if action not in {'speak','listen'}:raise ValueError('Unknown voice action')
    script=SCRIPT

    try:
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],input=json.dumps({'action':action,'text':text[:6000]}),capture_output=True,text=True,encoding='utf-8',timeout=180 if action=='speak' else 30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except (OSError,subprocess.TimeoutExpired):raise ValueError('Local speech timed out or is unavailable. Check installed Windows speech language packs and your microphone.') from None
    if result.returncode:raise ValueError('Local speech could not start. Install a Windows speech voice/recognizer for your language and allow microphone access.')
    return result.stdout.strip()


def register(app):
    import asyncio,re
    from fastapi import Body,HTTPException
    active={}
    app.state.voice_tasks=active
    @app.get('/api/voice/status')
    def status():return {'native':os.name=='nt'}
    @app.delete('/api/voice/listen/{iid}')
    async def stop(iid:str):
        task=active.get(iid)
        if task:task.cancel()
        return {'stopped':bool(task)}
    @app.post('/api/voice/listen')
    async def listen(id:str=Body(),language:str=Body(default='en-US')):
        if os.name!='nt':raise HTTPException(400,'Windows microphone is available only on Windows.')
        if not re.fullmatch(r'[a-zA-Z0-9-]{1,64}',id) or not re.fullmatch(r'[a-zA-Z-]{2,30}',language):raise HTTPException(400,'Invalid capture or language')
        if active:raise HTTPException(409,'Another microphone capture is running.')
        async def capture():
            process=None
            try:
                process=await asyncio.create_subprocess_exec('powershell.exe','-NoProfile','-NonInteractive','-Command',SCRIPT,stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                output,_=await asyncio.wait_for(process.communicate(json.dumps({'action':'listen','language':language}).encode()),30)
                if process.returncode:raise HTTPException(400,'Install a Windows speech recognition pack for this language and enable microphone access in Windows Settings.')
                return {'text':output.decode('utf-8').strip()}
            except (OSError,TimeoutError):raise HTTPException(400,'Windows speech timed out or is unavailable. Check the microphone and installed recognition language.')
            finally:
                if process and process.returncode is None:
                    process.kill();await process.wait()
        task=asyncio.create_task(capture());active[id]=task
        try:return await task
        except asyncio.CancelledError:return {'text':'','stopped':True}
        finally:active.pop(id,None)
