# Troubleshooting

Start with **Workspace → System → Run diagnostics** or `nila doctor`.

| Symptom/code | Meaning | Next step |
| --- | --- | --- |
| NILA-001 | Ollama unavailable | Open Ollama or run `ollama serve`. |
| NILA-002 | Selected model missing | Run `nila pull llama3.2:1b` or use System → Model download. |
| NILA-003 | Another generation is active | Stop/wait for it. A crash-held lease expires within 12 minutes. |
| NILA-004 | Generation interrupted or timed out | Check RAM/Ollama; try a shorter prompt or 2,048 context. |
| NILA-005 | Non-local Ollama URL | Unset `NILA_OLLAMA_URL` or use a loopback HTTP address. |
| NILA-006 | Internal error | Restart and reproduce with non-private test data. |
| NILA-010 | Encryption key unavailable/invalid | Restore the original `vault.key`; do not delete/reset the database. |
| NILA-020 | Installer/pointer integrity problem | Retry the official installer; retain your data directory. |
| `nila` not recognized | New PATH not loaded | Open a new terminal; check `%LOCALAPPDATA%\NilaApp\bin`. |
| WinGet unavailable | App Installer missing | Install/update Microsoft App Installer from Microsoft Store. |
| Prerequisite install fails | WinGet, permissions or network issue | Complete Windows permission prompts, check internet, then rerun. |
| Old automation no longer runs | Retired in v0.5 | Old data is retained; the worker now serves optional Telegram access. |
| Memory not learned | Conservative extraction skipped it | Use a short first-person statement or add the fact manually. |
| Update unavailable | Offline/API limit or unsupported install | Retry later; use manual rebuild for Linux/source installs. |

## Windows setup and updates

Rerun the one-line installer to recover a partial setup; it checks existing prerequisites/model before downloading them again. Application binaries live under `%LOCALAPPDATA%\NilaApp\versions`, while personal data normally lives under `%LOCALAPPDATA%\Nila`.

An update activates on the next launch. Close the Web/CLI process and reopen it; stop/start the login worker to move it to the new version. A failed staged build leaves the active binary intact. Check `last-update.log` or `auto-update-launch.log` in NilaApp. The `previous.txt` pointer retains the previous active commit for manual recovery; preserve it until a new version has been exercised.

## Encryption and backups

Stop Nila and its worker before backing up the entire data folder. Keep `vault.key` with `nila.db`; the database alone is insufficient. Windows DPAPI keys are account-bound. Existing external plaintext backups from v0.1.0 are not encrypted by the upgrade.

## Offline behavior

Chat and attached-text retrieval work offline with an installed local model. Search, Telegram, Gemini, downloads and updates need internet. Notes, tasks and scheduled automation no longer run.

## Source development

If `/` reports that the interface is missing, run `npm ci` and `npm run build` in `web/`, then restart. If port 8765 is occupied, stop the other server or use `nila web --port 8766`; Vite's development proxy targets 8765 by default.

## Learning Lab

- **No Gemini models:** save a valid key, then load models. This action needs internet. Account restrictions may hide or deny models.
- **Quota/rate limit:** the session stops without automatic retries. Check your AI Studio quota and choose an available model or retry later. Nila does not upgrade billing automatically.
- **Invalid or blocked review:** no lesson is saved for that review. Try a different supported Gemini model or a clearer topic.
- **Local model unavailable:** download it in System or with `nila pull MODEL`. Learning Lab needs a local text-chat model; embedding-only and cloud-tagged local-model selections are unsuitable.
- **Another request is running:** Learning Lab reserves local generation. Stop the lab or wait before starting ordinary chat.
- **No learned improvement:** only acceptable reviewed lessons are saved; matching uses topic/content keywords. Check Learning Lab → Learned knowledge and the Preferences knowledge switch. This is retrieved context, not model-weight training.
- **How to stop:** use Stop session, `nila learn --stop ID`, or Ctrl+C in the terminal running the session. Closing a browser tab alone does not stop the server-hosted session.
- **CLI feels complicated:** run `nila` once, then type normal messages. `/model` switches models; `/learn` opens the guided discussion wizard.

## Windows: OSError / missing PyInstaller hook / long paths

The earlier installer nested `.venv` under a long `stage-<GUID>/source/<repository>-<40-character-commit>` path. This could exceed Windows' traditional path limit for dependency filenames. The current installer uses short `b-<id>/s` and `b-<id>/v` paths, without requiring a system registry change. Rerun the one-command installer from README. App data is separate and retained. Build cleanup removes only the current staging directory. An unusually long LOCALAPPDATA path is rejected before downloading dependencies.

## NILA-020 — Web search unavailable

Check internet connectivity, try a shorter query, or select Off. Search services can throttle or block requests; no API key is required but availability is not guaranteed. Deep issues three public query variants. The query is derived automatically from the first 500 characters of the current question. Failed lookup leaves an edited conversation branch intact and does not fabricate a live answer.

## Feedback or edited prompts

Thumbs express preference; use regeneration instructions when you want a specific correction to the current answer. Feedback stays local and does not train model weights. Click a selected thumb again to clear its stored guidance. Editing an earlier user prompt preserves the original conversation in a branch and replaces subsequent dependent turns in the current chat, but separately stored personal memories must be managed on the Memory page.

## v0.5 chat, files and connections

- **Telegram does not reply:** start the bot yourself, enter your positive private user ID, enable the connection and keep Nila/Ollama awake. Groups are intentionally ignored. Test checks the token only, not a delivered message. A polling conflict means another process or webhook owns that bot; stop it before retrying. Do not paste tokens into issues.
- **Gemini never asks/reviews:** inspect the inline Lab status. Confirm key, selected model access, internet and quota. The session stops on invalid structured output or provider failure. Opening-question failure now occurs before local generation. No live Gemini key is needed for normal chat.
- **Low/Medium/High looks similar:** smaller/non-thinking models use different answer budgets and guidance. Native thinking depends on Ollama capability support and is not model training.
- **PDF has no text:** scanned PDFs need OCR outside Nila. Attach UTF-8 text or a text-based PDF. File/page/text limits and the extraction timeout are intentional.
- **CLI shows little color:** use a modern terminal with color support. Redirected output may omit ANSI colors. Markdown code blocks intentionally preserve characters such as `#` and `*`.
- **Suggested questions are absent:** they are optional local generations and may be skipped if Ollama is busy, times out or returns invalid JSON. Chat continues normally.
- **Old automation stopped:** v0.5 retires scheduled work; the login worker now hosts the optional Telegram connection. Old data is retained, not executed.
- **Temporary chat remains after closing a tab:** use New conversation or delete/close the temporary conversation, or stop the server. A tab closing alone does not guarantee RAM disposal.
