export function readTheme(storage, prefersDark = false) {
  try {
    const saved = storage.getItem('part-investigator-theme');
    if (saved === 'dark' || saved === 'light') return saved;
  } catch {}
  return prefersDark ? 'dark' : 'light';
}

export function initializeTheme(button, root, storage, prefersDark = false) {
  function apply(theme) {
    root.dataset.theme = theme;
    button.textContent = theme === 'dark' ? '☀ Light' : '☾ Dark';
    button.setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`);
    button.setAttribute('aria-pressed', String(theme === 'dark'));
  }
  apply(readTheme(storage, prefersDark));
  button.onclick = () => {
    const theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    apply(theme);
    try { storage.setItem('part-investigator-theme', theme); } catch {}
  };
}
