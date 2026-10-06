# Nila Personal Assistant

**A personal AI workspace for your browser, terminal and private Telegram chat.**

Version **0.8.0** · Developed by [Nadeem](https://github.com/nadeemmhdm) · MIT license

Nila uses Ollama on your computer. New installs default to **Smart (`qwen3:4b`)**. Select **Fast (`qwen3:0.6b`)**, **Medium (`qwen3:1.7b`)**, or any installed compatible text model. Existing selections, including `llama3.2:1b`, are preserved. Personal conversations, memories and attached text stay local unless you deliberately use an online feature. No Ollama API key is needed for the local endpoint.

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
7. Registers a per-user Windows login worker for the optional Telegram connection.

Open a **new terminal** after installation:

```powershell
nila
nila web
```

`nila` starts terminal chat. `nila web` opens **http://127.0.0.1:8765**. The launcher selects the installed `nila.exe`; Python is not required to execute that binary, although the installer uses Python to build it.

**Requirements:** Windows 10/11 with WinGet/App Installer, internet for initial downloads, and enough disk space for build tools and model weights. Windows may request permission to install prerequisites. If WinGet is absent, the installer attempts to bootstrap it using Microsoft.WinGet.Client. If Windows policy prevents that, install Microsoft App Installer from Microsoft Store and rerun. Managed Windows installations receive automatic code updates. Linux/source installations use the manual workflow below.

## A cleaner conversation experience

Run `nila` and type naturally, or open `nila web`. Continue a conversation by sending your next message; Nila receives the previous turns automatically.

- Web messages appear on opposite sides, with dark/light themes, a collapsible sidebar and separate Explore/History views.
- Search, thinking level, model selection and attachments live inside the composer. Inline notices replace confirmation popups.
- Answers render headings, **bold**, *italic*, underline, lists, tables and code. Copy either a prompt or answer. Literal syntax inside code is preserved.
- Use the edit icon on a prompt to rewrite that turn. Later turns are preserved in a separate branch before replacement.
- Use the regenerate icon on an answer for an optional “What should change?” instruction. The new answer replaces that same answer after successful generation. Cancellation/failure retains the original. Later turns move to an archived branch.
- Contextual suggested questions are generated locally from the current question and answer. They are optional; sending a new message cancels pending suggestions.
- 👍 and 👎 provide local preference examples. They influence future context without retraining model weights or sending feedback to Gemini.
- CLI has a colorful Nila banner, animated status and rendered Markdown. Terminal support determines available colors and emphasis; underline is rendered as emphasis.

## Thinking and models

Choose **Low**, **Medium** or **High**. These change answer depth and output budget. Nila checks Ollama model capabilities before enabling native thinking; `llama3.2:1b` does not gain a new reasoning capability from this setting. Progress labels describe current work and do not expose private reasoning traces.

The composer lists installed Ollama models. Workspace → Setup checks available RAM and model readiness; RAM estimates are approximate. Workspace → System can download a model and show diagnostics. Nila introduces itself as Nila. Developer attribution is requested in the system prompt only when the user asks who developed the application.

## Search: Off, Quick or Deep

Search starts **Off**. Quick uses one query and up to four sources; Deep uses three query perspectives and up to eight deduplicated sources. Both use open-source [DDGS](https://github.com/deedy5/ddgs) without a paid search key.

When enabled, the current question (up to 500 characters) supplies the query automatically. There is no separate query box. Saved history, memories, profile and attachments are excluded from search requests. Search providers receive that query and network metadata. Do not enter private information with search enabled.

Answers include clickable source URLs. “Sources & context” shows the references supplied to the model. Search uses result snippets, not full-page browsing; Deep is broader retrieval, not exhaustive research. Results may be unavailable or incorrect. Failed searches show an inline error instead of claiming live evidence. Regeneration uses local context and does not launch another search.

## Personalization, memory and files

Preferences include your name, description, language, tone and position. Student fields include course/completion year; employee fields include company/role. Nila does not require everyone to enter college details.

Local memory extraction proposes explicit useful facts. **Review is on by default**: approve, edit or reject suggestions in Workspace → Memory inbox. Saved memories can be edited/deleted, and learning/use can be disabled. Sensitive-fact filtering is heuristic.

Projects group conversations, instructions and documents. Attach PDF or UTF-8 TXT, Markdown, CSV, JSON, Python, JavaScript, TypeScript, HTML or CSS. Limits: 5 MB per file, 100 PDF pages, 500,000 extracted characters, 100 stored documents and 10 direct attachments per conversation. Nila retrieves relevant text excerpts with filename/page references. Scanned PDF OCR, images, audio and arbitrary binary formats are not supported. Files are read as data, never executed.

Temporary chats keep their chat and attachment records in RAM. They exclude personal profile/memory/feedback, do not appear in saved history/backups, and close when deleted, when you switch away using Nila controls, or when the server exits. Closing only the browser tab does not guarantee immediate disposal. OS swap/crash dumps remain outside this guarantee.

Password-encrypted backups include saved workspace content but exclude API credentials and temporary chats. Restore previews counts, then replaces saved workspace data and disables Telegram/automatic updates. Keep the password; there is no recovery backdoor. Sources/provenance record supplied context, not proof of why a model answered.

## Learning Lab: Gemini asks, Nila answers

Save an optional Gemini key in Learning Lab. Enter a non-private topic and description, acknowledge sharing that study content, then start a timed session.

1. Gemini asks the opening question.
2. The selected local model answers.
3. Gemini reviews the answer, identifies mistakes and explains corrections.
4. The local model revises, or proceeds to the next related question.

Both sides and waiting/error states are visible. Stop at any time; duration and round limits also stop the session. Accepted lessons can be saved as editable local study references. This is context learning, **not weight training**. Gemini can also be wrong.

**Gemini never receives ordinary personal chats, profile, memories, attachments or feedback from Nila's context store.** It receives only the explicitly shared study-session content. Do not paste private information into that topic. A free-tier key remains subject to Google's model access, quotas and terms. See [Learning Lab](docs/LEARNING_LAB.md).

## Telegram connection

In Workspace → Telegram, enter your BotFather token and your numeric **private user/chat ID**. Start the bot from your own Telegram account, test the token, save and enable the connection. Keep `nila web` or `nila worker`, Ollama, the laptop and internet running.

Only the configured private user can use the bot; groups and other senders are ignored. `/new` starts a new bot conversation. The token is encrypted and never returned by status APIs or included in backups. Personal-memory sharing is off by default and requires a separate opt-in. Telegram receives bot messages and replies even when the underlying model runs locally. Disable/disconnect in the same section to stop access. One poller owns the connection across Web/worker processes.

## CLI shortcuts and parity

| CLI | Web |
| --- | --- |
| `nila`, `nila ask "Explain Python dictionaries"` | Chat |
| `/resume ID`, `nila history` | Sidebar → History |
| `/regenerate optional instructions` | Regenerate icon + optional instructions |
| `/think low`, `/think medium`, `/think high` | Thinking selector |
| `/search off`, `/search quick`, `/search deep` | Search selector |
| `/attach FILE` | Composer attachment button |
| `/up`, `/down` | 👍 / 👎 |
| `nila models`, `nila model use NAME` | Installed-model selector |
| `nila inbox`, `nila memory` | Memory inbox / Memory |
| `nila projects`, `nila documents` | Workspace → Projects / Documents |
| `nila backup FILE`, `nila restore FILE` | Workspace → Backup |
| `nila telegram setup/status/test/disable/remove` | Workspace → Telegram |
| `nila gemini setup`, `nila learn` | Learning Lab |
| `nila setup`, `nila doctor` | Workspace → Setup / System |
| `nila update --check`, `nila update`, `nila rollback` | System updates / Versions |

Use `--help` on a command for arguments. `nila chat --temporary` starts a temporary terminal conversation. `/exit` exits. `nila mini` opens the compact Web view while the server is running.

Notes, tasks and scheduled automations have been removed from active interfaces and execution in v0.5. Existing records are retained for backup compatibility; they are not run by the new worker.

## Updates and privacy

Managed Windows installations check **stable GitHub Releases**. Updates use a prebuilt Windows executable with GitHub SHA-256 verification and a version smoke check before activation. The initial source installer uses short build paths and verifies Git blob hashes. Restart Nila to use the new version. Failed updates keep the previous version; Versions offers rollback. Disable automatic updates with `nila settings --auto-update off`.

Web runs only on loopback. Do not expose it publicly. Saved content uses authenticated encryption; Windows protects its key with CurrentUser DPAPI. Local account compromise remains outside the protection boundary. Ollama cloud-tagged models are not offline models. See [Security](SECURITY.md), [Troubleshooting](docs/TROUBLESHOOTING.md), [Validation](docs/VALIDATION.md), [Changelog](CHANGELOG.md) and [Contributing](CONTRIBUTING.md).

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

**Keep `vault.key` with the database.** On Windows the key is bound to your Windows user through DPAPI; copying files alone to another account or computer may not unlock them. On Linux it is a private local key file. Losing the key makes encrypted data unreadable. This is protection for stored data, not protection against a malicious process already running as your user. Conversation exports are plaintext; portable workspace backups are password-encrypted.

The server binds to loopback only. Do not publish it through a tunnel or expose it as a multi-user service. See [SECURITY.md](SECURITY.md) for boundaries and reporting guidance.

## Current limits

- Real model speed and Malayalam quality depend on your hardware and selected model. `llama3.2:1b` is a starting point, not a guarantee of advanced reasoning.
- Nila does not run arbitrary shell commands or scheduled automations.
- No wake word, scanned-PDF OCR, arbitrary file manipulation or remote computer control. Local speech requires supported browser/Windows language packs.
- Initial installs, updates, model downloads and Gemini Learning Lab require internet. Installed local models work offline when search and online integrations are disabled.
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

## New in 0.8.0

See [release notes](docs/releases/v0.8.0.md) for stable-release updates, Models and Skills dashboards, offline web-reference caching, Telegram modes, persistent attachments and local browser voice capabilities.

Use **Workspace → Models → Load & use** to switch local models. Import a Markdown skill through **Workspace → Skills → Add skill**. Multiple skills can be active until individually disabled; they provide instructions, not executable tools. **Workspace → Knowledge** manages dated saved web references.

Voice input is available only where the browser supports on-device recognition with an installed language pack; read-aloud needs an installed local voice. These controls do not send audio to Gemini.

## Shared model profiles

Use the header selector or Workspace → Models. Missing selections download and load before activation; installed models are reused. Failed activation retains the previous model. Nila never silently falls back to a different model. Profile mappings can be changed under Models → Configure profile model names.

```sh
nila model
nila model use fast
nila model use medium
nila model use current
nila model use llama3.2:1b
```

Telegram: `/model`, `/model fast`, `/model medium`, `/model current`. All interfaces share the same saved selection and apply it to subsequent requests without a restart. A running generation or Learning Lab session retains its original model.

Memory shows counts for personal facts, pending suggestions, accepted Learning Lab lessons and saved web topics. Opening Memory also recovers web references from up to 200 older completed answers once. Saved knowledge is reusable offline when knowledge recall is enabled. Model-reviewed notes and retrieved snippets can be wrong or outdated; Nila does not train its model weights.

## Nila's home and birthday

Open **About Nila & docs** in the Web sidebar or visit `/about/` on your local Nila server. The responsive landing page includes an origin story (fiction for fun), model controls, setup, releases, privacy, complete guides and offline error-code search. Source: `landing/`; `npm run build` in `web/` generates the bundled site automatically.

Nila's chosen birthday is **March 2, 2026**. Its identity prompt retains this date even when personal memory is disabled. On March 2 (laptop local date), a successful normal chat requests one birthday mention per year across Web/CLI/Telegram. No background greeting is sent when the app is closed.

## Voice and model switching

The microphone panel lets you select a language, install a supported browser speech pack and start local recognition. Unsupported English locales fall back to `en-US`. Windows users can explicitly choose **Use Windows microphone** with an installed Windows speech recognizer. Unsupported local languages remain unavailable; no cloud fallback is silently enabled. Read aloud toggles to Stop in the same response button.

Model selection now checks installed models, downloads only if missing, loads the selection, then saves it. Use `nila model use fast`, `/model fast` in interactive CLI or Telegram, or the Web selector. Keep the selection window/process open until activation completes. Failed activation retains the previous selection.

Files stay attached to a conversation until removed. Send files alone to summarize them, or include your question. Filenames appear on sent user messages. Attached-file requests prioritize local document context even with web mode selected; image vision and scanned-PDF OCR are not supported.

### Public landing-page hosting

The `Nila landing page` workflow builds the same static About page and saves it as the `nila-landing-site` artifact. If Pages is disabled, it reports that setup is required and does not claim a deployment. Once configured, it publishes to GitHub Pages. Enable **Settings → Pages → Source: GitHub Actions** once, then run the workflow (subsequent main pushes redeploy automatically). No user chat, memory, API credentials or local server is deployed. All assets use relative paths so the project URL works. The local `/about/` page does not depend on public hosting.

## Connect Google services through a PHP website

Open **Workspace → Google** to connect Gmail, Drive, Docs, Sheets, Classroom, YouTube or Meet individually. The separately delivered PHP OAuth broker handles sign-in; Nila reads Google data directly on your laptop. Preview selected content and use it in a local chat. Gemini cannot read these connections or imported documents. Read-only access is the default; explicit writes require the read/write bundle and local write permission.

Deploy the `public/` folder from the separate **Nila-PHP-OAuth-Website-v0.8.1.zip** to an HTTPS PHP 8.2+ host and register a Google Cloud **Web application** OAuth client. Configure the Google Client Secret on that server, then enter your domain and private pairing key in Nila; Nila adds HTTPS and the endpoint and checks the connection. Your laptop does not need a public address. GitHub Pages cannot run this PHP endpoint.

See [Google connections: deployment, permissions and commands](docs/GOOGLE_CONNECT.md), also bundled in **About Nila & docs**. Live Google access requires your own deployment and consent; this repository does not include an already connected Google application.

```bash
nila google setup
nila google connect gmail
nila google read gmail
nila google status
```

The PHP website source is distributed separately, not in the current repository. Its ZIP includes `START_HERE_MALAYALAM.md`, full OAuth setup and hosting instructions. Existing historical releases are unchanged.

### Ask connected Google services in chat

With a service connected, simply ask **“Show my YouTube channel”**, **“Show my Google Meet history”**, or paste a Google Doc/Sheet URL and ask for a summary. English, common Manglish and Malayalam read requests are supported. Missing links/connections prompt for setup; reads are bounded; explicit write actions require separate write permission. YouTube video links provide metadata, not a transcript. Google account reads work in normal local Web/CLI chats and do not send content to Gemini or public search. See [examples and limits](docs/GOOGLE_CONNECT.md#ask-in-normal-chat-082).

Pages deployment now uses only `.github/workflows/static.yml`; it builds and uploads `web/public/about`, not the repository root. Do not add a second stock Pages workflow that uploads `.`.


### Connected workspace (0.8.3)

Type @ in Web chat to choose a connected service with its account email. Connect all Google services in one sign-in, choosing read-only or read/write. Explicit writes also require the persistent local write toggle. See [0.8.3 examples and limitations](docs/releases/v0.8.3.md). Multiple skills stay enabled until disabled. Telegram accepts documents/photos up to 5 MB; images require a vision-capable local model.
