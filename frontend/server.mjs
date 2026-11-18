import http from 'node:http';
import fs from 'node:fs/promises';
import {existsSync, watch} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawn, execFile} from 'node:child_process';

const directory = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(directory, '..');
const environmentPython = path.join(root, 'backend', '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const python = process.env.PYTHON_BIN || (existsSync(environmentPython) ? environmentPython : process.platform === 'win32' ? 'py' : 'python3');
const pythonArgs = python === 'py' ? ['-3'] : [];
const port = Number(process.env.PORT || 3201);
let child, backendPort, closing = false, restarting = false, reloadTimer;
const watchers = [];

function startBackend() {
  backendPort = undefined;
  return new Promise((resolve, reject) => {
    let output = '', settled = false;
    const launched = spawn(python, [...pythonArgs, '-X', 'utf8', path.join(root, 'backend/run.py'), '--port', '0'], {cwd: path.join(root, 'backend'), windowsHide: true, stdio: ['ignore', 'pipe', 'pipe']});
    child = launched;
    const timer = setTimeout(() => finish(new Error('Backend startup timed out. Check the Python environment and backend/requirements.txt.')), 60000);
    function finish(error) { if (!settled) { settled = true; clearTimeout(timer); error ? reject(error) : resolve(); } }
    launched.stdout.on('data', chunk => {
      output += chunk;
      const match = output.match(/BACKEND_PORT=(\d+)/);
      if (match && !backendPort) { backendPort = Number(match[1]); waitForHealth(); }
    });
    function waitForHealth() {
      if (settled) return;
      const probe = http.get({hostname: '127.0.0.1', port: backendPort, path: '/api/health', timeout: 1000}, response => {
        response.resume();
        if (response.statusCode === 200) finish(); else setTimeout(waitForHealth, 200);
      });
      probe.on('error', () => { if (!settled) setTimeout(waitForHealth, 200); });
      probe.on('timeout', () => probe.destroy());
    }
    launched.stderr.on('data', chunk => process.stderr.write(chunk));
    launched.on('error', finish);
    launched.on('exit', code => {
      if (!settled) finish(new Error('Python backend failed to start. Install backend/requirements.txt in backend/.venv.'));
      if (child === launched && !closing && !restarting) { backendPort = undefined; console.error('Backend stopped:', code, 'Restart the app or save a backend file to retry.'); }
    });
  });
}

function stopBackend() {
  backendPort = undefined;
  const owned = child;
  if (!owned || owned.exitCode !== null) return Promise.resolve();
  return new Promise(resolve => {
    if (process.platform === 'win32') execFile('taskkill', ['/PID', String(owned.pid), '/T', '/F'], {windowsHide: true}, () => resolve());
    else { owned.once('exit', resolve); owned.kill('SIGTERM'); setTimeout(resolve, 1500).unref(); }
  });
}

async function reloadBackend() {
  if (closing) return;
  if (restarting) { reloadTimer = setTimeout(reloadBackend, 400); return; }
  restarting = true;
  console.log('Python source changed. Reloading backend…');
  try { await stopBackend(); await startBackend(); console.log('Backend reloaded.'); }
  catch (error) { console.error(error.message); await stopBackend(); }
  finally { restarting = false; }
}

function startWatcher() {
  try {
    watchers.push(watch(path.join(root, 'backend/app'), {recursive: true}, (event, name) => {
      if (!name || !String(name).endsWith('.py')) return;
      clearTimeout(reloadTimer); reloadTimer = setTimeout(reloadBackend, 300);
    }));
  } catch { console.log('Automatic reload unavailable. Restart after Python edits.'); }
}

const assets = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/styles.css', ['styles.css', 'text/css; charset=utf-8']],
  ['/comparison.css', ['comparison.css', 'text/css; charset=utf-8']],
  ['/themes.css', ['themes.css', 'text/css; charset=utf-8']],
  ['/src/app.js', ['src/app.js', 'text/javascript; charset=utf-8']],
  ['/src/services/api.js', ['src/services/api.js', 'text/javascript; charset=utf-8']],
  ['/src/services/theme.js', ['src/services/theme.js', 'text/javascript; charset=utf-8']],
  ['/src/components/sources.js', ['src/components/sources.js', 'text/javascript; charset=utf-8']],
  ['/src/components/comparison.js', ['src/components/comparison.js', 'text/javascript; charset=utf-8']],
]);
function sendError(response, status, message) {
  if (!response.headersSent) response.writeHead(status, {'Content-Type': 'application/json', 'Cache-Control': 'no-store'});
  response.end(JSON.stringify({error: {message}}));
}
const server = http.createServer(async (request, response) => {
  const url = new URL(request.url, 'http://localhost');
  response.setHeader('X-Content-Type-Options', 'nosniff');
  const mcpRequest = url.pathname === '/mcp' || url.pathname === '/mcp/';
  if (url.pathname.startsWith('/api/') || mcpRequest || url.pathname === '/openapi.json') {
    if (!(mcpRequest ? ['GET', 'POST', 'DELETE'] : ['GET', 'POST']).includes(request.method)) { sendError(response, 405, 'Method not allowed.'); return; }
    if (request.headers.origin && ![`http://127.0.0.1:${server.address().port}`, `http://localhost:${server.address().port}`].includes(request.headers.origin)) { sendError(response, 403, 'Use the local app window to send requests.'); return; }
    if (!backendPort || restarting) { sendError(response, 503, 'The backend is restarting. Wait a moment, then retry.'); return; }
    if (url.pathname === '/api/documents/upload') {
      const upload = http.request({hostname: '127.0.0.1', port: backendPort, path: url.pathname, method: request.method, headers: {'Content-Type': request.headers['content-type'] || 'application/octet-stream', ...(request.headers['content-length'] ? {'Content-Length': request.headers['content-length']} : {})}}, incoming => {
        response.writeHead(incoming.statusCode, {'Content-Type': incoming.headers['content-type'] || 'application/json', 'Cache-Control': 'no-store'}); incoming.pipe(response);
      });
      let uploaded = 0;
      request.on('data', chunk => { uploaded += chunk.length; if (uploaded > 26 * 1024 * 1024) { request.unpipe(upload); upload.destroy(); if (!response.writableEnded) sendError(response, 413, 'Use a file smaller than 25 MB.'); } });
      upload.on('error', () => { if (!response.writableEnded) sendError(response, 502, 'The upload could not reach the backend. Retry once it is ready.'); });
      request.on('aborted', () => upload.destroy()); upload.setTimeout(120000, () => upload.destroy());
      request.pipe(upload); return;
    }
    const chunks = []; let length = 0;
    try {
      for await (const chunk of request) { length += chunk.length; if (length > 16384) { sendError(response, 413, 'Request too large.'); return; } chunks.push(chunk); }
      const upstreamHeaders = {'Content-Type': request.headers['content-type'] || 'application/json', 'Content-Length': length};
      for (const name of ['accept', 'mcp-protocol-version', 'mcp-session-id', 'last-event-id']) if (request.headers[name]) upstreamHeaders[name] = request.headers[name];
      const proxy = http.request({hostname: '127.0.0.1', port: backendPort, path: (mcpRequest ? '/mcp' : url.pathname) + url.search, method: request.method, headers: upstreamHeaders}, incoming => {
        const headers = {'Content-Type': incoming.headers['content-type'] || 'application/json', 'Cache-Control': 'no-store'};
        if (incoming.headers['content-disposition']) headers['Content-Disposition'] = incoming.headers['content-disposition'];
        for (const name of ['mcp-session-id', 'mcp-protocol-version']) if (incoming.headers[name]) headers[name] = incoming.headers[name];
        response.writeHead(incoming.statusCode, headers); incoming.pipe(response);
      });
      proxy.setTimeout(110000, () => proxy.destroy(new Error('API timeout')));
      proxy.on('error', () => sendError(response, 502, 'The backend is unavailable. Check the project terminal.'));
      proxy.end(Buffer.concat(chunks));
    } catch { if (!response.writableEnded) sendError(response, 400, 'Could not read the request.'); }
    return;
  }
  const asset = assets.get(url.pathname);
  if (!asset || request.method !== 'GET') { response.writeHead(404); response.end('Not found'); return; }
  try { const body = await fs.readFile(path.join(directory, asset[0])); response.writeHead(200, {'Content-Type': asset[1], 'Cache-Control': 'no-store'}); response.end(body); }
  catch { response.writeHead(404); response.end('Not found'); }
});

async function shutdown(code = 0) {
  if (closing) return;
  closing = true; clearTimeout(reloadTimer); watchers.forEach(watcher => watcher.close());
  await stopBackend(); server.close(() => process.exit(code)); setTimeout(() => process.exit(code), 1500).unref();
}
process.on('SIGINT', () => shutdown()); process.on('SIGTERM', () => shutdown());
server.on('error', error => { console.error(error.message); shutdown(1); });
try { await startBackend(); startWatcher(); server.listen(port, '127.0.0.1', () => console.log(`PROJECT_READY=http://127.0.0.1:${server.address().port}`)); }
catch (error) { console.error(error.message); await shutdown(1); }
