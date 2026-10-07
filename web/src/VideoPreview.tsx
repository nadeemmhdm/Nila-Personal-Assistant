import {useState} from 'react';
export function VideoPreview({text}:{text:string}){
 const [active,setActive]=useState('');
 const ids=Array.from(new Set((text.match(/https?:\/\/[^\s<>]+/g)||[]).flatMap(raw=>{
  try{const url=new URL(raw.replace(/[).,;]+$/,''));if(url.username||url.password)return [];
   const host=url.hostname.toLowerCase();let id='';
   if(host==='youtu.be')id=url.pathname.slice(1);
   else if(['youtube.com','www.youtube.com','m.youtube.com'].includes(host))id=url.searchParams.get('v')||url.pathname.match(/^\/(?:shorts|embed)\/([^/]+)/)?.[1]||'';
   return /^[A-Za-z0-9_-]{11}$/.test(id)?[id]:[];
  }catch{return []}
 }))).slice(0,3);
 return <>{ids.map(id=><div className="video-preview" key={id}>{active===id?<><iframe title="YouTube video" src={'https://www.youtube-nocookie.com/embed/'+id} allow="encrypted-media; picture-in-picture; fullscreen" allowFullScreen referrerPolicy="strict-origin-when-cross-origin"/><button onClick={()=>setActive('')}>Close player</button></>:<button className="video-load" onClick={()=>setActive(id)}>▶ Play YouTube video <small>Loads YouTube when you click</small></button>}</div>)}</>;
}
