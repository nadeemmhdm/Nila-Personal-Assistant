import asyncio
import pytest
from nila import engine
from nila.storage import Store
from nila.conversation import is_greeting,developer_question
from test_app import mock_ollama

@pytest.mark.parametrize('prompt',['Hi','Hi!!!','hello Nila','Hey','ഹായ്','good mrning nil','Good evening Nila'])
def test_greetings_use_model_and_preserve_actual_prompt(tmp_path,monkeypatch,prompt):
    seen=mock_ollama(monkeypatch);s=Store(tmp_path);s.save_settings({'user_name':'Nadeem','description':'PRIVATE_PROJECTS','auto_memory':False})
    cid=s.create_chat()['id'];s.add_message(cid,'user','Hi');s.add_message(cid,'assistant','BAD_ANSWER developer scraper')
    from nila import websearch
    monkeypatch.setattr(websearch,'lookup',lambda *args:(_ for _ in ()).throw(AssertionError('No web lookup for greetings')))
    async def run():return ''.join([x async for x in engine.reply(s,cid,prompt,search_mode='quick')])
    assert asyncio.run(run())=='Hello Nadeem.'
    assert seen[0]['messages'][-1]['content']==prompt
    assert 'PRIVATE_PROJECTS' not in str(seen) and 'BAD_ANSWER' not in str(seen)

@pytest.mark.parametrize('text',['Hi, explain Python dictionaries','hello world in Python','continue','what about the second example?','Who developed Python?'])
def test_substantive_messages_are_not_canned_greetings(text):
    assert not is_greeting(text)

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

def test_telegram_no_personal_context_greeting(tmp_path,monkeypatch):
    seen=mock_ollama(monkeypatch)
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
