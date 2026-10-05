"""Windows offline speech using installed System.Speech voices/recognizers."""
import json,os,subprocess

def run(action,text=''):
    if os.name!='nt':raise ValueError('Native CLI voice currently requires Windows. Web voice depends on your browser’s on-device support.')
    if action not in {'speak','listen'}:raise ValueError('Unknown voice action')
    script=r'''
$ErrorActionPreference='Stop'
[Console]::InputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$value=[Console]::In.ReadToEnd() | ConvertFrom-Json
Add-Type -AssemblyName System.Speech
if ($value.action -eq 'speak') {
  $speech=New-Object System.Speech.Synthesis.SpeechSynthesizer
  try { $speech.Speak([string]$value.text) } finally { $speech.Dispose() }
} else {
  $recognizer=New-Object System.Speech.Recognition.SpeechRecognitionEngine
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
    try:
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],input=json.dumps({'action':action,'text':text[:6000]}),capture_output=True,text=True,encoding='utf-8',timeout=180 if action=='speak' else 30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except (OSError,subprocess.TimeoutExpired):raise ValueError('Local speech timed out or is unavailable. Check installed Windows speech language packs and your microphone.') from None
    if result.returncode:raise ValueError('Local speech could not start. Install a Windows speech voice/recognizer for your language and allow microphone access.')
    return result.stdout.strip()
