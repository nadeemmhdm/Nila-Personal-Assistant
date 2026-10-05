# Changelog

## 0.7.0 — Shared Models

- Central Fast/Medium/Smart model profiles across Web, CLI and Telegram, configurable mappings and safe legacy selection migration.
- Icon-only composer controls and the supplied lotus logo.
- One thinking indicator per request, removed on streaming; Telegram edits the same message.
- Strict Nila identity matching and isolated public research context fix third-party founder confusion.
- Unified memory counts, Learning Lab status and one-time recovery of older saved web references.


## 0.6.0 — Personal Workspace

See [complete release notes](docs/releases/v0.6.0.md). Stable-release prebuilt updates, Telegram controls, skills, voice, local knowledge cache, persistent attachments, model loading and interface fixes.

### Earlier fixes included

- Handle standalone greetings locally without model/search calls or unrelated profile/history retrieval; retain normal model generation for questions and follow-ups.
- Shorten chat instructions, include developer attribution only when requested, and clarify that user projects are not the assistant's experiences.
- Widen the CLI welcome panel to display its subtitle fully.

- Report installer-lock contention as busy, add `nila version` as an alias for `--version`, and catch the `updatw` typo before it can start chat or automatic updating.

- Report Windows executable policy denials as NILA-021, include the update log path and preserve mandatory binary validation. Document that the device trust policy must accept the build before activation.

- Fix Windows CLI smoke-test decoding: explicitly use UTF-8 for subprocess input/output so the Unicode Nila banner is not decoded as CP1252.

## 0.5.0 — 2026-10-05

- Redesigned chat composer, opposite-side bubbles, themes, collapsible Explore/History sidebar and inline notices.
- Added contextual local follow-up questions, same-answer regeneration with optional instructions, branch preservation and thumbs-only feedback.
- Added Rich CLI rendering/banner/status, thinking effort levels and installed model selection.
- Automatic question-based Quick/Deep search with clickable sources; fixed composer refilling after answers.
- Added projects, text/PDF attachments, source-context inspection, reviewed memory inbox and RAM-only temporary chats.
- Added password-encrypted portable backup/restore, setup checks, compact view and managed Windows rollback.
- Added encrypted, private-ID-restricted Telegram connection with opt-in personal context.
- Learning Lab now starts with a Gemini question, then local answer and Gemini correction; isolated personal-data boundary retained.
- Removed Notes, Tasks, written-feedback controls and scheduled automations from active use. Existing legacy data is retained.
- Preserved short Windows build paths and main-commit updates.


## 0.4.0 — 2026-10-05

- Fixed Windows dependency installation paths by flattening extracted source and using a short sibling virtual environment; added a Windows hook-install regression check.
- Added opt-in DDGS Quick/Deep search, bounded sources, separate public query, Off default and explicit no-evidence errors.
- Added local thumbs feedback with encrypted guidance and contextual reuse; no model weight training.
- Added prompt edit/regenerate with dependent-branch replacement, continue response, CLI shortcuts, and prompt/reply copy.
- Added safe underline rendering and refined streaming/motion controls.
- Strengthened Gemini session isolation and privacy regression coverage.

## 0.3.0 — 2026-10-04

- Added optional Gemini Learning Lab with visible model discussions, review/revision cycles, duration and round limits, Stop, encrypted transcripts and relevant saved knowledge.
- Added encrypted Gemini key setup, model discovery, quota handling and explicit cloud-sharing acknowledgement.
- Kept llama3.2:1b as a recommendation; users can choose other compatible Ollama chat models.
- Added position-based Student/Employee profiles and removed the college question.
- Simplified terminal chat with plain-text one-shot input, /help, /model and a guided /learn flow.
- Added MIT license and Learning Lab security/documentation.

## 0.2.0 — 2026-10-04

- Added single-command Windows setup with prerequisite detection/WinGet installation, model detection, standalone `nila.exe` build and a PATH launcher.
- Added staged updates based on GitHub main-branch commits, independent of releases.
- Encrypted profile, chat, memory, notes, tasks and automation content; added legacy migration and Windows DPAPI key protection.
- Added personal profile fields, friendly tone controls and local evidence-checked automatic memory.
- Added offline scheduler, local AI jobs, notes/tasks briefs, scheduled notes/to-dos, natural-language drafts, run history and a Windows login worker.
- Added System and Automations Web pages and corresponding CLI controls.
- Updated setup, contribution, security and troubleshooting documentation.

## 0.1.0 — 2026-10-04

- Initial Ollama-powered Web UI and CLI, shared history, explicit memory, notes/tasks, streaming and binary build workflow.
