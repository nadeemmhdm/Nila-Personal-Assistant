# Nila Personal Assistant

A personal space to think, create, and explore — powered by Ollama on your computer.

**Repository slug:** `nila-personal-assistant`  
**Version:** 0.1.0  
**Suggested GitHub description:** Local-first personal AI assistant powered by Ollama, with an animated React interface, a native CLI, shared chat history, and editable memory.

## Included

- React + Vite + TypeScript interface, responsive sidebar, dark/light themes, animated orb, streaming replies, stop control, Markdown and code blocks, copy, conversation search, and Markdown export.
- `nila` command: interactive chat, one-shot questions, Web UI launcher, diagnostics, model selection, settings, history, export, memory, notes, and tasks.
- Local SQLite storage shared by Web UI and CLI. Explicit memory with edit/delete controls and an off switch.
- Default model `llama3.2:1b`, model availability checks, clear error codes, and conservative 2,048-token context.
- Local-only HTTP server, origin/host checks, blocked remote Ollama addresses, no telemetry, and no external fonts or image requests.
- Windows/Linux binary build script and GitHub Actions build artifacts.

## Packaged source ZIP

The source ZIP includes a prebuilt Web UI, so Node.js is optional unless you change the interface. With Python installed, run `powershell -File scripts/setup.ps1` on Windows (if your policy allows local scripts), or `bash scripts/setup.sh` on Linux. Then run `.venv\Scripts\nila.exe web` or `.venv/bin/nila web`. The manual steps below also work.

The ZIP includes an optional tested Linux binary under `binaries/linux/nila`. Windows users should use the Python installation or build `nila.exe` on Windows.

## Quick start — Windows

Install Python 3.11+ (add Python to PATH), Node.js 22 LTS, and Ollama from their official websites. Open Ollama. Extract this project, open PowerShell in its folder, and run:

```powershell
ollama pull llama3.2:1b
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
cd web
npm ci
npm run build
cd ..
.\.venv\Scripts\nila.exe settings --user "Nadeem"
.\.venv\Scripts\nila.exe doctor
.\.venv\Scripts\nila.exe web
```

The browser opens at **http://127.0.0.1:8765**. Keep the terminal running. Stop the server with Ctrl+C.

To get the short `nila` command in the current PowerShell session without changing execution policy:

```powershell
$env:Path = "$PWD\.venv\Scripts;$env:Path"
nila
```

## Quick start — Linux

Install Python 3.11+, Python venv support, Node.js 22, and Ollama. Start Ollama, then:

```bash
ollama pull llama3.2:1b
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
cd web
npm ci
npm run build
cd ..
nila settings --user "Nadeem"
nila doctor
nila web
```

Dependencies and the model need internet for initial installation. Normal chat runs locally after installation. Ollama must remain installed and running; the Nila binary does not embed Ollama or model weights.

## CLI

```bash
nila                                  # interactive chat
nila ask "Explain Python dictionaries"
nila chat --chat CONVERSATION_ID       # continue a Web or CLI conversation
nila ask "Give an example" --chat CONVERSATION_ID
nila web                              # start Web UI
nila web --no-open --port 8765
nila doctor
nila models
nila model use llama3.2:1b
nila settings --name "Nila" --user "Nadeem" --language English
nila history
nila export CONVERSATION_ID > conversation.md
nila delete CONVERSATION_ID
nila memory add "I prefer practical examples"
nila memory                            # shows item IDs
nila memory edit ITEM_ID "I prefer short examples"
nila memory remove ITEM_ID
nila notes add "Project idea: a habit tracker"
nila tasks add "Review my project"
nila tasks done ITEM_ID
nila --version
```

Inside interactive chat: `/new`, `/remember TEXT`, `/exit`. Ctrl+C stops the current operation and exits. Restart with `nila chat --chat ID` to resume. The Web UI has an explicit Stop button.

## Build a standalone binary

Build on the target operating system. You cannot build a Windows executable on Linux using PyInstaller.

```bash
python -m pip install -e ".[dev]"
# Build the Web UI first (npm ci, npm run build in web/).
python scripts/build_binary.py
```

Output: `dist/nila.exe` on Windows or `dist/nila` on Linux. Put the binary in a folder on PATH to use `nila` from anywhere. It includes the Web UI and Python runtime. Linux binaries depend on a compatible system/glibc; build on your target Linux version for best compatibility.

The included GitHub workflow tests and builds both platforms and uploads downloadable artifacts under the Actions run. It does not publish releases automatically.

## Development

```bash
python -m pip install -e ".[dev]"
nila web --no-open
# In another terminal:
cd web
npm ci
npm run dev
```

Vite runs at `http://127.0.0.1:5173`, proxying `/api` to port 8765. The production server serves compiled assets directly. Run `python -m pytest -q` and `npm run build` before packaging.

## Data and privacy

- Data directory: Windows `%LOCALAPPDATA%\Nila`; Linux normally `~/.local/share/Nila`. `nila doctor` prints the actual path.
- Override with `NILA_DATA_DIR`. Back up the entire folder after stopping Nila.
- SQLite is **not encrypted**. Do not save passwords, API keys, or other secrets in memory. Use OS account controls and disk encryption.
- Only explicitly saved memories are injected into prompts. Chat history is saved automatically. Notes/tasks are separate and are not sent automatically.
- Long conversations are trimmed to recent context, and saved memory is capped in the prompt. The UI retains full saved history. Context estimation is approximate; the model/runtime determines the effective context window.
- One generation at a time across Web and CLI. A crash may leave a lease for up to 11 minutes; wait before retrying.
- The backend only binds to loopback. Do not expose it through a public tunnel or reverse proxy; this release has no multi-user login.
- Optional `NILA_OLLAMA_URL` accepts only a loopback HTTP endpoint. Default: `http://127.0.0.1:11434`. No cloud API key support in this local release.

## Current limits

This is a first working release, not an autonomous computer-control agent. Voice, wake word, document Q&A, live web search, attachments, notifications, automatic updates, and system command execution are not included. Model downloads use `ollama pull` in your terminal. Code blocks render as formatted text without syntax highlighting. “Use last prompt again” fills the composer; submitting it creates a new turn. Assistant identity is instructed through the system prompt; small models can still make mistakes. Malayalam quality depends on the selected model.

See [troubleshooting](docs/TROUBLESHOOTING.md), [security](SECURITY.md), and [validation](docs/VALIDATION.md).
