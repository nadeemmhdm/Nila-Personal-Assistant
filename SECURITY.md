# Security Policy

## Supported scope

Nila 0.2.x is a single-user, local-first assistant. Use the latest main-branch build and review changes before deploying it in a sensitive environment. Nila is not a hardened multi-tenant service.

## Data protection

Content fields are encrypted with Fernet authenticated encryption. Windows stores the encryption key using CurrentUser DPAPI. Linux uses a file restricted to the current account. Metadata such as IDs, timestamps, statuses, roles, schedules and normalized-memory fingerprints is not encrypted.

Nila can decrypt content while running. A process acting as your OS user can access Nila and potentially its data. Encryption is not a substitute for device account protection, full-disk encryption, backups or endpoint security. Do not intentionally store passwords, recovery codes or API keys in conversations.

The v0.1.0 migration encrypts existing records transactionally, uses SQLite secure deletion, checkpoints the WAL and vacuums the database. External backups, filesystem snapshots and storage-device remnants are outside that migration's control. Keep the original encryption key: no recovery backdoor exists. DPAPI keys may not be portable to another machine/account. Plaintext exports must be protected separately.

## Automatic memory

Memory learning uses only the configured local Ollama endpoint. It considers short first-person statements, filters sensitive markers, validates extracted values against verbatim evidence and limits categories and sizes. It never intentionally infers health, political, religious or other sensitive attributes. These checks are heuristic, not a guarantee; inspect and correct saved facts.

Automatic memory is enabled by default and can be disabled independently. Turning off memory use also stops learning. Deleted facts are suppressed by normalized fingerprints; a differently worded fact can still be learned later. Manually configured profile information remains separate and must be cleared in Preferences if no longer wanted.

## Local API and model output

The server binds to 127.0.0.1 and checks request host, browser origin and cross-site request metadata. There is no network-user authentication. Other processes under your local account are within the trust boundary. Do not expose the port through a tunnel, LAN binding or reverse proxy.

React escapes output, Markdown raw HTML is disabled, external Markdown images are omitted, and a restrictive content policy is used. Generated links and code remain untrusted. Nila does not execute shell commands supplied by the model.

## Automation boundaries

The scheduler permits four defined local actions: AI writing, local notes/tasks briefs, adding notes and adding to-dos. AI-generated schedules require a user to review and save a draft. Arbitrary commands, outbound messages, credentials, and arbitrary filesystem paths are not exposed as model tools.

Jobs and outputs are encrypted. Atomic database claims prevent simultaneous workers from executing the same scheduled occurrence. A crash may still cause a repeated note/to-do write after recovery. Pause disables future runs and cancels an active generation when the worker next checks. Computer sleep/shutdown prevents execution.

## Installer and update trust

The installer is downloaded from this repository. It uses WinGet for prerequisites and builds a standalone binary locally. Repository downloads are pinned to a commit and source files are checked against Git blob hashes. Automatic updates follow `main`, not releases. HTTPS, the repository owner, package registries and installed build dependencies are trusted. This is not a publisher-signature system.

Installations are staged; the active pointer is switched only after a new binary starts successfully. Existing processes are not hot-patched. App versions and personal data have separate directories. The Windows login task runs under the signed-in user at limited privilege. Windows may request elevation when installing a prerequisite; the assistant does not run a general elevated command agent.

## Reporting a vulnerability

Do not post chat databases, encryption keys, secrets, or exploit details in a public issue. Use GitHub's private vulnerability reporting option if enabled. If it is unavailable, open a minimal issue requesting a private contact without sensitive details. Include version, OS, affected component and reproducible non-sensitive steps once a private channel is available.
