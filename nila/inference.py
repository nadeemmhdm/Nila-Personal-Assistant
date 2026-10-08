"""Local transport adapter: preserve Ollama callers while supporting llama.cpp."""
import json
import httpx
from . import local_runtime as runtime

class Events(httpx.AsyncByteStream):
    def __init__(self,response):self.response=response
    async def __aiter__(self):
        try:
            async for line in self.response.aiter_lines():
                if not line.startswith('data: '):continue
                value=line[6:]
                if value=='[DONE]':yield b'{"done":true}\n';return
                data=json.loads(value);choice=(data.get('choices') or [{}])[0]
                delta=choice.get('delta',{})
                yield (json.dumps({'message':{'content':delta.get('content') or ''},'done':bool(choice.get('finish_reason'))})+'\n').encode()
        finally:await self.response.aclose()
    async def aclose(self):await self.response.aclose()

class LlamaTransport(httpx.AsyncBaseTransport):
    def __init__(self):self.inner=httpx.AsyncHTTPTransport()
    async def handle_async_request(self,request):
        c=runtime.config();path=request.url.path
        if request.url.host not in {'127.0.0.1','localhost','::1'}:raise ValueError('Local inference cannot access external hosts')
        if path=='/api/tags':return httpx.Response(200,json={'models':[{'name':c['model']}]})
        if path=='/api/show':return httpx.Response(200,json={'capabilities':['completion']+(['vision'] if c.get('mmproj') else [])})
        if path=='/api/generate':await runtime.ensure(c);return httpx.Response(200,json={'done':True})
        if path!='/api/chat':return httpx.Response(400,json={'error':'Use Engine & downloads to manage llama.cpp models'})
        data=json.loads(request.content)
        if data.get('model')!=c['model']:return httpx.Response(400,json={'error':'Select the currently loaded llama.cpp model'})
        await runtime.ensure(c)
        messages=[]
        for message in data['messages']:
            item={'role':message['role'],'content':message['content']}
            if message.get('images'):
                item['content']=[{'type':'text','text':message['content']}]+[{'type':'image_url','image_url':{'url':('data:image/png;base64,' if x.startswith('iVBOR') else 'data:image/jpeg;base64,')+x}} for x in message['images']]
            messages.append(item)
        opts=data.get('options',{});payload={'model':c['model'],'messages':messages,'stream':data.get('stream',False),'temperature':opts.get('temperature',.7),'max_tokens':opts.get('num_predict',1024),'chat_template_kwargs':{'enable_thinking':False}}
        if isinstance(data.get('format'),dict):payload['response_format']={'type':'json_schema','json_schema':{'name':'response','schema':data['format']}}
        out=httpx.Request('POST','http://127.0.0.1:11436/v1/chat/completions',json=payload,headers={'Authorization':'Bearer '+c['key']},extensions=request.extensions)
        response=await self.inner.handle_async_request(out)
        if response.status_code>=400:return response
        if payload['stream']:return httpx.Response(200,stream=Events(response))
        raw=await response.aread();await response.aclose();value=json.loads(raw)
        return httpx.Response(200,json={'message':{'content':value['choices'][0]['message'].get('content','')},'done':True})
    async def aclose(self):await self.inner.aclose()

def client(**kwargs):
    if runtime.config().get('engine')=='llama.cpp':kwargs['transport']=LlamaTransport()
    return httpx.AsyncClient(**kwargs)
