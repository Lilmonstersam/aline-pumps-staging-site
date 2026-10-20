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
