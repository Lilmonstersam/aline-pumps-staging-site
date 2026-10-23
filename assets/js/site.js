(function () {
  const toggle = document.querySelector('.menu-toggle');
  const menu = document.getElementById('primary-menu');
  if (toggle && menu) {
    function setMenu(open) {
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
      toggle.textContent = open ? 'Close' : 'Menu';
      menu.classList.toggle('is-open', open);
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
    const hoverSearch = window.matchMedia('(hover: hover) and (min-width: 701px)');
    function setSearch(open) {
      headerSearch.classList.toggle('is-open', open);
      searchToggle.setAttribute('aria-expanded', String(open));
      searchToggle.setAttribute('aria-label', open ? 'Close site search' : 'Open site search');
      searchInput.tabIndex = open ? 0 : -1;
      searchSubmit.tabIndex = open ? 0 : -1;
    }
    searchToggle.addEventListener('click', () => {
      const open = hoverSearch.matches || !headerSearch.classList.contains('is-open');
      if (open && toggle && toggle.getAttribute('aria-expanded') === 'true') toggle.click();
      setSearch(open);
      if (open) searchInput.focus();
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
