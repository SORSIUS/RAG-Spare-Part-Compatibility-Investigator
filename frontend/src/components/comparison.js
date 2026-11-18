import {textElement, safePdfUrl} from './sources.js';

export const verdictLabels = {conflict: 'Documented dimension conflict', documented_reference: 'Published direct reference', unknown: 'Not enough evidence for interchangeability'};

export function dimensionValue(values) {
  return values.length ? values.map(value => value + ' mm').join(' / ') : 'Not documented';
}

function evidenceLinks(evidence) {
  const links = textElement('div', undefined, 'comparison-links');
  const seen = new Set();
  for (const record of evidence) {
    const url = safePdfUrl(record.pdf_url);
    if (!url || seen.has(url)) continue;
    seen.add(url);
    const link = textElement('a', 'PDF page ' + record.page_number, 'source-link');
    link.href = url; link.target = '_blank'; link.rel = 'noopener'; link.title = record.quote; links.append(link);
  }
  return links;
}

export function renderComparison(result) {
  const container = textElement('div', undefined, 'comparison-result');
  container.append(textElement('strong', verdictLabels[result.status] || result.status, 'comparison-verdict ' + result.status), textElement('p', result.explanation));
  const table = textElement('table');
  const head = textElement('thead'), heading = textElement('tr');
  for (const title of ['Specification', result.original, result.candidate, 'Finding / evidence']) { const cell = textElement('th', title); cell.scope = 'col'; heading.append(cell); }
  head.append(heading); table.append(head);
  const body = textElement('tbody');
  for (const check of result.dimension_checks) {
    const row = textElement('tr');
    const label = textElement('th', check.field.replace('_mm', '')); label.scope = 'row';
    const finding = textElement('td');
    finding.append(textElement('span', check.status, 'finding ' + check.status), evidenceLinks(check.evidence));
    row.append(label, textElement('td', dimensionValue(check.original_values)), textElement('td', dimensionValue(check.candidate_values)), finding); body.append(row);
  }
  table.append(body);
  const scroll = textElement('div', undefined, 'comparison-scroll'); scroll.append(table); container.append(scroll);
  container.append(textElement('p', 'Direct reference: ' + result.cross_reference_status + ' · Vehicle fitment: ' + result.vehicle_fitment), evidenceLinks(result.cross_reference_evidence));
  if (result.original_lookup_status === 'ambiguous_brand') container.append(textElement('p', 'This external number appears under multiple brands. Enter the original brand before relying on a reference.', 'comparison-unknown'));
  if (result.original_lookup_status === 'not_found' || result.candidate_lookup_status === 'not_found') container.append(textElement('p', 'At least one part was not found in the extracted catalogue. Missing evidence stays unknown.', 'comparison-unknown'));
  container.append(textElement('p', result.notice, 'answer-notice'));
  return container;
}

export function comparisonMarkdown(result) {
  const lines = ['# Spare-part comparison', '', result.original + ' → ' + result.candidate, '', 'Status: ' + result.status, '', result.explanation, '', 'Source SHA-256: ' + result.source_sha256, '', 'Created: ' + result.created_at, '', 'Original brand: ' + (result.brand || 'not specified'), '', '| Specification | Original | Candidate | Status |', '| --- | --- | --- | --- |'];
  for (const check of result.dimension_checks) lines.push(`| ${check.field} | ${dimensionValue(check.original_values)} | ${dimensionValue(check.candidate_values)} | ${check.status} |`);
  lines.push('', 'Direct reference: ' + result.cross_reference_status, '', 'Vehicle fitment: ' + result.vehicle_fitment, '', '## Evidence', '');
  const seen = new Set();
  for (const evidence of [...result.dimension_checks.flatMap(check => check.evidence), ...result.cross_reference_evidence]) {
    const identity = evidence.source + ':' + evidence.page_number + ':' + evidence.quote;
    if (seen.has(identity)) continue;
    seen.add(identity);
    lines.push(`${evidence.source} | PDF page ${evidence.page_number}`, '', evidence.quote, '', 'Local PDF link: ' + evidence.pdf_url, '');
  }
  lines.push(result.notice, '', 'Local PDF links require the running app and the same catalogue revision.', '');
  return lines.join('\n');
}

export function downloadComparison(result, format) {
  const content = format === 'json' ? JSON.stringify(result, null, 2) : comparisonMarkdown(result);
  const url = URL.createObjectURL(new Blob([content], {type: format === 'json' ? 'application/json' : 'text/markdown;charset=utf-8'}));
  const link = document.createElement('a'); link.href = url; link.download = 'part-comparison.' + (format === 'json' ? 'json' : 'md'); link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
