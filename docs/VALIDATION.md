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
