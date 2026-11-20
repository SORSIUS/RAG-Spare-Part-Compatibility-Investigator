import {textElement} from './sources.js';
export function markdown(value) {
  const root = textElement('div', undefined, 'markdown');
  function inline(node, text) {
    for (const piece of text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g)) {
      if (piece.startsWith('**') && piece.endsWith('**')) node.append(textElement('strong', piece.slice(2,-2)));
      else if (piece.startsWith('`') && piece.endsWith('`')) node.append(textElement('code', piece.slice(1,-1)));
      else node.append(document.createTextNode(piece));
    }
  }
  let list;
  for (const line of String(value || '').split('\n')) {
    if (!line.trim()) { list = null; continue; }
    const heading = line.match(/^#{1,4}\s+(.+)/), bullet = line.match(/^(?:[-*]|\d+\.)\s+(.+)/);
    if (bullet) { if (!list) { list=document.createElement('ul');root.append(list); } const item=document.createElement('li');inline(item,bullet[1]);list.append(item); }
    else { list=null;const node=document.createElement(heading ? 'h3':'p');inline(node,heading ? heading[1]:line);root.append(node); }
  }
  return root;
}
