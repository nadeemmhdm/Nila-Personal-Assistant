# Nila Personal Assistant

**A friendly, local-first AI assistant for your browser and terminal.**

Nila runs on Ollama, remembers useful details about you, and carries out scheduled local work. The Web UI and `nila` command share encrypted storage and the same assistant settings.

**Version:** 0.4.0 · **Recommended default:** `llama3.2:1b` · **Platforms:** Windows and Linux

## Install on Windows — one command

Open **PowerShell** and paste:

```powershell
irm 'https://raw.githubusercontent.com/nadeemmhdm/Nila-Personal-Assistant/main/scripts/install.ps1' | iex
```

The command runs this repository's installer. It:

1. Checks Python, Node.js/npm, and Ollama; installs missing requirements using WinGet.
2. Downloads an immutable `main` commit and verifies each archived source file against its Git blob hash.
3. Builds the Web UI and a standalone **`nila.exe`** in a compact staging directory with a separate short-path Python environment (avoids the reported Windows MAX_PATH dependency error).
4. Checks that the new binary starts before changing the active installation.
5. Adds the `nila` launcher to your user PATH.
6. Downloads `llama3.2:1b` only when it is missing.
7. Registers a per-user Windows login worker for offline scheduled tasks.

Open a **new terminal** after installation:

```powershell
nila
nila web
```

`nila` starts terminal chat. `nila web` opens **http://127.0.0.1:8765**. The launcher selects the installed `nila.exe`; Python is not required to execute that binary, although the installer uses Python to build it.

**Requirements:** Windows 10/11 with WinGet/App Installer, internet for initial downloads, and enough disk space for build tools and model weights. Windows may request permission to install prerequisites. If WinGet is absent, the installer attempts to bootstrap it using Microsoft.WinGet.Client. If Windows policy prevents that, install Microsoft App Installer from Microsoft Store and rerun. Managed Windows installations receive automatic code updates. Linux/source installations use the manual workflow below.

## What Nila can do

| Capability | Details |
| --- | --- |
| Personal chat | Streaming replies, stop control, Markdown/code blocks, conversation search and export |
| Personal profile | Name, description, Student/Employee/other position, role-specific details, interests, language and tone |
| Friendly responses | Profile-aware system instructions; model quality still determines the result |
| Automatic memory | Local AI extracts supported, explicit facts from short personal statements |
| Memory controls | Inspect source, correct, delete, deduplicate, disable learning or disable memory use |
| Local storage protection | Authenticated content encryption; Windows encryption key protected by CurrentUser DPAPI |
| Notes and tasks | Create, edit, remove and complete local items |
| Offline automations | AI writing, notes/tasks briefs, scheduled notes and scheduled to-dos |
| Natural-language scheduling draft | Describe a job; review and save the proposed action and schedule |
| Maintenance | Diagnostics, model download/resume and commit-based update controls |
| Interface | Animated orb, response animation, responsive navigation, themes and reduced-motion support |

## Web search, chat controls and feedback

Web search starts **Off**. Select **Quick** for one query (up to four sources) or **Deep** for three query perspectives (up to eight deduplicated sources). Nila uses the open-source [DDGS](https://github.com/deedy5/ddgs) metasearch library with DuckDuckGo, Brave and Google backends, without a paid search API key. Search requires internet. Evidence consists of search-result snippets and source links; Deep broadens retrieval, but is not an exhaustive full-page research agent or a guarantee of correctness. Search generation uses at least a 4096-token context.

The optional **Web search query** field lets you supply public search terms separately from your message. If blank, only the new message is sent to search services. No saved chat history, profile, memory or feedback is included in search queries. Review the visible query before sending sensitive information. Search providers see the query and network metadata. Failed/no-result searches show `NILA-020`; Nila does not silently present an offline answer as a live result. Off makes no search requests. Automated tasks remain offline.

Replies render headings, **bold**, *italic*, lists, tables, links and fenced code. `++underlined text++` renders underlined; arbitrary HTML and remote images remain disabled. Streaming includes a thinking indicator, animated blocks and a cursor, with reduced-motion support. Copy buttons are available on both prompts and replies; copied text preserves the original Markdown.

- **Edit prompt → Save & regenerate** replaces that user turn and removes its old answer and all dependent later turns. Earlier turns remain. If search/model preflight fails, the existing branch remains. A generation interruption saves the new partial answer. Editing chat does not erase separately saved memories; use Memory controls for that.
- **Continue response** asks the model to continue in the same chat. Type any follow-up normally, or select a saved conversation in the sidebar to resume after reopening the app.
- **Thumbs up/down** records local feedback; click the selected thumb to clear it. **Add feedback** supplies a correction or style preference. Relevant rated examples and recent explicit guidance influence subsequent local chat prompts automatically. Guidance is encrypted, removable with its vote/chat, and never sent to Gemini. Votes are preference signals, not factual verification or model-weight training.

Terminal equivalents:

```powershell
nila
# Inside chat: /search quick, /search deep, /search off
# /up, /down, /feedback Use examples, /edit, /continue, /resume CHAT_ID
nila ask "Explain the latest changes" --search deep --query "Python official release notes"
nila chat --chat CHAT_ID
nila ask "Revised prompt" --chat CHAT_ID --edit USER_MESSAGE_ID
nila feedback CHAT_ID ASSISTANT_MESSAGE_ID down --reason "Please use examples"
```

`nila export CHAT_ID` prints the conversation. Clipboard buttons belong to the browser interface; terminal selection/copy remains available. Gemini is used only in the separately consented Learning Lab, never to review personal chat replies or feedback.

## Choose any compatible Ollama model

`llama3.2:1b` is a lightweight recommended starting point, not a requirement. Choose an installed text-chat model in Preferences or use `/model` inside terminal chat:

```powershell
nila pull YOUR_MODEL_NAME
nila model use YOUR_MODEL_NAME
```

Model speed, memory needs, language support and features vary. Embedding-only models cannot produce chat answers. Ollama cloud-tagged models require Ollama's own authentication and internet; only downloaded local models work offline. Learning Lab specifically uses a local text model plus the online Gemini reviewer.

## Chat without repeated commands

Run `nila`, then type normal messages and press Enter. You do not need `nila ask` for each message. Type `/help` for shortcuts, `/model` to select a model, `/learn` to open the guided Learning Lab, or `/exit` to leave. One-shot plain text also works: `nila Explain Python dictionaries`. Shell metacharacters may still need quoting; interactive chat avoids that issue.

## Gemini Learning Lab

Open **Learning Lab** in the Web UI:

1. Save your Gemini API key. It is encrypted locally and never returned by the settings API.
2. Load available Gemini models and select a reviewer available to your account.
3. Select your Ollama model, enter a topic and optional description, and choose a time limit (for example, 15 minutes) and maximum rounds.
4. Review the cloud-sharing notice, then start. Watch the local answer, Gemini feedback and local revisions in the transcript.
5. Use **Stop session** anytime. Review, edit, disable or delete saved lessons below the conversation.

This is **retrieval-based learning, not model-weight training or fine-tuning**. When Gemini marks a response acceptable, a short reviewed lesson can be saved and matched to related future chat questions. Gemini can also make mistakes; saved notes are labeled model-reviewed, not verified facts. No lesson is saved from an invalid/failed review. Turn off all note retrieval in Preferences or with `nila settings --knowledge off`.

The lab sends the topic, description, discussion question and local model answer to Google. It does not include your personal profile, ordinary chat history, notes or personal memories. Free-tier availability and limits depend on the Gemini model/project; a key does not guarantee free usage on a billing-enabled account. Google may use unpaid-service content for product improvement, so do not put private data in the lab. See [Learning Lab details](docs/LEARNING_LAB.md).

Each round makes one Gemini request, with a 12-second pause between rounds. The session stops at the time limit, round limit, a user stop or an error. Quota errors stop immediately without automatic retries. Local generation is reserved during a lab session to avoid overloading a small computer. Keep the hosting Web server or terminal running.

```powershell
nila gemini setup
nila gemini models
nila learn
# Or provide the topic and options; Gemini model selection and consent are prompted:
nila learn "Python dictionaries" --minutes 15 --rounds 10
nila learn --list
nila learn --show SESSION_ID
nila learn --stop SESSION_ID
nila knowledge
```

The guided `/learn` path inside interactive chat is the simplest terminal route. API keys are entered using a hidden prompt, not command arguments. Ctrl+C stops a terminal session. Web transcripts show partial local tokens; CLI transcripts print each completed turn and preserve partial content on stop.

## Personalize Nila

Open **Preferences** in the Web UI, or use:

```powershell
nila settings --user "Nadeem" --position Student --course "Your course" --completion-year 2027
nila settings --position Employee --company "Your company" --job-role "Developer"
nila settings --description "I am learning web development" --interests "Python, cybersecurity"
nila settings --tone Friendly --language English
nila settings --auto-memory on
```

Automatic memory is on by default. It only considers short first-person statements, skips messages containing sensitive markers, and requires quoted evidence and values to appear in your actual message. It does not mine questions, long pasted text, or automation prompts. It is deliberately conservative and may miss facts, especially with a small model or Malayalam text. It can still make extraction mistakes—review the **Memory** page.

Disabling memory use also disables automatic extraction. Disabling automatic extraction alone keeps previously saved facts available. Deleted/corrected facts are blocked from being saved again in exactly the same normalized form; paraphrases may still be learned. Profile fields are separate from saved memories.

## Offline automation

Open **Automations** to create a job, optionally ask Nila to draft it, select its next run and interval, and save it. No job is enabled merely by generating a draft.

Examples:

```powershell
nila automation add --title "Study tip" --kind ai --prompt "Write one practical Python study tip" --every 1440 --after 5
nila automation add --title "My briefing" --kind brief --prompt "Summarize my notes and unfinished tasks into a short plan" --every 1440
nila automation add --title "Practice reminder" --kind task --prompt "Practice Python for 20 minutes" --after 30
nila automation list
nila automation run AUTOMATION_ID
nila automation pause AUTOMATION_ID
nila automation logs
```

Allowed actions are local AI text generation, summaries of local notes/tasks, and creating notes or to-dos. There is **no arbitrary command execution, external messaging, browser control, or access to arbitrary folders**. Results are stored in the encrypted run history, accessible in the Web UI and CLI. These jobs do not produce native notification pop-ups.

The Web server runs a scheduler while open. The Windows installer also registers a background worker at login. To run a worker manually:

```powershell
nila worker
```

Your computer must be on and awake. A missed schedule runs once when Nila resumes; it does not replay every missed interval. Intervals are elapsed minutes, not calendar/timezone rules; `1440` means every 24 hours. A cross-process claim prevents simultaneous workers from running the same scheduled occurrence. A process crash at the exact point of writing an item can still cause a repeated side effect after retry; this is not an exactly-once transaction system.

Windows background worker controls:

```powershell
nila service start
nila service stop
nila service enable
nila service disable
```

Start/stop controls affect the Windows scheduled worker. The Web server keeps its own scheduler active while running. **Pause a job** to disable and stop it across workers. Disabling login startup does not terminate an already running worker.

## Updates without releases

Managed Windows installs check the latest **GitHub `main` commit** at startup, at most once every 24 hours, and build a new binary if necessary. Updates do not wait for tags or GitHub Releases. Offline checks fail quietly without blocking local chat.

```powershell
nila update --check
nila update
nila settings --auto-update off
```

The Web UI exposes the same controls under **System**. A new version is built in isolation and activates on the **next launch**. Your current process and model remain in use until restarted. Personal data is kept outside application version folders. Failed builds retain the previous active version. Update logs are under `%LOCALAPPDATA%\NilaApp`.

The update trust boundary is this GitHub repository and HTTPS. Git blob checks detect mismatched downloads; they are not independent publisher signatures. Installed dependencies are also trusted. This mechanism does not automatically upgrade every installed model or unrelated system package.

## CLI and Web UI parity

| Terminal | Web UI |
| --- | --- |
| `nila`, `nila ask`, `nila chat --chat ID` | Conversations; resume a saved chat |
| `nila history`, `nila delete ID`, `nila export ID` | Sidebar history, delete and export |
| `nila settings` | Preferences and profile |
| `nila memory`, `nila notes`, `nila tasks` | Memory, Notes, Tasks |
| `nila gemini setup/models/remove`, `nila learn` | Learning Lab connection, session controls and transcript |
| `nila knowledge list/edit/disable/enable/remove` | Learning Lab → Learned knowledge |
| `nila models`, `nila model use NAME` | Preferences model selector; System model list |
| `nila pull NAME` | System → Model download |
| `nila doctor` | System → Run diagnostics |
| `nila update --check`, `nila update` | System → Update controls |
| `nila automation add/edit/list/run/pause/remove/logs/draft` | Automations form, job actions and run history |
| `nila service start/stop/enable/disable` | System → Background worker |

`nila web` and `nila worker` are process launch commands; the browser cannot launch itself. Interactive CLI shortcuts: `/new`, `/remember TEXT`, `/exit`. Ctrl+C stops terminal chat or the worker. Web chat has a Stop button.

Additional examples:

```powershell
nila ask "Explain Python dictionaries"
nila chat --chat CONVERSATION_ID
nila export CONVERSATION_ID > conversation.md
nila memory add "I prefer practical examples"
nila memory edit ITEM_ID "I prefer short examples"
nila memory remove ITEM_ID
nila tasks add "Review my project"
nila tasks done ITEM_ID
nila settings --context 2048 --temperature 0.7
nila automation draft --prompt "Every hour, write a short study tip"
```

## Manual setup / development

Install Python 3.11+, Node.js 22+, and Ollama. Clone the repository, then:

```bash
python -m venv .venv
# Linux:
source .venv/bin/activate
# Windows PowerShell, if activation is restricted, use .venv\Scripts\python.exe directly.
python -m pip install -e ".[dev]"
cd web
npm ci
npm run build
cd ..
ollama pull llama3.2:1b
nila web
```

For the frontend development server, run `npm run dev` in `web/` while the backend runs on port 8765. Tests: `python -m pytest -q`. Binary: `python scripts/build_binary.py`. Build Windows binaries on Windows and Linux binaries on Linux. GitHub Actions builds both.

## Data and security

Run `nila doctor` to see the actual data path. Defaults: `%LOCALAPPDATA%\Nila` on Windows; `~/.local/share/Nila` on Linux. `NILA_DATA_DIR` overrides it.

Content fields—including messages, chat titles, profile/settings, notes, tasks, memories and automation outputs—are encrypted using Fernet authenticated encryption. IDs, timestamps, roles, schedules, statuses and memory fingerprints remain SQLite metadata. Existing v0.1.0 plaintext content is migrated on first use. Migration cannot remove copies in external backups, filesystem snapshots or SSD history.

**Keep `vault.key` with the database.** On Windows the key is bound to your Windows user through DPAPI; copying files alone to another account or computer may not unlock them. On Linux it is a private local key file. Losing the key makes encrypted data unreadable. This is protection for stored data, not protection against a malicious process already running as your user. Exports are plaintext.

The server binds to loopback only. Do not publish it through a tunnel or expose it as a multi-user service. See [SECURITY.md](SECURITY.md) for boundaries and reporting guidance.

## Current limits

- Real model speed and Malayalam quality depend on your hardware and selected model. `llama3.2:1b` is a starting point, not a guarantee of advanced reasoning.
- Normal chat does not autonomously create schedules; use the automation draft/form or CLI.
- No voice, wake word, PDF ingestion, arbitrary file manipulation, live web search, or remote computer control.
- Initial installs, updates, model downloads and Gemini Learning Lab require internet. Installed local models and scheduled local operations work offline.
- Automatic binary updating is implemented for the managed Windows installer. Linux/source installs require manual updates and rebuilds.
- The Windows installer and DPAPI path require Windows validation; see the current [validation report](docs/VALIDATION.md).

## Project documentation

- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Validation](docs/VALIDATION.md)
- [Changelog](CHANGELOG.md)

## License

Nila source code is licensed under the [MIT License](LICENSE), copyright 2026 Nadeem Muhammed. Ollama models, Gemini services and third-party dependencies retain their own licenses and terms.
