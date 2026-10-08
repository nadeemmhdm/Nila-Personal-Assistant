import {Mic,MicOff,Play,Square,X} from 'lucide-react';
import {useEffect,useRef,useState} from 'react';
let activeSpeech='';
let localAudio:HTMLAudioElement|null=null;
function stopAudio(){if(localAudio){localAudio.pause();URL.revokeObjectURL(localAudio.src)}localAudio=null;if('speechSynthesis' in window)speechSynthesis.cancel()}
function announceSpeech(id:string){activeSpeech=id;window.dispatchEvent(new Event('nila-speech'))}
export function ReadAloud({id,text,onError}:{id:string;text:string;onError:(t:string)=>void}){
 const [playing,setPlaying]=useState(false),ticket=useRef(0);
 useEffect(()=>{const sync=()=>setPlaying(activeSpeech===id);window.addEventListener('nila-speech',sync);return()=>{ticket.current++;window.removeEventListener('nila-speech',sync);if(activeSpeech===id){stopAudio();announceSpeech('')}}},[id]);
 async function toggle(){
  const current=++ticket.current;
  if(activeSpeech===id){stopAudio();announceSpeech('');return}
  stopAudio();announceSpeech(id);
  try{
   const state=await (await fetch('/api/runtime')).json();
   if(state.speech?.installed&&!/[\u0d00-\u0d7f]/.test(text)){
    const r=await fetch('/api/runtime/speak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:text.replace(/[#*_`]/g,'').slice(0,12000)})});
    if(!r.ok)throw Error((await r.json()).detail);
    const url=URL.createObjectURL(await r.blob());
    if(current!==ticket.current||activeSpeech!==id){URL.revokeObjectURL(url);return}
    const audio=new Audio(url);localAudio=audio;
    audio.onended=()=>{URL.revokeObjectURL(url);if(activeSpeech===id)announceSpeech('')};
    audio.onerror=()=>{URL.revokeObjectURL(url);announceSpeech('');onError('Local speech playback failed')};
    await audio.play();return;
   }
  }catch(e:any){if(current===ticket.current){announceSpeech('');onError(e.message)}return}
  if(current!==ticket.current||activeSpeech!==id)return;
  if(!('speechSynthesis' in window)){onError('Read aloud is unavailable in this browser.');return}
  stopAudio();announceSpeech(id);
  let voices=speechSynthesis.getVoices().filter(v=>v.localService);
  if(!voices.length)voices=await new Promise<SpeechSynthesisVoice[]>(resolve=>{let timer:number;const ready=()=>{window.clearTimeout(timer);speechSynthesis.removeEventListener('voiceschanged',ready);resolve(speechSynthesis.getVoices().filter(v=>v.localService))};timer=window.setTimeout(ready,1800);speechSynthesis.addEventListener('voiceschanged',ready)});
  if(current!==ticket.current||activeSpeech!==id)return;
  const lang=/[\u0d00-\u0d7f]/.test(text)?'ml':'en',voice=voices.find(v=>v.lang.toLowerCase().startsWith(lang));
  if(!voice){announceSpeech('');onError(`Install a local ${lang==='ml'?'Malayalam':'English'} text-to-speech voice in Windows language settings, then reopen Nila.`);return}
  const u=new SpeechSynthesisUtterance(text.replace(/[#*_`]/g,''));u.voice=voice;u.lang=voice.lang;
  u.onend=()=>{if(activeSpeech===id&&current===ticket.current)announceSpeech('')};u.onerror=e=>{if(activeSpeech===id&&current===ticket.current){announceSpeech('');if(e.error!=='canceled'&&e.error!=='interrupted')onError('Speech playback stopped. Check the installed local voice.')}};speechSynthesis.speak(u);
 }
 return <button className="read-aloud" aria-label={playing?'Stop reading':'Read aloud'} aria-pressed={playing} onClick={toggle}>{playing?<Square size={14}/>:<Play size={14}/>} {playing?'Stop':'Read aloud'}</button>
}
export function VoiceInput({disabled,onText,onError}:{disabled:boolean;onText:(t:string)=>void;onError:(t:string)=>void}){
 const [open,setOpen]=useState(false),[listening,setListening]=useState(false),[busy,setBusy]=useState(false),[native,setNative]=useState(false),[status,setStatus]=useState('Audio stays on this device.'),[language,setLanguage]=useState(()=>localStorage.getItem('nila-voice-language')||navigator.language||'en-US');
 const recorder=useRef<MediaRecorder|null>(null),micStream=useRef<MediaStream|null>(null);
 const recognition=useRef<any>(null),capture=useRef(''),alive=useRef(true),attempt=useRef(0);
 useEffect(()=>{alive.current=true;fetch('/api/voice/status').then(r=>r.json()).then(d=>{if(alive.current)setNative(d.native)}).catch(()=>{});return()=>{alive.current=false;attempt.current++;if(recorder.current?.state==='recording')recorder.current.stop();micStream.current?.getTracks().forEach(t=>t.stop());recognition.current?.abort();if(capture.current)fetch('/api/voice/listen/'+capture.current,{method:'DELETE',keepalive:true}).catch(()=>{})}},[]);
 function stop(){attempt.current++;if(recorder.current?.state==='recording')recorder.current.stop();micStream.current?.getTracks().forEach(t=>t.stop());recognition.current?.abort();if(capture.current){fetch('/api/voice/listen/'+capture.current,{method:'DELETE'}).catch(()=>{});capture.current=''}setListening(false);setBusy(false);setStatus('Microphone stopped.')}
 async function start(){
  if(recorder.current?.state==='recording'){recorder.current.stop();return}
  if(listening||busy){stop();return}setOpen(true);setBusy(true);const serial=++attempt.current;
  try{
   const pack=await (await fetch('/api/runtime')).json();
   if(pack.speech?.installed){
    const stream=await navigator.mediaDevices.getUserMedia({audio:true});
    if(!alive.current||serial!==attempt.current){stream.getTracks().forEach(t=>t.stop());return}
    micStream.current=stream;const r=new MediaRecorder(stream);recorder.current=r;const chunks:BlobPart[]=[];
    r.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
    const timer=window.setTimeout(()=>{if(r.state==='recording')r.stop()},20000);
    r.onstop=async()=>{clearTimeout(timer);stream.getTracks().forEach(t=>t.stop());recorder.current=null;
     if(!alive.current||serial!==attempt.current)return;
     setListening(false);setBusy(true);setStatus('Transcribing locally…');
     try{const blob=new Blob(chunks,{type:r.mimeType});if(blob.size>5*1024*1024)throw Error('Audio exceeds 5 MB');
      const data=await new Promise<string>((resolve,reject)=>{const f=new FileReader();f.onload=()=>resolve(String(f.result).split(',')[1]);f.onerror=reject;f.readAsDataURL(blob)});
      const response=await fetch('/api/runtime/transcribe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({data})});const result=await response.json();if(!response.ok)throw Error(result.detail);
      if(alive.current&&serial===attempt.current){onText(result.text);setStatus('Text added. Review before sending.')}
     }catch(e:any){if(alive.current)setStatus(e.message)}finally{if(alive.current)setBusy(false)}
    };r.start();setListening(true);setStatus('Listening locally · click microphone to finish, or wait 20 seconds.');return;
   }
   const API=(window as any).SpeechRecognition||(window as any).webkitSpeechRecognition;
   if(!API||!('processLocally' in new API()))throw Error('This browser has no on-device speech support. Use Windows microphone below, or a browser with local speech recognition.');
   let lang=language,state=API.available?await API.available({langs:[lang],processLocally:true}):'available';
   if(state==='unavailable'&&lang.toLowerCase().startsWith('en')&&lang!=='en-US'){lang='en-US';state=await API.available({langs:[lang],processLocally:true});setLanguage(lang);localStorage.setItem('nila-voice-language',lang);setStatus('Using the supported English (US) local speech pack.')}
   if(state==='unavailable')throw Error('This browser has no local pack for '+lang+'. Choose another language, or use an installed Windows recognizer.');
   if(state!=='available'){
    if(!API.install)throw Error('This browser cannot install a local speech pack. Try Windows microphone.');
    setStatus('Downloading the local '+lang+' speech pack… Internet is needed only for this download.');
    const ok=await API.install({langs:[lang],processLocally:true});if(!ok)throw Error('Speech pack download did not finish. Check internet and retry.');
   }
   if(!alive.current||serial!==attempt.current)return;
   const r=new API();r.processLocally=true;r.lang=lang;r.interimResults=false;r.continuous=false;
   r.onresult=(e:any)=>{if(alive.current&&serial===attempt.current){const text=Array.from(e.results as any).map((v:any)=>v[0].transcript).join(' ');onText(text);setStatus('Text added. Review it before sending.')}};
   r.onerror=(e:any)=>{if(alive.current){setListening(false);setStatus(e.error==='not-allowed'?'Allow microphone access in the browser’s site permissions.':'Microphone stopped: '+e.error+'. Try another local language or Windows microphone.')}};
   r.onend=()=>{if(alive.current)setListening(false)};recognition.current=r;r.start();setListening(true);setStatus('Listening locally in '+lang+'…');
  }catch(e:any){if(alive.current)setStatus(e.message)}finally{if(alive.current&&serial===attempt.current)setBusy(false)}
 }
 async function nativeStart(){setOpen(true);setListening(true);const serial=++attempt.current,id=crypto.randomUUID();capture.current=id;setStatus('Listening through the Windows microphone for up to 20 seconds…');try{const r=await fetch('/api/voice/listen',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,language})});const d=await r.json();if(!r.ok)throw Error(d.detail||'Windows speech failed');if(alive.current&&serial===attempt.current){if(d.text)onText(d.text);setStatus(d.text?'Text added. Review before sending.':'No speech detected. Check the Windows microphone and retry.')}}catch(e:any){if(alive.current&&serial===attempt.current)setStatus(e.message)}finally{if(capture.current===id)capture.current='';if(alive.current&&serial===attempt.current)setListening(false)}}
 return <div className="voice-wrap"><button type="button" className="icon" title={listening||busy?'Stop microphone':'Microphone'} aria-label={listening||busy?'Stop microphone':'Microphone'} disabled={disabled&&!listening&&!busy} aria-pressed={listening} onClick={start}>{listening||busy?<MicOff size={17}/>:<Mic size={17}/>}</button>{open&&<div className="voice-panel" role="region" aria-label="Voice input"><button type="button" className="icon" aria-label="Close voice settings" onClick={()=>{stop();setOpen(false)}}><X size={15}/></button><label>Speech language<select value={language} disabled={listening||busy} onChange={e=>{setLanguage(e.target.value);localStorage.setItem('nila-voice-language',e.target.value)}}>{[...new Set([language,'en-US','en-IN','ml-IN','hi-IN','en-GB'])].map(l=><option key={l} value={l}>{l}</option>)}</select></label><p role="status">{status}</p><button type="button" disabled={disabled||listening||busy} onClick={start}>Use browser microphone</button>{native&&<button type="button" disabled={disabled||listening||busy} onClick={nativeStart}>Use Windows microphone</button>}<p>Only installed/supported local recognizers are used. Malayalam availability varies by browser and Windows language pack.</p></div>}</div>
}
