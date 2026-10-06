# Validation — v0.5.0

Validated in Linux on 2026-10-05. Simulated providers are explicitly identified below.

| Check | Result |
| --- | --- |
| Python regression suite | 54 passed; one upstream Starlette/httpx deprecation warning |
| TypeScript and Vite production build | Passed |
| Chromium chat controls | Copy prompt/answer, thumbs, prompt edit, same-place regeneration and normal follow-up passed |
| Search and suggestions | Automatic Quick query, clickable sources, contextual follow-up questions and empty composer passed with simulated providers |
| Markdown and layout | Bold/italic/underline/code, mobile overflow, light theme and History/sidebar controls passed |
| Personalization | Student/Employee conditional fields and absence of forced college question passed |
| Learning Lab browser flow | Gemini opening question → local answer → reviewer turn, saved lesson/disable and Stop passed with simulated providers |
| Privacy regressions | Gemini payload sentinel exclusion; RAM temporary records/files; project isolation; encrypted backup and wrong-password handling passed |
| Telegram security | Token masking/encryption, private sender allowlist, rejected groups/other users, personal context off and disable-before-send passed using mocks |
| Thinking and terminal | Unsupported/native capability mapping, effort budgets and rendered Markdown passed |
| Linux standalone binary | Built successfully; version and packaged PDF extraction passed |
| Windows installer and DPAPI end-to-end | Not run here; Windows CI includes tests, binary build, script parsing and compact-path dependency installation |
| Live Gemini / Telegram | Not tested; no real credentials were supplied |
| Real Ollama generation quality | Not established by mocked integration tests |
| Live search reliability | Provider/network dependent; prior live checks returned one result but later requests timed out or returned none |

The Windows MAX_PATH repair keeps source and virtual-environment paths short rather than requiring a registry change. Linux packaging does not establish Windows installation success. Mocked Gemini reviews do not establish factual accuracy, free quota, billing behavior or real model access. Telegram tests did not send messages to a real account. No model-weight fine-tuning is implemented.

## 0.8.0 validation

- Local Python suite: 117 passed; 2 PHP integration tests skipped because this execution environment has no PHP runtime. Linux CI installs PHP with cURL, PDO SQLite and Sodium and runs those tests.
- Production Web build and TypeScript checks passed, including the Google connections panel.
- Google tests cover encrypted credentials, masked status, account confirmation, granted-scope rejection, expiration, refresh/retry, disconnect during refresh, fixed read-only endpoints, cross-origin rejection and explicit encrypted import.
- Earlier Chromium integration checks exercised file + text/file-only requests, model download/load, browser pack installation and English locale fallback, read-aloud toggling, logo serving, mobile layout and About documentation. Browser speech and Ollama were simulated.
- Real Google OAuth sign-in, production PHP hosting, Google service entitlements, native Windows audio and real Ollama answer quality require deployment/hardware validation; they are not established by mocked tests.
