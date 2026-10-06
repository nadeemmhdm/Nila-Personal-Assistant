import {useState} from 'react';
export function VideoPreview({text}:{text:string}){
 const [active,setActive]=useState('');
 const ids=Array.from(new Set(Array.from(text.matchAll(/https?:\/\/(?:www\.)?(?:youtube\.com\/(?:watch\?v=|shorts\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/g),m=>m[1]))).slice(0,3);
 return <>{ids.map(id=><div className="video-preview" key={id}>{active===id?<><iframe title="YouTube video" src={'https://www.youtube-nocookie.com/embed/'+id} allow="encrypted-media; picture-in-picture; fullscreen" allowFullScreen referrerPolicy="strict-origin-when-cross-origin"/><button onClick={()=>setActive('')}>Close player</button></>:<button className="video-load" onClick={()=>setActive(id)}>▶ Play YouTube video <small>Loads YouTube when you click</small></button>}</div>)}</>;
}
