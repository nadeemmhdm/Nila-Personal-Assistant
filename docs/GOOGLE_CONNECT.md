# Google connections · PHP OAuth broker

Nila runs on your laptop. A small PHP website handles Google OAuth sign-in and token refresh. Gmail, Drive, Docs, Sheets, Classroom, YouTube and Meet requests go **directly from Nila to Google**. The website is not a chat server and does not receive conversations, memories, documents or model answers.

This is an opt-in, read-only integration for a private deployment. It requires an HTTPS PHP host and your own Google Cloud OAuth app. It does not include hosting, a shared Nila Google client, public multi-tenant user registration or a deployed service.

## What you can do

| Service | Implemented reads | Requested API scope |
| --- | --- | --- |
| Gmail | First/next inbox pages; open a message by ID; decode plain-text message body | `gmail.readonly` |
| Drive | First/next pages of file metadata; inspect a file ID | `drive.metadata.readonly` |
| Docs | Read document text by ID, including tabs | `documents.readonly` |
| Sheets | Read a spreadsheet ID and A1 range, default `A1:Z100` | `spreadsheets.readonly` |
| Classroom | List courses and open a course ID | `classroom.courses.readonly` |
| YouTube | Your channel, channel ID, or your playlists | `youtube.readonly` |
| Meet | List conference records and inspect a record ID | `meetings.space.readonly` |

Scope names above have the prefix `https://www.googleapis.com/auth/`. Each connection also requests `openid email` so you can confirm the verified account in Nila. Connecting one service does not enable all seven. One account per service is supported; reconnect to replace it.

This version does not send email, edit files, create meetings, join calls, control a live meeting, watch videos, retrieve all Classroom assignments or perform arbitrary Google actions. API access also depends on the account's permissions, Workspace edition/admin policies and Google's quotas.

## Why a public website, when Nila is local?

Google redirects sign-in to the registered HTTPS PHP callback. Nila polls that website using a private, short-lived claim secret, then asks you to confirm the account locally. Your laptop does not need a public address or an open inbound port. Do not expose Nila's localhost Web UI to the internet.

A separate Google **Desktop app** OAuth client can use a loopback callback without a PHP website. This implementation follows the requested **Web application + PHP broker** design; those client types and redirect settings are not interchangeable.

## 1. Create the Google Cloud app

1. Create/select a project in Google Cloud Console. Enable only the APIs you will connect: Gmail, Google Drive, Google Docs, Google Sheets, Google Classroom, YouTube Data API v3 and Google Meet API.
2. Configure Google Auth Platform branding, audience and data access. For private development, keep the app in Testing and add your Google account as a test user. Add only the scopes you intend to use.
3. Create an OAuth client of type **Web application**. Keep the Client Secret on the PHP server.
4. Register this **exact authorized redirect URI**, replacing the domain:

   ```text
   https://connect.example.com/index.php?action=callback
   ```

   No browser JavaScript client secret, wildcard callback, Nila localhost URL or token in a redirect URL is needed.
5. If distributing outside your test users, complete Google's applicable OAuth verification requirements. Gmail read access is a restricted scope; requirements may include a security assessment depending on deployment and use. Testing apps with these permissions normally receive refresh tokens that expire after seven days. Google policy, admin settings or revocation can require reconnection sooner.

Official references: [web-server OAuth](https://developers.google.com/identity/protocols/oauth2/web-server), [OAuth scopes](https://developers.google.com/identity/protocols/oauth2/scopes), [Gmail scope classification](https://developers.google.com/workspace/gmail/api/auth/scopes), [Meet authorization](https://developers.google.com/workspace/meet/api/guides/authenticate-authorize), [desktop loopback flow](https://developers.google.com/identity/protocols/oauth2/resources/loopback-migration).

## 2. Deploy the PHP endpoint

Requirements: PHP **8.2+**, cURL, PDO SQLite and Sodium extensions; HTTPS with a valid certificate; outbound HTTPS access to `accounts.google.com` and `oauth2.googleapis.com`. No Composer packages are required.

1. Upload `oauth-broker/public/index.php` to your PHP host. Set `oauth-broker/public/` as the document root. Do not publish the repository root.
2. Create a private writable directory outside the document root, e.g. `/var/lib/nila-oauth`, owned by the PHP worker and mode `0700` on Linux.
3. Generate two independent keys on the server:

   ```bash
   php -r 'echo bin2hex(random_bytes(32)), PHP_EOL;'
   php -r 'echo base64_encode(random_bytes(32)), PHP_EOL;'
   ```

   First output is `NILA_PAIRING_KEY`; second is `NILA_ENCRYPTION_KEY`. Keep both private. The pairing key is for your own Nila installations, not a public client credential or a replacement for Google consent.
4. Set server environment variables using `oauth-broker/env.example` as the reference:

   ```text
   GOOGLE_CLIENT_ID=<your web application client ID>
   GOOGLE_CLIENT_SECRET=<your Google client secret>
   NILA_BROKER_URL=https://connect.example.com/index.php
   NILA_PAIRING_KEY=<first generated value>
   NILA_ENCRYPTION_KEY=<second generated value>
   NILA_DB_PATH=/var/lib/nila-oauth/sessions.sqlite
   ```

   The application reads actual environment variables; it does not automatically load `.env` files. For PHP-FPM, configure `env[NAME] = value` in a private pool configuration or use your hosting control panel. Ensure the PHP worker receives the variables. Restart PHP after changes.
5. Ensure the web server forwards the `Authorization` header to PHP. For Nginx/FastCGI use `fastcgi_param HTTP_AUTHORIZATION $http_authorization;`. On Apache, enable the equivalent Authorization forwarding supported by your hosting setup.
6. Redirect HTTP to HTTPS at the host. Disable access logging of OAuth callback **query strings** (use `$uri` instead of `$request_uri` in a dedicated Nginx access-log format, or disable this endpoint's access log). Do not enable body/header tracing, debug error display, analytics or third-party scripts on the endpoint. Apply per-IP rate limiting at the reverse proxy.
7. Check syntax with `php -l oauth-broker/public/index.php`. Opening the configured HTTPS endpoint should display “Nila Google connection”. A configuration error returns a generic JSON error; check environment variables and extensions without logging credentials.

GitHub Pages cannot execute PHP. The Nila landing site can remain on GitHub Pages; host this endpoint on PHP-capable hosting under a separate HTTPS domain/subdomain.

## 3. Connect from Nila

1. Open **Workspace → Google → OAuth website setup**.
2. Enter your trusted HTTPS endpoint and private deployment pairing key. These are stored in Nila's encrypted local database. Do not enter your Google Client Secret here.
3. Choose a service, click **Connect with Google**, then **Open Google sign-in**.
4. Grant the requested permissions. Return to Nila and confirm the displayed account address. The connection is not enabled until you confirm it.
5. Click **Read from Google**. Docs and Sheets need an item ID; copy the portion between `/d/` and the next slash in the Google document URL. Sheets also accepts an A1 range such as `Sheet1!A1:D25`.
6. To ask the local model about a preview, click **Use this preview in a local chat**. Nila saves that preview as an encrypted document and opens a chat with it attached. It does not automatically crawl your Google account or import everything.

CLI uses the same encrypted connections:

```bash
nila google setup
nila google connect gmail
nila google read gmail
nila google read gmail --item MESSAGE_ID
nila google connect docs
nila google read docs --item DOCUMENT_ID
nila google connect sheets
nila google read sheets --item SPREADSHEET_ID --range 'Sheet1!A1:D25'
nila google read youtube --item playlists
nila google status
nila google disconnect gmail
```

Use `--page-token` with a returned `nextPageToken` to read subsequent list pages. CLI prints results; save/import selected text through the existing document commands if you want to use it in a local chat. Google reads are not automatically available through Telegram or Learning Lab.

## Token and content boundaries

- The PHP operator is trusted: the broker processes authorization codes and tokens. Use your own host or one whose operator you trust.
- The broker validates random OAuth state and a secure HttpOnly SameSite browser cookie. A separate local claim secret and private deployment key protect token pickup. Nila then verifies the account directly with Google and requires local confirmation.
- Pending tokens are encrypted with Sodium, delivered once, and removed on claim. Unclaimed sessions expire after ten minutes and are purged on the next broker request. To physically remove expired rows on an idle host, schedule an hourly SQLite `DELETE FROM sessions WHERE expires < unixepoch()` with appropriate private-file permissions.
- Persistent access/refresh tokens live encrypted on the laptop. Refresh passes the refresh token through the PHP broker because the Web application's Client Secret stays there. The broker does not persist refresh-request bodies or refreshed tokens.
- Tokens and Google account content are not included in model system prompts, Gemini requests, public searches or automatic memory capture. Explicitly imported documents follow Nila's existing local-document context rules. A model may reference document content in its local answer.
- Google connection credentials are excluded from Nila workspace exports/backups; reconnect after restoring elsewhere. Imported documents/chats follow the normal encrypted backup policy.
- **Disconnect locally** removes local credentials/pending handoffs. It does not revoke Google's grant or delete previously imported documents/chats. Revoke the app at [Google account connections](https://myaccount.google.com/connections); Google may revoke all service permissions for the app together.
- Internet is required for OAuth and live Google reads. Previously imported documents can be discussed offline with an installed Ollama model. OAuth “offline access” means renewable authorization, not offline access to Google's servers.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `redirect_uri_mismatch` | Web client type and exact `?action=callback` redirect, including path/scheme/domain |
| App blocked or access denied | Test user, granted scope, app verification and Workspace admin policy |
| OAuth broker rejected request | Pairing key matches the server; Authorization header reaches PHP; server environment is available |
| Sign-in expires | Reconnect within ten minutes and use the same browser for login and callback |
| Browser could not be verified | Allow the broker's first-party secure cookie; start a fresh connection |
| Google cannot read item | Correct ID/account, enabled service API, file permissions and quota |
| Reconnect after about seven days | Google Testing-mode refresh-token expiry; configure verified production use when eligible |
| Empty Meet/Classroom/YouTube lists | The connected account may have no accessible records/channel/courses or lack the required service entitlement |

## Verification status

Automated tests use simulated Google responses. PHP tests check authentication, scoped authorization redirects, cookie/state enforcement, denial, one-time handoff and replay. No real Gmail account, Google OAuth client, production PHP domain or Workspace organization was supplied for live integration testing.
