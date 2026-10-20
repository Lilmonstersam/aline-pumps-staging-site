(() => {
  const page = document.querySelector('.site-search-page');
  if (!page) return;

  const input = document.getElementById('search-page-query');
  const status = document.getElementById('search-status');
  const results = document.getElementById('search-results');
  const query = new URLSearchParams(location.search).get('q')?.trim() || '';
  document.querySelectorAll('input[name="q"]').forEach(field => { field.value = query; });
  if (!query) return;

  const terms = query.toLocaleLowerCase().split(/\s+/).filter(Boolean);
  const matches = (window.ALINE_SEARCH_INDEX || []).map(item => {
    const title = item.title.toLocaleLowerCase();
    const description = item.description.toLocaleLowerCase();
    const body = item.text.toLocaleLowerCase();
    if (!terms.every(term => title.includes(term) || description.includes(term) || body.includes(term))) return null;
    let score = 0;
    for (const term of terms) {
      if (title.includes(term)) score += 12;
      if (description.includes(term)) score += 4;
      if (body.includes(term)) score += 1;
    }
    if (title.includes(query.toLocaleLowerCase())) score += 8;
    return { item, score };
  }).filter(Boolean).sort((a, b) => b.score - a.score || a.item.title.localeCompare(b.item.title));

  status.textContent = matches.length
    ? `${matches.length} result${matches.length === 1 ? '' : 's'} for “${query}”${matches.length > 80 ? '. Showing the first 80.' : '.'}`
    : `No results for “${query}”. Try a product name, application or project.`;

  const fragment = document.createDocumentFragment();
  for (const { item } of matches.slice(0, 80)) {
    const card = document.createElement('article');
    card.className = 'search-result';
    const type = document.createElement('span');
    type.className = 'eyebrow';
    type.textContent = item.type;
    const heading = document.createElement('h2');
    const link = document.createElement('a');
    link.href = page.dataset.root + item.path;
    link.textContent = item.title;
    heading.append(link);
    const summary = document.createElement('p');
    summary.textContent = item.description || item.text.slice(0, 210);
    card.append(type, heading, summary);
    fragment.append(card);
  }
  results.append(fragment);
})();
