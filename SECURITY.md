# Security

Nila 0.1.0 is intended for one user on their own computer. It binds to 127.0.0.1, checks request hosts and browser origins, and rejects non-local Ollama URLs. Browser output uses React escaping and Markdown without raw HTML; external Markdown images are omitted. No shell execution is exposed to the model.

The database is unencrypted. Any process running as your account may read it and may access the unauthenticated loopback server. Local origin checks reduce drive-by website access; they are not authentication. Do not expose Nila to LAN or internet clients. Stop the server when not in use.

Model output is untrusted. Check code before running it, and verify important information. Notes, tasks, and memory edits are explicit UI/CLI operations, not actions performed autonomously by the model. Never store credentials in chat memory.

Dependencies should be reviewed and updated before public distribution. The included workflow has read-only repository permissions. Do not include local databases or environment files in issues or repository commits.
