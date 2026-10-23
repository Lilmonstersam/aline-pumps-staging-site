window.alineSearchMatches = function (records, query) {
  const normalised = query.trim().toLocaleLowerCase();
  const terms = normalised.split(/\s+/).filter(Boolean);
  if (!terms.length) return [];
  return records.map(item => {
    const title = item.title.toLocaleLowerCase();
    const description = item.description.toLocaleLowerCase();
    const body = item.text.toLocaleLowerCase();
    if (!terms.every(term => title.includes(term) || description.includes(term) || body.includes(term))) return null;
    let score = 0;
    for (const term of terms) {
      if (title.includes(term)) score += 12;
      if (description.includes(term)) score += 4;
      if (body.includes(term)) score += 1;
      if (title.startsWith(term)) score += 4;
    }
    if (title.includes(normalised)) score += 8;
    if (title.startsWith(normalised)) score += 10;
    if (title === normalised) score += 20;
    return { item, score };
  }).filter(Boolean).sort((a, b) => b.score - a.score || a.item.title.length - b.item.title.length || a.item.title.localeCompare(b.item.title));
};

(function () {
  const toggle = document.querySelector('.menu-toggle');
  const menu = document.getElementById('primary-menu');
  const supportItem = menu?.querySelector('.has-submenu');
  const supportToggle = supportItem?.querySelector('.submenu-toggle');
  function setSupportMenu(open) {
    if (!supportItem) return;
    supportItem.classList.toggle('is-open', open);
    supportToggle.setAttribute('aria-expanded', String(open));
    supportToggle.setAttribute('aria-label', open ? 'Hide Support and Service options' : 'Show Support and Service options');
  }
  if (supportItem) {
    const hoverSupport = window.matchMedia('(hover: hover) and (min-width: 1151px)');
    supportToggle.addEventListener('click', () => setSupportMenu(supportToggle.getAttribute('aria-expanded') !== 'true'));
    supportItem.addEventListener('mouseenter', () => { if (hoverSupport.matches) setSupportMenu(true); });
    supportItem.addEventListener('mouseleave', () => { if (hoverSupport.matches && !supportItem.contains(document.activeElement)) setSupportMenu(false); });
    supportItem.addEventListener('focusout', event => { if (!supportItem.contains(event.relatedTarget)) setSupportMenu(false); });
    document.addEventListener('pointerdown', event => { if (!supportItem.contains(event.target)) setSupportMenu(false); });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && supportToggle.getAttribute('aria-expanded') === 'true') {
        setSupportMenu(false);
        supportToggle.focus();
      }
    });
  }
  if (toggle && menu) {
    function setMenu(open) {
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
      toggle.textContent = open ? 'Close' : 'Menu';
      menu.classList.toggle('is-open', open);
      if (!open) setSupportMenu(false);
    }
    toggle.addEventListener('click', () => setMenu(toggle.getAttribute('aria-expanded') !== 'true'));
    menu.addEventListener('click', event => {
      if (event.target.closest('a')) setMenu(false);
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
        setMenu(false);
        toggle.focus();
      }
    });
    document.addEventListener('click', event => {
      if (toggle.getAttribute('aria-expanded') === 'true' && !event.target.closest('.navbar')) setMenu(false);
    });
    window.matchMedia('(min-width: 1151px)').addEventListener('change', event => {
      if (event.matches) setMenu(false);
    });
  }

  const headerSearch = document.querySelector('.header-search');
  if (headerSearch) {
    const searchToggle = headerSearch.querySelector('.header-search-toggle');
    const searchInput = headerSearch.querySelector('input[type="search"]');
    const searchSubmit = headerSearch.querySelector('.header-search-submit');
    const preview = headerSearch.querySelector('.header-search-preview');
    const previewStatus = preview.querySelector('.header-search-preview-status');
    const previewList = preview.querySelector('.header-search-preview-list');
    const allResults = preview.querySelector('.header-search-all');
    const hoverSearch = window.matchMedia('(hover: hover) and (min-width: 701px)');
    let indexPromise;
    let searchTimer;
    let searchRevision = 0;
    function loadIndex() {
      if (window.ALINE_SEARCH_INDEX) return Promise.resolve(window.ALINE_SEARCH_INDEX);
      if (!indexPromise) indexPromise = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = headerSearch.dataset.indexSrc;
        script.onload = () => resolve(window.ALINE_SEARCH_INDEX || []);
        script.onerror = () => reject(new Error('Search index unavailable'));
        document.head.append(script);
      });
      return indexPromise;
    }
    function hidePreview() {
      preview.hidden = true;
      searchInput.setAttribute('aria-expanded', 'false');
    }
    function renderPreview(matches, query) {
      previewList.replaceChildren();
      previewStatus.textContent = matches.length
        ? `${matches.length} result${matches.length === 1 ? '' : 's'} for “${query}”. Showing the top ${Math.min(matches.length, 5)}.`
        : `No results for “${query}”.`;
      for (const { item } of matches.slice(0, 5)) {
        const row = document.createElement('li');
        const link = document.createElement('a');
        link.href = headerSearch.dataset.root + item.path;
        const type = document.createElement('span');
        type.className = 'header-search-preview-type';
        type.textContent = item.type;
        const title = document.createElement('strong');
        title.textContent = item.title;
        link.append(type, title);
        row.append(link);
        previewList.append(row);
      }
      allResults.href = headerSearch.dataset.root + 'search/index.html?q=' + encodeURIComponent(query);
      preview.hidden = false;
      searchInput.setAttribute('aria-expanded', 'true');
    }
    async function updatePreview() {
      const query = searchInput.value.trim();
      const revision = ++searchRevision;
      if (query.length < 2 || !headerSearch.classList.contains('is-open')) {
        hidePreview();
        return;
      }
      previewStatus.textContent = 'Searching…';
      previewList.replaceChildren();
      preview.hidden = false;
      try {
        const records = await loadIndex();
        if (revision !== searchRevision || !headerSearch.classList.contains('is-open')) return;
        renderPreview(window.alineSearchMatches(records, query), query);
      } catch {
        if (revision === searchRevision) {
          previewStatus.textContent = 'Search preview is unavailable. Press Enter to search.';
          previewList.replaceChildren();
          preview.hidden = false;
        }
      }
    }
    function setSearch(open) {
      headerSearch.classList.toggle('is-open', open);
      searchToggle.setAttribute('aria-expanded', String(open));
      searchToggle.setAttribute('aria-label', open ? 'Close site search' : 'Open site search');
      searchInput.tabIndex = open ? 0 : -1;
      searchSubmit.tabIndex = open ? 0 : -1;
      if (!open) {
        clearTimeout(searchTimer);
        searchRevision++;
        hidePreview();
      }
    }
    searchToggle.addEventListener('click', () => {
      const open = hoverSearch.matches || !headerSearch.classList.contains('is-open');
      if (open && toggle && toggle.getAttribute('aria-expanded') === 'true') toggle.click();
      setSearch(open);
      if (open) searchInput.focus();
    });
    searchInput.addEventListener('input', () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(updatePreview, 130);
    });
    searchInput.addEventListener('focus', () => { if (searchInput.value.trim().length >= 2) updatePreview(); });
    searchInput.addEventListener('keydown', event => {
      if (event.key === 'ArrowDown' && !preview.hidden) {
        const first = previewList.querySelector('a');
        if (first) { event.preventDefault(); first.focus(); }
      }
    });
    headerSearch.addEventListener('mouseenter', () => {
      if (hoverSearch.matches) setSearch(true);
    });
    headerSearch.addEventListener('mouseleave', () => {
      if (hoverSearch.matches && !headerSearch.contains(document.activeElement)) setSearch(false);
    });
    headerSearch.addEventListener('focusin', event => {
      if (event.target !== searchToggle) setSearch(true);
    });
    headerSearch.addEventListener('focusout', event => {
      if (!headerSearch.contains(event.relatedTarget)) setSearch(false);
    });
    headerSearch.addEventListener('keydown', event => {
      if (event.key === 'Escape') {
        setSearch(false);
        searchToggle.focus();
      }
    });
    document.addEventListener('pointerdown', event => {
      if (!headerSearch.contains(event.target)) setSearch(false);
    });
    if (toggle) toggle.addEventListener('click', () => setSearch(false));
  }

  const filterGroup = document.querySelector('.archive-filters');
  if (filterGroup) {
    const cards = [...document.querySelectorAll('.filter-item')];
    const empty = document.querySelector('.filter-empty');
    filterGroup.addEventListener('click', event => {
      const button = event.target.closest('button[data-filter]');
      if (!button) return;
      const selection = button.dataset.filter;
      filterGroup.querySelectorAll('button').forEach(item => {
        const selected = item === button;
        item.classList.toggle('is-active', selected);
        item.setAttribute('aria-pressed', String(selected));
      });
      let shown = 0;
      cards.forEach(card => {
        const match = selection === 'all' || card.dataset.categories.split(' ').includes(selection);
        card.hidden = !match;
        if (match) shown++;
      });
      if (empty) empty.hidden = shown !== 0;
    });
  }

  document.querySelectorAll('.related-project-carousel').forEach(carousel => {
    const track = carousel.querySelector('.project-carousel-track');
    carousel.querySelectorAll('[data-scroll]').forEach(button => {
      button.addEventListener('click', () => {
        const direction = Number(button.dataset.scroll);
        track.scrollBy({ left: direction * track.clientWidth * .85, behavior: 'smooth' });
      });
    });
  });

  const context = document.getElementById('enquiry-context');
  if (context) {
    const params = new URLSearchParams(location.search);
    const fields = [['topic', 'Enquiry'], ['model', 'Model'], ['category', 'Range'], ['service', 'Service']];
    const items = fields.filter(([key]) => params.get(key)).map(([key, label]) => {
      let value = params.get(key).replace(/[-_]/g, ' ');
      if (key === 'model') value = value.toUpperCase();
      return `${label}: ${value}`;
    });
    if (items.length) {
      context.hidden = false;
      const heading = document.createElement('strong');
      heading.textContent = 'Your enquiry';
      const detail = document.createElement('span');
      detail.textContent = items.join(' · ');
      context.append(heading, detail);
      const text = items.join('\n');
      const target = document.getElementById('contact-enquiry-form');
      if (target) {
        const prefill = () => {
          const message = target.querySelector('textarea[name="message"], textarea[name*="message"]');
          if (!message || message.dataset.alinePrefilled) return;
          if (message.value.trim()) {
            message.dataset.alinePrefilled = 'true';
            return;
          }
          message.value = `${text}\n\n${message.value}`;
          message.dataset.alinePrefilled = 'true';
          message.dispatchEvent(new Event('input', { bubbles: true }));
        };
        new MutationObserver(prefill).observe(target, { childList: true, subtree: true });
        prefill();
      }
    }
  }
})();
