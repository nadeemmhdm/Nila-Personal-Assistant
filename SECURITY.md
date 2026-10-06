# Security Policy

## Supported scope

Nila 0.6.x is a single-user, local-first assistant. Use the latest stable release and review changes before deploying it in a sensitive environment. Nila is not a hardened multi-tenant service.

## Data protection

Content fields are encrypted with Fernet authenticated encryption. Windows stores the encryption key using CurrentUser DPAPI. Linux uses a file restricted to the current account. Metadata such as IDs, timestamps, statuses, roles, schedules and normalized-memory fingerprints is not encrypted.

Nila can decrypt content while running. A process acting as your OS user can access Nila and potentially its data. Encryption is not a substitute for device account protection, full-disk encryption, backups or endpoint security. Do not intentionally store passwords, recovery codes or API keys in conversations.

The v0.1.0 migration encrypts existing records transactionally, uses SQLite secure deletion, checkpoints the WAL and vacuums the database. External backups, filesystem snapshots and storage-device remnants are outside that migration's control. Keep the original encryption key: no recovery backdoor exists. DPAPI keys may not be portable to another machine/account. Plaintext exports must be protected separately.

## Automatic memory

Memory learning uses only the configured local Ollama endpoint. It considers short first-person statements, filters sensitive markers, validates extracted values against verbatim evidence and limits categories and sizes. It never intentionally infers health, political, religious or other sensitive attributes. These checks are heuristic, not a guarantee; inspect and correct saved facts.

Memory suggestions require review by default and are not used until approved. Automatic memory is enabled by default and can be disabled independently. Turning off memory use also stops learning. Deleted facts are suppressed by normalized fingerprints; a differently worded fact can still be learned later. Manually configured profile information remains separate and must be cleared in Preferences if no longer wanted.

## Local API and model output

The server binds to 127.0.0.1 and checks request host, browser origin and cross-site request metadata. There is no network-user authentication. Other processes under your local account are within the trust boundary. Do not expose the port through a tunnel, LAN binding or reverse proxy.

React escapes output, Markdown raw HTML is disabled, external Markdown images are omitted, and a restrictive content policy is used. Generated links and code remain untrusted. Nila does not execute shell commands supplied by the model.

## Telegram and removed automation boundaries

The optional Telegram bridge uses a fixed HTTPS API origin, an encrypted token and one allowlisted positive private user/chat ID. Both sender and private chat IDs must match. Groups, bot senders, stale requests and non-text messages are ignored. Only one local poller owns the connection. Disabling or changing credentials cancels active generation and prevents subsequent sends; already submitted Telegram messages cannot be recalled.

Personal context sharing is off by default. Changing that setting resets the bot conversation to avoid reusing previously shared context. Telegram receives messages and generated answers; it is not an offline or end-to-end encrypted bot channel. Tokens are excluded from backups and status responses. Treat the local account as trusted.

Notes, tasks and scheduled automations are retired. Their Web routes return 410 and the worker no longer runs the scheduler. Old records remain for backup compatibility. Model output never executes shell commands or arbitrary tools.

## Temporary chats, attachments and backups

Temporary chat records and extracted attachments use an in-memory database and ephemeral key. No ordinary chat record is written to the persistent store. OS swap, process dumps and browser memory are outside this boundary. Closing a browser tab alone does not immediately destroy its server-side RAM state.

PDF extraction runs in a bounded subprocess with a timeout and page/text limits; Linux additionally applies a memory limit. No OCR or remote parsing service is used. Only extracted text is stored, encrypted. Document excerpts are untrusted context and never instructions to execute code. Keyword matching can miss relevant material.

Portable backups use Scrypt-derived Fernet encryption and require a password. Restore validates the schema and runs transactionally, pauses legacy jobs and disables updates/Telegram. Credentials and temporary chats are excluded. Backup passwords cannot be recovered. Old answers and branches may retain text later deleted from a memory or source document.

## Installer and update trust

The installer is downloaded from this repository. It uses WinGet for prerequisites and builds a standalone binary locally. Repository downloads are pinned to a commit and source files are checked against Git blob hashes. Automatic updates follow stable releases, verify the GitHub asset SHA-256 digest and smoke-test the executable under the shared installer lock before activation. HTTPS, the repository owner, package registries and installed build dependencies are trusted. This is not a publisher-signature system.

Installations are staged; the active pointer is switched only after a new binary starts successfully. Existing processes are not hot-patched. App versions and personal data have separate directories. The Windows login task runs under the signed-in user at limited privilege. Windows may request elevation when installing a prerequisite; the assistant does not run a general elevated command agent.

## Reporting a vulnerability

Do not post chat databases, encryption keys, secrets, or exploit details in a public issue. Use GitHub's private vulnerability reporting option if enabled. If it is unavailable, open a minimal issue requesting a private contact without sensitive details. Include version, OS, affected component and reproducible non-sensitive steps once a private channel is available.

## Gemini Learning Lab

Gemini integration is optional. Its API key is stored in a separate encrypted secrets table and is never returned by settings or key-status endpoints. CLI setup uses a hidden prompt. The key is sent only in the `x-goog-api-key` header to the fixed HTTPS Gemini API origin. Redirects are not followed; upstream error bodies are not echoed into the transcript.

Starting a session requires explicit acknowledgement that its topic, description, question and local model answers are sent to Google. The Learning Lab does not load personal profile, chat history or personal memory into its model prompts. It is an online feature. Google unpaid-service data terms and account-specific quotas apply; the application cannot guarantee a key has no billable usage. Do not include private information in session input.

Sessions have bounded duration and rounds, support cancellation during network requests, and stop on quota errors without automatic retries. The lab never executes model output as code. Gemini feedback is a model opinion, not proof of factual accuracy. Only acceptable reviews may produce saved lessons; lessons are editable and removable and are injected as untrusted reference text into relevant later chats. This changes retrieved context, not model weights.

Deleting a session also removes its associated learned lessons. Removing the API key requests active sessions to stop; an already submitted request cannot be recalled from Google. Application-level cancellation cannot undo charges or processing already initiated by a provider. Existing ordinary conversation transcripts may contain copies of previously used content.

Ollama cloud-tagged models selected for ordinary chat may route data through Ollama's cloud service and require that service's credentials. Use locally downloaded models for offline operation. Learning Lab rejects explicitly cloud-tagged local-model selections.

## Web evidence and local feedback

DDGS receives only a user-supplied search query or the current message when Quick/Deep is selected. The search module has no Store parameter and cannot retrieve saved chats, personal memory, profile or feedback. Off returns before importing the search provider. No Gemini call is involved in normal chat or web search. Search snippets are bounded, deduplicated, labeled untrusted and never executed. Only HTTP(S) public-looking source URLs are retained; Nila does not fetch arbitrary result pages. Search results and linked pages may still be malicious or inaccurate. Search-provider network metadata is outside local encryption.

Current feedback controls save only thumbs up/down. Legacy feedback reasons remain encrypted; ratings and associated message IDs are metadata. Local chat context uses bounded examples/guidance; votes are not authoritative corrections and do not fine-tune the model. Clearing a vote removes its guidance, and deleting a chat or truncating a branch cascades to associated feedback.

The Learning Lab local-model prompt is isolated from ordinary chat context, including retrieved feedback and web-search history. Its outbound review client accepts only a key and explicit study-session data, with no Store access. Extra session fields (including memory-inclusion flags) are rejected. Tests seed private profile, memory, notes, conversations and feedback and check both local-Lab and Gemini HTTP payloads. Content explicitly pasted into the study topic/description is still sent with the user's session consent.

Custom Markdown skills are encrypted local instructions and cannot grant execution privileges. Telegram excludes them when personal context is disabled. Cached public evidence is dated, unverified and deletable. Neither feature is passed to Gemini Learning Lab. Voice input requires on-device browser recognition; no automatic cloud fallback is used.

## Optional Google OAuth broker

Google integration is opt-in and read-only. The private PHP deployment keeps the Google Client Secret server-side. OAuth state is random and bound to a secure HttpOnly browser cookie; token pickup requires a separate claim secret and private deployment key. Short-lived pending tokens are Sodium-encrypted and removed after a single claim. The user must confirm the verified account in local Nila before reads are enabled.

Persistent tokens are encrypted with Nila's local vault in a separate table, excluded from normal settings, model context and portable workspace backups. Gmail/Drive/Docs/Sheets/Classroom/YouTube/Meet calls use fixed Google endpoints directly from the laptop with redirects disabled. No Google token, preview or document is forwarded to Gemini. Content is only imported to local documents when the user clicks **Use this preview in a local chat**.

The PHP server operator is trusted because it handles tokens during authorization and refresh. Host it under HTTPS, outside public repositories, without callback-query/body/header logging or analytics. Keep the SQLite file and environment secrets outside the public directory. Pending sessions expire after ten minutes and are purged on the next request; schedule cleanup for idle deployments. Protect the endpoint with host-level rate limits. Do not distribute the private pairing key publicly.

Disconnect removes local credentials; revoke the app in Google account settings to invalidate its Google grant. Disconnect does not delete imported documents or chats. A revoked Google grant can affect all service connections for that application. See [deployment and privacy boundaries](docs/GOOGLE_CONNECT.md).

## Prompt-driven Google reads (0.8.2)

The local chat router examines only the user's current prompt and previously recorded Google source identifiers for limited follow-ups. Provider text, memory and model output never create a tool plan. Calls are bounded and read-only; destinations remain fixed Google API endpoints. Explicit negative requests and unsupported writes block reads. Disconnected services return setup guidance without falling back to public search. Private requests skip automatic memory extraction and never call Gemini. Google credentials remain outside the model context.

Normal chat history retains the generated answer encrypted. Raw results are not automatically archived as documents. Telegram and temporary chats cannot use private Google tools. The Telegram memory-sharing setting does not authorize Google data access.
