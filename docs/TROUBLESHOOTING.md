# Troubleshooting

Start with **System → Run diagnostics** or `nila doctor`.

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
| Automation did not run | PC asleep, job paused, or no worker/server | Check schedule, run `nila service start` or `nila worker`; keep PC awake. |
| Memory not learned | Conservative extraction skipped it | Use a short first-person statement or add the fact manually. |
| Update unavailable | Offline/API limit or unsupported install | Retry later; use manual rebuild for Linux/source installs. |

## Windows setup and updates

Rerun the one-line installer to recover a partial setup; it checks existing prerequisites/model before downloading them again. Application binaries live under `%LOCALAPPDATA%\NilaApp\versions`, while personal data normally lives under `%LOCALAPPDATA%\Nila`.

An update activates on the next launch. Close the Web/CLI process and reopen it; stop/start the login worker to move it to the new version. A failed staged build leaves the active binary intact. Check `last-update.log` or `auto-update-launch.log` in NilaApp. The `previous.txt` pointer retains the previous active commit for manual recovery; preserve it until a new version has been exercised.

## Encryption and backups

Stop Nila and its worker before backing up the entire data folder. Keep `vault.key` with `nila.db`; the database alone is insufficient. Windows DPAPI keys are account-bound. Existing external plaintext backups from v0.1.0 are not encrypted by the upgrade.

## Offline and scheduling behavior

Chat, saved content and installed-model jobs work offline. Downloading a model, installing requirements or checking/building updates requires internet. Scheduled repeats use elapsed minutes. Missed intervals are collapsed to one run when a scheduler returns. Notes/to-dos created by automation are not native desktop notification reminders.

## Source development

If `/` reports that the interface is missing, run `npm ci` and `npm run build` in `web/`, then restart. If port 8765 is occupied, stop the other server or use `nila web --port 8766`; Vite's development proxy targets 8765 by default.
