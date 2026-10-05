# Learning Lab

Learning Lab lets a local Ollama text model discuss a topic with a Gemini reviewer. It is optional and online. Ordinary local chat remains usable without a Gemini key.

## Conversation cycle

1. Gemini asks an opening question about the supplied topic and description; then the local model answers.
2. Gemini assesses that answer and returns an `acceptable`, `revise` or `uncertain` review.
3. If revision is needed, the next local turn receives the previous answer and feedback and explains the correction.
4. After an acceptable review, a short lesson may be saved and the models move to a related question.

The user sees both sides. Web transcripts refresh while local tokens arrive; Gemini opening questions and completed reviews appear as separate turns, with explicit waiting/error status. CLI output prints completed turns and preserves partial output on cancellation. These are task answers and reviews, not private model reasoning traces.

## Timing and controls

- Default: 15 minutes, at most 10 rounds.
- Allowed: 1–60 minutes and 1–40 rounds.
- One initial Gemini question request plus one review request per round, with a 12-second inter-round delay.
- Stop cancels in-flight work; the database stop flag is checked approximately every half-second.
- Time limit includes model requests and waits. Slow models may finish fewer rounds.
- Quota/authentication/network/invalid-review errors end the session rather than causing repeated billable attempts.
- Closing the browser tab alone does not stop a server-hosted session. Use Stop or stop the hosting Nila process. A crashed process leaves an interrupted transcript; it is not resumed automatically.
- Only one lab session runs at a time. It reserves local generation; ordinary chat may report busy until it finishes.

## What learning means

The feature saves encrypted study notes and retrieves up to three matching enabled notes for related future chat questions. Matching is keyword-based, not an embedding search. Turning off learned knowledge in Preferences stops that retrieval. Individual lessons can be edited, disabled or deleted.

This does not retrain Ollama model weights. Gemini review is not independent verification. The models may agree on an error, fail to revise correctly, or produce no useful lesson. Use authoritative sources for important decisions. The app labels these notes as model-reviewed references and never treats them as system commands.

## Gemini setup and privacy

Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey). Save it in Learning Lab or use `nila gemini setup`. Key input is hidden/encrypted; no key is placed in command history or returned by the status API. Model discovery lists models supporting `generateContent`; listing does not prove the account has free quota for each model.

For each session, you acknowledge sharing topic, description, questions and model answers with Google. Personal profile, ordinary chat history and personal memories are excluded. Do not include private or confidential material in the lab input. Unpaid Gemini services may use content for product improvement; review [Google's terms](https://ai.google.dev/gemini-api/terms) and [pricing](https://ai.google.dev/gemini-api/docs/pricing). Billing-enabled keys may incur charges. Nila does not change Google billing settings or bypass rate limits.

Official integration references: [Gemini API](https://ai.google.dev/api), [model discovery](https://ai.google.dev/api/models), [content generation](https://ai.google.dev/api/generate-content).

## Terminal examples

```text
nila
You › /learn
```

The wizard asks for a key if needed, a Gemini model, topic, optional description, time limit and sharing acknowledgement. For scripting:

```powershell
nila learn "Python dictionaries" --gemini-model YOUR_GEMINI_MODEL --model YOUR_OLLAMA_MODEL --minutes 15 --rounds 10 --consent
nila learn --list
nila learn --show SESSION_ID
nila learn --stop SESSION_ID
nila learn --delete SESSION_ID
nila knowledge list
nila knowledge disable LESSON_ID
nila knowledge edit LESSON_ID --text "Corrected lesson"
nila knowledge remove LESSON_ID
```

Use `--no-save` to discuss without adding reusable notes. Deleting a session removes both its transcript and its associated lessons. Local transcripts/lessons are encrypted; downloaded Markdown exports are plaintext. Removing the key stops active sessions but cannot recall data already sent to Google.
