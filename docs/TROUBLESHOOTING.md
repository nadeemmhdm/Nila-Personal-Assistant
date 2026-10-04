# Troubleshooting

| Code | Meaning | Fix |
| --- | --- | --- |
| NILA-001 | Ollama is unreachable | Open Ollama or run `ollama serve`. Run `nila doctor`. |
| NILA-002 | Selected model is missing | Run `ollama pull llama3.2:1b`, or pull the model shown in the error. |
| NILA-003 | Another generation is active | Stop it in the Web UI or wait. After a crash, the lock expires within 11 minutes. |
| NILA-004 | Generation failed, disconnected, or timed out | Check Ollama, RAM, and model availability. Retry with a shorter prompt or 2,048 context. |
| NILA-005 | Non-local Ollama URL | Unset `NILA_OLLAMA_URL` or use `http://127.0.0.1:11434`. |
| NILA-006 | Internal server error | Restart Nila, run `nila doctor`, and report reproducible steps without private chat data. |

## Browser shows “Build the web interface”

In the project folder: `cd web`, `npm ci`, `npm run build`. Restart `nila web`.

## `nila` is not recognized

Use `.venv\Scripts\nila.exe` on Windows or activate the virtual environment. For a packaged binary, add its folder to PATH. Use `python -m nila` as an alternative.

## Port already used

Stop the other instance or use `nila web --port 8766`. Vite development still expects backend port 8765 unless you edit its proxy configuration.

## 8 GB RAM laptop

Start with `llama3.2:1b`, 2,048 context, and one request at a time. Close memory-heavy applications. Speed depends on CPU and Ollama's hardware configuration; no tokens-per-second guarantee is made.

## Offline use

Initial dependency/model downloads require internet. Once installed, local chats, memory, notes, and tasks do not require internet. These features do not provide current web information.
