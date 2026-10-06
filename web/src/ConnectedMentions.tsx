import {useEffect,useState} from 'react';
import {workApi} from './Workspace';
import {ServiceIcon} from './ServiceIcon';
export function ConnectedMentions({value,onChange}:{value:string;onChange:(v:string)=>void}){
 const [services,setServices]=useState<any[]>([]);
 useEffect(()=>{let live=true;workApi('/google').then(d=>{if(live)setServices(d.services.filter((s:any)=>s.connected))}).catch(()=>{});return()=>{live=false}},[value.includes('@')]);
 const match=value.match(/@([A-Za-z]*)$/);
 if(!match)return null;
 const available=services.filter(s=>s.name.toLowerCase().startsWith(match[1].toLowerCase()));
 return <div className="mention-picker" aria-label="Connected services">{available.length?available.map(s=><button type="button" key={s.id} onClick={()=>onChange(value.replace(/@[A-Za-z]*$/,'@'+s.name+' '))}><ServiceIcon service={s.id}/><span>{s.name}<small>{s.email}</small></span></button>):<small>No matching connected service. Connect your account in Workspace → Google.</small>}</div>;
}
