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

Google Chromium flow also passed: configure broker, connect, local account confirmation, preview, mobile overflow and actual encrypted document import. Google responses were simulated. Linux CI executes the PHP handoff tests against a real PHP process.

Linux CI passed 119 tests, including both PHP router integration tests, and built/smoke-tested the standalone binary. PHP server tests are Linux-only; Windows validates the Nila client and updater rather than requiring PHP hosting extensions.

## 0.8.1 validation

- Local Nila suite: 133 passed, including domain normalization, unsafe URL rejection and callback mismatch checks.
- TypeScript/production Web build passed. Chromium exercised domain setup, connection confirmation, preview, mobile layout and actual encrypted local document import using simulated Google responses.
- The separate PHP ZIP passed syntax checks and 6 real PHP router tests under PHP 8.3, covering both environment and private-file configuration. Its PHP source/tests are no longer in the repository.
- The previous Pages failure was a 404 from configure-pages because the repository had no Pages site. The updated workflow builds an artifact and clearly reports that deployment needs setup when Pages is disabled. Public deployment requires repository administration; a successful build with skipped deployment does not mean the site is online.

## 0.8.2 validation

Local suite: 155 passed. New tests cover English/Manglish/Malayalam routing, ordinary-question exclusion, missing IDs, read-only limits, negative requests, direct Google data in local model context, token exclusion, disabled public search/memory extraction, same-chat source follow-up, blocked channels and YouTube metadata endpoints. Production Web build passed. Google provider responses are mocked; live OAuth account reads still require credentials and user deployment.
