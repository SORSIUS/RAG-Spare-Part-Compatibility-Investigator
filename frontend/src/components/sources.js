export function safePdfUrl(value) {
  return typeof value === 'string' && (/^\/api\/catalogue\/pdf\?version=[a-f0-9]{64}#page=[1-9]\d*$/.test(value) || /^\/api\/documents\/[a-f0-9]{64}\/pdf#page=[1-9]\d*$/.test(value)) ? value : null;
}

export function sourceLabel(source) {
  if (!source || !Number.isInteger(source.page_number) || source.page_number < 1) return 'Source page unavailable';
  return `${source.id} · PDF page ${source.page_number}`;
}

export function textElement(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = String(text);
  if (className) element.className = className;
  return element;
}

export function renderSource(source, selected, choose) {
  const card = textElement('article', undefined, 'source-card' + (selected ? ' selected' : ''));
  const label = textElement('div', undefined, 'source-card-head');
  const button = textElement('button', sourceLabel(source), 'source-select');
  button.type = 'button'; button.onclick = () => choose(source.id);
  label.append(button, textElement('span', source.section.replaceAll('_', ' '), 'section-tag'));
  card.append(label, textElement('h3', source.title), textElement('p', source.content, 'source-excerpt'));
  const url = safePdfUrl(source.pdf_url);
  if (url) {
    const link = textElement('a', 'Open PDF page ↗', 'source-link'); link.href = url; link.target = '_blank'; link.rel = 'noopener'; card.append(link);
  }
  const raw = document.createElement('details'); raw.append(textElement('summary', 'View the underlying extraction'), textElement('pre', source.raw_excerpt)); card.append(raw);
  return card;
}
