# Validation — v0.2.0

Validated in the Linux build environment on 2026-10-04.

| Check | Result |
| --- | --- |
| Python regression suite | 21 passed |
| TypeScript check and Vite production build | Passed |
| Profile saving in Chromium | Passed: name, college, course and description |
| Automation creation and immediate run in Chromium | Passed with a real local scheduler and deterministic note action |
| Automation history and shared Notes result | Passed |
| System diagnostics and encryption status | Passed |
| Mobile navigation and layout at 390 × 844 | Passed; no horizontal overflow |
| Chromium runtime errors during exercised flows | None |
| Linux standalone binary build | Passed |
| Packaged binary Web UI, settings and System API | Passed |
| Packaged binary encrypted storage and scheduled note | Passed |
| Windows script parsing | Added to Windows CI; not executed locally |
| Windows prerequisite installation / PATH / login task | Implemented; requires end-to-end testing on Windows |
| Windows DPAPI key protection | Implemented; requires Windows test runner |
| Real llama3.2:1b inference, extraction quality and speed | Not tested locally; model unavailable in this environment |
| Live main-branch update installation | Not executed locally; managed updater targets Windows |

Regression tests cover encrypted persistence and plaintext migration, wrong-key failure, explicit memory controls, evidence validation, sensitive-marker filtering, deduplication and forgetting, profile validation, scheduler claims, cancellation/pause state, API action allowlists, commit-based update checks, offline behavior, installer integrity rejection, streaming, origin checks and CLI/Web data sharing.

Model-dependent tests use simulated Ollama responses. They establish protocol handling and validation behavior, not model quality. The browser automation exercised real local note execution rather than an AI-generated response. Previous v0.1.0 browser checks covered conversation interaction, offline error handling, memory, notes, tasks, mobile navigation and theme switching.

Before distributing the Windows installer broadly, test a clean Windows account, an existing Ollama installation, interrupted downloads, unavailable WinGet, rollback after a build failure, and an upgrade from v0.1.0 using non-sensitive sample data.
