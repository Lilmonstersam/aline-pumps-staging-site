"""Build the static migration mockup from the supplied WordPress backup.

Run from anywhere with Python 3 and lxml installed. The SQL backup is read only;
generated HTML and selected image assets are written under staging-site.
"""
from __future__ import annotations

import csv
import html
import os
import re
import shutil
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse, quote

from lxml import html as lhtml


SITE = Path(__file__).resolve().parents[1]
PROJECT = SITE.parents[2]
BACKUP = next((PROJECT / "seo/mockups/current-site-backup").glob("site-archive-*/"))
SQL = BACKUP / "wp-content/mysql.sql"
INVENTORY = PROJECT / "seo/strategies/pre-migration-2026-10-13/indexable_url_inventory.csv"
ORIGIN = "https://www.alinepumps.com.au"


def sql_rows(line: str):
    """Parse a mysqldump INSERT row, including MySQL backslash escapes."""
    rows, row, field = [], [], []
    quoted = escaping = active = string = False
    for ch in line[line.index(" VALUES ") + 8 :].rstrip(" ;\n"):
        if not active:
            if ch == "(":
                active, row, field, string = True, [], [], False
            continue
        if quoted:
            if escaping:
                field.append({"0": "\0", "n": "\n", "r": "\r", "t": "\t", "b": "\b", "Z": "\x1a"}.get(ch, ch))
                escaping = False
            elif ch == "\\":
                escaping = True
            elif ch == "'":
                quoted = False
            else:
                field.append(ch)
        elif ch == "'":
            quoted, string = True, True
        elif ch in ",)":
            value = "".join(field)
            row.append(value if string else (None if value == "NULL" else value))
            field, string = [], False
            if ch == ")":
                rows.append(row)
                active = False
        else:
            field.append(ch)
    return rows


tables = {key: [] for key in ("posts", "postmeta", "terms", "term_taxonomy", "term_relationships", "termmeta")}
for line in SQL.open(errors="replace"):
    for table in tables:
        if line.startswith(f"INSERT INTO `wp_{table}`"):
            tables[table].extend(sql_rows(line))

posts = {int(row[0]): row for row in tables["posts"]}
terms = {int(row[0]): row for row in tables["terms"]}
taxonomy = {int(row[0]): row for row in tables["term_taxonomy"]}
postmeta = defaultdict(dict)
for row in tables["postmeta"]:
    if row[2] in {"_thumbnail_id", "_wp_attached_file", "_yoast_wpseo_title", "_yoast_wpseo_metadesc", "_product_image_gallery", "product_broucher", "product_drawing", "product_short_description", "product_code", "product_features"} or re.match(r"^product_specification_\d+_specification_(title|value[1-5])$", row[2]):
        postmeta[int(row[1])][row[2]] = row[3]
termmeta = defaultdict(dict)
for row in tables["termmeta"]:
    if not row[2].startswith("_"):
        termmeta[int(row[1])][row[2]] = row[3]
relations = defaultdict(lambda: defaultdict(list))
for post_id, taxonomy_id, _ in tables["term_relationships"]:
    tax = taxonomy.get(int(taxonomy_id))
    if tax:
        term = terms[int(tax[1])]
        relations[int(post_id)][tax[2]].append(term[2])

with INVENTORY.open(newline="") as file:
    inventory = list(csv.DictReader(file))
inventory_title = {urlparse(row["old_url"]).path: row["title"] for row in inventory}

category_terms = {row[2]: row for row in terms.values() if any(t[2] == "product_cat" and int(t[1]) == int(row[0]) for t in taxonomy.values()) and row[2] != "uncategorized"}
category_ids = {row[2]: int(row[0]) for row in category_terms.values()}
product_posts = sorted((p for p in posts.values() if p[20] == "product" and p[7] == "publish" and p[11] != "round"), key=lambda p: int(p[0]))
project_posts = sorted((p for p in posts.values() if p[20] == "portfolio" and p[7] == "publish"), key=lambda p: p[5].lower())
article_posts = sorted((p for p in posts.values() if p[20] == "post" and p[7] == "publish"), key=lambda p: p[2], reverse=True)
product_category = {int(p[0]): relations[int(p[0])]["product_cat"][0] for p in product_posts}
product_path = {p[11]: f"products/{product_category[int(p[0])]}/{p[11]}/index.html" for p in product_posts}
category_path = {slug: f"products/{slug}/index.html" for slug in category_terms}
article_path = {p[11]: f"{p[11]}/index.html" for p in article_posts}
project_path = {p[11]: f"portfolio/{p[11]}/index.html" for p in project_posts}
extra_pages = {p[11]: p for p in posts.values() if p[20] == "page" and p[7] == "publish" and p[11] in {"terms-and-conditions", "return-of-goods-policy", "privacy-policy", "metal-water-tanks", "plumbing-supplies"}}
blog_category_slugs = sorted({urlparse(row["old_url"]).path.split("/")[2] for row in inventory if urlparse(row["old_url"]).path.startswith("/category/") and len(urlparse(row["old_url"]).path.split("/")) > 2})
blog_category_names = {row[2]: html.unescape(row[1]) for row in terms.values() if any(t[2] == "category" and int(t[1]) == int(row[0]) for t in taxonomy.values())}

known_paths = {
    "/": "index.html", "/about/": "about.html", "/products/": "products.html",
    "/support-and-service/": "support-and-service.html",
    "/support-and-service/aline-service/": "aline-service.html",
    "/support-and-service/training/": "training.html",
    "/training/": "training.html", "/services/": "support-and-service.html",
    "/our-projects/": "our-projects/index.html", "/blog/": "blog/index.html",
    "/contact-us/": "contact-us/index.html", "/meet-the-team/": "about.html",
}
for slug, path in category_path.items():
    known_paths[f"/products/{slug}/"] = path
    known_paths[f"/product-category/{slug}/"] = path
for slug, path in product_path.items():
    known_paths[f"/product/{slug}/"] = path
    known_paths["/" + path.removesuffix("index.html")] = path
known_paths["/product/round/"] = product_path["round-water-storage-tank"]
known_paths["/products/water-storage-tanks/round/"] = product_path["round-water-storage-tank"]
for slug, path in article_path.items():
    known_paths[f"/{slug}/"] = path
for slug, path in project_path.items():
    known_paths[f"/portfolio/{slug}/"] = path
for slug in extra_pages:
    known_paths[f"/{slug}/"] = f"{slug}/index.html"
for slug in blog_category_slugs:
    known_paths[f"/category/{slug}/"] = f"category/{slug}/index.html"
for page in range(2, 6):
    known_paths[f"/blog/page/{page}/"] = f"blog/page/{page}/index.html"
for slug in ("aline-news", "aline-pumps"):
    known_paths[f"/category/{slug}/page/2/"] = f"category/{slug}/page/2/index.html"
known_paths["/authors/"] = "authors/index.html"
known_paths["/authors/harland-mackenzie/"] = "authors/harland-mackenzie/index.html"
for slug in ("commercial", "government", "residential"):
    known_paths[f"/portfolio_categories/{slug}/"] = f"portfolio_categories/{slug}/index.html"


def local_link(target: str, current: str):
    """Keep the static file preview navigable while retaining clean canonicals."""
    target = html.unescape(target or "")
    parsed = urlparse(target)
    if parsed.scheme in {"tel", "mailto"} or target.startswith("#"):
        return target
    if parsed.netloc and parsed.netloc not in {"www.alinepumps.com.au", "alinepumps.com.au"}:
        return target
    path = parsed.path or "/"
    if not path.endswith("/") and "." not in path.rsplit("/", 1)[-1]:
        path += "/"
    resolved = known_paths.get(path)
    if resolved:
        relative = os.path.relpath(SITE / resolved, (SITE / current).parent).replace(os.sep, "/")
        return relative + ("?" + parsed.query if parsed.query else "") + ("#" + parsed.fragment if parsed.fragment else "")
    if parsed.netloc or path.startswith("/"):
        return ORIGIN + path + ("?" + parsed.query if parsed.query else "") + ("#" + parsed.fragment if parsed.fragment else "")
    return target


copied_media = {}


def copy_media(upload_path: str):
    upload_path = html.unescape(upload_path).replace("\\/", "/")
    upload_path = upload_path.split("?", 1)[0]
    marker = "/wp-content/uploads/"
    if marker in upload_path:
        upload_path = upload_path.split(marker, 1)[1]
    source = BACKUP / "wp-content/uploads" / upload_path.lstrip("/")
    if not source.is_file():
        webp = Path(str(source) + ".webp")
        if webp.is_file():
            source = webp
        else:
            return None
    if source in copied_media:
        return copied_media[source]
    key = re.sub(r"[^A-Za-z0-9._-]", "-", str(source.relative_to(BACKUP / "wp-content/uploads")))
    dest = SITE / "assets/media" / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    copied_media[source] = "assets/media/" + key
    return copied_media[source]


def attachment_media(attachment_id):
    try:
        source = postmeta[int(attachment_id)].get("_wp_attached_file")
    except (TypeError, ValueError):
        return None
    return copy_media(source) if source else None


def media_url(media: str | None, current: str):
    return os.path.relpath(SITE / media, (SITE / current).parent).replace(os.sep, "/") if media else ""


ALLOWED = {"p", "h2", "h3", "h4", "ul", "ol", "li", "strong", "em", "b", "i", "a", "img", "blockquote", "table", "thead", "tbody", "tr", "th", "td", "br", "figure", "figcaption", "sup", "sub"}
DROP = {"script", "style", "iframe", "form", "input", "button", "select", "textarea", "noscript"}


def clean_markup(raw: str, current: str):
    if not raw:
        return ""
    raw = raw.replace("Â–", "–").replace("Â’s", "’").replace("Â ", " ")
    try:
        root = lhtml.fragment_fromstring(raw, create_parent="div")
    except (ValueError, lhtml.ParserError):
        return "<p>" + html.escape(raw) + "</p>"

    def render(node):
        tag = node.tag.lower() if isinstance(node.tag, str) else ""
        if tag in DROP:
            return ""
        inner = html.escape(node.text or "")
        for child in node:
            inner += render(child) + html.escape(child.tail or "")
        if tag == "div":
            return "<p>" + inner + "</p>" if inner.strip() else ""
        if tag not in ALLOWED:
            return inner
        if tag == "a":
            href = node.get("href", "")
            if href.lower().startswith(("javascript:", "data:")):
                return inner
            return f'<a href="{html.escape(local_link(href, current), quote=True)}">{inner}</a>'
        if tag == "img":
            src = copy_media(node.get("src", ""))
            if not src:
                return ""
            alt = html.escape(node.get("alt", ""), quote=True)
            return f'<img src="{html.escape(media_url(src, current), quote=True)}" alt="{alt}" loading="lazy">'
        if tag == "br":
            return "<br>"
        return f"<{tag}>{inner}</{tag}>"

    return (html.escape(root.text or "") + "".join(render(child) + html.escape(child.tail or "") for child in root)).strip()


def plain(raw: str):
    if not raw:
        return ""
    try:
        return re.sub(r"\s+", " ", lhtml.fromstring("<div>" + raw + "</div>").text_content()).strip()
    except Exception:
        return re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", " ", raw))).strip()


def excerpt(post, limit=210):
    copy = plain(post[6] or post[4])
    return copy if len(copy) <= limit else copy[:limit].rsplit(" ", 1)[0] + "…"


def title(post):
    return html.unescape(post[5]).strip()


def e(value):
    return html.escape(str(value or ""), quote=True)


def header(current: str, active: str):
    nav = [("About", "about.html", "about"), ("Products", "products.html", "products"), ("Support and Service", "support-and-service.html", "support"), ("Projects", "our-projects/index.html", "projects"), ("News &amp; Insights", "blog/index.html", "blog")]
    links = "".join(f'<li><a {"aria-current=\"page\" class=\"active\"" if active == section else ""} href="{e(os.path.relpath(SITE / dest, (SITE / current).parent).replace(os.sep, "/"))}">{label}</a></li>' for label, dest, section in nav)
    home = local_link("/", current)
    contact = local_link("/contact-us/", current)
    logo = media_url("assets/logos/aline-pumps-logo.webp", current)
    return f'''<header class="site-header"><div class="topbar"><div class="wrap"><a class="logo" href="{e(home)}" aria-label="Aline Pumps home"><img src="{e(logo)}" alt="Aline Pumps" width="134" height="46"></a><a class="call" href="tel:1800018999">Call us <strong>1800 018 999</strong></a><div class="social"><a href="https://www.linkedin.com/company/aline-pumps/" aria-label="Aline Pumps on LinkedIn" target="_blank" rel="noopener">in</a></div></div></div><nav class="navbar" aria-label="Main"><div class="wrap"><ul class="menu" id="primary-menu">{links}</ul><button class="menu-toggle" type="button" aria-controls="primary-menu" aria-expanded="false" aria-label="Open menu">Menu</button><div class="nav-actions"><a class="btn btn-primary" href="{e(contact)}">Contact us</a></div></div></nav></header>'''


def footer(current: str):
    items = [("About", "/about/"), ("Products", "/products/"), ("Support and Service", "/support-and-service/"), ("Projects", "/our-projects/"), ("News &amp; Insights", "/blog/"), ("Contact us", "/contact-us/")]
    links = "".join(f'<li><a href="{e(local_link(path, current))}">{label}</a></li>' for label, path in items)
    legal = "".join(f'<a href="{e(local_link("/"+slug+"/", current))}">{label}</a>' for label, slug in (("Terms and Conditions", "terms-and-conditions"), ("Return of Goods Policy", "return-of-goods-policy"), ("Privacy Policy", "privacy-policy")))
    return f'''<footer class="site-footer"><div class="wrap cols"><div><img class="flogo" src="{e(media_url("assets/logos/aline-pumps-logo.webp", current))}" alt="Aline Pumps"><p>100% Australian owned and operated. Pump and water system design, supply and lifecycle support.</p></div><div><h4>Explore</h4><ul>{links}</ul></div><div><h4>Talk to our team</h4><ul class="contact"><li><a href="tel:1800018999">1800 018 999</a></li><li><a href="{e(local_link('/contact-us/', current))}">Send an enquiry</a></li></ul></div></div><div class="footer-bottom"><div class="wrap"><span>2026 &copy; Aline Australasia Pty Ltd</span><nav aria-label="Legal">{legal}</nav></div></div></footer>'''


def document(current: str, page_title: str, description: str, active: str, content: str, canonical: str, extra_script: str = ""):
    css = media_url("assets/css/site.css", current)
    js = media_url("assets/js/site.js", current)
    return f'''<!DOCTYPE html><html lang="en-AU"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{e(page_title)}</title><meta name="description" content="{e(description[:160])}"><meta name="robots" content="noindex, nofollow"><link rel="canonical" href="{e(ORIGIN + canonical)}"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700&family=Open+Sans:wght@400;600&display=swap" rel="stylesheet"><link rel="stylesheet" href="{e(css)}"></head><body>{header(current, active)}<main>{content}</main>{footer(current)}<script src="{e(js)}" defer></script>{extra_script}</body></html>'''


def write(current: str, markup: str):
    path = SITE / current
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markup, encoding="utf-8")


def banner(current: str, heading: str, parent: str, parent_path: str):
    return f'''<section class="page-banner archive-banner"><div class="wrap"><span class="eyebrow">{e(parent)}</span><h1>{e(heading)}</h1><p class="crumbs"><a href="{e(local_link('/',current))}">Home</a> &nbsp;/&nbsp; <a href="{e(local_link(parent_path,current))}">{e(parent)}</a> &nbsp;/&nbsp; {e(heading)}</p></div></section>'''


def cta(current: str, topic: str, heading="Discuss your requirements"):
    contact = local_link("/contact-us/", current) + "?topic=" + quote(topic) + "&message=" + quote(f"Enquiry about {topic.lower()}")
    return f'''<section class="cta on-dark"><div class="wrap"><div><span class="eyebrow">Talk to Aline Pumps</span><h2>{e(heading)}</h2><p>Send your requirements to our team, or call <a href="tel:1800018999">1800 018 999</a>.</p></div><div class="actions"><a class="btn btn-primary" href="{e(contact)}">Send an enquiry <span aria-hidden="true">&rarr;</span></a></div></div></section>'''


def card(current: str, dest: str, image: str | None, heading: str, summary: str, kind: str = "Explore", meta: str = ""):
    pic = f'<img src="{e(media_url(image,current))}" alt="" loading="lazy">' if image else '<span class="archive-card-placeholder" aria-hidden="true">Aline Pumps</span>'
    return f'''<article class="archive-card"><a href="{e(local_link(dest,current))}" class="archive-card-media">{pic}</a><div class="archive-card-body">{meta}<h3><a href="{e(local_link(dest,current))}">{e(heading)}</a></h3><p>{e(summary)}</p><a class="link-arrow" href="{e(local_link(dest,current))}">{e(kind)}</a></div></article>'''


def featured(post):
    return attachment_media(postmeta[int(post[0])].get("_thumbnail_id"))


def related_records(records, slug, limit):
    tokens = [part.rstrip("s") for part in slug.split("-") if len(part) > 3]
    def rank(post):
        heading = title(post).lower()
        body = plain(post[4]).lower()
        return sum((4 if word in heading else 0) + (1 if word in body else 0) for word in tokens)
    return sorted(records, key=rank, reverse=True)[:limit]


def application_items(raw):
    if not raw:
        return []
    try:
        root = lhtml.fragment_fromstring(raw, create_parent="div")
        return [plain(item.text_content()) for item in root.xpath(".//li") if plain(item.text_content())]
    except (ValueError, lhtml.ParserError):
        return []


def split_intro(markup):
    root = lhtml.fragment_fromstring(markup or "", create_parent="div")
    pieces = []
    if root.text and root.text.strip():
        pieces.append(f"<p>{e(root.text.strip())}</p>")
    for child in root:
        pieces.append(lhtml.tostring(child, encoding="unicode", method="html", with_tail=False))
        if child.tail and child.tail.strip():
            pieces.append(f"<p>{e(child.tail.strip())}</p>")
    return (pieces[0] if pieces else "", "".join(pieces[1:]))


def product_card(current, post, category_name):
    image = featured(post)
    visual = f'<img src="{e(media_url(image,current))}" alt="{e(title(post))}" loading="lazy">' if image else ""
    return f'''<a class="product-card" href="{e(local_link('/product/'+post[11]+'/',current))}"><div class="thumb">{visual}</div><div class="body"><span class="cat">{e(category_name)}</span><h3>{e(title(post))}</h3><span class="link-arrow">View product</span></div></a>'''


def product_copy_sections(raw):
    """Pick the product's own lead and applications from its backed-up copy."""
    if not raw:
        return "", []
    try:
        root = lhtml.fragment_fromstring(raw, create_parent="div")
    except (ValueError, lhtml.ParserError):
        return "", []
    paragraphs = [plain(node.text_content()) for node in root.xpath(".//p")]
    lead = next((p for p in paragraphs if len(p) >= 35 and "lorem ipsum" not in p.lower()), "")
    description_heading = next((node for node in root.xpath(".//h2 | .//h3 | .//h4") if plain(node.text_content()).lower() == "description"), None)
    if description_heading is not None and description_heading.tail and len(plain(description_heading.tail)) >= 25:
        lead = plain(description_heading.tail)
    applications = []
    for heading in root.xpath(".//h2 | .//h3 | .//h4"):
        if "application" not in plain(heading.text_content()).lower():
            continue
        for sibling in heading.itersiblings():
            if sibling.tag in {"h2", "h3", "h4"}:
                break
            applications.extend(plain(li.text_content()) for li in sibling.xpath(".//li | self::li"))
        if applications:
            break
    return lead, list(dict.fromkeys(item for item in applications if item))[:8]


def build_category(slug, term):
    current = category_path[slug]
    tid = category_ids[slug]
    meta = termmeta[tid]
    display = html.unescape(term[1]).strip()
    desc = clean_markup(meta.get("product_category_desc", ""), current)
    intro_lead, intro_more = split_intro(desc)
    app_desc = clean_markup(meta.get("common_applications_desc", ""), current)
    app_items = application_items(meta.get("common_applications_list", ""))
    banner_img = attachment_media(meta.get("product_category_banner") or meta.get("thumbnail_id"))
    content_img = attachment_media(meta.get("product_category_content_image"))
    members = [p for p in product_posts if product_category[int(p[0])] == slug]
    cards = "".join(product_card(current, p, display) for p in members)
    side = "".join(f'<li><a {"class=\"current\" aria-current=\"page\"" if s == slug else ""} href="{e(local_link("/products/"+s+"/",current))}"><span>{e(html.unescape(t[1]))}</span><span class="count">{sum(product_category[int(p[0])] == s for p in product_posts)}</span></a></li>' for s,t in sorted(category_terms.items(), key=lambda x:x[1][1]))
    faqs = []
    for i in range(12):
        q, a = meta.get(f"faq_section_{i}_faq_question"), meta.get(f"faq_section_{i}_faq_answer")
        if q and a:
            faqs.append(f'<details {"open" if not faqs else ""}><summary>{e(plain(q))}</summary><div class="answer">{clean_markup(a,current)}</div></details>')
    image = f'<figure class="cat-figure generated"><img src="{e(media_url(content_img,current))}" alt="{e(display)}" loading="lazy"></figure>' if content_img else ""
    contact = local_link('/contact-us/',current)+'?topic=Product%20selection&category='+slug+'&message='+quote('Product advice requested for '+display)
    banner_style = f' style="background-image:linear-gradient(rgba(38,55,69,.86),rgba(38,55,69,.86)),url(\'{e(media_url(banner_img,current))}\')"' if banner_img else ""
    hero = f'''<section class="page-banner cat-banner"{banner_style}><div class="wrap"><span class="brand-kicker">Aline Pumps</span><h1>{e(display)}</h1><p class="crumbs"><a href="{e(local_link('/',current))}">Home</a> &nbsp;/&nbsp; <a href="{e(local_link('/products/',current))}">Products</a> &nbsp;/&nbsp; {e(display)}</p></div></section>'''
    intro = f'''<section class="section cat-intro" id="overview"><div class="wrap"><div><span class="eyebrow">Overview</span><h2>{e(display)}</h2><div class="archive-rich">{intro_lead}</div>{f'<details><summary>Read more</summary><div class="archive-rich">{intro_more}</div></details>' if intro_more else ''}<a class="btn btn-primary" href="{e(contact)}">Ask for product advice <span aria-hidden="true">&rarr;</span></a></div>{image}</div></section>'''
    products = f'''<section class="section range" id="range"><div class="wrap"><aside class="range-nav" aria-label="Product categories"><h3>Our Range</h3><ul>{side}</ul><div class="bluebook"><h4>Aline Blue Book</h4><p>Specifications, drawings and selection data for the Aline range.</p><a class="btn btn-primary" href="{e(local_link('/2023-blue-book/',current))}">View the Blue Book</a></div></aside><div><div class="range-head"><div><span class="eyebrow">Our range</span><h2>{e(display)}</h2></div><p>{len(members)} products</p></div><div class="products-grid">{cards}</div></div></div></section>'''
    ticks = ''.join(f'<div class="app"><span class="tick"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9.5 16.2 5.3 12l-1.4 1.4 5.6 5.6L20.1 8.4 18.7 7z"/></svg></span>{e(item)}</div>' for item in app_items)
    applications = f'''<section class="section apps" id="applications"><div class="wrap"><div><span class="eyebrow">Where they are used</span><h2>Common Applications</h2><div class="archive-rich">{app_desc}</div></div><div class="app-grid">{ticks}</div></div></section>'''
    projects = related_records([p for p in project_posts if featured(p)], slug, 2)
    project_cards = ''.join(f'<a class="work" href="{e(local_link("/portfolio/"+p[11]+"/",current))}" style="background-image:url(\'{e(media_url(featured(p),current))}\')"><h3>{e(title(p))}</h3><span>Project</span></a>' for p in projects)
    project_section = f'''<section id="projects"><div class="works-head"><div class="wrap"><div class="section-head"><div><span class="eyebrow">Aline Pumps projects</span><h2>Our Past Projects</h2></div><a class="btn btn-primary" href="{e(local_link('/our-projects/',current))}">View projects</a></div></div></div><div class="works two">{project_cards}</div></section>'''
    articles = related_records(article_posts, slug, 6)
    article_cards = ''.join(f'<article class="post"><a class="thumb" href="{e(local_link("/"+p[11]+"/",current))}">{f"<img src={chr(34)}{e(media_url(featured(p),current))}{chr(34)} alt={chr(34)}{e(title(p))}{chr(34)} loading={chr(34)}lazy{chr(34)}>" if featured(p) else ""}</a><div class="body"><h3><a href="{e(local_link("/"+p[11]+"/",current))}">{e(title(p))}</a></h3><p>{e(excerpt(p,150))}</p><a class="link-arrow" href="{e(local_link("/"+p[11]+"/",current))}">Read article</a></div></article>' for p in articles)
    insights = f'''<section class="section" id="insights"><div class="wrap"><div class="section-head"><div><span class="eyebrow">News and insights</span><h2>You Might Want to Know</h2></div><a class="link-arrow" href="{e(local_link('/blog/',current))}">View all articles</a></div><div class="posts-grid">{article_cards}</div></div></section>'''
    faq = f'''<section class="section faq" id="faq"><div class="wrap"><div class="faq-panel on-dark"><span class="eyebrow">Speak to our team</span><h2>Have More Questions?</h2><p>Ask our team to confirm the right fit for your application.</p><a class="btn btn-primary" href="{e(contact)}">Ask for product advice <span aria-hidden="true">&rarr;</span></a></div><div><span class="eyebrow">FAQ</span><h2>Frequently Asked Questions</h2><div class="accordion">{"".join(faqs)}</div></div></div></section>'''
    bottom = f'''<section class="cta on-dark" id="contact"><div class="wrap"><div><span class="eyebrow">Talk to our team</span><h2>Need help specifying {e(display)}?</h2><p>Send your application requirements to Aline Pumps or call <a href="tel:1800018999">1800 018 999</a>.</p></div><div class="actions"><a class="btn btn-primary" href="{e(contact)}">Ask for product advice <span aria-hidden="true">&rarr;</span></a></div></div></section>'''
    body = hero + intro + products + applications + project_section + insights + faq + bottom
    seo = inventory_title.get(f"/product-category/{slug}/", f"{display} | Aline Pumps")
    write(current, document(current, seo, plain(meta.get("product_category_desc", "")), "products", body, f"/products/{slug}/"))


def build_product(post):
    pid, slug = int(post[0]), post[11]
    current = product_path[slug]
    category = product_category[pid]
    category_name = html.unescape(category_terms[category][1])
    meta = postmeta[pid]
    short = meta.get("product_short_description", "")
    source_lead, source_applications = product_copy_sections(post[4])
    short_plain = plain(short)
    summary = short_plain if short_plain and "lorem ipsum" not in short_plain.lower() and not short_plain.upper().startswith("DESCRIPTION ") else (source_lead or excerpt(post, 280))
    if len(summary) > 280:
        summary = summary[:277].rsplit(" ", 1)[0] + "…"
    detail = clean_markup(post[4], current) or f"<p>{e(summary)}</p>"
    image_ids = [meta.get("_thumbnail_id")] + [part.strip() for part in (meta.get("_product_image_gallery") or "").split(",")]
    gallery_media = list(dict.fromkeys(media for media in (attachment_media(image_id) for image_id in image_ids if image_id) if media))
    primary = gallery_media[0] if gallery_media else featured(post)
    main_image = f'<img src="{e(media_url(primary,current))}" alt="{e(title(post))}" loading="eager">' if primary else '<span>Product image unavailable</span>'
    thumbnails = ''.join(f'<button type="button" aria-label="Show {e(title(post))} image {i+1}" aria-pressed="{str(i==0).lower()}" data-image="{e(media_url(media,current))}" data-alt="{e(title(post))} image {i+1}"><img src="{e(media_url(media,current))}" alt="" loading="lazy"></button>' for i, media in enumerate(gallery_media))
    spec_data = []
    for index in range(30):
        label = plain(meta.get(f"product_specification_{index}_specification_title", ""))
        values = [plain(meta.get(f"product_specification_{index}_specification_value{part}", "")) for part in range(1, 6)]
        values = [value for value in values if value]
        if label and values:
            spec_data.append((label, " / ".join(values)))
    spec_rows = f'<tr><th scope="row">Model</th><td>{e(title(post))}</td></tr><tr><th scope="row">Range</th><td>{e(category_name)}</td></tr>'
    if meta.get("product_code"):
        spec_rows += f'<tr><th scope="row">Product code</th><td>{e(meta["product_code"])}</td></tr>'
    spec_rows += ''.join(f'<tr><th scope="row">{e(label)}</th><td>{e(value)}</td></tr>' for label, value in spec_data)
    highlights = [(label, value) for label, value in spec_data if value.upper() != "N/A" and len(value) <= 32][:3]
    highlight_markup = f'<ul class="product-highlights" aria-label="Key specifications">{"".join(f"<li><strong>{e(value)}</strong><span>{e(label)}</span></li>" for label,value in highlights)}</ul>' if highlights else ""
    contact = local_link("/contact-us/", current) + f"?topic=Product%20quote&model={quote(slug)}&message={quote('Quote request for ' + title(post) + ' (model: ' + slug + ')')}"
    brochure_media = attachment_media(meta.get("product_broucher")) if meta.get("product_broucher") else None
    brochure_request = local_link("/contact-us/", current) + f"?topic=Product%20brochure&model={quote(slug)}&message={quote('Please send the product brochure for ' + title(post) + ' (model: ' + slug + ')')}"
    brochure_action = (f'<a class="btn btn-ghost" href="{e(media_url(brochure_media,current))}" target="_blank" rel="noopener">Product brochure</a>' if brochure_media else f'<a class="btn btn-ghost" href="{e(brochure_request)}">Request brochure</a>')
    crumb = f'''<nav class="product-crumbs" aria-label="Breadcrumb"><div class="wrap"><a href="{e(local_link('/',current))}">Home</a> &nbsp;/&nbsp; <a href="{e(local_link('/products/',current))}">Products</a> &nbsp;/&nbsp; <a href="{e(local_link('/products/'+category+'/',current))}">{e(category_name)}</a> &nbsp;/&nbsp; {e(title(post))}</div></nav>'''
    model = f'<p class="model">{e(meta["product_code"])}</p>' if meta.get("product_code") else ""
    hero = f'''<section class="product-main generated" aria-labelledby="product-title"><div class="wrap"><div class="product-gallery" role="group" aria-label="{e(title(post))} product images"><div class="main-image">{main_image}</div><div class="thumbs">{thumbnails}</div></div><div class="product-summary"><span class="brand">{e(category_name)}</span><h1 id="product-title">{e(title(post))}</h1>{model}<p>{e(summary)}</p>{highlight_markup}<div class="actions"><a class="btn btn-primary" href="{e(contact)}">Request a quote <span aria-hidden="true">&rarr;</span></a>{brochure_action}</div></div></div></section>'''
    tabs = '''<div class="product-tabs"><div class="wrap" role="tablist" aria-label="Product details"><button type="button" id="tab-specs" role="tab" aria-controls="specs" aria-selected="true" tabindex="0">Specs</button><button type="button" id="tab-construction" role="tab" aria-controls="construction" aria-selected="false" tabindex="-1">Construction</button><button type="button" id="tab-applications" role="tab" aria-controls="applications" aria-selected="false" tabindex="-1">Applications</button><button type="button" id="tab-downloads" role="tab" aria-controls="downloads" aria-selected="false" tabindex="-1">Downloads</button></div></div>'''
    specs = f'''<section class="product-detail-section" id="specs" role="tabpanel" aria-labelledby="tab-specs" tabindex="0"><div class="wrap"><div class="section-head"><div><span class="eyebrow">Product details</span><h2>Specifications</h2></div></div><table class="spec-table"><tbody>{spec_rows}</tbody></table></div></section>'''
    construction = f'''<section class="product-detail-section alt" id="construction" role="tabpanel" aria-labelledby="tab-construction" tabindex="0"><div class="wrap construction-grid"><div><span class="eyebrow">Product information</span><h2>Construction</h2><div class="archive-rich">{detail}</div></div></div></section>'''
    uses = source_applications or application_items(termmeta[category_ids[category]].get("common_applications_list", ""))
    use_items = ''.join(f'<li>{e(item)}</li>' for item in uses)
    applications = f'''<section class="product-detail-section" id="applications" role="tabpanel" aria-labelledby="tab-applications" tabindex="0"><div class="wrap"><div class="section-head"><div><span class="eyebrow">Range applications</span><h2>Applications</h2></div></div><ul class="product-apps">{use_items}</ul><p class="product-range-note">These are common applications for the {e(category_name)} range. Confirm product suitability with Aline Pumps for your project.</p></div></section>'''
    downloads = []
    for field, label in (("product_broucher", "Product brochure"), ("product_drawing", "Product drawing")):
        value = meta.get(field)
        media = attachment_media(value) if value else None
        if media:
            kind = "PDF" if media.lower().endswith(".pdf") else "FILE"
            downloads.append(f'<div class="download-card"><div class="download-icon" aria-hidden="true">{kind}</div><div><h3>{e(title(post))} {e(label)}</h3><p>View the product document.</p></div><a class="btn btn-dark" href="{e(media_url(media,current))}" target="_blank" rel="noopener">View {e(label.lower())} <span aria-hidden="true">&rarr;</span></a></div>')
    if not downloads:
        downloads.append(f'<div class="download-card"><div class="download-icon" aria-hidden="true">INFO</div><div><h3>Technical documents</h3><p>Ask Aline Pumps for the current brochure and product drawings.</p></div><a class="btn btn-dark" href="{e(brochure_request)}">Request brochure <span aria-hidden="true">&rarr;</span></a></div>')
    download_panel = f'''<section class="product-detail-section alt" id="downloads" role="tabpanel" aria-labelledby="tab-downloads" tabindex="0"><div class="wrap"><div class="section-head"><div><span class="eyebrow">Technical information</span><h2>Downloads</h2></div></div><div class="download-list">{"".join(downloads)}</div></div></section>'''
    related = [p for p in product_posts if product_category[int(p[0])] == category and p[0] != post[0]][:2]
    cards = "".join(product_card(current, p, category_name) for p in related)
    related_panel = f'''<section class="section related-products"><div class="wrap"><div class="section-head"><div><span class="eyebrow">{e(category_name)}</span><h2>Related Products</h2></div><a class="link-arrow" href="{e(local_link('/products/'+category+'/',current))}">View the full range</a></div><div class="products-grid">{cards}</div></div></section>''' if related else ""
    bottom = f'''<section class="cta on-dark"><div class="wrap"><div><span class="eyebrow">Talk to our team</span><h2>Need help specifying {e(title(post))}?</h2><p>Send your application requirements to Aline Pumps or call <a href="tel:1800018999">1800 018 999</a>.</p></div><div class="actions"><a class="btn btn-primary" href="{e(contact)}">Request a quote <span aria-hidden="true">&rarr;</span></a></div></div></section>'''
    body = crumb + hero + tabs + specs + construction + applications + download_panel + related_panel + bottom
    seo = postmeta[pid].get("_yoast_wpseo_title") or f"{title(post)} | Aline Pumps"
    description = postmeta[pid].get("_yoast_wpseo_metadesc") or summary
    product_script = f'<script src="{e(media_url("assets/js/kusp40.js",current))}" defer></script>'
    write(current, document(current, seo, description, "products", body, f"/products/{category}/{slug}/", product_script))


def build_archive(kind):
    if kind == "blog":
        build_blog_archive()
        return
    if kind == "projects":
        current, heading, eyebrow, records, url, active = "our-projects/index.html", "Our Projects", "Project experience", project_posts, "/our-projects/", "projects"
        categories = sorted({c for p in records for c in relations[int(p[0])]["portfolio_categories"]})
        destination = lambda p: "/portfolio/" + p[11] + "/"
        action = "View project"
    else:
        current, heading, eyebrow, records, url, active = "blog/index.html", "News & Insights", "Technical articles and news", article_posts, "/blog/", "blog"
        categories = sorted({c for p in records for c in relations[int(p[0])]["category"]})
        destination = lambda p: "/" + p[11] + "/"
        action = "Read article"
    category_buttons = '<button type="button" class="is-active" data-filter="all" aria-pressed="true">All</button>' + "".join(f'<button type="button" data-filter="{e(slug)}" aria-pressed="false">{e(slug.replace("-", " ").title())}</button>' for slug in categories)
    cards = "".join(f'<div class="filter-item" data-categories="{e(" ".join(relations[int(p[0])]["portfolio_categories" if kind == "projects" else "category"]))}">{card(current,destination(p),featured(p),title(p),excerpt(p,150),action)}</div>' for p in records)
    body = f'''<section class="page-banner archive-banner projects-banner"><div class="wrap"><h1>{e(heading)}</h1><p class="crumbs"><a href="{e(local_link('/',current))}">Home</a> &nbsp;/&nbsp; {e(heading)}</p></div></section><section class="section archive-index projects-archive"><div class="wrap"><div class="section-head"><div><span class="eyebrow">Browse {e(heading.lower())}</span><h2>Work across Australia</h2></div></div><div class="archive-filters" role="group" aria-label="Filter {e(heading.lower())}">{category_buttons}</div><div class="archive-grid archive-filter-grid">{cards}</div><p class="filter-empty" hidden>No items in this category.</p></div></section>''' + cta(current, "Project enquiry", "Discuss your next project")
    write(current, document(current, f"{heading} | Aline Pumps", f"Explore Aline Pumps {heading.lower()}.", active, body, url))


def article_topics(current, post, limit=2):
    slugs = [slug for slug in relations[int(post[0])]["category"] if slug in blog_category_slugs]
    slugs.sort(key=lambda slug: slug in {"aline-news", "aline-pumps"})
    links = "".join(f'<a href="{e(local_link("/category/" + slug + "/", current))}" rel="tag">{e(blog_category_names.get(slug, slug.replace("-", " ").title()))}</a>' for slug in slugs[:limit])
    if not links:
        links = '<span>Pump guides</span>'
    return f'<div class="article-topic-tags" aria-label="Article topics">{links}</div>' if links else ""


def build_blog_archive():
    current = "blog/index.html"
    lead = article_posts[0]
    recent = article_posts[1:5]
    lead_link = local_link("/" + lead[11] + "/", current)
    lead_image = featured(lead)
    lead_media = f'<a class="blog-featured-media" href="{e(lead_link)}"><img src="{e(media_url(lead_image, current))}" alt="" fetchpriority="high"></a>' if lead_image else ""
    recent_items = "".join(f'''<article class="blog-recent-item">{article_topics(current, post, 1)}<h3><a href="{e(local_link("/" + post[11] + "/", current))}">{e(title(post))}</a></h3></article>''' for post in recent)
    categories = sorted({slug for post in article_posts for slug in relations[int(post[0])]["category"] if slug in blog_category_slugs})
    buttons = '<button type="button" class="is-active" data-filter="all" aria-pressed="true">All</button>' + "".join(f'<button type="button" data-filter="{e(slug)}" aria-pressed="false">{e(blog_category_names.get(slug, slug.replace("-", " ").title()))}</button>' for slug in categories)
    cards = "".join(f'''<div class="filter-item" data-categories="{e(" ".join(relations[int(post[0])]["category"]))}">{card(current, "/" + post[11] + "/", featured(post), title(post), excerpt(post, 150), "Read article", article_topics(current, post))}</div>''' for post in article_posts)
    body = f'''<section class="blog-hero"><div class="wrap"><div class="blog-hero-intro"><span class="eyebrow">Technical articles and news</span><h1>News &amp; Insights</h1><p class="crumbs"><a href="{e(local_link('/', current))}">Home</a> &nbsp;/&nbsp; News &amp; Insights</p></div><div class="blog-hero-grid"><article class="blog-featured">{lead_media}<div class="blog-featured-content"><span class="blog-section-label">Featured article</span>{article_topics(current, lead)}<h2><a href="{e(lead_link)}">{e(title(lead))}</a></h2><p>{e(excerpt(lead, 230))}</p><a class="link-arrow" href="{e(lead_link)}">Read article</a></div></article><aside class="blog-recent" aria-labelledby="blog-recent-heading"><span class="blog-section-label">Stay up to date</span><h2 id="blog-recent-heading">Most recent articles</h2><div class="blog-recent-list">{recent_items}</div></aside></div></div></section><section class="section archive-index blog-archive"><div class="wrap"><div class="section-head"><div><span class="eyebrow">Browse articles</span><h2>Ideas, guidance and company news</h2></div></div><div class="archive-filters" role="group" aria-label="Filter articles by topic">{buttons}</div><div class="archive-grid archive-filter-grid">{cards}</div><p class="filter-empty" hidden>No articles in this topic.</p></div></section>''' + cta(current, "Technical advice", "Talk to our team")
    write(current, document(current, "News & Insights | Aline Pumps", "Technical articles, guidance and company news from Aline Pumps.", "blog", body, "/blog/"))


def build_story(post, kind):
    project = kind == "project"
    current = project_path[post[11]] if project else article_path[post[11]]
    collection = project_posts if project else article_posts
    category = relations[int(post[0])]["portfolio_categories" if project else "category"]
    parent = "/our-projects/" if project else "/blog/"
    image = featured(post)
    visual = f'<img src="{e(media_url(image,current))}" alt="{e(title(post))}" loading="lazy">' if image else ""
    content = clean_markup(post[4], current)
    date = str(post[2])[:10]
    kicker = "Project" if project else "News & Insights"
    hero = f'''<section class="page-banner archive-banner"><div class="wrap"><span class="eyebrow">{e(kicker)}{": " + e(category[0].replace("-", " ").title()) if category else ""}</span><h1>{e(title(post))}</h1><p class="crumbs"><a href="{e(local_link('/',current))}">Home</a> &nbsp;/&nbsp; <a href="{e(local_link(parent,current))}">{"Projects" if project else "News & Insights"}</a> &nbsp;/&nbsp; {e(title(post))}</p></div></section>'''
    more = [p for p in collection if p[0] != post[0]][:3]
    dest = (lambda p: "/portfolio/"+p[11]+"/") if project else (lambda p: "/"+p[11]+"/")
    cards = "".join(card(current, dest(p), featured(p), title(p), excerpt(p,120), "View project" if project else "Read article") for p in more)
    bluebook = '''<section class="section archive-bluebook"><div class="wrap archive-reading"><span class="eyebrow">Aline Blue Book</span><h2>Request access to the product guide</h2><p>The guide download is available through Aline Pumps' access form.</p><a class="btn btn-primary" href="https://info.alinepumps.com.au/blue-book-form-page" target="_blank" rel="noopener">Open the Blue Book access form <span aria-hidden="true">↗</span></a></div></section>''' if post[11] == "2023-blue-book" else ""
    body = hero + f'''<article class="section archive-story"><div class="wrap archive-reading"><p class="archive-story-meta">{e(category[0].replace("-"," ").title()) if category else e(kicker)}{" · " + date if not project else ""}</p>{f'<figure class="archive-story-image">{visual}</figure>' if visual else ''}<div class="archive-rich">{content}</div><a class="link-arrow" href="{e(local_link(parent,current))}">Back to {"projects" if project else "news and insights"}</a></div></article>''' + bluebook + f'''<section class="section archive-related"><div class="wrap"><div class="section-head"><div><span class="eyebrow">Keep exploring</span><h2>{"More projects" if project else "More articles"}</h2></div></div><div class="archive-grid">{cards}</div></div></section>''' + cta(current, "Project enquiry" if project else "Technical advice", "Talk to our team")
    seo = postmeta[int(post[0])].get("_yoast_wpseo_title") or f"{title(post)} | Aline Pumps"
    description = postmeta[int(post[0])].get("_yoast_wpseo_metadesc") or excerpt(post)
    canonical = f"/portfolio/{post[11]}/" if project else f"/{post[11]}/"
    write(current, document(current, seo, description, "projects" if project else "blog", body, canonical))


def build_article_listing(slug: str | None, page: int = 1):
    """Retain the current site's article category and paginated archive paths."""
    if slug:
        current = f"category/{slug}/" + (f"page/{page}/" if page > 1 else "") + "index.html"
        canonical = f"/category/{slug}/" + (f"page/{page}/" if page > 1 else "")
        heading = blog_category_names.get(slug, slug.replace("-", " ").title())
        records = [p for p in article_posts if slug in relations[int(p[0])]["category"]]
    else:
        current = f"blog/page/{page}/index.html"
        canonical = f"/blog/page/{page}/"
        heading = "News & Insights"
        records = article_posts
    visible = records[(page - 1) * 12 : page * 12]
    cards = "".join(card(current, "/" + p[11] + "/", featured(p), title(p), excerpt(p, 145), "Read article") for p in visible)
    nav = []
    for number in range(1, max(2, (len(records) + 11) // 12 + 1)):
        if slug:
            path = f"/category/{slug}/" if number == 1 else f"/category/{slug}/page/{number}/"
        else:
            path = "/blog/" if number == 1 else f"/blog/page/{number}/"
        if path not in known_paths:
            continue
        nav.append(f'<a {"aria-current=\"page\"" if number == page else ""} href="{e(local_link(path,current))}">{number}</a>')
    body = f'''<section class="page-banner archive-banner"><div class="wrap"><span class="eyebrow">News &amp; Insights</span><h1>{e(heading)}</h1><p class="crumbs"><a href="{e(local_link('/',current))}">Home</a> &nbsp;/&nbsp; <a href="{e(local_link('/blog/',current))}">News &amp; Insights</a> &nbsp;/&nbsp; {e(heading)}</p></div></section><section class="section archive-index"><div class="wrap"><div class="section-head"><div><span class="eyebrow">Browse articles</span><h2>{e(heading)}</h2></div><p>{len(records)} articles</p></div><div class="archive-grid">{cards}</div><nav class="archive-pagination" aria-label="Article pages">{"".join(nav)}</nav></div></section>'''
    seo = inventory_title.get(canonical, f"{heading} | Aline Pumps")
    write(current, document(current, seo, f"Read Aline Pumps articles about {heading.lower()}.", "blog", body, canonical))


def build_authors():
    current = "authors/index.html"
    people = [("Harland Mackenzie", "/authors/harland-mackenzie/", "Articles by Harland Mackenzie")]
    cards = "".join(card(current, path, None, name, description, "View articles") for name, path, description in people)
    body = banner(current, "Authors", "News & Insights", "/blog/") + f'''<section class="section archive-index"><div class="wrap"><h2>Aline Pumps contributors</h2><div class="archive-grid">{cards}</div></div></section>'''
    write(current, document(current, inventory_title.get("/authors/", "Authors | Aline Pumps"), "Browse Aline Pumps contributors and their articles.", "blog", body, "/authors/"))
    current = "authors/harland-mackenzie/index.html"
    authored = [p for p in article_posts if p[1] == "20"]
    cards = "".join(card(current, "/" + p[11] + "/", featured(p), title(p), excerpt(p, 150), "Read article") for p in authored)
    body = banner(current, "Harland Mackenzie", "News & Insights", "/blog/") + f'''<section class="section archive-index"><div class="wrap"><h2>Articles by Harland Mackenzie</h2><div class="archive-grid">{cards}</div></div></section>'''
    write(current, document(current, inventory_title.get("/authors/harland-mackenzie/", "Harland Mackenzie | Aline Pumps"), "Articles by Harland Mackenzie for Aline Pumps.", "blog", body, "/authors/harland-mackenzie/"))


def build_project_categories():
    for slug in ("commercial", "government", "residential"):
        current = f"portfolio_categories/{slug}/index.html"
        heading = slug.title() + " Projects"
        records = [p for p in project_posts if slug in relations[int(p[0])]["portfolio_categories"]]
        cards = "".join(card(current, "/portfolio/" + p[11] + "/", featured(p), title(p), excerpt(p, 145), "View project") for p in records)
        body = banner(current, heading, "Projects", "/our-projects/") + f'''<section class="section archive-index"><div class="wrap"><div class="section-head"><div><span class="eyebrow">Aline Pumps work</span><h2>{e(heading)}</h2></div><p>{len(records)} projects</p></div><div class="archive-grid">{cards}</div></div></section>'''
        write(current, document(current, f"{heading} | Aline Pumps", f"Explore Aline Pumps {slug} projects.", "projects", body, f"/portfolio_categories/{slug}/"))


def build_contact():
    current = "contact-us/index.html"
    body = '''<section class="page-banner archive-banner"><div class="wrap"><span class="eyebrow">Aline Pumps</span><h1>Contact us</h1><p class="crumbs"><a href="../index.html">Home</a> &nbsp;/&nbsp; Contact us</p></div></section><section class="section contact-page"><div class="wrap contact-grid"><div><span class="eyebrow">Speak with an expert</span><h2>Tell us what your system needs</h2><p>For urgent technical enquiries, project sizing or immediate support, call our national line on <a href="tel:1800018999">1800 018 999</a>. Otherwise, send your project details and our team will be in touch.</p><div class="contact-context" id="enquiry-context" hidden></div><div class="office-list"><div><h3>New South Wales</h3><address>2–10 Yarrunga Street<br>Prestons NSW 2170</address></div><div><h3>Queensland</h3><address>16 Mica Street<br>Carole Park QLD 4300</address></div></div></div><div class="contact-form-card"><h2>Send an enquiry</h2><p id="form-instructions">Include the product model or service needed where relevant.</p><div id="contact-enquiry-form" aria-label="Contact enquiry form"></div><p class="form-fallback">If the form does not load, <a href="https://www.alinepumps.com.au/contact-us/">use the current Aline Pumps contact form</a> or call <a href="tel:1800018999">1800 018 999</a>.</p></div></div></section>'''
    script = '''<script src="https://js.hsforms.net/forms/embed/v2.js"></script><script>if(window.hbspt&&window.hbspt.forms){window.hbspt.forms.create({region:'ap1',portalId:'23542928',formId:'0c749eb6-6c6b-44df-a73b-d1a3a0e11875',target:'#contact-enquiry-form'});}</script>'''
    write(current, document(current, "Contact Aline Pumps | Product, Project and Service Enquiries", "Contact Aline Pumps for product selection, project requirements, servicing and technical support.", "contact", body, "/contact-us/", script))


def build_extra_page(post):
    current = f"{post[11]}/index.html"
    body = banner(current, title(post), "Aline Pumps", "/") + f'''<article class="section archive-story"><div class="wrap archive-reading"><div class="archive-rich">{clean_markup(post[4], current)}</div></div></article>'''
    write(current, document(current, postmeta[int(post[0])].get("_yoast_wpseo_title") or f"{title(post)} | Aline Pumps", postmeta[int(post[0])].get("_yoast_wpseo_metadesc") or excerpt(post), "", body, f"/{post[11]}/"))


for slug, term in sorted(category_terms.items()):
    build_category(slug, term)
for post in product_posts:
    build_product(post)
# Keep the duplicate legacy mockup URL usable while consolidating its content.
round_alias = "products/water-storage-tanks/round/index.html"
round_target = "../round-water-storage-tank/index.html"
round_canonical = ORIGIN + "/products/water-storage-tanks/round-water-storage-tank/"
write(round_alias, f'''<!DOCTYPE html><html lang="en-AU"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex, follow"><link rel="canonical" href="{round_canonical}"><meta http-equiv="refresh" content="0;url={round_target}"><title>Round Water Storage Tank | Aline Pumps</title></head><body><p>This product has moved to <a href="{round_target}">Round Water Storage Tank</a>.</p></body></html>''')
build_archive("projects")
build_archive("blog")
for post in project_posts:
    build_story(post, "project")
for post in article_posts:
    build_story(post, "article")
for slug in blog_category_slugs:
    build_article_listing(slug)
for slug in ("aline-news", "aline-pumps"):
    build_article_listing(slug, 2)
for page in range(2, 6):
    build_article_listing(None, page)
build_authors()
build_project_categories()
build_contact()
for post in extra_pages.values():
    build_extra_page(post)
print(f"Built {len(category_terms)} product categories, {len(product_posts)} products, {len(project_posts)} projects, {len(article_posts)} articles, {len(blog_category_slugs)} article categories and {len(extra_pages)} extra pages; copied {len(copied_media)} media files.")
