(() => {
  const mainImage = document.querySelector('.product-gallery .main-image img');
  const thumbnails = Array.from(document.querySelectorAll('.product-gallery .thumbs button'));

  thumbnails.forEach((button) => {
    button.addEventListener('click', () => {
      if (!mainImage) return;
      mainImage.src = button.dataset.image;
      mainImage.alt = button.dataset.alt;
      thumbnails.forEach((thumbnail) => {
        thumbnail.setAttribute('aria-pressed', String(thumbnail === button));
      });
    });
  });

  const tabs = Array.from(document.querySelectorAll('.product-tabs [role="tab"]'));
  if (!tabs.length) return;
  const panels = tabs.map((tab) => document.getElementById(tab.getAttribute('aria-controls')));

  function activate(tab, focus = false) {
    tabs.forEach((item, index) => {
      const active = item === tab;
      item.setAttribute('aria-selected', String(active));
      item.tabIndex = active ? 0 : -1;
      panels[index].hidden = !active;
    });
    if (focus) tab.focus();
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => activate(tab));
    tab.addEventListener('keydown', (event) => {
      let next;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      if (next === undefined) return;
      event.preventDefault();
      activate(tabs[next], true);
    });
  });

  const deepLink = tabs.find((tab) => `#${tab.getAttribute('aria-controls')}` === window.location.hash);
  activate(deepLink || tabs[0]);
  window.addEventListener('hashchange', () => {
    const linkedTab = tabs.find((tab) => `#${tab.getAttribute('aria-controls')}` === window.location.hash);
    if (linkedTab) activate(linkedTab);
  });
})();
