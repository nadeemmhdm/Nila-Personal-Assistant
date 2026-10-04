# Validation — v0.1.0

Validated in the Linux build environment on 2026-10-04.

| Check | Result |
| --- | --- |
| Python test suite | 11 passed |
| TypeScript type check and Vite production build | Passed |
| Desktop Chromium render (1440 × 950) | Passed; screenshot inspected |
| Mobile Chromium render (390 × 844) | Passed; screenshot inspected; no horizontal overflow |
| Browser preferences save | Passed |
| Browser memory and notes creation | Passed |
| Browser task completion | Passed |
| Browser mobile menu and light/dark theme | Passed |
| Ollama unavailable error and prompt restoration | Passed |
| Streaming through actual local HTTP connections | Passed with a simulated Ollama service |
| Stop during generation, partial-response persistence, and next request | Passed with a simulated Ollama service |
| Linux standalone binary build | Passed |
| Linux binary `--version`, Web UI, and settings endpoint | Passed |
| Windows binary build | Workflow supplied; not run in this Linux environment |
| Actual llama3.2:1b inference and Malayalam quality | Not tested; no Ollama model installed here |

Automated tests cover persistent history, cascading chat deletion, settings validation, memory CRUD, host/origin checks, shared generation locking, memory exclusion, streaming, missing model handling, broken streams, cancellation, local endpoint restrictions, and CLI/Web storage sharing.

A mocked model verifies integration and error handling; it does not establish real model quality, latency, RAM use, or hardware compatibility. Run `nila doctor` and a real chat on your own computer after downloading the model.
