import {useEffect,useState} from 'react';
import {Cpu,Zap,Scale,Brain} from 'lucide-react';
import {ChoiceMenu} from './ChoiceMenu';
import {workApi} from './Workspace';
export function ModelSelector({compact=false,disabled=false,onError,onStatus}:{compact?:boolean;disabled?:boolean;onError:(message:string)=>void;onStatus?:(message:string)=>void}){
 const [data,setData]=useState<any>(null),[installed,setInstalled]=useState<any[]>([]),[switching,setSwitching]=useState(false);
 async function refresh(){const [d,s]=await Promise.all([workApi('/models/profiles'),workApi('/status')]);setData(d);setInstalled(s.models||[])}
 useEffect(()=>{const reload=()=>{refresh().catch(e=>onError(e.message))};reload();window.addEventListener('nila-settings-changed',reload);window.addEventListener('focus',reload);const t=setInterval(reload,15000);return()=>{window.removeEventListener('nila-settings-changed',reload);window.removeEventListener('focus',reload);clearInterval(t)}},[]);
 const value=data?.mode==='custom'?data.model:data?.mode||'';
 async function choose(value:string){setSwitching(true);onStatus?.('Checking model availability…');try{
 const response=await fetch('/api/models/activate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({value})});if(!response.ok)throw Error('Model change could not start.');
 const reader=response.body!.getReader(),decoder=new TextDecoder();let buffer='',done=false;
 function event(line:string){if(!line.trim())return;const item=JSON.parse(line);if(item.progress)onStatus?.(item.progress);if(item.error)throw Error(item.error);if(item.selection){setData(item.selection);onStatus?.('Model ready: '+item.selection.label);window.dispatchEvent(new Event('nila-settings-changed'))}if(item.done)done=true}
 while(true){const chunk=await reader.read();if(chunk.done)break;buffer+=decoder.decode(chunk.value,{stream:true});const lines=buffer.split('\n');buffer=lines.pop()||'';for(const line of lines)event(line)}buffer+=decoder.decode();event(buffer);if(!done)throw Error('Model change interrupted. Previous selection is retained unless activation already completed.');
 }catch(e:any){onError(e.message)}finally{setSwitching(false);refresh().catch(()=>{})}}
 const icons:Record<string,any>={fast:<Zap size={18}/>,medium:<Scale size={18}/>,current:<Brain size={18}/>};
 const options=[...(data?.profiles||[]).map((p:any)=>({value:p.id,label:p.label,icon:icons[p.id],detail:p.model+(installed.some(m=>m.name===p.model)?' · Installed':' · Download & use')})),...installed.filter(m=>!data?.profiles.some((p:any)=>p.model===m.name)).map(m=>({value:m.name,label:m.name,detail:'Installed custom model'}))];
 if(data?.mode==='custom'&&!options.some(o=>o.value===value))options.push({value,label:value,detail:'Download & use'});
 return <ChoiceMenu label={compact?'Local model':'Active model profile'} value={value} options={options} icon={<Cpu size={17}/>} compact={compact} disabled={disabled||switching||!data} onChange={choose}/>;

}
export function ProfileCards({installed,busy,load,download}:{installed:any[];busy:boolean;load:(value:string)=>void;download:(value:string)=>void}){
 const [data,setData]=useState<any>(null),[draft,setDraft]=useState<Record<string,string>>({}),[notice,setNotice]=useState('');
 useEffect(()=>{workApi('/models/profiles').then(d=>{setData(d);setDraft(Object.fromEntries(d.profiles.map((p:any)=>[p.id,p.model])))}).catch(e=>setNotice(e.message))},[]);
 return <><div className="model-grid">{data?.profiles.map((p:any)=><div className="panel" key={p.id}><h3>{p.label}</h3><p>{p.purpose}</p><small>{p.model}</small><p><button disabled={busy} onClick={()=>installed.some(m=>m.name===p.model)?load(p.model):load(p.model)}>{installed.some(m=>m.name===p.model)?'Load & use '+p.label:'Download & use '+p.label}</button></p></div>)}</div><details className="panel"><summary>Configure profile model names</summary><form onSubmit={async e=>{e.preventDefault();try{const d=await workApi('/models/profiles','PUT',draft);setData(d);window.dispatchEvent(new Event('nila-settings-changed'));setNotice('Profile mapping saved. Download any missing model before chatting.')}catch(e:any){setNotice(e.message)}}}>{data?.profiles.map((p:any)=><label key={p.id}>{p.label}<input required value={draft[p.id]||''} pattern="[a-zA-Z0-9_.:/\-]+" maxLength={120} onChange={e=>setDraft({...draft,[p.id]:e.target.value})}/></label>)}<button disabled={busy}>Save profiles</button><p role="status">{notice}</p></form></details></>
}
