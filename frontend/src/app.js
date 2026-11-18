import {request} from './services/api.js';
import {textElement, renderSource, safePdfUrl} from './components/sources.js';
import {renderComparison, downloadComparison} from './components/comparison.js';
import {initializeTheme} from './services/theme.js';

const $ = identifier => document.getElementById(identifier);
let themeStorage;
try { themeStorage = localStorage; } catch {}
initializeTheme($('theme-toggle'), document.documentElement, themeStorage, window.matchMedia('(prefers-color-scheme: dark)').matches);
$('history-toggle').onclick = () => {
  const open = $('history-toggle').getAttribute('aria-expanded') !== 'true';
  $('history-toggle').setAttribute('aria-expanded', String(open));
  document.querySelector('.sidebar').dataset.historyOpen = String(open);
};
let configuration, conversationId = null, messages = [], sources = [], selectedSource = null, busy = false, statusBusy = false;
let comparison = null, loadingTimer;
let uploadBusy = false, libraryBusy = false;
try { conversationId = localStorage.getItem('part-investigator-conversation'); } catch {}

function showError(message = '') { $('error').textContent = message; $('error').hidden = !message; }
function saveConversation() { try { conversationId ? localStorage.setItem('part-investigator-conversation', conversationId) : localStorage.removeItem('part-investigator-conversation'); } catch {} }
function setBusy(value, label = 'Retrieving catalogue evidence and preparing the response…') {
  if (value && !busy) {
    const started = Date.now();
    $('loading-text').textContent = label;
    loadingTimer = setInterval(() => { $('loading-text').textContent = label + ' ' + Math.floor((Date.now() - started) / 1000) + 's'; }, 1000);
  } else if (!value) clearInterval(loadingTimer);
  busy = value; $('loading').hidden = !value; $('question').disabled = value; $('new-chat').disabled = value; $('reindex').disabled = value;
  const searchReady = configuration?.search_ready ?? configuration?.catalogue_ready;
  $('search-evidence').disabled = value || !searchReady;
  $('ask').disabled = value || !searchReady || !configuration?.llm_configured;
  document.querySelectorAll('[data-question]').forEach(button => button.disabled = value);
  document.querySelector('.conversation-pane').setAttribute('aria-busy', String(value));
  document.querySelectorAll('#compare-form input, #compare-form button').forEach(element => element.disabled = value || !configuration?.catalogue_ready);
}

async function updateStatus() {
  if (statusBusy) return;
  statusBusy = true; $('refresh-status').disabled = true;
  try {
    configuration = await request('status');
    const catalogue = configuration.catalogue;
    if (configuration.document_library) drawLibrary(configuration.document_library);
    $('catalogue-status').textContent = catalogue ? `${catalogue.dimensions.toLocaleString()} dimension records · ${catalogue.cross_references.toLocaleString()} cross-references · ${catalogue.applications.toLocaleString()} applications` : 'Local catalogue unavailable. Check the PDF download, then use Reindex.';
    $('page-count').textContent = catalogue ? catalogue.pages + ' pages' : 'PDF missing';
    const url = safePdfUrl(catalogue?.pdf_url);
    $('catalogue-link').hidden = !url;
    if (url) $('catalogue-link').href = url;
    $('provider-status').textContent = configuration.llm_configured ? 'Answers ready' : 'Answer setup needed';
    $('provider-dot').className = 'provider-dot' + (configuration.llm_configured ? ' ready' : '');
    $('setup-banner').hidden = configuration.llm_configured;
    $('compose-hint').textContent = configuration.llm_configured ? 'Enter to ask · Shift+Enter for a new line' : 'Search sources works without a key';
    if (configuration.catalogue_error) showError(configuration.catalogue_error);
    setBusy(busy);
  } catch (error) { showError(error.message); }
  finally { statusBusy = false; $('refresh-status').disabled = false; }
}

function showSources(nextSources, selected = null) {
  sources = nextSources;
  selectedSource = selected;
  $('source-count').textContent = sources.length + (sources.length === 1 ? ' source' : ' sources');
  $('empty-sources').hidden = !!sources.length;
  $('sources').replaceChildren(...sources.map(source => renderSource(source, source.id === selectedSource, chooseSource)));
}

function chooseSource(identifier) {
  const source = sources.find(item => item.id === identifier);
  if (!source) return;
  showSources(sources, identifier);
  const url = safePdfUrl(source.pdf_url);
  if (url) { $('pdf-frame').src = url; $('pdf-preview-title').textContent = identifier + ' · PDF page ' + source.page_number; $('pdf-preview').hidden = false; }
  document.querySelector('.evidence-pane').scrollIntoView({behavior: 'smooth', block: 'nearest'});
}

function renderMessage(message) {
  const wrapper = textElement('article', undefined, 'message');
  wrapper.append(textElement('div', message.question, 'user-question'));
  const answer = textElement('div', undefined, 'answer-card');
  const header = textElement('div', undefined, 'answer-header');
  const titles = {answered: 'Here’s what the documents say', evidence_only: 'Sources for your question', insufficient_evidence: 'Let’s check a few details first', unverified_response: 'This answer needs a closer check'};
  header.append(textElement('strong', message.summary || titles[message.status] || 'Your answer'), textElement('span', message.model ? 'WITH SOURCES' : message.answer_method === 'catalogue_rules' ? 'DOCUMENT CHECK' : 'EVIDENCE', 'answer-mode')); answer.append(header);
  for (const claim of message.claims) {
    const paragraph = textElement('p', claim.text, 'claim');
    for (const citation of claim.citations) {
      const button = textElement('button', citation.source_id, 'citation-chip'); button.type = 'button'; button.title = citation.quote;
      button.onclick = () => { showSources(message.sources); chooseSource(citation.source_id); }; paragraph.append(button);
    }
    answer.append(paragraph);
  }
  if (message.mode === 'evidence' && message.sources.length) {
    const paragraph = textElement('p', `${message.sources.length} source passages are available. Select a citation to read the evidence, or use Enter for an explained answer once answer setup is complete.`, 'claim');
    for (const source of message.sources) {
      const button = textElement('button', source.id, 'citation-chip'); button.type = 'button'; button.onclick = () => { showSources(message.sources); chooseSource(source.id); }; paragraph.append(button);
    }
    answer.append(paragraph);
  }
  if (message.unknowns.length) {
    const unknowns = textElement('div', undefined, 'unknowns'); unknowns.append(textElement('strong', 'What we still need to check'));
    for (const unknown of message.unknowns) unknowns.append(textElement('p', unknown)); answer.append(unknowns);
  }
  const followUps = textElement('div', undefined, 'follow-ups');
  for (const question of message.follow_up_questions) { const button = textElement('button', question + ' →'); button.onclick = () => { $('question').value = question; $('question').focus(); }; followUps.append(button); }
  answer.append(followUps, textElement('p', message.notice, 'answer-notice'));
  const copy = textElement('button', 'Copy response', 'copy-answer');
  copy.onclick = async () => {
    const value = [message.question, ...message.claims.map(claim => claim.text + ' ' + claim.citations.map(citation => '[' + citation.source_id + ']').join(' ')), ...message.unknowns, ...message.sources.map(source => source.id + ': ' + source.source + ', PDF page ' + source.page_number), message.notice].join('\n');
    try { await navigator.clipboard.writeText(value); copy.textContent = 'Copied'; } catch { showError('Clipboard permission is unavailable. You can select and copy the displayed text.'); }
  };
  answer.append(copy); wrapper.append(answer); return wrapper;
}

function drawMessages() {
  $('welcome').hidden = messages.length > 0; $('messages').replaceChildren(...messages.map(renderMessage));
  $('conversation-exports').hidden = !conversationId || !messages.length;
  if (conversationId) for (const format of ['markdown', 'json']) $('export-' + format).href = '/api/conversations/' + encodeURIComponent(conversationId) + '/export?format=' + format;
}

async function listConversations() {
  const response = await request('conversations');
  $('conversations').replaceChildren(...response.conversations.map(conversation => {
    const button = textElement('button', conversation.title, 'conversation-link' + (conversation.id === conversationId ? ' active' : '')); button.title = conversation.title;
    if (conversation.id === conversationId) button.setAttribute('aria-current', 'true');
    button.onclick = () => loadConversation(conversation.id); return button;
  }));
  if (!response.conversations.length) $('conversations').append(textElement('p', 'Your saved conversations will appear here.', 'history-empty'));
}

async function loadConversation(identifier) {
  if (busy) return;
  setBusy(true); showError();
  try {
    const conversation = await request('conversations/' + encodeURIComponent(identifier));
    conversationId = conversation.id; messages = conversation.messages; saveConversation(); drawMessages();
    showSources(messages.at(-1)?.sources || []); $('pdf-preview').hidden = true; $('pdf-frame').removeAttribute('src'); await listConversations();
  } catch (error) {
    showError(error.message);
    // A temporary server error must not detach the current conversation.
  }
  finally { setBusy(false); }
}

async function send(mode) {
  const question = $('question').value.trim();
  if (busy || !question) { if (!question) $('question').focus(); return; }
  if (mode === 'answer' && !configuration?.llm_configured) { showError('Complete answer setup in backend/.env, refresh status, or search sources.'); return; }
  setBusy(true); showError();
  try {
    const message = await request('chat', {question, conversation_id: conversationId, mode});
    conversationId = message.conversation_id; messages.push(message); saveConversation(); drawMessages(); showSources(message.sources); $('question').value = ''; $('pdf-preview').hidden = true; $('pdf-frame').removeAttribute('src');
    $('messages').lastElementChild?.scrollIntoView({behavior: 'smooth', block: 'nearest'}); await listConversations();
  } catch (error) { showError(error.message); }
  finally { setBusy(false); }
}

$('chat-form').onsubmit = event => { event.preventDefault(); send('answer'); };
$('search-evidence').onclick = () => send('evidence');
$('question').onkeydown = event => { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); send(configuration?.llm_configured ? 'answer' : 'evidence'); } };
$('new-chat').onclick = () => { if (busy) return; conversationId = null; messages = []; saveConversation(); drawMessages(); showSources([]); $('pdf-preview').hidden = true; $('pdf-frame').removeAttribute('src'); showError(); $('question').value = ''; $('question').focus(); listConversations().catch(error => showError(error.message)); };

function drawLibrary(library) {
  const labels = {queued: 'Saved · preparing in background', indexing: 'Preparing · you can keep using the app', ready: 'Ready to search', needs_ocr: 'Needs OCR before it can be searched', failed: 'Could not prepare this document', verification: 'Test reference · excluded from answers'};
  $('document-list').replaceChildren(...library.documents.map(document => {
    const row = textElement('div', undefined, 'library-row');
    row.append(textElement('strong', document.name), textElement('span', labels[document.status] || document.status, 'library-state ' + document.status));
    if (document.error) row.append(textElement('span', document.error, 'library-error'));
    if (document.status === 'failed') { const retry = textElement('button', 'Retry this document', 'outline-button'); retry.type = 'button'; retry.onclick = async () => { try { await request('documents/' + document.id + '/retry', {}); await refreshLibrary(); } catch (error) { showError(error.message); } }; row.append(retry); }
    return row;
  }));
}

async function refreshLibrary() {
  if (libraryBusy) return;
  libraryBusy = true;
  try {
    const library = await request('documents'); drawLibrary(library);
    if (configuration) { configuration.search_ready = configuration.catalogue_ready || library.ready_documents > 0; setBusy(busy); }
  } catch {} finally { libraryBusy = false; }
}

$('upload-form').onsubmit = async event => {
  event.preventDefault(); if (uploadBusy) return;
  const file = $('upload-file').files[0];
  if (!file) return;
  if (file.size > 25 * 1024 * 1024) { showError('Use a document smaller than 25 MB.'); return; }
  uploadBusy = true; $('upload-submit').disabled = true; $('upload-feedback').textContent = 'Uploading your file…';
  try {
    const form = new FormData(); form.append('file', file);
    const response = await fetch('/api/documents/upload', {method: 'POST', body: form});
    const document = await response.json();
    if (!response.ok) throw new Error(document.error?.message || 'Upload failed.');
    $('upload-feedback').textContent = document.duplicate ? 'This file is already saved. Its indexing history has been kept.' : 'File saved. We will prepare it in the background—you can continue using the app.';
    $('upload-file').value = ''; await refreshLibrary();
  } catch (error) { showError(error.message); $('upload-feedback').textContent = 'The file was not accepted. Check the message above.'; }
  finally { uploadBusy = false; $('upload-submit').disabled = false; }
};
setInterval(() => { if (!document.hidden) refreshLibrary(); }, 3000);
$('refresh-status').onclick = () => { showError(); updateStatus(); };
$('close-preview').onclick = () => { $('pdf-preview').hidden = true; $('pdf-frame').removeAttribute('src'); };
$('reindex').onclick = async () => { if (busy) return; setBusy(true, 'Reading the PDF and rebuilding catalogue records…'); showError(); try { await request('catalogue/reindex', {}); await updateStatus(); } catch (error) { showError(error.message); } finally { setBusy(false); } };
$('compare-form').onsubmit = async event => {
  event.preventDefault(); if (busy) return;
  comparison = null; $('comparison-output').replaceChildren(); $('comparison-downloads').hidden = true;
  const original = $('compare-original').value.trim(), candidate = $('compare-candidate').value.trim(), brand = $('compare-brand').value.trim() || null;
  setBusy(true, 'Comparing documented dimensions and references…'); showError();
  try {
    comparison = await request('catalogue/compare', {original, candidate, brand});
    $('comparison-output').replaceChildren(renderComparison(comparison)); $('comparison-downloads').hidden = false;
  } catch (error) { showError(error.message); }
  finally { setBusy(false); }
};
for (const format of ['markdown', 'json']) $('comparison-' + format).onclick = () => { if (comparison) downloadComparison(comparison, format); };
document.querySelectorAll('[data-question]').forEach(button => button.onclick = () => { $('question').value = button.dataset.question; $('question').focus(); });
window.addEventListener('focus', () => { if (!busy) updateStatus(); });
await updateStatus();
try { await listConversations(); if (conversationId) await loadConversation(conversationId); } catch (error) { showError(error.message); }

