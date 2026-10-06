<?php
declare(strict_types=1);
// OAuth-only personal deployment. Set public/ as the document root.
// Never log request bodies, Authorization, callback query strings or token responses.
ini_set('display_errors', '0');
header('Cache-Control: no-store');
header('Pragma: no-cache');
header('Referrer-Policy: no-referrer');
header("Content-Security-Policy: default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'");
header('X-Content-Type-Options: nosniff');

function output(array $value, int $status = 200): never {
    http_response_code($status); header('Content-Type: application/json');
    echo json_encode($value, JSON_THROW_ON_ERROR); exit;
}
function page(string $text, int $status = 200): never {
    http_response_code($status); header('Content-Type: text/html; charset=utf-8');
    echo '<!doctype html><html lang="en"><meta name="viewport" content="width=device-width"><title>Nila · Google connection</title><h1>Nila Google connection</h1><p>'.htmlspecialchars($text, ENT_QUOTES).'</p><p>You can close this tab and return to Nila.</p></html>'; exit;
}
function envRequired(string $name): string {
    $value = getenv($name);
    if (!$value) throw new RuntimeException('Missing configuration');
    return $value;
}
function googlePost(string $url, array $fields): array {
    $handle = curl_init($url);
    curl_setopt_array($handle, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => http_build_query($fields),
        CURLOPT_RETURNTRANSFER => true, CURLOPT_FOLLOWLOCATION => false, CURLOPT_TIMEOUT => 30,
        CURLOPT_PROTOCOLS => CURLPROTO_HTTPS, CURLOPT_HTTPHEADER => ['Content-Type: application/x-www-form-urlencoded']]);
    $body = curl_exec($handle); $status = curl_getinfo($handle, CURLINFO_RESPONSE_CODE); curl_close($handle);
    if ($body === false || $status !== 200 || strlen($body) > 65536) throw new RuntimeException('Google token exchange failed');
    $data = json_decode($body, true, 32, JSON_THROW_ON_ERROR);
    if (empty($data['access_token'])) throw new RuntimeException('Missing token');
    // No ID token needed; Nila queries Google's UserInfo endpoint directly.
    return array_intersect_key($data, array_flip(['access_token', 'refresh_token', 'scope', 'expires_in', 'token_type']));
}
function seal(array $data, string $key): string {
    $nonce = random_bytes(SODIUM_CRYPTO_SECRETBOX_NONCEBYTES);
    return base64_encode($nonce . sodium_crypto_secretbox(json_encode($data, JSON_THROW_ON_ERROR), $nonce, $key));
}
function unseal(string $data, string $key): array {
    $raw = base64_decode($data, true);
    if ($raw === false) throw new RuntimeException('Invalid envelope');
    $plain = sodium_crypto_secretbox_open(substr($raw, 24), substr($raw, 0, 24), $key);
    if ($plain === false) throw new RuntimeException('Invalid envelope');
    return json_decode($plain, true, 32, JSON_THROW_ON_ERROR);
}
try {
    $client = envRequired('GOOGLE_CLIENT_ID'); $clientSecret = envRequired('GOOGLE_CLIENT_SECRET');
    $base = envRequired('NILA_BROKER_URL'); $pairing = envRequired('NILA_PAIRING_KEY');
    $key = base64_decode(envRequired('NILA_ENCRYPTION_KEY'), true);
    $database = envRequired('NILA_DB_PATH');
    if (strlen($pairing) < 32 || $key === false || strlen($key) !== 32 || !str_starts_with($base, 'https://') || parse_url($base, PHP_URL_QUERY)) throw new RuntimeException('Invalid configuration');
    if (!is_dir(dirname($database)) || str_starts_with(realpath(dirname($database)).DIRECTORY_SEPARATOR, __DIR__.DIRECTORY_SEPARATOR)) throw new RuntimeException('Database must be outside public root');
    umask(0077);
    $db = new PDO('sqlite:'.$database, null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
    $db->exec('PRAGMA busy_timeout=5000; PRAGMA secure_delete=ON; CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, secret TEXT NOT NULL, service TEXT NOT NULL, expires INTEGER NOT NULL, status TEXT NOT NULL, payload TEXT, browser TEXT);');
    $delete = $db->prepare('DELETE FROM sessions WHERE expires < ?'); $delete->execute([time()]);
    $scopes = ['gmail'=>'gmail.readonly', 'drive'=>'drive.metadata.readonly', 'docs'=>'documents.readonly', 'sheets'=>'spreadsheets.readonly', 'classroom'=>'classroom.courses.readonly', 'youtube'=>'youtube.readonly', 'meet'=>'meetings.space.readonly'];
    $action = $_GET['action'] ?? '';
    $callback = $base.'?action=callback';
    if (in_array($action, ['authorize','callback'], true)) {
        if ($_SERVER['REQUEST_METHOD'] !== 'GET') page('Method not allowed.', 405);
        $id = $action === 'authorize' ? ($_GET['id'] ?? '') : ($_GET['state'] ?? '');
        if (!is_string($id) || !preg_match('/^[a-f0-9]{64}$/D', $id)) page('Invalid or expired connection.', 400);
        $query = $db->prepare('SELECT * FROM sessions WHERE id=?'); $query->execute([$id]); $row = $query->fetch(PDO::FETCH_ASSOC);
        if (!$row || $row['status'] !== 'pending') page('Connection expired or already completed. Start again in Nila.', 400);
        $cookieName = 'nila_oauth_'.substr($id, 0, 24);
        if ($action === 'authorize') {
            // Opening the handoff URL twice cannot silently rebind the browser.
            if ($row['browser']) page('This connection was already opened. Return to Nila to start a new connection.', 400);
            $browser = bin2hex(random_bytes(32));
            $update = $db->prepare('UPDATE sessions SET browser=? WHERE id=? AND browser IS NULL');
            $update->execute([hash('sha256', $browser), $id]);
            if ($update->rowCount() !== 1) page('Connection was already opened.', 400);
            setcookie($cookieName, $browser, ['expires'=>time()+600, 'path'=>'/', 'secure'=>true, 'httponly'=>true, 'samesite'=>'Lax']);
            $url = 'https://accounts.google.com/o/oauth2/v2/auth?'.http_build_query([
                'client_id'=>$client, 'redirect_uri'=>$callback, 'response_type'=>'code',
                'scope'=>'openid email https://www.googleapis.com/auth/'.$scopes[$row['service']],
                'access_type'=>'offline', 'prompt'=>'consent select_account', 'state'=>$id,
                'include_granted_scopes'=>'false']);
            header('Location: '.$url, true, 302); exit;
        }
        $browser = $_COOKIE[$cookieName] ?? '';
        if (!$row['browser'] || !is_string($browser) || !hash_equals($row['browser'], hash('sha256', $browser))) page('Login browser could not be verified. Start again in Nila.', 400);
        setcookie($cookieName, '', ['expires'=>1, 'path'=>'/', 'secure'=>true, 'httponly'=>true, 'samesite'=>'Lax']);
        // Claim the callback once before contacting Google.
        $update = $db->prepare("UPDATE sessions SET status='exchanging' WHERE id=? AND status='pending'"); $update->execute([$id]);
        if ($update->rowCount() !== 1) page('Connection already completed.', 400);
        if (isset($_GET['error']) || !isset($_GET['code']) || !is_string($_GET['code']) || strlen($_GET['code']) > 8192) {
            $db->prepare("UPDATE sessions SET status='denied' WHERE id=?")->execute([$id]);
            page('Permission was not granted. Nothing was connected.');
        }
        try {
            $tokens = googlePost('https://oauth2.googleapis.com/token', ['client_id'=>$client, 'client_secret'=>$clientSecret,
                'grant_type'=>'authorization_code', 'code'=>$_GET['code'], 'redirect_uri'=>$callback]);
            $db->prepare("UPDATE sessions SET status='ready', payload=? WHERE id=?")->execute([seal($tokens, $key), $id]);
        } catch (Throwable $e) {
            $db->prepare("UPDATE sessions SET status='denied' WHERE id=?")->execute([$id]);
            page('Google could not complete the connection. Check the OAuth configuration and try again.', 400);
        }
        page('Google sign-in complete. Confirm the account shown in your local Nila app.');
    }
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') page('This is the private OAuth connection endpoint for Nila. Start connections from your Nila app.');
    if (!hash_equals('Bearer '.$pairing, $_SERVER['HTTP_AUTHORIZATION'] ?? '')) output(['error'=>'unauthorized'], 401);
    if (!str_starts_with(strtolower($_SERVER['CONTENT_TYPE'] ?? ''), 'application/json')) output(['error'=>'json_required'], 415);
    $raw = file_get_contents('php://input', false, null, 0, 16385);
    if ($raw === false || strlen($raw) > 16384) output(['error'=>'request_too_large'], 413);
    $body = json_decode($raw, true, 16, JSON_THROW_ON_ERROR);
    if (!is_array($body)) output(['error'=>'invalid_request'], 400);
    if ($action === 'start') {
        $service = $body['service'] ?? ''; $secret = $body['claim_secret'] ?? '';
        if (!is_string($service) || !isset($scopes[$service]) || !is_string($secret) || !preg_match('/^[A-Za-z0-9_-]{43,128}$/D', $secret)) output(['error'=>'invalid_request'], 400);
        if ((int)$db->query('SELECT COUNT(*) FROM sessions')->fetchColumn() >= 100) output(['error'=>'busy'], 429);
        $id = bin2hex(random_bytes(32));
        $db->prepare("INSERT INTO sessions(id,secret,service,expires,status) VALUES (?,?,?,?,'pending')")->execute([$id, hash('sha256', $secret), $service, time()+600]);
        output(['id'=>$id, 'url'=>$base.'?action=authorize&id='.$id]);
    }
    if ($action === 'claim') {
        $id = $body['id'] ?? ''; $secret = $body['claim_secret'] ?? '';
        if (!is_string($id) || !is_string($secret)) output(['error'=>'invalid_request'], 400);
        $db->exec('BEGIN IMMEDIATE');
        $query = $db->prepare('SELECT * FROM sessions WHERE id=?'); $query->execute([$id]); $row = $query->fetch(PDO::FETCH_ASSOC);
        if (!$row || !hash_equals($row['secret'], hash('sha256', $secret))) { $db->exec('ROLLBACK'); output(['error'=>'expired'], 400); }
        if (in_array($row['status'], ['pending','exchanging'], true)) { $db->exec('COMMIT'); output(['status'=>'pending']); }
        $db->prepare('DELETE FROM sessions WHERE id=?')->execute([$id]); $db->exec('COMMIT');
        if ($row['status'] !== 'ready') output(['status'=>'denied']);
        output(['status'=>'ready', 'tokens'=>unseal($row['payload'], $key)]);
    }
    if ($action === 'refresh') {
        $refresh = $body['refresh_token'] ?? '';
        if (!is_string($refresh) || strlen($refresh) < 10 || strlen($refresh) > 8192) output(['error'=>'invalid_request'], 400);
        output(googlePost('https://oauth2.googleapis.com/token', ['client_id'=>$client, 'client_secret'=>$clientSecret,
            'grant_type'=>'refresh_token', 'refresh_token'=>$refresh]));
    }
    output(['error'=>'unknown_action'], 404);
} catch (Throwable $e) {
    // Do not echo exception details: credentials may appear in provider errors.
    output(['error'=>'connection_failed', 'message'=>'Check server configuration and reconnect.'], 400);
}
