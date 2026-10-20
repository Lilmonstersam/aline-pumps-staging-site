"""Add evidence-based product brands and project/category cross-links."""
from __future__ import annotations

import html
import os
import re
from collections import defaultdict
from pathlib import Path

from lxml import html as lhtml


SITE = Path(__file__).resolve().parents[1]
ORIGIN = "https://www.alinepumps.com.au"
BRANDS = {
    "defender": ("Defender", r"\bdefender\b"),
    "hercules": ("Hercules", r"\bhercules\b"),
    "hydrosmooth": ("HydroSmooth", r"\bhydrosmooth\b"),
    "javelin": ("Javelin", r"\bjavelin\b"),
    "kwikflo": ("Kwikflo", r"\bkwikflo(?:w)?\b"),
    "stormwarden": ("StormWARDEN", r"\bstormwarden\b"),
    "torpedo": ("Torpedo", r"\btorpedo\b"),
}
CATEGORIES = {
    "access-covers": ("Access Covers", r"\baccess covers?\b"),
    "filtration": ("Filtration", r"\bfiltration\b|\bbackwash filters?\b|\bUV disinfection\b"),
    "fire-pumpset-accessories": ("Fire Pumpset Accessories", r"\bfire pump controllers?\b|\bfire pumpset accessories\b"),
    "fire-pumpsets": ("Fire Pumpsets", r"\bfire pumps?(?:ets?| sets?)?\b|\b(?:diesel|electric) (?:sprinkler|hydrant) pumpsets?\b"),
    "general-purpose-pits": ("General Purpose Pits", r"\bgeneral purpose pits?\b"),
    "grease-arrestors": ("Grease Arrestors", r"\bgrease (?:arrestors?|traps?)\b"),
    "hot-water-circulators": ("Hot Water Circulators", r"\bhot water circulat(?:ors?|ion pumps?)\b"),
    "oil-water-separators": ("Oil Water Separators", r"\boil[ -]water separators?\b"),
    "pressure-systems": ("Pressure Systems", r"\bpressure (?:systems?|pumps?|boosters?)\b|\bbooster (?:pumps?|sets?|systems?)\b"),
    "pump-stations": ("Pump Stations", r"\bpump(?:ing)?\s*stations?\b|\bpumpstations?\b|\btank stations?\b"),
    "stormwarden": ("StormWARDEN Backup Power", r"\bstormwarden\b"),
    "submersible-pumps": ("Submersible Pumps", r"\bsubmersible pumps?(?: sets?)?\b"),
    "undersink-pumpstations": ("Undersink Pump Stations", r"\bunder[- ]?sink\b"),
    "water-storage-tanks": ("Water Storage Tanks", r"\b(?:water|rainwater|fire water)\s+(?:storage\s+)?tanks?\b"),
}


def relative_url(from_page: Path, to_page: Path) -> str:
    return os.path.relpath(to_page, from_page.parent).replace(os.sep, "/")


def text_of(node) -> str:
    return re.sub(r"\s+", " ", node.text_content()).strip()


def inner_html(node) -> str:
    return html.escape(node.text or "") + "".join(lhtml.tostring(child, encoding="unicode", method="html", with_tail=True) for child in node)


def project_data():
    projects = {}
    by_category = defaultdict(list)
    for path in sorted((SITE / "portfolio").glob("*/index.html")):
        tree = lhtml.parse(str(path))
        content = tree.xpath('//article[contains(@class,"archive-story")]//div[contains(@class,"archive-rich")]')
        if not content:
            continue
        title = tree.xpath('string(//main//h1)').strip()
        source = title + " " + text_of(content[0])
        tags = []
        scores = {}
        for slug, (_, pattern) in CATEGORIES.items():
            matches = re.findall(pattern, source, flags=re.I)
            if matches:
                tags.append(slug)
                scores[slug] = len(matches) + (3 if re.search(pattern, title, flags=re.I) else 0)
        image = tree.xpath('string(//article[contains(@class,"archive-story")]//figure//img/@src)')
        projects[path.parent.name] = {"path": path, "title": title, "image": image, "tags": tags, "scores": scores}
        for slug in tags:
            by_category[slug].append(projects[path.parent.name])
    for slug, records in by_category.items():
        records.sort(key=lambda item: (-item["scores"][slug], item["title"].lower()))
    return projects, by_category


def project_card(current: Path, item: dict, compact=False) -> str:
    url = relative_url(current, item["path"])
    title = html.escape(item["title"], quote=True)
    image = ""
    if item["image"]:
        source = (item["path"].parent / item["image"]).resolve()
        if source.is_file():
            image = relative_url(current, source)
    if compact:
        visual = f'<img src="{html.escape(image, quote=True)}" alt="" loading="lazy">' if image else '<span class="project-mini-placeholder" aria-hidden="true">Aline Pumps</span>'
        return f'<a class="project-mini-card" href="{html.escape(url, quote=True)}">{visual}<span>{title}</span><small>View project →</small></a>'
    style = f' style="background-image:url(\'{html.escape(image, quote=True)}\')"' if image else ""
    return f'<a class="work" href="{html.escape(url, quote=True)}"{style}><h3>{title}</h3><span>View project</span></a>'


def tag_projects(projects: dict) -> None:
    for item in projects.values():
        path = item["path"]
        raw = path.read_text()
        raw = re.sub(r'<!-- project-product-tags-start -->.*?<!-- project-product-tags-end -->', '', raw, flags=re.S)
        raw = re.sub(r'(<article class="section archive-story")[^>]*>', lambda m: m.group(1) + (f' data-product-categories="{" ".join(item["tags"])}"' if item["tags"] else '') + '>', raw, count=1)
        if item["tags"]:
            links = "".join(f'<a rel="tag" href="{html.escape(relative_url(path, SITE / "products" / slug / "index.html"), quote=True)}">{html.escape(CATEGORIES[slug][0])}</a>' for slug in item["tags"])
            section = f'<!-- project-product-tags-start --><section class="project-product-links" aria-label="Product ranges used in this project"><span class="eyebrow">Products in this project</span><h2>Explore the product ranges</h2><div class="tag-links">{links}</div></section><!-- project-product-tags-end -->'
            raw = raw.replace('</div></article>', section + '</div></article>', 1)
        path.write_text(raw)


def update_category_projects(by_category: dict) -> None:
    paths = list((SITE / "products").glob("*/index.html")) + [SITE / "category-undersink-pumpstations.html"]
    for path in paths:
        slug = "undersink-pumpstations" if path.name == "category-undersink-pumpstations.html" else path.parent.name
        raw = path.read_text().replace('<!-- category-projects-slot -->', '')
        records = by_category.get(slug, [])[:2]
        if records:
            cards = "".join(project_card(path, item) for item in records)
            archive = relative_url(path, SITE / "our-projects/index.html")
            section = f'<section id="projects"><div class="works-head"><div class="wrap"><div class="section-head"><div><span class="eyebrow">Installed by Aline</span><h2>Our Past Projects</h2></div><a class="btn btn-primary" href="{archive}">View projects</a></div></div></div><div class="works two">{cards}</div></section>'
        else:
            section = ""
        raw, count = re.subn(r'<section id="projects">.*?</section>', '<!-- category-projects-slot -->' + section, raw, count=1, flags=re.S)
        if count != 1:
            target = '<section class="section" id="insights">'
            if target not in raw:
                raise ValueError(f"Missing project placement in {path}")
            raw = raw.replace(target, '<!-- category-projects-slot -->' + section + target, 1)
        path.write_text(raw)


def construction_layout(path: Path, raw: str) -> str:
    match = re.search(r'<section class="product-detail-section alt" id="construction".*?</section>', raw, flags=re.S)
    if not match or 'class="product-main generated"' not in raw:
        return raw
    tree = lhtml.fromstring(match.group(0))
    rich = tree.xpath('.//div[contains(@class,"archive-rich")]')
    if not rich:
        return raw
    rich = rich[0]
    bullets = []
    for listing in list(rich.xpath('.//ul[not(ancestor::ul)]')):
        previous = listing.getprevious()
        heading = text_of(previous).lower() if previous is not None and previous.tag in {"h2", "h3", "h4"} else ""
        if any(term in heading for term in ("application", "liquid handled", "suitable fluids")):
            continue
        items = [text_of(node) for node in listing.xpath('.//li[not(.//li)]')]
        items = [item for item in items if item and len(item) <= 180]
        if not items:
            continue
        bullets.extend(items)
        listing.drop_tree()
        if previous is not None and previous.tag in {"h2", "h3", "h4"}:
            previous.drop_tree()
    bullets = list(dict.fromkeys(bullets))
    left = inner_html(rich).strip()
    if not bullets:
        source = re.sub(r'^(?:Specifications|Description|Construction)\s+', '', text_of(rich), flags=re.I)
        sentences = [part.strip() for part in re.split(r'(?<=[.!?])\s+', source) if part.strip()]
        if len(sentences) > 1:
            left = f'<p>{html.escape(sentences[0])}</p>'
            bullets = sentences[1:]
    if not text_of(lhtml.fragment_fromstring(left or "<div></div>", create_parent="div")):
        summary = lhtml.fromstring(raw).xpath('string(//div[@class="product-summary"]/p[not(@class)])')
        left = f'<p>{html.escape(summary)}</p>'
    if bullets:
        aside = '<ul class="construction-list">' + "".join(f'<li>{html.escape(item)}</li>' for item in bullets) + '</ul>'
    else:
        brochure = re.search(r'<a class="btn btn-ghost"[^>]*>(?:Product brochure|Request brochure)</a>', raw)
        action = brochure.group(0) if brochure else ""
        aside = f'<div class="construction-aside"><span class="eyebrow">Technical information</span><h3>Construction details</h3><p>View the product brochure for construction and selection details.</p>{action}</div>'
    section = f'<section class="product-detail-section alt construction-aligned" id="construction" role="tabpanel" aria-labelledby="tab-construction" tabindex="0"><div class="wrap construction-grid"><div><span class="eyebrow">What is supplied</span><h2>Construction</h2><div class="archive-rich">{left}</div></div>{aside}</div></section>'
    return raw[:match.start()] + section + raw[match.end():]


def product_brands(path: Path, raw: str) -> list[str]:
    tree = lhtml.fromstring(raw)
    sources = tree.xpath('//title/text() | //meta[@name="description"]/@content | //section[contains(@class,"product-main")]//img/@alt | //section[contains(@class,"product-main")]//span[contains(@class,"brand")]/text() | //section[@id="construction"]//text()')
    source = " ".join(sources)
    return [slug for slug, (_, pattern) in BRANDS.items() if re.search(pattern, source, flags=re.I)]


def tag_products(by_category: dict) -> dict[str, list[Path]]:
    brand_products = defaultdict(list)
    for path in sorted((SITE / "products").glob("*/*/index.html")):
        if path.parent.name == "round":
            continue
        raw = path.read_text()
        raw = re.sub(r'<!-- product-brand-tags-start -->.*?<!-- product-brand-tags-end -->', '', raw, flags=re.S)
        raw = re.sub(r'<!-- product-projects-start -->.*?<!-- product-projects-end -->', '', raw, flags=re.S)
        raw = re.sub(r'(<section class="product-main(?: generated)?") data-brand-tags="[^"]*"', r'\1', raw, count=1)
        brands = product_brands(path, raw)
        raw = construction_layout(path, raw)
        for slug in brands:
            brand_products[slug].append(path)
        if brands:
            links = "".join(f'<a rel="tag" href="{html.escape(relative_url(path, SITE / "brands" / slug / "index.html"), quote=True)}">{html.escape(BRANDS[slug][0])}</a>' for slug in brands)
            tags = f'<!-- product-brand-tags-start --><div class="product-brand-tags"><span>Brand</span><div class="tag-links">{links}</div></div><!-- product-brand-tags-end -->'
            raw, count = re.subn(r'(<div class="product-summary">.*?<div class="actions">.*?</div>)(\s*</div>)', lambda m: m.group(1) + tags + m.group(2), raw, count=1, flags=re.S)
            if count != 1:
                raise ValueError(f"Missing product summary in {path}")
        attrs = f' data-brand-tags="{" ".join(brands)}"' if brands else ''
        raw = re.sub(r'<section class="product-main(?: generated)?"', lambda m: m.group(0) + attrs, raw, count=1)
        category = path.parent.parent.name
        records = by_category.get(category, [])[:6]
        if records:
            cards = "".join(project_card(path, item, compact=True) for item in records)
            carousel = f'<!-- product-projects-start --><div class="related-project-carousel"><div class="project-carousel-head"><div><span class="eyebrow">See it in practice</span><h3>Related projects</h3></div><div class="project-carousel-controls"><button type="button" data-scroll="-1" aria-label="Scroll projects left">←</button><button type="button" data-scroll="1" aria-label="Scroll projects right">→</button></div></div><div class="project-carousel-track" tabindex="0" aria-label="Projects using this product range">{cards}</div></div><!-- product-projects-end -->'
            raw, count = re.subn(r'(<section class="product-detail-section" id="applications".*?)(</div>\s*</section>)', lambda m: m.group(1) + carousel + m.group(2), raw, count=1, flags=re.S)
            if count != 1:
                raise ValueError(f"Missing applications panel in {path}")
        path.write_text(raw)
    return brand_products


def build_brand_archives(brand_products: dict[str, list[Path]]) -> None:
    for slug, products in brand_products.items():
        current = SITE / "brands" / slug / "index.html"
        current.parent.mkdir(parents=True, exist_ok=True)
        name = BRANDS[slug][0]
        cards = []
        for path in products:
            tree = lhtml.parse(str(path))
            title = tree.xpath('string(//h1[@id="product-title"])').strip()
            image = tree.xpath('string(//div[contains(@class,"product-gallery")]//div[contains(@class,"main-image")]//img/@src)')
            source = (path.parent / image).resolve() if image else None
            visual = f'<img src="{html.escape(relative_url(current,source),quote=True)}" alt="{html.escape(title,quote=True)}" loading="lazy">' if source and source.is_file() else ""
            category = path.parent.parent.name.replace("-", " ").title()
            cards.append(f'<a class="product-card" href="{html.escape(relative_url(current,path),quote=True)}"><div class="thumb">{visual}</div><div class="body"><span class="cat">{html.escape(category)}</span><h3>{html.escape(title)}</h3><span class="link-arrow">View product</span></div></a>')
        count_label = f'{len(products)} product' + ('s' if len(products) != 1 else '')
        body = f'<section class="page-banner archive-banner"><div class="wrap"><span class="eyebrow">Product brands</span><h1>{html.escape(name)}</h1><p class="crumbs"><a href="../../index.html">Home</a> &nbsp;/&nbsp; <a href="../../products.html">Products</a> &nbsp;/&nbsp; {html.escape(name)}</p></div></section><section class="section brand-archive"><div class="wrap"><div class="section-head"><div><span class="eyebrow">Browse by brand</span><h2>{html.escape(name)} products</h2></div><p>{count_label}</p></div><div class="products-grid">{"".join(cards)}</div></div></section>'
        page = f'<!DOCTYPE html><html lang="en-AU"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(name)} products | Aline Pumps</title><meta name="description" content="Browse {html.escape(name,quote=True)} products from Aline Pumps."><meta name="robots" content="noindex, nofollow"><link rel="canonical" href="{ORIGIN}/brands/{slug}/"><link rel="stylesheet" href="../../assets/css/site.css"></head><body><header class="site-header"></header><main>{body}</main><footer class="site-footer"></footer><script src="../../assets/js/site.js" defer></script></body></html>'
        current.write_text(page)


def link_hub_brands(brand_products: dict[str, list[Path]]) -> None:
    for path in (SITE / "products.html", SITE / "products/index.html"):
        raw = path.read_text()
        def replace(match):
            image = match.group(1)
            alt = html.unescape(re.search(r'alt="([^"]+)"', image).group(1)).lower()
            slug = next((key for key in brand_products if key in alt), None)
            href = html.escape(relative_url(path, SITE / "brands" / slug / "index.html"), quote=True) if slug else ""
            return f'<a class="cell" href="{href}" aria-label="Browse {html.escape(BRANDS[slug][0],quote=True)} products">{image}</a>' if slug else f'<div class="cell">{image}</div>'
        raw = re.sub(r'<(?:div|a) class="cell"(?: [^>]*)?>(<img [^>]+>)</(?:div|a)>', replace, raw)
        path.write_text(raw)


def enrich() -> None:
    projects, by_category = project_data()
    tag_projects(projects)
    update_category_projects(by_category)
    brands = tag_products(by_category)
    build_brand_archives(brands)
    link_hub_brands(brands)
    print(f"Tagged {sum(bool(p['tags']) for p in projects.values())} projects and {sum(map(len, brands.values()))} product-brand relationships; built {len(brands)} brand archives.")


if __name__ == "__main__":
    enrich()
