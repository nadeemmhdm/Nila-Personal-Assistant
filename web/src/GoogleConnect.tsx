import {useEffect,useRef,useState} from 'react';
import {ExternalLink,Link2,Unplug,ShieldCheck,RefreshCw} from 'lucide-react';
import {workApi} from './Workspace';

type Service={id:string;name:string;description:string;connected:boolean;email:string;scope:string};
export function GoogleConnect({openChat}:{openChat:(id:string)=>void}){
 const [data,setData]=useState<{configured:boolean;url:string;services:Service[]}|null>(null);
 const [url,setUrl]=useState(''),[key,setKey]=useState(''),[selected,setSelected]=useState('gmail'),[item,setItem]=useState(''),[range,setRange]=useState('A1:Z100');
 const [pending,setPending]=useState(''),[loginUrl,setLoginUrl]=useState(''),[confirm,setConfirm]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[result,setResult]=useState<any>(null);
 const alive=useRef(true);
 const refresh=async()=>{const d=await workApi('/google');if(alive.current){setData(d);setUrl(d.url)}};
 useEffect(()=>{alive.current=true;refresh().catch(e=>setError(e.message));return()=>{alive.current=false}},[]);
 useEffect(()=>{if(!pending)return;let cancelled=false;let timer:ReturnType<typeof setTimeout>;
 const poll=async()=>{try{const r=await workApi(`/google/${pending}/poll`,'POST');if(cancelled)return;if(r.status==='pending')timer=setTimeout(poll,3000);else{setConfirm(r.email);setPending('');setNotice('Check the account below before enabling access.')}}catch(e:any){if(!cancelled){setError(e.message);setPending('')}}};timer=setTimeout(poll,3000);return()=>{cancelled=true;clearTimeout(timer)}},[pending]);
 async function run(fn:()=>Promise<void>){setBusy(true);setError('');try{await fn()}catch(e:any){setError(e.message)}finally{setBusy(false)}}
 function choose(value:string){setSelected(value);setItem('');setResult(null);setNotice('');setError('')}
 async function connect(){await run(async()=>{const r=await workApi(`/google/${selected}/connect`,'POST');setLoginUrl(r.url);setPending(selected);setConfirm('');setNotice('Open Google sign-in below. Return here after granting access.');})}
 async function read(id=item,page=''){await run(async()=>{const r=await workApi(`/google/${selected}/read`,'POST',{item:id,cell_range:range,page_token:page});setResult(r);setItem(id);setNotice('Read directly from Google. Nothing has been added to a chat or memory.');})}
 const service=data?.services.find(s=>s.id===selected);
 const rows=result?.files||result?.messages||result?.courses||result?.items||result?.conferenceRecords||[];
 const preview=result?.readable_text||JSON.stringify(result,null,2);
 return <div className="panel google-connect"><span className="eyebrow">YOUR ACCOUNTS · YOUR CHOICE</span><h2>Google connections</h2>
 <p>Connect through your own PHP OAuth website. Google data is read on this laptop. Gemini cannot access these connections, tokens or imported files.</p>
 {error&&<p className="inline-error" role="alert">{error}</p>}{notice&&<p className="section-notice" role="status">{notice}</p>}
 <details open={!data?.configured}><summary>OAuth website setup</summary><p>Use a broker that you own or trust: its operator can process authorization tokens. The Google Client Secret belongs on the PHP server, never in this form.</p>
 <label>HTTPS broker URL<input placeholder="https://connect.example.com/index.php" value={url} onChange={e=>setUrl(e.target.value)} maxLength={1000}/></label>
 <label>Private deployment pairing key<input type="password" autoComplete="new-password" value={key} onChange={e=>setKey(e.target.value)} maxLength={256}/></label>
 <button disabled={busy||!url||key.length<32||!!pending||!!confirm} onClick={()=>run(async()=>{await workApi('/google/config','PUT',{url,key});setKey('');setResult(null);await refresh();setNotice('OAuth website configured. Choose a service to connect.');})}>Save OAuth website</button>
 <a href="https://github.com/nadeemmhdm/Nila-Personal-Assistant/blob/main/docs/GOOGLE_CONNECT.md" target="_blank" rel="noreferrer">PHP deployment & Google Cloud setup <ExternalLink size={14}/></a></details>
 <div className="google-services">{data?.services.map(s=><button key={s.id} className={selected===s.id?'selected':''} disabled={busy||!!pending||!!confirm} onClick={()=>choose(s.id)}><strong>{s.name}</strong><small>{s.connected?'Connected':'Not connected'}</small></button>)}</div>
 {service&&<section><h3>{service.name}</h3><p>{service.description} · Read-only</p>{service.connected&&<p><ShieldCheck size={16}/> {service.email}</p>}
 <button disabled={busy||!data?.configured||!!pending||!!confirm} onClick={connect}><Link2 size={16}/>{service.connected?'Reconnect':'Connect with Google'}</button>
 {(service.connected||pending||confirm)&&<button disabled={busy} onClick={()=>run(async()=>{setPending('');setConfirm('');setLoginUrl('');setResult(null);await workApi(`/google/${selected}`,'DELETE');await refresh();setNotice('Local credentials removed. To revoke the Google grant, use your Google account permissions below.');})}><Unplug size={16}/>{pending||confirm?'Cancel connection':'Disconnect locally'}</button>}
 {pending&&<p className="section-notice"><a href={loginUrl} target="_blank" rel="noreferrer">Open Google sign-in <ExternalLink size={14}/></a><br/>Waiting for permission… This connection expires after 10 minutes.</p>}
 {confirm&&<div className="section-notice"><p>Connect <strong>{confirm}</strong> to {service.name} on this laptop?</p><button disabled={busy} onClick={()=>run(async()=>{await workApi(`/google/${selected}/confirm`,'POST');setConfirm('');setLoginUrl('');await refresh();setNotice('Account connected. You can now read this service.');})}>Yes, use this account</button></div>}
 {service.connected&&!pending&&!confirm&&<><label>{selected==='docs'?'Document ID':selected==='sheets'?'Spreadsheet ID':'Item ID (optional)'}<input value={item} maxLength={180} placeholder={selected==='youtube'?'Leave empty for channel, or enter playlists':'Copy the ID from the Google item URL'} onChange={e=>setItem(e.target.value)}/></label>
 {selected==='sheets'&&<label>Cell range<input value={range} onChange={e=>setRange(e.target.value)} maxLength={200}/></label>}
 <button className="primary" disabled={busy||(['docs','sheets'].includes(selected)&&!item)} onClick={()=>read()}><RefreshCw size={16}/>Read from Google</button></>}
 </section>}
 {result&&<section className="google-results"><h3>{service?.name} preview</h3>{rows.length>0&&<div className="google-items">{rows.map((r:any,i:number)=><button disabled={busy} key={r.id||r.name||i} onClick={()=>read(r.id||String(r.name).split('/').pop())}>{r.name||r.snippet?.title||r.id||'Item '+(i+1)}</button>)}</div>}
 <pre>{preview}</pre>{result.nextPageToken&&<button disabled={busy} onClick={()=>read('',result.nextPageToken)}>Next page</button>}
 <button disabled={busy||preview.length>450000} onClick={()=>run(async()=>{const r=await workApi('/google/import/chat','POST',{service:selected,text:preview});openChat(r.chat_id)})}>Use this preview in a local chat</button>
 <p>This explicitly saves the preview as an encrypted local document. Ask Nila about the attached document in the new chat. Disconnecting Google does not delete imported documents; remove those from Documents and delete their chats separately.</p></section>}
 <p><a href="https://myaccount.google.com/connections" target="_blank" rel="noreferrer">Manage or revoke Google permissions <ExternalLink size={14}/></a>. Revoking this app at Google can affect all connected services. Live calls require internet; imported documents can be used offline.</p>
 </div>
}
