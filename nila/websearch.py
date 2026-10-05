"""Opt-in web evidence. No Store, chat context, profile, memory, or Gemini access."""
import asyncio
import ipaddress
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit, quote


def public_url(value):
    try:
        p=urlsplit(str(value))
        if p.scheme not in {'http','https'} or not p.hostname or p.username or p.password: return None
        host=p.hostname.lower()
        if not re.fullmatch(r'[a-z0-9.-]+',host): return None
        if '.' not in host or host.endswith(('.local','.localhost','.internal')): return None
        try:
            if not ipaddress.ip_address(host).is_global: return None
        except ValueError: pass
        if p.port not in {None,80,443}: return None
        return urlunsplit((p.scheme,p.netloc,quote(p.path,safe='/%:@-._~!$&()*+,;='),quote(p.query,safe='=&%:/?@-._~!$()*+,;'),''))
    except (ValueError,TypeError): return None


def lookup(query,limit):
    from ddgs import DDGS
    # Bound provider I/O. DDGS uses public search services; no API key required.
    return DDGS(timeout=8).text(query,max_results=limit,backend="duckduckgo,brave,google")


async def search(query,mode='off'):
    if mode=='off': return []  # No import, network, or provider invocation.
    if mode not in {'quick','deep'}: raise ValueError('Invalid web search mode')
    from .engine import NilaError
    query=query.strip()
    if not query or len(query)>500:
        raise NilaError('NILA-020: Web query must be 1–500 characters. Use a short separate search query.')
    queries=[query] if mode=='quick' else [query,query+' official sources',query+' latest updates']
    results=[]
    try:
        async with asyncio.timeout(30):
            batches=await asyncio.gather(*(asyncio.to_thread(lookup,q,4) for q in queries),return_exceptions=True)
        seen=set()
        for batch in batches:
            if isinstance(batch,BaseException): continue
            for item in batch:
                url=public_url(item.get('href',''))
                if not url or url in seen: continue
                seen.add(url)
                results.append({'source':len(results)+1,'title':str(item.get('title',''))[:160],'url':url,'snippet':str(item.get('body',''))[:350],'retrieved':datetime.now(timezone.utc).isoformat()})
                if len(results)>=(4 if mode=='quick' else 8): break
            if len(results)>=(4 if mode=='quick' else 8): break
    except TimeoutError:
        raise NilaError('NILA-020: Search timed out. Retry or switch web search Off.') from None
    if not results: raise NilaError('NILA-020: No web evidence available. Check your connection, retry, or switch web search Off. No live answer was generated.')
    return results
