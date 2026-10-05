"""Rich terminal rendering shared by interactive, one-shot, and regenerated replies."""
import io,re
from rich.console import Console,Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner

console=Console(highlight=False)

def prepared(text):
    # Rich has no Markdown underline extension: render underline markers as emphasis.
    return re.sub(r'\+\+([^+]+)\+\+',r'**\1**',text)

def plain_text(text):
    out=io.StringIO();c=Console(file=out,color_system=None,width=10000,highlight=False)
    c.print(Markdown(prepared(text)),end='')
    return out.getvalue().strip()

def banner():
    console.print(Panel(Text('N I L A',style='bold bright_cyan',justify='center'),subtitle='Your personal assistant',border_style='bright_magenta',padding=(1,6),width=36,expand=True))
    console.print('[dim]Just type your message. /help for shortcuts · /exit to leave[/dim]')

async def render_reply(store,cid,prompt,**kwargs):
    from .engine import reply
    from .conversation import thinking_message
    text='';stage=thinking_message()
    with Live(Spinner('simpleDots',text=stage,style='cyan'),console=console,refresh_per_second=12,transient=False,vertical_overflow='visible') as live:
        def progress(label):
            pass  # Keep one chosen message until the first response token.
        async for part in reply(store,cid,prompt,progress=progress,**kwargs):
            text+=part;live.update(Markdown(prepared(text)))
        live.update(Markdown(prepared(text)) if text else Text('No response generated.',style='dim'))
    console.print()
