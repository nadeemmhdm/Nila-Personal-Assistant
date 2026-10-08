# Local engines and optional components

Open **Workspace → Engine & downloads**, choose a profile, then **Install / use llama.cpp**. Nila downloads an official CPU runtime and the selected GGUF model, verifies SHA-256 checksums, starts a loopback-only authenticated server and selects it. Existing model files are reused. Internet is needed for installation; generation then runs locally.

Automatic llama.cpp installation supports Windows and Linux x64. CPU instruction support and Linux shared libraries must match the upstream binary. Errors are recorded in `runtime/llama-server.log` inside the Nila data directory. Other platforms can continue using Ollama. This backend is experimental until validated on your hardware.

| Profile | GGUF | Intended use |
| --- | --- | --- |
| Fast | Qwen3 0.6B Q4_0 | Low memory, short questions |
| Medium | Qwen3 1.7B Q8_0 | Balanced responses |
| Smart | Qwen3 4B Q8_0 | Larger download and memory use |
| Vision | SmolVLM 500M Q8_0 + projector | Small image model |

Choose Fast first on limited-memory laptops. The managed server uses one generation slot and 4096 context tokens. Switching back to Ollama restores its previous model name; Ollama must be running. Existing custom Ollama model support remains available. CLI and Telegram profile switches use the same active backend.

```powershell
nila engine llama.cpp --profile fast
nila engine ollama
nila engine status
nila components speech
nila components vision
nila transcribe recording.wav
```

## Responsive work and queueing

Chat and Learning Lab can remain open together. Local generation waits for the current inference operation instead of immediately returning a busy error. Gemini's tutor/review calls do not retain the local inference lease. This is serialized generation, not simultaneous model execution; queue order is not guaranteed. Navigation remains available while an answer streams, and finishing an old response does not replace the conversation you subsequently opened.

## Offline speech

**Install speech pack** creates an isolated Python environment and downloads faster-whisper's multilingual `base` model and Piper's `en_US-lessac-medium` voice. Windows can install Python 3.12 through winget when missing; Linux needs Python 3.10+ with venv support. This explicit installation can take several minutes and needs internet, disk space and RAM. The tools and models retain their own licenses, including Piper's GPL license; Nila's MIT license does not replace those licenses.

Once installed, the microphone uses browser audio capture and local Whisper transcription. Click again to finish, or wait 20 seconds. Audio is limited to 5 MB, sent only to Nila's loopback server, and its temporary file is removed afterward. Review the text before sending. English read-aloud uses local Piper; playback toggles to Stop. Malayalam read-aloud still requires an installed local OS/browser voice. Whisper's multilingual accuracy varies; a model download does not guarantee perfect transcription.

Without the pack, existing on-device browser/Windows voice support remains. Setup continues while navigating, but stops if Nila exits. Dependency failures are recorded in `runtime/speech-install.log`.

## Images and files

**Install / use vision model** selects Moondream on Ollama or SmolVLM with its projector on llama.cpp. Telegram's existing photo analysis uses the selected vision-capable model. PDF/TXT/Markdown text extraction needs no additional AI model; scanned PDFs still need OCR. This change does not add OCR or unlimited document/image support.

## Validation boundaries

Automated tests cover queue cancellation, adapter requests/streaming, checksum reuse/failure, restoring Ollama selection, and temporary audio cleanup. Live runtime and speech-pack downloads depend on external hosts and target hardware. They were not fully exercised in the development environment; use the status and log messages to diagnose device-specific failures.
