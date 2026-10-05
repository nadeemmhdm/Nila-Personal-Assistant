"""One persistent model selection for Web, CLI, Telegram and local generation."""
import re
DEFAULT_PROFILES={'fast':'qwen3:0.6b','medium':'qwen3:1.7b','current':'qwen3:4b'}
LABELS={'fast':'Fast','medium':'Medium','current':'Smart','custom':'Custom'}
PURPOSES={'fast':'Quick questions and lightweight tasks','medium':'Balanced everyday assistance','current':'Reasoning, coding and complex tasks'}

def profiles(value=None):
    data=DEFAULT_PROFILES|dict(value or {})
    if set(data)!=set(DEFAULT_PROFILES) or any(not isinstance(v,str) or not re.fullmatch(r'[a-zA-Z0-9_.:/-]{1,120}',v) for v in data.values()):raise ValueError('Configure Fast, Medium and Current with valid Ollama model names')
    return data

def normalize(saved):
    data=dict(saved);mapping=profiles(data.get('model_profiles'));name=data.get('model',mapping['current'])
    mode=data.get('model_mode')
    if mode not in mapping or mapping[mode]!=name:mode=next((k for k,v in mapping.items() if v==name),'custom')
    data.update(model_profiles=mapping,model=name,model_mode=mode)
    return data

def selection(store):
    settings=store.settings();return {'model':settings['model'],'mode':settings['model_mode'],'label':LABELS[settings['model_mode']],'profiles':[{'id':k,'label':LABELS[k],'model':v,'purpose':PURPOSES[k]} for k,v in settings['model_profiles'].items()]}

async def select(store,value,warm=False):
    from .engine import models,ollama_url,NilaError
    import httpx
    settings=store.settings();value=value.lower() if value.lower() in {'fast','medium','current','smart'} else value
    if value=='smart':value='current'
    name=settings['model_profiles'].get(value,value)
    if not re.fullmatch(r'[a-zA-Z0-9_.:/-]{1,120}',name):raise ValueError('Invalid Ollama model name')
    token=store.acquire()
    try:
        if name not in [m['name'] for m in await models()]:raise NilaError(f'NILA-002: The selected model is not installed in Ollama. Model: {name}. Install it with: ollama pull {name}')
        if warm:
            async with httpx.AsyncClient(timeout=180,trust_env=False) as c:
                r=await c.post(ollama_url()+'/api/generate',json={'model':name,'prompt':'','stream':False,'keep_alive':'5m'});r.raise_for_status()
                if r.json().get('error'):raise NilaError('Ollama could not load this model. Check available RAM.')
        store.save_settings({'model':name}|({'model_mode':value} if value in settings['model_profiles'] else {}));return selection(store)
    finally:store.release(token)

def register(app,store):
    from fastapi import Body,HTTPException
    from .engine import NilaError
    @app.get('/api/models/profiles')
    def get():return selection(store)
    @app.post('/api/models/select')
    async def choose(value:str=Body(embed=True)):
        try:return await select(store,value)
        except (NilaError,ValueError) as exc:raise HTTPException(400,str(exc))
        except RuntimeError as exc:raise HTTPException(409,str(exc))
    @app.put('/api/models/profiles')
    def configure(value:dict[str,str]=Body()):
        mapping=profiles(value);old=store.settings();changes={'model_profiles':mapping}
        if old['model_mode']!='custom':changes['model']=mapping[old['model_mode']]
        store.save_settings(changes);return selection(store)
