import asyncio
import pytest
from nila import engine
from nila.storage import Store
from nila.conversation import greeting_reply,developer_question
from test_app import mock_ollama

@pytest.mark.parametrize('prompt',['Hi','Hi!!!','hello Nila','Hey','ഹായ്'])
def test_greeting_ignores_poisoned_history_and_never_calls_model_or_search(tmp_path,monkeypatch,prompt):
    s=Store(tmp_path);s.save_settings({'user_name':'Nadeem','description':'PRIVATE_PROJECTS'})
    cid=s.create_chat()['id'];s.add_message(cid,'user','Hi');s.add_message(cid,'assistant','BAD_ANSWER developer profile scraper code')
    async def forbidden(*a,**k):raise AssertionError('Greeting must not call external services')
    monkeypatch.setattr(engine,'models',forbidden)
    from nila import websearch
    monkeypatch.setattr(websearch,'search',forbidden)
    async def run():return ''.join([x async for x in engine.reply(s,cid,prompt,search_mode='quick')])
    answer=asyncio.run(run())
    assert 'Nadeem' in answer and len(answer)<100
    assert all(x not in answer for x in ['PRIVATE_PROJECTS','BAD_ANSWER','github','code','Developer'])
    assert s.chat(cid)['messages'][-1]['content']==answer
    token=s.acquire();s.release(token)

@pytest.mark.parametrize('text',['Hi, explain Python dictionaries','hello world in Python','continue','what about the second example?','Who developed Python?'])
def test_substantive_messages_are_not_canned_greetings(text):
    assert greeting_reply(text,{}) is None

def test_user_question_reaches_model_and_followup_keeps_history(tmp_path,monkeypatch):
    seen=mock_ollama(monkeypatch);s=Store(tmp_path);s.save_settings({'auto_memory':False})
    cid=s.create_chat()['id'];s.add_message(cid,'user','Explain Python dictionaries');s.add_message(cid,'assistant','They map keys to values.')
    async def run():return ''.join([x async for x in engine.reply(s,cid,'Show another example')])
    asyncio.run(run());messages=seen[0]['messages']
    assert messages[-1]['content']=='Show another example'
    assert any(m['content']=='They map keys to values.' for m in messages)
    assert 'github.com/nadeemmhdm' not in messages[0]['content']
    assert 'Nadeem' not in messages[0]['content']

def test_developer_attribution_only_when_requested(tmp_path):
    s=Store(tmp_path);cid=s.create_chat()['id']
    s.add_message(cid,'user','Who developed Python?')
    assert not developer_question('Who developed Python?')
    assert 'github.com/nadeemmhdm' not in engine.context(s,cid,s.settings())[0]['content']
    s.add_message(cid,'user','Who developed you?')
    assert 'github.com/nadeemmhdm' in engine.context(s,cid,s.settings())[0]['content']

def test_telegram_no_personal_context_greeting(tmp_path):
    s=Store(tmp_path);s.save_settings({'user_name':'PRIVATE_NAME'});cid=s.create_chat()['id']
    async def run():return ''.join([x async for x in engine.reply(s,cid,'Hi',personal_context=False)])
    assert 'PRIVATE_NAME' not in asyncio.run(run())


def test_banner_subtitle_is_not_truncated(monkeypatch):
    import io
    from rich.console import Console
    from nila import terminal
    output=io.StringIO();monkeypatch.setattr(terminal,'console',Console(file=output,width=80,color_system=None))
    terminal.banner()
    assert 'Your personal assistant' in output.getvalue()
