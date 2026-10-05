import {useEffect,useRef,useState} from 'react';
export function speak(text:string){
 if(!('speechSynthesis' in window))throw Error('Read aloud is unavailable in this browser.');
 const voices=speechSynthesis.getVoices().filter(v=>v.localService);
 if(!voices.length)throw Error('Install a local speech voice in your operating-system language settings, then reopen Nila.');
 speechSynthesis.cancel();const utterance=new SpeechSynthesisUtterance(text.replace(/[#*_`]/g,''));utterance.voice=voices.find(v=>v.lang.toLowerCase().startsWith(/[\u0d00-\u0d7f]/.test(text)?'ml':'en'))||voices[0];speechSynthesis.speak(utterance);
}
export function VoiceInput({disabled,onText,onError}:{disabled:boolean;onText:(t:string)=>void;onError:(t:string)=>void}){
 const [listening,setListening]=useState(false),[needsPack,setNeedsPack]=useState(false),[installing,setInstalling]=useState(false);const recognition=useRef<any>(null);
 useEffect(()=>{window.speechSynthesis?.getVoices();return()=>{recognition.current?.abort();window.speechSynthesis?.cancel()}},[]);
 async function toggle(){
  if(listening){recognition.current?.stop();return}
  const API=(window as any).SpeechRecognition||(window as any).webkitSpeechRecognition;
  if(!API){onError('Local speech recognition is unavailable in this browser. You can still type.');return}
  const r=new API();
  if(!('processLocally' in r)){onError('This browser cannot guarantee local speech recognition. Nila will not upload your microphone audio. Use a browser with on-device speech support.');return}
  try{
   r.processLocally=true;r.lang=navigator.language||'en-US';
   if(API.available){const state=await API.available({langs:[r.lang],processLocally:true});if(state!=='available'){setNeedsPack(state==='downloadable'||state==='downloading');onError('Local speech language pack is '+state+'. Voice input stays off until the pack is ready.');return}}
   r.interimResults=false;r.continuous=false;r.onresult=(e:any)=>onText(e.results[0][0].transcript);r.onerror=(e:any)=>{setListening(false);onError('Voice input stopped: '+e.error)};r.onend=()=>setListening(false);recognition.current=r;r.start();setListening(true);
  }catch{onError('Could not start local speech recognition. Check microphone permission and language support.')}
 }
 async function installPack(){const API=(window as any).SpeechRecognition||(window as any).webkitSpeechRecognition;if(!API?.install)return;setInstalling(true);try{const ok=await API.install({langs:[navigator.language||'en-US'],processLocally:true});setNeedsPack(!ok);onError(ok?'Local speech pack ready. Click Microphone to begin.':'Speech pack could not be installed. Check browser language support and internet.')}catch{onError('Browser speech pack installation failed.')}finally{setInstalling(false)}}
 return <>{needsPack&&<button type="button" disabled={installing} onClick={installPack}>{installing?'Installing voice…':'Install local speech pack'}</button>}<button type="button" disabled={disabled} aria-pressed={listening} onClick={toggle}>{listening?'Stop microphone':'Microphone'}</button><button type="button" onClick={()=>window.speechSynthesis?.cancel()}>Stop speech</button></>
}
