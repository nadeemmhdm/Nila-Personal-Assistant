# Nila Personal Assistant

**A friendly, local-first AI assistant for your browser and terminal.**

Nila runs on Ollama, remembers useful details about you, and carries out scheduled local work. The Web UI and `nila` command share encrypted storage and the same assistant settings.

**Version:** 0.2.0 · **Default model:** `llama3.2:1b` · **Platforms:** Windows and Linux

## Install on Windows — one command

Open **PowerShell** and paste:

```powershell
irm 'https://raw.githubusercontent.com/nadeemmhdm/Nila-Personal-Assistant/main/scripts/install.ps1' | iex
```

The command runs this repository's installer. It:

1. Checks Python, Node.js/npm, and Ollama; installs missing requirements using WinGet.
2. Downloads an immutable `main` commit and verifies each archived source file against its Git blob hash.
3. Builds the Web UI and a standalone **`nila.exe`** in a staging directory.
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
| Personal profile | Name, description, college, course/role, interests, language and conversation tone |
| Friendly responses | Profile-aware system instructions; model quality still determines the result |
| Automatic memory | Local AI extracts supported, explicit facts from short personal statements |
| Memory controls | Inspect source, correct, delete, deduplicate, disable learning or disable memory use |
| Local storage protection | Authenticated content encryption; Windows encryption key protected by CurrentUser DPAPI |
| Notes and tasks | Create, edit, remove and complete local items |
| Offline automations | AI writing, notes/tasks briefs, scheduled notes and scheduled to-dos |
| Natural-language scheduling draft | Describe a job; review and save the proposed action and schedule |
| Maintenance | Diagnostics, model download/resume and commit-based update controls |
| Interface | Animated orb, response animation, responsive navigation, themes and reduced-motion support |

## Personalize Nila

Open **Preferences** in the Web UI, or use:

```powershell
nila settings --user "Nadeem" --college "Your college" --course "Your course"
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
- Initial installs, updates and model downloads need internet; installed local models and scheduled local operations work offline.
- Automatic binary updating is implemented for the managed Windows installer. Linux/source installs require manual updates and rebuilds.
- The Windows installer and DPAPI path require Windows validation; see the current [validation report](docs/VALIDATION.md).

## Project documentation

- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Validation](docs/VALIDATION.md)
- [Changelog](CHANGELOG.md)
