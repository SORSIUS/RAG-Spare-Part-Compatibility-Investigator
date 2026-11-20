import {createPartsFinder} from './parts-finder.js';
import {textElement} from './sources.js';

export function setupStorefront() {
  const stylesheet = document.createElement('link'); stylesheet.rel = 'stylesheet'; stylesheet.href = '/storefront.css'; document.head.append(stylesheet);
  const polish = document.createElement('link'); polish.rel = 'stylesheet'; polish.href = '/polish.css'; document.head.append(polish);
  const pagesCSS = document.createElement('link'); pagesCSS.rel='stylesheet';pagesCSS.href='/pages.css';document.head.append(pagesCSS);
  const main = document.querySelector('main');
  const header = document.querySelector('.topbar');
  header.querySelector('.top-label').textContent = 'AUTOMOTIVE PARTS REFERENCE';
  header.querySelector('h2').textContent = 'Car parts, made simple.';
  const catalogues = document.createElement('details'); catalogues.id = 'catalogues-drawer'; catalogues.className = 'catalogues-drawer';
  catalogues.append(textElement('summary', 'Document library'));
  const tools = textElement('div', undefined, 'catalogue-tools');
  tools.append(document.getElementById('catalogue-link'), document.getElementById('reindex'));
  catalogues.append(tools, document.querySelector('.catalogue-strip'), document.querySelector('.document-library'));
  const finder = createPartsFinder();
  const photograph = document.createElement('img'); photograph.src = '/assets/automotive-hero.png'; photograph.alt = 'Illustrative suspension parts, filter and spark plug on a green-lit workbench'; photograph.width = 1536; photograph.height = 1024; photograph.decoding = 'async';
  finder.element.querySelector('.garage-illustration').replaceChildren(photograph, textElement('span', 'Illustrative image · use the catalogue for the exact part'));
  header.after(finder.element, catalogues);
  const workspace = document.querySelector('.workspace'); workspace.id = 'questions';
  const heading = textElement('div', undefined, 'question-section-title');
  heading.append(textElement('span', 'NEED A SECOND LOOK?', 'shop-kicker'), textElement('h2', 'Ask about a part or compare the evidence'), textElement('p', 'Use plain language. Your saved investigations and source pages stay together.'));
  workspace.before(heading);
  const composition = document.getElementById('chat-form');
  const pane = document.querySelector('.conversation-pane');
  const intro = textElement('div', undefined, 'chat-intro'); intro.id = 'chat-intro';
  intro.append(textElement('strong', 'Hi, what would you like to check?'), textElement('p', 'Tell me your car, year and part. I’ll check the documents and show you the references.'));
  pane.prepend(intro);
  pane.append(composition, pane.querySelector('.scope-note'));
  document.getElementById('messages').setAttribute('role', 'log');
  composition.querySelector('label').textContent = 'Ask a question about your car';
  document.getElementById('question').placeholder = 'e.g. What does a cabin filter do? Or: which filter is listed for my car?';
  document.querySelector('.brand').setAttribute('aria-label', 'Part Investigator home');
  document.getElementById('history-toggle').textContent = 'Saved investigations';
  const nav = textElement('nav', undefined, 'shop-nav'); nav.setAttribute('aria-label', 'Main sections');
  for (const [name, id] of [['Home', '#home'], ['Browse parts', '#parts'], ['Chat assistant', '#chat'], ['Documents', '#documents']]) {
    const a = textElement('a', name); a.href = id; nav.append(a);
  }
  const home = textElement('section', undefined, 'home-page');
  home.innerHTML = `<div class="home-hero"><div><span class="shop-kicker">UNDERSTAND YOUR CAR</span><h1>Your car.<br>Clearer answers.</h1><p>Understand car parts, explore your options and get help in plain language. Our current document library mainly covers Toyota Corolla; coverage for other cars varies.</p><div class="home-actions"><a class="primary-button" href="#parts">Explore parts</a><a class="outline-button" href="#chat">Ask the assistant</a></div></div><img src="/assets/automotive-hero.png" alt="Illustrative automotive parts on a green-lit workbench"></div><div class="toyota-guide"><article><h2>Start with your car</h2><p>Tell us the make, model, year and engine. We can explain parts for any car; exact part matches depend on the references available.</p><a href="https://www.toyota.com/owners/warranty-owners-manuals" target="_blank" rel="noopener">Toyota owner manuals</a></article><article><h2>Understand your parts</h2><p>Explore filters, brakes, ignition, suspension, engine and electrical parts. See document findings separately from general explanations.</p><a href="#parts">Browse by category</a></article><article><h2>Know what is covered</h2><p>Corolla is our main starting point. General advice is labelled separately from document findings. We will say when a vehicle or part is not covered, and never assume Corolla parts fit another car.</p><a href="#chat">Get help checking a part</a></article></div>`;
  header.after(home);
  const comparison = document.querySelector('.comparison-panel');
  const setup = document.getElementById('setup-banner'); catalogues.append(setup);
  const groups = {home: [home], parts: [finder.element], chat: [heading, workspace, comparison], documents: [catalogues]};
  const applyRoute = () => {
    const route = ({questions:'chat', 'parts-finder':'parts', 'catalogues-drawer':'documents'})[location.hash.slice(1)] || location.hash.slice(1) || 'home';
    const current = groups[route] ? route : 'home';
    for (const [name, nodes] of Object.entries(groups)) for (const node of nodes) node.hidden = name !== current;
    document.body.dataset.page = current;
    catalogues.open = current === 'documents';
    for (const link of nav.querySelectorAll('a')) { if(link.hash === '#' + current) link.setAttribute('aria-current', 'page');else link.removeAttribute('aria-current'); }
    window.scrollTo(0,0);
  };
  window.addEventListener('hashchange', applyRoute); applyRoute();
  document.querySelector('.brand').href = '#home';
  document.querySelector('.brand').after(nav);
  return finder;
}
