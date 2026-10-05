import React,{useEffect,useRef,useState} from 'react';
export function useInlineConfirm(){
 const [message,setMessage]=useState('');
 const pending=useRef<((value:boolean)=>void)|null>(null);
 useEffect(()=>()=>{pending.current?.(false)},[]);
 const finish=(value:boolean)=>{pending.current?.(value);pending.current=null;setMessage('')};
 const ask=(text:string)=>new Promise<boolean>(resolve=>{pending.current?.(false);pending.current=resolve;setMessage(text)});
 const confirmation=message?<div className="section-confirm" role="region" aria-label="Confirm action"><p>{message}</p><button onClick={()=>finish(true)}>Confirm</button><button onClick={()=>finish(false)}>Cancel</button></div>:null;
 return {ask,confirmation};
}
