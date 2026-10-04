# Validation — v0.3.0

Validated in the Linux development environment on 2026-10-04.

| Check | Result |
| --- | --- |
| Python regression suite | 30 passed |
| TypeScript and Vite production build | Passed |
| Student/Employee conditional profile fields | Passed in Chromium; no college question |
| Gemini key save/status | Passed using a fake key; encrypted at rest and excluded from settings |
| Learning Lab model selection and transcript | Passed with simulated local/Gemini providers |
| Reviewed lesson save and disable | Passed in Chromium |
| Stop during a pending local answer | Passed in Chromium and unit tests |
| Time limit during a pending request | Passed in unit tests |
| Gemini quota error | One request, no retry, no key leaked, no lesson saved |
| Correction forwarded to the next local answer | Passed with simulated providers |
| Personal profile/memory excluded from Gemini payload | Passed |
| Relevant learned knowledge retrieval and off switch | Passed |
| Interactive CLI and plain-text one-shot input | Passed |
| Mobile Learning Lab at 390 × 844 | Passed; no horizontal overflow |
| Browser runtime errors in exercised v0.3.0 flows | None |
| Linux standalone binary build | Passed |
| Packaged Web assets, Learning API and role profile | Passed |
| Live Gemini key/model compatibility and free quota | Not tested; no real API key was used |
| Real Ollama model quality, speed or fine-tuning | Not tested; this feature does not fine-tune weights |
| Windows installer, login task and DPAPI end-to-end | Requires Windows validation; CI includes Windows tests/build and script parsing |

Simulated provider tests exercise lifecycle, transcript, feedback, knowledge and failure handling; they do not establish Gemini factual accuracy, real account quota, cost, or live model availability. Model discovery uses the official models endpoint, but a listed model may still have account-specific restrictions.

Previous regression coverage retains encrypted migration, memory controls, scheduler claims/cancellation, offline automation, origin checks, streaming, updater integrity checks and CLI/Web storage sharing. v0.2.0 browser and binary tests verified real local deterministic note scheduling.
