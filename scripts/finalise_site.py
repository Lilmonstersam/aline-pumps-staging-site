"""Apply one site shell and build client-side search for the static mockup."""
from __future__ import annotations

import json
import re
from pathlib import Path

from lxml import html as lhtml


SITE = Path(__file__).resolve().parents[1]
EXCLUDE = {"Water Pump System Supplier Sydney _ Aline Pumps Australia.html"}
EXCLUDE_PATHS = {"products/water-storage-tanks/round/index.html"}
FACEBOOK = "https://www.facebook.com/alinepumps.pumpingwithinnovation/"
LINKEDIN = "https://www.linkedin.com/company/aline-pumps/"
PORTAL = "https://www.alinepumps.com.au/wp-login.php"


def prefix_for(path: Path) -> str:
    return "../" * (len(path.relative_to(SITE).parts) - 1)


def active_section(path: Path) -> str:
    relative = path.relative_to(SITE).as_posix()
    if relative in {"products.html", "kusp40.html", "category-undersink-pumpstations.html"} or relative.startswith(("products/", "brands/")):
        return "products"
    if relative in {"support-and-service.html", "aline-service.html", "training.html"} or relative.startswith("support-and-service/"):
        return "support"
    if relative in {"our-projects/index.html"} or relative.startswith(("portfolio/", "portfolio_categories/")):
        return "projects"
    if relative in {"about.html", "about/index.html"}:
        return "about"
    other_pages = {"contact-us/index.html", "search/index.html", "terms-and-conditions/index.html", "return-of-goods-policy/index.html", "privacy-policy/index.html", "metal-water-tanks/index.html", "plumbing-supplies/index.html"}
    if relative.startswith(("blog/", "category/")) or (len(path.relative_to(SITE).parts) == 2 and relative not in other_pages):
        return "news"
    return ""


def search_icon() -> str:
    return '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/></svg>'


def header(path: Path) -> str:
    root = prefix_for(path)
    active = active_section(path)
    links = (("Support and Service", "support", "support-and-service.html"), ("Products", "products", "products.html"), ("Projects", "projects", "our-projects/index.html"), ("News &amp; Insights", "news", "blog/index.html"), ("About", "about", "about.html"))
    menu_items = []
    for label, key, target in links:
        attrs = ' class="active" aria-current="page"' if key == active else ""
        menu_items.append(f'<li><a href="{root}{target}"{attrs}>{label}</a></li>')
    menu = "".join(menu_items)
    return f'''<header class="site-header">
  <div class="topbar"><div class="wrap">
    <a class="logo" href="{root}index.html" aria-label="Aline Pumps home"><img src="{root}assets/logos/aline-pumps-logo.webp" alt="Aline Pumps" width="134" height="46"></a>
    <div class="topbar-contact"><a class="call" href="tel:1800018999">Call us <strong>1800 018 999</strong></a>
    <div class="social">
      <a href="{FACEBOOK}" aria-label="Aline Pumps on Facebook" target="_blank" rel="noopener"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13.5 21v-7.6h2.6l.4-3h-3V8.5c0-.9.3-1.5 1.5-1.5h1.6V4.3c-.3 0-1.2-.1-2.3-.1-2.3 0-3.9 1.4-3.9 4v2.2H7.8v3h2.6V21z"/></svg></a>
      <a href="{LINKEDIN}" aria-label="Aline Pumps on LinkedIn" target="_blank" rel="noopener"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5zM3 9h4v12H3zM9 9h3.8v1.7h.1c.5-1 1.8-2 3.8-2 4 0 4.8 2.6 4.8 6V21h-4v-5.6c0-1.3 0-3-1.9-3s-2.1 1.4-2.1 2.9V21H9z"/></svg></a>
    </div></div>
  </div></div>
  <nav class="navbar" aria-label="Main"><div class="wrap">
    <ul class="menu" id="primary-menu">{menu}</ul>
    <button class="menu-toggle" type="button" aria-controls="primary-menu" aria-expanded="false" aria-label="Open menu">Menu</button>
    <div class="header-search"><button class="header-search-toggle" type="button" aria-controls="header-search-form" aria-expanded="false" aria-label="Open site search">{search_icon()}</button><form id="header-search-form" role="search" action="{root}search/index.html" method="get"><label class="sr-only" for="header-site-search">Search Aline Pumps</label><input id="header-site-search" type="search" name="q" placeholder="Search the site" autocomplete="off" required tabindex="-1"><button class="header-search-submit" type="submit" aria-label="Submit search" tabindex="-1">Go</button></form></div>
    <div class="nav-actions"><a class="btn btn-outline portal-link" href="{PORTAL}" target="_blank" rel="noopener">Log in <span class="external-arrow" aria-hidden="true">↗</span></a><a class="btn btn-primary" href="{root}contact-us/index.html">Contact us</a></div>
  </div></nav>
</header>'''


def footer(path: Path) -> str:
    root = prefix_for(path)
    return f'''<footer class="site-footer">
  <div class="wrap footer-search-bar"><div><span class="eyebrow">Find what you need</span><h2>Search Aline Pumps</h2></div><form role="search" action="{root}search/index.html" method="get"><label class="sr-only" for="footer-site-search">Search Aline Pumps</label><input id="footer-site-search" type="search" name="q" placeholder="Products, projects, articles…" required><button type="submit" aria-label="Search the site">{search_icon()}<span>Search</span></button></form></div>
  <div class="wrap cols">
    <div><img class="flogo" src="{root}assets/logos/aline-pumps-logo.webp" alt="Aline Pumps"><p>100% Australian owned and operated. Pump and water system design, supply and lifecycle support.</p><div class="badges"><img src="{root}assets/logos/fpa-gold-member.jpg" alt="FPA Australia Gold Member"><img src="{root}assets/logos/iso-9001.png" alt="ISO 9001 certification"></div></div>
    <div><h4>Explore</h4><ul><li><a href="{root}support-and-service.html">Support and Service</a></li><li><a href="{root}products.html">Products</a></li><li><a href="{root}our-projects/index.html">Projects</a></li><li><a href="{root}blog/index.html">News &amp; Insights</a></li><li><a href="{root}about.html">About</a></li><li><a href="{root}contact-us/index.html">Contact us</a></li></ul></div>
    <div><h4>Our Services</h4><ul><li><a href="{root}aline-service.html">Aline Service</a></li><li><a href="https://alinespares.com/" target="_blank" rel="noopener">Aline Spares <span class="external-arrow" aria-hidden="true">↗</span></a></li><li><a href="https://pumps2you.com/" target="_blank" rel="noopener">Pumps 2 You <span class="external-arrow" aria-hidden="true">↗</span></a></li><li><a href="{root}training.html">Aline Training</a></li><li><a href="{PORTAL}" target="_blank" rel="noopener">Log in <span class="external-arrow" aria-hidden="true">↗</span></a></li></ul></div>
    <div><h4>Get in touch</h4><ul class="contact"><li>Phone: <a href="tel:1800018999"><strong>1800 018 999</strong></a></li><li>Email: <a href="mailto:pumps@alinepumps.com">pumps@alinepumps.com</a></li><li><a href="{FACEBOOK}" target="_blank" rel="noopener">Follow us on Facebook</a></li><li><a href="{LINKEDIN}" target="_blank" rel="noopener">Follow us on LinkedIn</a></li></ul></div>
  </div>
  <div class="footer-bottom"><div class="wrap"><span>2026 &copy; Aline Australasia Pty Ltd</span><nav aria-label="Legal"><a href="{root}terms-and-conditions/index.html">Terms and Conditions</a><a href="{root}return-of-goods-policy/index.html">Return of Goods Policy</a><a href="{root}privacy-policy/index.html">Privacy Policy</a></nav></div></div>
</footer>'''


def make_search_page() -> None:
    target = SITE / "search/index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('''<!DOCTYPE html><html lang="en-AU"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Search | Aline Pumps</title><meta name="description" content="Search Aline Pumps products, pump systems, projects and articles."><meta name="robots" content="noindex, nofollow"><link rel="canonical" href="https://www.alinepumps.com.au/search/"><link rel="stylesheet" href="../assets/css/site.css"></head><body>
<header class="site-header"></header><main><section class="page-banner archive-banner"><div class="wrap"><span class="eyebrow">Aline Pumps</span><h1>Search</h1><p class="crumbs"><a href="../index.html">Home</a> &nbsp;/&nbsp; Search</p></div></section><section class="section site-search-page" data-root="../"><div class="wrap"><form class="search-page-form" role="search" action="index.html" method="get"><label for="search-page-query">Search products, projects and articles</label><div><input id="search-page-query" type="search" name="q" required autofocus placeholder="What are you looking for?"><button class="btn btn-primary" type="submit">Search</button></div></form><p class="search-status" id="search-status" role="status" aria-live="polite">Enter a search term to begin.</p><div class="search-results" id="search-results"></div></div></section></main><footer class="site-footer"></footer>
<script src="../assets/js/site.js" defer></script><script src="../assets/js/search-index.js" defer></script><script src="../assets/js/search.js" defer></script></body></html>''', encoding="utf-8")


def search_records() -> list[dict[str, str]]:
    records = []
    for path in sorted(SITE.rglob("*.html")):
        if path.name in EXCLUDE or path.relative_to(SITE).as_posix() in EXCLUDE_PATHS or path == SITE / "search/index.html":
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = lhtml.fromstring(raw)
        except (ValueError, lhtml.ParserError):
            continue
        canonical = tree.xpath('string(//link[@rel="canonical"]/@href)')
        if not canonical.startswith("https://www.alinepumps.com.au/"):
            continue
        route = canonical.removeprefix("https://www.alinepumps.com.au/")
        preferred = SITE / route / "index.html" if route else SITE / "index.html"
        if path != preferred:
            continue
        main = tree.xpath("//main")
        if not main:
            continue
        heading = " ".join(main[0].xpath(".//h1[1]//text()")).strip()
        if not heading:
            continue
        relative = path.relative_to(SITE).as_posix()
        if relative.startswith("brands/"):
            kind = "Brand"
        elif relative.startswith("products/"):
            kind = "Product" if len(path.relative_to(SITE).parts) == 4 else "Product range"
        elif relative.startswith("portfolio/"):
            kind = "Project"
        elif relative.startswith("category/") or (len(path.relative_to(SITE).parts) == 2 and relative not in {"about/index.html", "products/index.html", "support-and-service/index.html", "our-projects/index.html", "blog/index.html", "contact-us/index.html"}):
            kind = "Article"
        else:
            kind = "Page"
        description = tree.xpath('string(//meta[@name="description"]/@content)').strip()
        content = re.sub(r"\s+", " ", main[0].text_content()).strip()
        records.append({"title": heading, "type": kind, "description": description[:240], "text": content[:1800], "path": relative})
    return records


def finalise() -> None:
    from enrich_links import enrich
    enrich()
    make_search_page()
    records = search_records()
    (SITE / "assets/js/search-index.js").write_text("window.ALINE_SEARCH_INDEX = " + json.dumps(records, ensure_ascii=True, separators=(",", ":")) + ";\n", encoding="utf-8")
    count = 0
    for path in SITE.rglob("*.html"):
        if path.name in EXCLUDE or path.relative_to(SITE).as_posix() in EXCLUDE_PATHS:
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        raw, h = re.subn(r'<header class="site-header"[^>]*>.*?</header>', header(path), raw, count=1, flags=re.S)
        raw, f = re.subn(r'<footer class="site-footer"[^>]*>.*?</footer>', footer(path), raw, count=1, flags=re.S)
        if h != 1 or f != 1:
            raise ValueError(f"Missing site shell in {path}")
        raw = re.sub(r'<p>\d+ (?:projects|articles) from the current Aline Pumps site\.</p>', '', raw)
        raw = raw.replace("Open the document from the Aline Pumps backup.", "View the product document.")
        raw = raw.replace('<span class="external-note">External site</span> <span aria-hidden="true">&rarr;</span>', '<span class="external-arrow" aria-hidden="true">↗</span>')
        path.write_text(raw, encoding="utf-8")
        count += 1
    print(f"Applied shared header and footer to {count} pages; indexed {len(records)} pages for search.")


if __name__ == "__main__":
    finalise()
