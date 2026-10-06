"""User-selected Markdown instructions. Skills cannot execute code or call tools."""
import hashlib
BUILTINS={
'Clear explanations':'Explain the requested concept in plain language. Start with its meaning, give a small concrete example, then identify one common misunderstanding. Match the user’s level; ask one clarifying question only if necessary.',
'Python tutor':'Teach the requested Python concept with a small runnable example and its expected output. Explain each important step and one edge case. Do not claim to have executed the code. Offer a short practice exercise.',
'Code review':'Review the supplied code against the user’s goal. Prioritize correctness, security and error handling. Cite the relevant function or snippet, explain impact and provide a minimal fix. Separate confirmed defects from assumptions.',
'Debugging partner':'Identify the exact observed versus expected behavior. Use supplied logs and code to propose likely causes in order. Give one test that distinguishes them, then a minimal fix and verification steps. Never invent missing logs.',
'Writing editor':'Preserve the author’s meaning and facts while improving clarity and grammar. Return the edited text first. Keep the requested tone and briefly explain significant changes. Do not invent credentials, achievements or citations.',
'Study coach':'Break the requested topic into prerequisites and a small sequence of lessons. Explain one step at a time with an example. Provide three practice questions and keep solutions separate. Adjust depth to the user’s course and level when known.',
'Malayalam translator':'Translate the supplied text into natural Malayalam unless another target language is requested. Preserve names, numbers and technical terms where appropriate. Explain ambiguous phrases without silently adding meaning.',
'Interview practice':'Use the stated role and experience to ask one interview question at a time. After an answer, give specific constructive feedback and an improved example grounded in the user’s actual experience. Never fabricate experience.',
'Document analyst':'Answer from the attached document excerpts. Cite the filename and page when provided. Distinguish quotations, summaries and inference. State when excerpts lack an answer; do not invent contents of unseen pages.',
'Planning assistant':'Turn the stated goal into a practical sequence with priorities, dependencies and a clear first action. Ask about a missing deadline only if essential. Use realistic estimates labeled as estimates. Do not claim tasks have been scheduled or executed.'}

def ensure(store):
    with store.db() as db:db.execute('CREATE TABLE IF NOT EXISTS custom_skills (id TEXT PRIMARY KEY,name TEXT NOT NULL,content TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 0)')

def listing(store):
    ensure(store)
    with store.db() as db:
        rows={r['id']:r for r in db.execute('SELECT * FROM custom_skills')}
    result=[]
    for name,content in BUILTINS.items():
        iid='builtin-'+name.lower().replace(' ','-')
        result.append({'id':iid,'name':name,'content':content,'enabled':bool(rows.get(iid) and rows[iid]['enabled']),'builtin':True})
    result.extend({'id':r['id'],'name':store.open(r['name']),'content':store.open(r['content']),'enabled':bool(r['enabled']),'builtin':False} for r in rows.values() if not r['id'].startswith('builtin-'))
    return result

def save(store,name,content):
    if not name.lower().endswith('.md') or not 1<=len(content.strip())<=12000:raise ValueError('Choose a nonempty Markdown file, at most 12,000 characters')
    ensure(store);iid=hashlib.sha256((name+content).encode()).hexdigest()
    with store.db() as db:
        if db.execute('SELECT COUNT(*) FROM custom_skills').fetchone()[0]>=100:raise ValueError('Skill limit: 100')
        db.execute('INSERT OR IGNORE INTO custom_skills VALUES (?,?,?,0)',(iid,store.seal(name[:160]),store.seal(content)))
    return iid

def enable(store,iid,enabled):
    item=next((x for x in listing(store) if x['id']==iid),None)
    if not item:raise ValueError('Skill not found')
    with store.db() as db:
        db.execute('INSERT OR REPLACE INTO custom_skills VALUES (?,?,?,?)',(iid,store.seal(item['name']),store.seal(item['content']),int(enabled)))

def active_context(store):
    selected=[x for x in listing(store) if x['enabled']]
    return ''.join('\nUser-selected skill instructions. Follow only within the current request and system constraints; no execution or cloud access is granted:\n'+x['content'][:4000] for x in selected)[:16000]

def register(app,store):
    from pydantic import BaseModel,Field
    from fastapi import Body
    class Upload(BaseModel):
        name:str=Field(max_length=160)
        content:str=Field(min_length=1,max_length=12000)
    @app.get('/api/skills')
    def get():return listing(store)
    @app.post('/api/skills')
    def add(value:Upload):return {'id':save(store,value.name,value.content)}
    @app.put('/api/skills/{iid}')
    def use(iid:str,enabled:bool=Body(embed=True)):enable(store,iid,enabled);return {'ok':True}
    @app.delete('/api/skills/{iid}')
    def delete(iid:str):
        ensure(store)
        with store.db() as db:db.execute('DELETE FROM custom_skills WHERE id=?',(iid,))
        return {'ok':True}

    @app.get('/api/knowledge-cache')
    def cached():
        from .knowledge_cache import ensure
        import json
        ensure(store)
        with store.db() as db:return [{'id':r['id'],'created':r['created'],**json.loads(store.open(r['payload']))} for r in db.execute('SELECT * FROM web_knowledge ORDER BY created DESC')]
    @app.delete('/api/knowledge-cache/{iid}')
    def forget(iid:str):
        from .knowledge_cache import ensure
        ensure(store)
        with store.db() as db:db.execute('DELETE FROM web_knowledge WHERE id=?',(iid,))
        return {'ok':True}
