export async function request(path, body, fetcher = globalThis.fetch) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 100000);
  try {
    const response = await fetcher('/api/' + path, {method: body === undefined ? 'GET' : 'POST', headers: {'Content-Type': 'application/json'}, body: body === undefined ? undefined : JSON.stringify(body), signal: controller.signal});
    let payload;
    try { payload = await response.json(); } catch { throw new Error('The server returned an unreadable response. Check the main project terminal.'); }
    if (!response.ok) throw new Error(payload.error?.message || 'The request failed. Try again.');
    if (path === 'status' && (payload.contract_version !== 3 || typeof payload.llm_configured !== 'boolean')) throw new Error('This page is connected to an older backend. Restart START_PROJECT.cmd, then refresh.');
    if (path === 'chat' && (!Array.isArray(payload.claims) || !Array.isArray(payload.sources))) throw new Error('The response does not match this app version. Restart the main project server.');
    if (path === 'catalogue/compare' && (!Array.isArray(payload.dimension_checks) || typeof payload.source_sha256 !== 'string')) throw new Error('The comparison response is incompatible. Restart the main project server.');
    return payload;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The request timed out. Check the terminal and try a narrower question.');
    throw error;
  } finally { clearTimeout(timer); }
}
