"""Terminal access to the same local workspace features as the browser."""
import asyncio,getpass,json,os
from pathlib import Path

def add_parsers(sub):
    p=sub.add_parser('google',help='Connect read-only Google services through your PHP broker')
    p.add_argument('action',choices=['setup','status','connect','read','disconnect'],nargs='?',default='status')
    p.add_argument('service',nargs='?',choices=['gmail','drive','docs','sheets','classroom','youtube','meet'])
    p.add_argument('--item',default='');p.add_argument('--range',dest='cell_range',default='A1:Z100')
    p.add_argument('--page-token',default='')
    p=sub.add_parser("speak",help="Read text aloud with an installed Windows offline voice");p.add_argument("text")
    sub.add_parser("listen",help="Transcribe one utterance using installed Windows offline speech recognition")
    p=sub.add_parser('skills',help='List, import or select local Markdown skills');p.add_argument('action',nargs='?',default='list',choices=['list','add','use','off','remove']);p.add_argument('value',nargs='?')
    p=sub.add_parser('telegram',help='Configure encrypted Telegram private-chat access');p.add_argument('action',choices=['setup','status','test','disable','remove'])
    sub.add_parser('setup',help='Check requirements and choose a model')
    sub.add_parser('brief',help='Show local workspace counts')
    sub.add_parser('mini',help='Open the compact local Web UI (start nila web first)')
    sub.add_parser('rollback',help='Select previous managed Windows installation')
    p=sub.add_parser('regenerate',help='Replace an AI answer in place, preserving an original branch')
    p.add_argument('chat_id');p.add_argument('message_id',type=int);p.add_argument('--instruction',default='')
    p=sub.add_parser('branch',help='Copy a conversation into a new branch');p.add_argument('chat_id')
    p=sub.add_parser('sources',help='Inspect context supplied to an answer');p.add_argument('chat_id');p.add_argument('message_id',type=int)
    p=sub.add_parser('backup',help='Write a password-encrypted workspace backup');p.add_argument('file')
    p=sub.add_parser('restore',help='Preview and confirm encrypted workspace restore');p.add_argument('file')
    p=sub.add_parser('inbox',help='Review suggested memories');p.add_argument('action',nargs='?',default='list',choices=['list','approve','reject']);p.add_argument('id',nargs='?');p.add_argument('--text')
    p=sub.add_parser('projects',help='Manage project instructions and conversations');p.add_argument('action',nargs='?',default='list',choices=['list','add','edit','remove','chat']);p.add_argument('id',nargs='?');p.add_argument('--name');p.add_argument('--instructions',default='')
    p=sub.add_parser('documents',help='Import and attach local PDF/TXT/Markdown');p.add_argument('action',nargs='?',default='list',choices=['list','add','remove','attach']);p.add_argument('value',nargs='?');p.add_argument('--project');p.add_argument('--chat')
    p=sub.add_parser('feedback-list',help='Inspect, clear or reset local feedback');p.add_argument('--clear',type=int);p.add_argument('--reset',action='store_true')


COMMANDS={'google','speak','listen','skills','telegram','setup','brief','mini','rollback','regenerate','branch','sources','backup','restore','inbox','projects','documents','feedback-list'}

def execute(args,store):
    from . import workspace as ws
    def show(value):print(json.dumps(value,ensure_ascii=False,indent=2))
    c=args.command
    if c=='google':
        from . import google_connect as google
        if args.action=='setup':
            url=input('Your trusted HTTPS PHP broker URL: ').strip()
            key=getpass.getpass('Private deployment pairing key (hidden): ')
            show(google.configure(store,url,key))
        elif args.action=='status':show(google.status(store))
        elif args.action=='disconnect':show(google.disconnect(store,args.service))
        elif args.action=='read':show(asyncio.run(google.read(store,args.service,args.item,args.cell_range,args.page_token)))
        elif args.action=='connect':
            import webbrowser,time
            result=asyncio.run(google.connect(store,args.service));print('Open this login page: '+result['url']);webbrowser.open(result['url'])
            try:
                while True:
                    time.sleep(3);result=asyncio.run(google.poll(store,args.service))
                    if result['status']!='pending':break
                if input('Connect '+result['email']+' to '+args.service+'? [y/N] ').lower()=='y':show(google.confirm(store,args.service))
                else:google.disconnect(store,args.service)
            except KeyboardInterrupt:google.disconnect(store,args.service);print('Connection cancelled.')
    elif c in {'speak','listen'}:
        from .voice import run
        print('Listening locally for up to 30 seconds…' if c=='listen' else 'Speaking locally…',flush=True)
        print(run(c,getattr(args,'text','')))
    elif c=='skills':
        from . import skills
        if args.action=='list':show(skills.listing(store))
        elif args.action=='add':
            path=Path(args.value or '');show({'id':skills.save(store,path.name,path.read_text(encoding='utf-8'))})
        elif args.action in {'use','off'}:skills.enable(store,args.value,args.action=='use');print('Skill selection updated.')
        elif args.action=='remove':
            skills.ensure(store)
            with store.db() as db:db.execute('DELETE FROM custom_skills WHERE id=?',(args.value,))
    elif c=='telegram':
        from . import telegram_bot as tg
        if args.action=='setup':
            token=getpass.getpass('Bot token (hidden): ');chat_id=input('Your private numeric Telegram chat ID: ').strip()
            print('Telegram receives your messages and generated replies. Personal memory is excluded unless you allow it.')
            share=input('Allow personal profile/memory in Telegram answers? [y/N] ').strip().lower()=='y'
            show(tg.save(store,token,chat_id,True,share));print('Run nila worker or keep nila web running. Start your bot in Telegram.')
        elif args.action=='status':show(tg.status(store))
        elif args.action=='test':show(asyncio.run(tg.test(store)))
        else:show(tg.disable(store,args.action=='remove'))
    elif c=='setup':
        from .workspace_api import setup_status
        state=asyncio.run(setup_status(store));show(state)
        if not state['ollama_online']:print('Open Ollama or run ollama serve, then nila setup.');return
        if not state['suggestions']:print('Run nila pull llama3.2:1b, then nila setup.');return
        name=input('Installed model name to use (Enter keeps current): ').strip()
        if name:
            if name not in [x['name'] for x in state['suggestions']]:raise ValueError('Choose an installed model')
            store.save_settings({'model':name})
        if store.settings()['model'] in [x['name'] for x in state['suggestions']]:store.save_settings({'setup_complete':True});print('Setup complete.')
    elif c=='brief':show(ws.daily_brief(store))
    elif c=='mini':
        import webbrowser
        webbrowser.open('http://127.0.0.1:8765/?mini=1');print('Mini view opened. Start nila web if the local server is not running. Ctrl+Shift+Space inside the Web UI opens a compact popup.')
    elif c=='rollback':
        from .updater import rollback
        show(rollback(store))
    elif c=='regenerate':
        from .engine import reply
        if len(args.instruction)>2000:raise ValueError('Instruction limit: 2000 characters')
        async def run():
            from .terminal import render_reply
            await render_reply(store,args.chat_id,'Regenerate',regenerate_id=args.message_id,instruction=args.instruction,learn_memory=False)
        asyncio.run(run())
    elif c=='branch':
        token=store.acquire()
        try:print(ws.branch(store,args.chat_id))
        finally:store.release(token)
    elif c=='sources':show(ws.provenance(store,args.chat_id,args.message_id))
    elif c=='backup':
        from .backup import export_backup
        password=getpass.getpass('Backup password (12+ characters): ')
        if password!=getpass.getpass('Confirm password: '):raise ValueError('Passwords do not match')
        data=export_backup(store,password)
        with os.fdopen(os.open(args.file,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'wb') as f:f.write(data)
        print('Encrypted backup saved. API keys are excluded.')
    elif c=='restore':
        from .backup import restore_backup,MAX
        path=Path(args.file)
        if path.stat().st_size>MAX:raise ValueError('Backup is too large')
        raw=path.read_bytes();password=getpass.getpass('Backup password: ')
        show(restore_backup(store,raw,password))
        if input('Type RESTORE to replace saved workspace data: ').strip()=='RESTORE':show(restore_backup(store,raw,password,True))
        else:print('No changes made.')
    elif c=='inbox':
        if args.action=='list':show(ws.inbox(store))
        elif not args.id:raise ValueError('Provide a suggestion ID')
        else:ws.decide_memory(store,args.id,args.action=='approve',args.text);print('Memory decision saved.')
    elif c=='projects':
        if args.action=='list':show(ws.projects(store))
        elif args.action in {'add','edit'}:
            if not args.name or (args.action=='edit' and not args.id):raise ValueError('Provide --name and ID for edits')
            print(ws.save_project(store,args.name,args.instructions,args.id if args.action=='edit' else None))
        elif not args.id:raise ValueError('Provide a project ID')
        elif args.action=='chat':
            from .cli import interactive
            cid=store.create_chat()['id'];ws.assign_project(store,cid,args.id);asyncio.run(interactive(store,cid))
        else:
            with store.db() as db:db.execute('DELETE FROM projects WHERE id=?',(args.id,))
            print('Project and documents removed; conversations retained.')
    elif c=='documents':
        if args.action=='list':show(ws.document_list(store))
        elif not args.value:raise ValueError('Provide a file path or document ID')
        elif args.action=='add':
            path=Path(args.value)
            if path.stat().st_size>5*1024*1024:raise ValueError('Document limit is 5 MB')
            print(ws.ingest(store,path.name,path.read_bytes(),args.project))
        elif args.action=='attach':
            if not args.chat:raise ValueError('Provide --chat ID')
            with store.db() as db:ids=[r[0] for r in db.execute('SELECT document_id FROM chat_documents WHERE chat_id=?',(args.chat,))]
            ws.attach(store,args.chat,list(dict.fromkeys(ids+[args.value])));print('Document attached.')
        else:
            with store.db() as db:db.execute('DELETE FROM documents WHERE id=?',(args.value,))
    elif c=='feedback-list':
        with store.db() as db:
            if args.reset:db.execute('DELETE FROM feedback')
            elif args.clear is not None:db.execute('DELETE FROM feedback WHERE message_id=?',(args.clear,))
        show(ws.feedback_list(store))
