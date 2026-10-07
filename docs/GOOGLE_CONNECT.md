# Google connections

The Nila repository contains the **local Google client only**. The PHP OAuth website is delivered separately as **Nila-PHP-OAuth-Website-v0.8.1.zip**. Do not commit that website package, its configuration, or its keys to this repository. The ZIP includes PHP source, English/Malayalam setup instructions and broker tests.

## Enter your website domain in Nila

Deploy the separate ZIP to your own HTTPS PHP hosting first, following `START_HERE_MALAYALAM.md` inside it. Configure your Google Cloud Web application and the private pairing key on that host.

In Nila **Workspace → Google → OAuth website setup**:

1. Enter `connect.yourdomain.com` (your own domain).
2. Enter the private deployment pairing key from your PHP configuration.
3. Click **Save & connect website**. Nila adds `https://` and `/index.php`, saves the endpoint encrypted and checks the server.
4. Copy the displayed callback URL into Google Cloud's authorized redirect URIs. It must match the PHP website configuration exactly.
5. Choose a service → **Connect with Google** → open sign-in → grant access → confirm the account shown locally.

A folder URL such as `connect.yourdomain.com/oauth` becomes `https://connect.yourdomain.com/oauth/index.php`. An explicit HTTPS `.php` endpoint is also accepted. Do not put credentials or query parameters in the domain field. The PHP website uses its explicitly configured domain, not an arbitrary incoming Host header.

Saving a different endpoint clears previous local Google connections so credentials are not silently reused with a different host. Supplying a domain does not bypass Google consent or deployment setup. Nila remembers the endpoint and refreshes valid tokens automatically after initial authorization.

## CLI

```powershell
nila google setup --domain connect.yourdomain.com
nila google check
nila google connect gmail
nila google read gmail
nila google read gmail --item MESSAGE_ID
nila google connect docs
nila google read docs --item DOCUMENT_ID
nila google connect sheets
nila google read sheets --item SPREADSHEET_ID --range 'Sheet1!A1:D25'
nila google status
nila google disconnect gmail
```

The setup command prompts for the pairing key without showing it. Do not pass keys in a command-line URL. `nila google setup` also works interactively without `--domain`.

## Supported read-only access

| Service | Available reads |
| --- | --- |
| Gmail | Inbox pages; a message by ID; plain-text body |
| Drive | File names and metadata |
| Docs | Document text by ID, including tabs |
| Sheets | Spreadsheet cells by ID and A1 range |
| Classroom | Courses and course details |
| YouTube | Your channel, channel details and playlists |
| Meet | Conference history and record details |

Use a returned `nextPageToken` with CLI `--page-token` for further list pages. These permissions do not send email, edit documents, retrieve every Classroom resource or join/control live Meet calls.

## Local data and privacy

- Each service requires its own consent; one account per service is supported.
- Tokens are encrypted locally and excluded from model context, Gemini and portable workspace backups.
- The PHP operator is trusted: the server handles OAuth tokens during authorization and refresh. Use your own trusted host.
- Service data is fetched directly from the laptop to fixed Google endpoints. The PHP website receives no chat history, memory or imported documents.
- **Use this preview in a local chat** explicitly saves selected content as an encrypted attached document. Reading alone does not save it to memory.
- Local disconnect removes credentials; revoke the app at [Google account connections](https://myaccount.google.com/connections) to invalidate Google's grant. Revocation may affect all services for the app. Delete imported documents/chats separately if required.
- Internet is needed for live Google calls. Imported documents can be used offline with an installed Ollama model.

## Troubleshooting

| Issue | Resolution |
| --- | --- |
| Website domain mismatch | Match PHP `NILA_BROKER_URL`, the saved Nila endpoint and Google's callback URI |
| Website is not compatible | Upload the latest separate ZIP, including its authenticated health endpoint |
| Broker rejected request | Check pairing key, PHP extensions/configuration and Authorization header forwarding |
| `redirect_uri_mismatch` | Register the exact callback URL in a Google Cloud **Web application** client |
| Access denied / app blocked | Check test users, consent scopes, app verification and Workspace admin policies |
| Expired login | Start a fresh connection and complete it within ten minutes |
| Token expires after about seven days | Google Testing-mode refresh tokens can expire; reconnect or configure eligible production use |

The ZIP's setup guides include hosting layout, Google API enablement, key generation and callback registration. Never enter the Google Client Secret in Nila chat or the domain field.

Official references: [Google web-server OAuth](https://developers.google.com/identity/protocols/oauth2/web-server), [Gmail scopes](https://developers.google.com/workspace/gmail/api/auth/scopes), [Meet authorization](https://developers.google.com/workspace/meet/api/guides/authenticate-authorize).

## Ask in normal chat (0.8.2+)

After connecting, use ordinary Web or CLI chat:

- `Show my YouTube channel details`
- `ente youtube channel details kanikku`
- `എന്റെ യൂട്യൂബ് വിവരങ്ങൾ കാണിക്കൂ`
- `Show my Google Meet history`
- `Summarize my Gmail inbox`
- `List my Google Drive files`
- `List my Google Classroom courses`
- `Summarize https://docs.google.com/document/d/YOUR_DOCUMENT_ID/edit`
- `Read https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit A1:C10`
- `Summarize https://youtu.be/VIDEO_ID` — metadata/description only, not video audio/transcript.

Nila checks explicit service names, read intent and supported links in the current user prompt. It makes bounded calls only to connected services. Ordinary questions such as “What is YouTube?” do not access your account. Unsupported/ambiguous operations request clarification. For a linkless item, `id: ITEM_ID` is supported. Use at most two services in one request.

The model summarizes retrieved data locally. Reading a result does not create a saved document or permanent memory; the resulting conversation is encrypted in normal chat history. Google references identify the service/linked item. “Summarize it” can re-read the last single Google reference; it requires a valid connection and internet. Use the existing explicit preview-import feature to keep a document for offline use.

Google data and tokens never enter Gemini. Public web retrieval and automatic personal-memory extraction are disabled for these requests, even when Quick/Deep search is selected. Retrieved text cannot authorize another tool call. Private Google tools are disabled in Telegram and temporary chats; use normal local Web/CLI chats. A missing connection does not trigger public search for your private request.

Only a bounded first page is read (Gmail: up to five message previews); Nila must not claim this is your entire account history. Meet reads conference history/metadata, not upcoming calendar events or live calls. Drive reads metadata only. Classroom reads courses only. These limitations follow the current API scopes.


## Bundles, mentions and writes (0.8.3)

Connect all · read only or Connect all · read & write grants the seven services in one Google consent flow. Confirm your account locally. Individual connections remain available. Type @ to choose a connected account; normal explicit read prompts also work. Writes need read/write scopes and Allow explicit chat writes. This toggle remains enabled until you disable it. See [release examples](releases/v0.8.3.md). Missing recipients, IDs or content never execute. Arbitrary edits, video audio analysis, live call joining and Classroom coursework remain unsupported.

InfinityFree free hosting blocks inbound API calls, including broker health/start/claim/refresh requests. Use an API-capable PHP host. The separate ZIP includes root index.php and private configuration instructions; no host-protection bypass is included. Google/Workspace can restrict scopes and APIs even after consent.


## Recent inbox reads (0.8.5)

`@Gmail read emails from the last 10 minutes`, `@Gmail last 2 hours` and `@Gmail unread emails` apply Gmail filters before fetching up to five previews. Windows must be greater than zero and no more than 31 days. Reads are limited to inbox messages; previews are not a complete mailbox scan. The service must already be connected. Gmail API filtering uses epoch seconds for precise time windows: https://developers.google.com/workspace/gmail/api/guides/filtering

If the broker returns a browser-only HTML page, Nila now explains that the host is not providing the required API. InfinityFree's free-host limitation is documented at https://forum.infinityfree.com/t/why-isnt-api-access-working-on-my-website/115198/1 .
