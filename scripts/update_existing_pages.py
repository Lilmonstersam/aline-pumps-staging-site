"""Keep the hand-built mockup pages aligned with the generated site routes."""
from pathlib import Path
import re
import html
import shutil
from urllib.parse import urlsplit, parse_qs, quote

SITE = Path(__file__).resolve().parents[1]
PUMPS2YOU_SOURCE = SITE.parents[2] / "seo/images/logos/Pumps2You-Logo_125x@2x.avif"
shutil.copy2(PUMPS2YOU_SOURCE, SITE / "assets/logos/pumps2you.avif")
PAGES = ["index.html", "about.html", "products.html", "category-undersink-pumpstations.html", "support-and-service.html", "aline-service.html", "training.html", "kusp40.html"]


def replace_link(match):
    value = match.group(1)
    parsed = urlsplit(value)
    path = parsed.path
    if path == "/contact-us/":
        target = "contact-us/index.html"
    elif path == "/our-projects/":
        target = "our-projects/index.html"
    elif path == "/blog/":
        target = "blog/index.html"
    elif path == "/products/":
        target = "products.html"
    elif path == "/login/":
        target = "2023-blue-book/index.html"
    elif path.startswith("/products/") and (SITE / path.lstrip("/") / "index.html").is_file():
        target = path.lstrip("/") + "index.html"
    elif path.startswith("/") and (SITE / path.lstrip("/") / "index.html").is_file():
        target = path.lstrip("/") + "index.html"
    else:
        return 'href="https://www.alinepumps.com.au' + value + '"'
    suffix = ("?" + parsed.query if parsed.query else "") + ("#" + parsed.fragment if parsed.fragment else "")
    return 'href="' + target + suffix + '"'


def enrich_contact(match):
    value = match.group(1)
    parsed = urlsplit(html.unescape(value))
    if parsed.path != "contact-us/index.html" or not parsed.query:
        return match.group(0)
    params = parse_qs(parsed.query)
    if "message" in params:
        return match.group(0)
    if params.get("model"):
        message = f"Quote request for model {params['model'][0]}"
    elif params.get("service"):
        message = f"Maintenance plan request for {params['service'][0]}"
    elif params.get("category"):
        message = f"Product advice request for {params['category'][0].replace('-', ' ')}"
    elif params.get("topic"):
        message = f"Enquiry about {params['topic'][0].lower()}"
    else:
        return match.group(0)
    return f'href="{value}&amp;message={quote(message)}"'


def update_category_images(markup):
    def replace_card(match):
        href = match.group("href")
        slug = "undersink-pumpstations" if href == "category-undersink-pumpstations.html" else href.split("/")[1]
        category = SITE / "products" / slug / "index.html"
        if not category.is_file():
            return match.group(0)
        figure = re.search(r'<figure class="cat-figure generated"><img src="([^"]+)" alt="([^"]+)"', category.read_text())
        if not figure:
            return match.group(0)
        image = (category.parent / html.unescape(figure.group(1))).resolve()
        if not image.is_file():
            return match.group(0)
        source = image.relative_to(SITE).as_posix()
        alt = figure.group(2)
        return match.group("prefix") + f'<img class="photo" src="{source}" alt="{alt}" loading="lazy">' + match.group("suffix")

    return re.sub(r'(?P<prefix><a class="(?:pkg|type-card)" href="(?P<href>[^"]+)"><div class="media">).*?(?P<suffix></div>)', replace_card, markup, flags=re.S)


for filename in PAGES:
    path = SITE / filename
    text = path.read_text()
    text = text.replace('<ul class="menu">', '<ul class="menu" id="primary-menu">')
    text = text.replace('<button class="menu-toggle" aria-label="Open menu">Menu</button>', '<button class="menu-toggle" type="button" aria-controls="primary-menu" aria-expanded="false" aria-label="Open menu">Menu</button>')
    text = text.replace('<!-- Placeholder wordmark: Pumps 2 You logo file still to be supplied -->', '')
    text = text.replace('<div class="service-media"><span class="placeholder-tag">Logo to supply</span><span class="wordmark">Pumps <span>2</span> You</span></div>', '<div class="service-media"><img class="logo-img" src="assets/logos/pumps2you.avif" alt="Pumps 2 You" loading="lazy"></div>')
    text = text.replace('<span class="external-note">External site</span> <span aria-hidden="true">&rarr;</span>', '<span class="external-arrow" aria-hidden="true">↗</span>')

    if filename == "index.html":
        text = text.replace('<a class="btn btn-primary" href="about.html">Learn more</a>\n      <a class="btn btn-outline" href="/contact-us/">Contact us</a>', '<a class="btn btn-primary" href="products.html">Explore pump systems</a>\n      <a class="btn btn-outline" href="aline-service.html">Request service</a>')
        text = re.sub(r'(?m)^\s*<a class="btn btn-outline"[^>]*>Get product advice</a>\n?', '', text)
        text = text.replace('href="aline-service.html">Learn more</a>', 'href="aline-service.html">Request servicing</a>')
        text = text.replace('href="training.html">Learn more</a>', 'href="training.html">Book training</a>')
        text = text.replace('href="https://alinespares.com/" target="_blank" rel="noopener">Buy now</a>', 'href="https://alinespares.com/" target="_blank" rel="noopener" aria-label="Shop spares on the external Aline Spares website">Shop spares <span aria-hidden="true">↗</span></a>')
        text = text.replace('href="https://pumps2you.com/" target="_blank" rel="noopener">Buy now</a>', 'href="https://pumps2you.com/" target="_blank" rel="noopener" aria-label="Shop domestic pumps on the external Pumps 2 You website">Shop domestic pumps <span aria-hidden="true">↗</span></a>')
        text = text.replace('href="/contact-us/">Work with us', 'href="/contact-us/?topic=Project%20enquiry">Discuss a project')
        text = text.replace('href="our-projects/index.html" style="background-image:url(\'assets/img/project-wellcamp-airport.jpg\')"', 'href="portfolio/wellcamp-airport/index.html" style="background-image:url(\'assets/img/project-wellcamp-airport.jpg\')"')
    if filename == "support-and-service.html":
        text = text.replace('href="https://alinespares.com/" target="_blank" rel="noopener noreferrer">Shop now', 'href="https://alinespares.com/" target="_blank" rel="noopener noreferrer" aria-label="Shop spares on the external Aline Spares website">Shop spares <span class="external-arrow" aria-hidden="true">↗</span>')
        text = text.replace('href="https://pumps2you.com/" target="_blank" rel="noopener noreferrer">Shop now', 'href="https://pumps2you.com/" target="_blank" rel="noopener noreferrer" aria-label="Shop domestic pumps on the external Pumps 2 You website">Shop domestic pumps <span class="external-arrow" aria-hidden="true">↗</span>')
        text = text.replace('href="/contact-us/">Contact us <span aria-hidden="true">&rarr;</span>', 'href="/contact-us/?topic=Support%20enquiry">Ask for support <span aria-hidden="true">&rarr;</span>')
        text = text.replace('href="our-projects/index.html" style="background-image:url(\'assets/img/project-wellcamp-airport.jpg\')"', 'href="portfolio/wellcamp-airport/index.html" style="background-image:url(\'assets/img/project-wellcamp-airport.jpg\')"')
    if filename == "aline-service.html":
        text = text.replace('href="/contact-us/">Talk to our Service team', 'href="/contact-us/?topic=Maintenance%20plan&amp;service=Aline%20Service">Request a maintenance plan')
        text = text.replace('href="/contact-us/">Contact us <span aria-hidden="true">&rarr;</span>', 'href="/contact-us/?topic=Maintenance%20plan&amp;service=Aline%20Service">Request a maintenance plan <span aria-hidden="true">&rarr;</span>')
    if filename == "kusp40.html":
        text = text.replace('href="/contact-us/">Submit an enquiry', 'href="/contact-us/?topic=Product%20quote&amp;model=KUSP40">Request a KUSP40 quote')
        text = text.replace('href="/contact-us/">Contact us <span aria-hidden="true">&rarr;</span>', 'href="/contact-us/?topic=Product%20quote&amp;model=KUSP40">Request a KUSP40 quote <span aria-hidden="true">&rarr;</span>')
    if filename == "category-undersink-pumpstations.html":
        text = text.replace('href="/contact-us/">Make an enquiry', 'href="/contact-us/?topic=Product%20selection&amp;category=undersink-pumpstations">Ask about undersink pump stations')
        text = text.replace('href="/login/">Log in to access</a>', 'href="/2023-blue-book/">View the Blue Book</a>')
        text = text.replace('href="kusp40.html"', 'href="products/undersink-pumpstations/kusp40/index.html"')
        text = text.replace('href="/contact-us/">Work with us', 'href="/contact-us/?topic=Product%20selection&amp;category=undersink-pumpstations">Ask for product advice')
        text = text.replace('<span>Water Storage Tanks</span><span class="count">3</span>', '<span>Water Storage Tanks</span><span class="count">2</span>')
    if filename == "products.html":
        text = text.replace('href="/contact-us/">Work with us', 'href="/contact-us/?topic=Product%20selection">Ask for product advice')
        text = update_category_images(text)
        text = text.replace('<h3>Water Storage Tanks</h3><span class="count">3 products</span>', '<h3>Water Storage Tanks</h3><span class="count">2 products</span>')
    if filename == "about.html":
        text = text.replace('href="/contact-us/">Work with us', 'href="/contact-us/?topic=Project%20enquiry">Discuss a project')
    text = re.sub(r'href="(/[^"#]+)"', replace_link, text)
    text = re.sub(r'href="(contact-us/index\.html\?[^"#]+)"', enrich_contact, text)
    if 'assets/js/site.js' not in text:
        text = text.replace('</body>', '<script src="assets/js/site.js" defer></script>\n</body>')
    path.write_text(text)

# Preserve the two hand-crafted layouts at their canonical migration paths.
for source, target in [
    ("about.html", "about/index.html"),
    ("products.html", "products/index.html"),
    ("support-and-service.html", "support-and-service/index.html"),
    ("aline-service.html", "support-and-service/aline-service/index.html"),
    ("training.html", "support-and-service/training/index.html"),
    ("kusp40.html", "products/undersink-pumpstations/kusp40/index.html"),
    ("category-undersink-pumpstations.html", "products/undersink-pumpstations/index.html"),
]:
    content = (SITE / source).read_text()
    prefix = "../" * (len(Path(target).parts) - 1)
    def prefix_local(match):
        attr, value = match.groups()
        if value.startswith(("#", "http:", "https:", "mailto:", "tel:", "data:")):
            return match.group(0)
        return f'{attr}="{prefix}{value}"'
    content = re.sub(r'\b(href|src)="([^"]+)"', prefix_local, content)
    content = content.replace("url('assets/", f"url('{prefix}assets/")
    (SITE / target).parent.mkdir(parents=True, exist_ok=True)
    (SITE / target).write_text(content)

print("Updated eight hand-built pages and seven canonical copies.")

from finalise_site import finalise
finalise()
