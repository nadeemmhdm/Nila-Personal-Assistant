# Contributing to Nila

Thank you for helping make local personal assistance more useful and reliable.

## Development setup

Use Python 3.11–3.13, Node.js 22+, and Ollama. Create a virtual environment, install `python -m pip install -e ".[dev]"`, then run `npm ci` and `npm run build` in `web/`. Start the backend with `nila web --no-open`. For frontend development run `npm run dev` in `web/`.

Use a separate test data directory via `NILA_DATA_DIR`. Never commit a personal database, encryption key, model file, access token, log containing private content, or generated executable.

## Architecture

| Module | Responsibility |
| --- | --- |
| `nila/storage.py`, `vault.py` | Database, encryption, migration and shared state |
| `nila/engine.py`, `memory.py` | Ollama streaming, profile context and evidence-checked memory |
| `nila/automation.py`, `worker.py` | Durable schedules, claims, run history and background worker |
| `nila/extensions.py`, `server.py` | Local API, maintenance and Web lifecycle |
| `nila/cli.py` | Terminal interface over the same services |
| `nila/updater.py` | Fixed-upstream commit checks and update launch |
| `scripts/install.ps1`, `launcher.ps1` | Staged Windows installer and stable launcher |
| `web/src` | React interface and shared settings/automation controls |

## Before opening a pull request

1. Explain the user problem and intended behavior.
2. Keep CLI and Web controls aligned for new capabilities.
3. Add regression tests for meaningful behavioral or security changes.
4. Run `python -m pytest -q` and `npm run build` in `web/`.
5. Check keyboard interaction, small-screen layout and reduced motion for UI changes.
6. Update README, troubleshooting, security boundaries and changelog when behavior changes.

Windows installer or DPAPI changes need Windows testing. A Linux unit test or PowerShell parse check does not establish end-to-end installation success. Record the exact checks you ran and anything you could not validate.

## Security and model behavior

Model output is data, not trusted executable instructions. Do not add arbitrary shell execution, expose loopback services publicly, weaken origin checks, or bypass update integrity checks. New automation actions must have explicit bounded schemas and user-visible controls. Memory changes must preserve user review, deletion and off switches.

See [SECURITY.md](SECURITY.md) for private reporting guidance. Keep pull requests focused, preserve existing user data, and avoid unrelated refactors.
