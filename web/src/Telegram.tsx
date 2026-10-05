import {useEffect,useState} from 'react';
import {workApi} from './Workspace';
export function Telegram(){
 const [data,setData]=useState<any>(null),[token,setToken]=useState(''),[chatId,setChatId]=useState(''),[enabled,setEnabled]=useState(false),[share,setShare]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const refresh=()=>workApi('/telegram').then(setData);
 useEffect(()=>{workApi('/telegram').then(d=>{setData(d);setChatId(d.chat_id);setEnabled(d.enabled);setShare(d.share_memory)}).catch(e=>setError(e.message));const t=setInterval(()=>refresh().catch(()=>{}),4000);return ()=>clearInterval(t)},[]);
 async function run(fn:()=>Promise<any>){setBusy(true);setError('');try{const d=await fn();setMessage(d.message||'Connection settings saved.');await refresh()}catch(e:any){setError(e.message)}finally{setBusy(false)}}
 return <div className="panel"><h2>Nila on Telegram</h2><p>Chat with Nila while your laptop and Ollama are running. Keep Nila Web or <code>nila worker</code> open. Only your configured private Telegram user can access this bot.</p>{error&&<p className="inline-error" role="alert">{error}</p>}{message&&<p className="section-notice" role="status">{message}</p>}
 <p>Status: <strong>{data?.status||'Not configured'}</strong></p>
 <label>Bot token<input type="password" autoComplete="new-password" maxLength={230} value={token} onChange={e=>setToken(e.target.value)} placeholder={data?.configured?'Saved securely — leave blank to keep':'Token from @BotFather'}/></label>
 <label>Your private chat ID<input inputMode="numeric" value={chatId} maxLength={19} onChange={e=>setChatId(e.target.value)} placeholder="Your numeric Telegram user ID"/></label>
 <label className="check"><input type="checkbox" checked={enabled} onChange={e=>setEnabled(e.target.checked)}/>Enable Telegram connection</label>
 <label className="check"><input type="checkbox" checked={share} onChange={e=>setShare(e.target.checked)}/>Allow my personal profile and memories in Telegram answers</label>
 <p>Telegram receives messages and generated answers. Gemini is never used here. Memory sharing is off by default; enabling it may include personal facts in replies sent through Telegram. Changing this option starts a fresh bot conversation.</p>
 <button className="primary" disabled={busy||!chatId||(!token&&!data?.configured)} onClick={()=>run(async()=>{const d=await workApi('/telegram','PUT',{token,chat_id:chatId,enabled,share_memory:share});setToken('');return d})}>Save connection</button>
 <button disabled={busy||!data?.configured} onClick={()=>run(()=>workApi('/telegram/test','POST'))}>Test token</button>
 <button disabled={busy||!data?.configured} onClick={()=>run(async()=>{const d=await workApi('/telegram','DELETE');setEnabled(false);setToken('');return d})}>Disconnect & remove token</button>
 <p>Create your own bot with <a href="https://t.me/BotFather" target="_blank" rel="noreferrer">BotFather</a>, enter its token and your private numeric user ID, then send <code>/start</code> to the bot. Group chats and other users are ignored. Use <code>/new</code> for a fresh conversation.</p></div>
}
