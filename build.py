#!/usr/bin/env python3
"""Build the Perceptron Data catalogue site into _site/.

Standard library only, so the daily GitHub Actions run needs no installs. Live
data (actors, prices) comes from Apify's public Store API; texts come from
content.py; the legal notice from data/legal.json. The build fails loudly
instead of publishing an empty catalogue or a site without a legal notice.
"""

from __future__ import annotations

import html
import json
import shutil
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from content import ACTORS, GROUPS

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site"
BASE = "https://perceptron-data.github.io"
APIFY_USER = "perceptr0n"
STORE_API = f"https://api.apify.com/v2/store?username={APIFY_USER}&limit=100"
GITHUB_ORG = "https://github.com/Perceptron-Data"
APIFY_PROFILE = f"https://apify.com/{APIFY_USER}"
GROUP_ORDER = ["ai", "sales", "research", "public", "free"]
TODAY = datetime.now(tz=UTC).strftime("%Y-%m-%d")

T = {
    "en": {"lang": "en", "home": "Home", "actors": "Actors", "run": "Run on Apify", "details": "Details",
           "features": "What you get", "uses": "Use cases", "example": "Example input", "faq": "FAQ",
           "price": "Price", "free": "Free", "per": "per 1,000", "cheaper": "Billed by Apify per result plus a small start fee per run — cheaper on paid Apify plans.",
           "meta": "Apify actors for AI, sales and research: PDF to Markdown, Google Ads Transparency checks, DACH company data, jobs and EU tenders. No login, pay per result.",
           "related": "Related actors", "legal": "Legal notice", "privacy": "Privacy", "other": "Deutsch",
           "tagline": "Data APIs for AI, sales and research",
           "hero": "Clean, structured data from public and official sources — ready for AI pipelines, CRMs and spreadsheets. Every actor runs on Apify: no login or API key needed, paid actors charge per result only.",
           "updated": "Prices and catalogue updated daily from the Apify Store. Last update:",
           "disclaimer": "Independent developer. Not affiliated with Apify or the data sources named.",
           "allactors": "All actors", "start": "from"},
    "de": {"lang": "de", "home": "Start", "actors": "Actors", "run": "Auf Apify starten", "details": "Details",
           "features": "Das bekommen Sie", "uses": "Anwendungsfälle", "example": "Beispiel-Eingabe", "faq": "Häufige Fragen",
           "price": "Preis", "free": "Kostenlos", "per": "pro 1.000", "cheaper": "Abrechnung über Apify pro Ergebnis plus eine kleine Startgebühr je Lauf — günstiger in bezahlten Apify-Tarifen.",
           "meta": "Apify-Actors für KI, Vertrieb und Marktforschung: PDF in Markdown, Google-Werbung prüfen, Impressum-Firmendaten, Stellen und EU-Ausschreibungen.",
           "related": "Ähnliche Actors", "legal": "Impressum", "privacy": "Datenschutz", "other": "English",
           "tagline": "Daten-APIs für KI, Vertrieb und Marktforschung",
           "hero": "Saubere, strukturierte Daten aus öffentlichen und amtlichen Quellen — fertig für KI-Pipelines, CRM und Tabellen. Jeder Actor läuft auf Apify: ohne Login und API-Schlüssel, bezahlte Actors rechnen nur pro Ergebnis ab.",
           "updated": "Preise und Katalog täglich aus dem Apify Store aktualisiert. Stand:",
           "disclaimer": "Unabhängiger Entwickler. Nicht verbunden mit Apify oder den genannten Datenquellen.",
           "allactors": "Alle Actors", "start": "ab"},
}


# ------------------------------------------------------------------ data

def fetch_store() -> list[dict]:
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(STORE_API, timeout=30) as response:
                items = json.load(response)["data"]["items"]
            items = [a for a in items if a["username"].lower() == APIFY_USER.lower()]
            if items:
                return items
            last = "empty result"
        except Exception as error:  # network hiccup: retry
            last = error
        time.sleep(5 * (attempt + 1))
    sys.exit(f"Apify Store API failed ({last}) — not publishing an empty catalogue.")


def price_info(item: dict) -> dict:
    """Main per-result price on the Free plan and on the cheapest tier."""
    info = item.get("currentPricingInfo") or {}
    events = (info.get("pricingPerEvent") or {}).get("actorChargeEvents") or {}
    if info.get("pricingModel") != "PAY_PER_EVENT" or not events:
        return {"free": True}
    candidates = [(k, v) for k, v in events.items() if k != "apify-actor-start"]
    main = next(((k, v) for k, v in candidates if v.get("isPrimaryEvent")), candidates[0] if candidates else None)
    if not main:
        return {"free": True}
    _, ev = main
    if ev.get("eventPriceUsd") is not None:
        low = high = ev["eventPriceUsd"]
    else:
        tiers = {k: v["tieredEventPriceUsd"] for k, v in (ev.get("eventTieredPricingUsd") or {}).items()}
        # "from" = the Business plan anyone can book, not the enterprise tiers
        # that need an individual contract.
        high, low = tiers.get("FREE"), tiers.get("GOLD", min(tiers.values()))
    return {"free": False, "per1000": high * 1000, "from1000": low * 1000}


def money(value: float, lang: str) -> str:
    text = f"{value:,.2f}"
    if lang == "de":
        return text.replace(",", "X").replace(".", ",").replace("X", ".") + " $"
    return "$" + text


# ------------------------------------------------------------------ html

def esc(text) -> str:
    return html.escape(str(text), quote=True)


def page(lang: str, path: str, alt_path: str, title: str, desc: str, body: str,
         jsonld: list[dict], og_image: str = "/assets/og/default.png") -> str:
    t = T[lang]
    en_path, de_path = (path, alt_path) if lang == "en" else (alt_path, path)
    ld = "\n".join(f'<script type="application/ld+json">{json.dumps(d, ensure_ascii=False)}</script>' for d in jsonld)
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{BASE}{path}">
<link rel="alternate" hreflang="en" href="{BASE}{en_path}">
<link rel="alternate" hreflang="de" href="{BASE}{de_path}">
<link rel="alternate" hreflang="x-default" href="{BASE}{en_path}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Perceptron Data">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{BASE}{path}">
<meta property="og:image" content="{BASE}{og_image}">
<meta property="og:locale" content="{'de_DE' if lang == 'de' else 'en_US'}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#312E81">
<link rel="icon" href="/assets/favicon.png" type="image/png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="stylesheet" href="/assets/style.css">
{ld}
</head>
<body>
<header class="top"><div class="wrap">
  <a class="brand" href="{'/' if lang == 'en' else '/de/'}"><img src="/assets/logo-64.png" alt="" width="32" height="32">Perceptron Data</a>
  <nav><a href="{'/' if lang == 'en' else '/de/'}#actors">{t['actors']}</a><a href="{alt_path}" hreflang="{'de' if lang == 'en' else 'en'}" lang="{'de' if lang == 'en' else 'en'}">{t['other']}</a></nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer><div class="wrap">
  <p>{t['updated']} {TODAY}. {t['disclaimer']}</p>
  <p><a href="{APIFY_PROFILE}">Apify</a> · <a href="{GITHUB_ORG}">GitHub</a> · <a href="/impressum/">{t['legal']}</a> · <a href="/datenschutz/">{t['privacy']}</a></p>
</div></footer>
</body>
</html>
"""


def price_html(p: dict, unit: str, lang: str) -> str:
    t = T[lang]
    if p["free"]:
        return f'<span class="price free">{t["free"]}</span>'
    main = f'{money(p["per1000"], lang)} {t["per"]} {esc(unit)}'
    if p["from1000"] < p["per1000"]:
        main += f' <span class="muted">({t["start"]} {money(p["from1000"], lang)})</span>'
    return f'<span class="price">{main}</span>'


def card(slug: str, a: dict, item: dict, p: dict, lang: str) -> str:
    c = a.get(lang) or {}
    t = T[lang]
    href = f"/actors/{slug}/" if lang == "en" else f"/de/actors/{slug}/"
    title = c.get("h1") or item["title"]
    return f"""<article class="card">
  <img src="/assets/icons/{esc(a.get('icon', 'logo-256.png'))}" alt="" width="56" height="56" loading="lazy">
  <div><h3><a href="{href}">{esc(item['title'])}</a></h3>
  <p>{esc(c.get('desc') or item.get('description', ''))}</p>
  <p class="meta">{price_html(p, a.get('unit', {}).get(lang, 'results'), lang)} · <a href="{esc(item['url'] if 'url' in item else APIFY_PROFILE + '/' + slug)}">{t['run']} →</a></p></div>
</article>"""


def actor_url(slug: str) -> str:
    return f"{APIFY_PROFILE}/{slug}"


def build_actor(slug: str, a: dict, item: dict, p: dict, lang: str, all_items: dict) -> str:
    c = a.get(lang) or {}
    t = T[lang]
    unit = a.get("unit", {}).get(lang, "results")
    path = f"/actors/{slug}/" if lang == "en" else f"/de/actors/{slug}/"
    alt = f"/de/actors/{slug}/" if lang == "en" else f"/actors/{slug}/"
    h1 = c.get("h1") or item["title"]
    desc = c.get("desc") or item.get("description", "")[:155]
    title = (c.get("title") or item["title"]) + " | Perceptron Data"
    feats = "".join(f"<li>{esc(x)}</li>" for x in c.get("features", []))
    uses = "".join(f"<li>{esc(x)}</li>" for x in c.get("uses", []))
    faq = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(ans)}</p></details>" for q, ans in c.get("faq", []))
    example = json.dumps(a.get("example", {}), indent=2, ensure_ascii=False)
    related = [s for s, o in ACTORS.items() if o["group"] == a["group"] and s != slug and s in all_items][:3]
    rel = "".join(f'<li><a href="{"/actors/" if lang == "en" else "/de/actors/"}{s}/">{esc(all_items[s]["title"])}</a></li>' for s in related)
    body = f"""<nav class="crumbs"><a href="{'/' if lang == 'en' else '/de/'}">{t['home']}</a> › {esc(item['title'])}</nav>
<section class="hero actor">
  <img src="/assets/icons/{esc(a.get('icon', 'logo-256.png'))}" alt="" width="96" height="96">
  <div><h1>{esc(h1)}</h1><p class="lead">{esc(c.get('intro') or item.get('description', ''))}</p>
  <p><a class="button" href="{actor_url(slug)}">{t['run']}</a> {price_html(p, unit, lang)}</p></div>
</section>
{f'<section><h2>{t["features"]}</h2><ul class="ticks">{feats}</ul></section>' if feats else ''}
{f'<section><h2>{t["uses"]}</h2><ul>{uses}</ul></section>' if uses else ''}
{f'<section><h2>{t["example"]}</h2><pre><code>{esc(example)}</code></pre></section>' if a.get('example') else ''}
<section><h2>{t['price']}</h2><p>{price_html(p, unit, lang)}</p><p class="muted">{t['cheaper']}</p></section>
{f'<section><h2>{t["faq"]}</h2>{faq}</section>' if faq else ''}
{f'<section><h2>{t["related"]}</h2><ul>{rel}</ul></section>' if rel else ''}
<p><a class="button" href="{actor_url(slug)}">{t['run']}</a></p>"""
    offer = {"@type": "Offer", "priceCurrency": "USD", "url": actor_url(slug),
             "price": 0 if p["free"] else round(p["per1000"], 2)}
    if not p["free"]:
        offer["priceSpecification"] = {"@type": "UnitPriceSpecification", "price": round(p["per1000"], 2), "priceCurrency": "USD",
                                       "referenceQuantity": {"@type": "QuantitativeValue", "value": 1000, "unitText": unit}}
    ld = [{"@context": "https://schema.org", "@type": "SoftwareApplication", "name": item["title"], "description": desc,
           "applicationCategory": "DeveloperApplication", "operatingSystem": "Web (Apify platform)", "url": f"{BASE}{path}",
           "image": f"{BASE}/assets/icons/{a.get('icon', 'logo-256.png')}", "offers": offer,
           "publisher": {"@type": "Organization", "name": "Perceptron Data", "url": BASE}},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": t["home"], "item": BASE + ("/" if lang == "en" else "/de/")},
              {"@type": "ListItem", "position": 2, "name": item["title"], "item": f"{BASE}{path}"}]}]
    if c.get("faq"):
        ld.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in c["faq"]]})
    og = f"/assets/og/{slug}.png" if (ROOT / "assets" / "og" / f"{slug}.png").exists() else "/assets/og/default.png"
    return page(lang, path, alt, title, desc, body, ld, og)


def build_index(lang: str, items: dict, prices: dict) -> str:
    t = T[lang]
    path, alt = ("/", "/de/") if lang == "en" else ("/de/", "/")
    sections = []
    for g in GROUP_ORDER:
        slugs = [s for s, a in ACTORS.items() if a["group"] == g and s in items]
        if slugs:
            cards = "\n".join(card(s, ACTORS[s], items[s], prices[s], lang) for s in slugs)
            sections.append(f'<section><h2>{GROUPS[g][lang]}</h2><div class="grid">{cards}</div></section>')
    extra = [s for s in items if s not in ACTORS]  # published on Apify but no texts yet
    if extra:
        cards = "\n".join(card(s, {"icon": "logo-256.png", "group": "research", "unit": {}}, items[s], prices[s], lang) for s in extra)
        sections.append(f'<section><h2>{t["allactors"]}</h2><div class="grid">{cards}</div></section>')
    body = f"""<section class="hero home"><h1>{t['tagline']}</h1><p class="lead">{t['hero']}</p>
<p><a class="button" href="{APIFY_PROFILE}">{t['allactors']} — Apify</a></p></section>
<div id="actors">{''.join(sections)}</div>"""
    ld = [{"@context": "https://schema.org", "@type": "Organization", "name": "Perceptron Data", "url": BASE,
           "logo": f"{BASE}/assets/logo-256.png", "sameAs": [APIFY_PROFILE, GITHUB_ORG]},
          {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
              {"@type": "ListItem", "position": i + 1, "url": f"{BASE}{'/actors/' if lang == 'en' else '/de/actors/'}{s}/", "name": items[s]["title"]}
              for i, s in enumerate(items)]}]
    title = f"Perceptron Data — {t['tagline']}"
    return page(lang, path, alt, title, t["meta"], body, ld)


def build_legal() -> tuple[str, str]:
    legal_file = ROOT / "data" / "legal.json"
    if not legal_file.exists():
        sys.exit("data/legal.json is missing — a German business site must not go live without a legal notice.")
    L = json.loads(legal_file.read_text(encoding="utf-8"))
    if any(not L.get(k) or "TODO" in str(L.get(k)) for k in ("name", "street", "city", "email")):
        sys.exit("data/legal.json is incomplete — not publishing without a full legal notice.")
    addr = f"{esc(L['name'])}<br>{esc(L['street'])}<br>{esc(L['city'])}<br>{esc(L.get('country', 'Deutschland'))}"
    imp = f"""<h1>Impressum / Legal notice</h1>
<h2>Angaben gemäß § 5 DDG</h2><p>{addr}</p>
<h2>Kontakt</h2><p>E-Mail: <a href="mailto:{esc(L['email'])}">{esc(L['email'])}</a></p>
<h2>Verantwortlich für den Inhalt</h2><p>{esc(L['name'])}, Anschrift wie oben.</p>
<h2>Hinweis</h2><p>Die Actors werden über die Plattform Apify (Apify Technologies s.r.o., Prag) angeboten und abgerechnet. Für Inhalte externer Links sind deren Betreiber verantwortlich.</p>"""
    priv = f"""<h1>Datenschutzerklärung / Privacy</h1>
<h2>Verantwortlicher</h2><p>{addr}<br>E-Mail: <a href="mailto:{esc(L['email'])}">{esc(L['email'])}</a></p>
<h2>Hosting</h2><p>Diese Website wird bei GitHub Pages gehostet (GitHub, Inc., 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, USA). Beim Aufruf verarbeitet GitHub technisch notwendige Daten wie die IP-Adresse in Server-Protokollen, um die Seite auszuliefern und abzusichern. Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse an einer sicheren, verfügbaren Website). GitHub ist unter dem EU-US Data Privacy Framework zertifiziert. Details: <a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement">GitHub Privacy Statement</a>.</p>
<h2>Keine Cookies, kein Tracking</h2><p>Diese Website setzt keine Cookies, nutzt keine Analyse- oder Werbedienste und bindet keine externen Schriftarten oder Skripte ein.</p>
<h2>Externe Links</h2><p>Links führen zu apify.com und github.com. Dort gelten die Datenschutzerklärungen der jeweiligen Anbieter.</p>
<h2>Ihre Rechte</h2><p>Sie haben das Recht auf Auskunft, Berichtigung, Löschung, Einschränkung der Verarbeitung, Datenübertragbarkeit und Widerspruch (Art. 15–21 DSGVO) sowie das Recht auf Beschwerde bei einer Datenschutz-Aufsichtsbehörde (Art. 77 DSGVO).</p>"""
    return imp, priv


def simple_page(path: str, title: str, inner: str) -> str:
    return page("de", path, path, f"{title} | Perceptron Data", title, f'<section class="prose">{inner}</section>', [])


# ------------------------------------------------------------------ output

def main() -> None:
    store = fetch_store()
    items = {a["name"]: {**a, "url": actor_url(a["name"])} for a in store}
    prices = {s: price_info(a) for s, a in items.items()}
    imp, priv = build_legal()

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "assets", OUT / "assets")

    def write(rel: str, text: str) -> None:
        target = OUT / rel.lstrip("/")
        if rel.endswith("/"):
            target = target / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    urls = []
    for lang in ("en", "de"):
        prefix = "" if lang == "en" else "/de"
        write(f"{prefix}/", build_index(lang, items, prices))
        urls.append((f"{prefix}/", "/de/" if lang == "en" else "/"))
        for slug, item in items.items():
            a = ACTORS.get(slug, {"icon": "logo-256.png", "group": "research", "unit": {}})
            write(f"{prefix}/actors/{slug}/", build_actor(slug, a, item, prices[slug], lang, items))
            urls.append((f"{prefix}/actors/{slug}/", f"{'/de' if lang == 'en' else ''}/actors/{slug}/"))
    write("/impressum/", simple_page("/impressum/", "Impressum", imp))
    write("/datenschutz/", simple_page("/datenschutz/", "Datenschutz", priv))
    write("/404.html", page("en", "/404.html", "/de/", "Not found | Perceptron Data", "Page not found",
                             '<section class="hero"><h1>Not found</h1><p><a href="/">Back to the catalogue</a></p></section>', []))

    # sitemap with hreflang pairs
    entries = []
    for path, alt in urls:
        en, de = (path, alt) if not path.startswith("/de/") else (alt, path)
        entries.append(f"""  <url><loc>{BASE}{path}</loc><lastmod>{TODAY}</lastmod>
    <xhtml:link rel="alternate" hreflang="en" href="{BASE}{en}"/>
    <xhtml:link rel="alternate" hreflang="de" href="{BASE}{de}"/></url>""")
    write("/sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
          'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(entries) + "\n</urlset>\n")
    write("/robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")

    # llms.txt: a plain summary for AI assistants and LLM-based search
    lines = ["# Perceptron Data", "", "> Data APIs on Apify for AI, sales and market research: document conversion, "
             "Google Ads Transparency checks, DACH company data, jobs, EU tenders and German registers. "
             "No login needed; paid actors charge per result.", ""]
    for g in GROUP_ORDER:
        slugs = [s for s, a in ACTORS.items() if a["group"] == g and s in items]
        if slugs:
            lines.append(f"## {GROUPS[g]['en']}")
            for s in slugs:
                lines.append(f"- [{items[s]['title']}]({actor_url(s)}): {ACTORS[s]['en']['desc']}")
            lines.append("")
    write("/llms.txt", "\n".join(lines))

    # machine-readable catalogue
    catalogue = [{"name": s, "title": items[s]["title"], "url": actor_url(s), "page": f"{BASE}/actors/{s}/",
                  "description": ACTORS.get(s, {}).get("en", {}).get("desc") or items[s].get("description"),
                  "pricePer1000Usd": None if prices[s]["free"] else round(prices[s]["per1000"], 4),
                  "unit": ACTORS.get(s, {}).get("unit", {}).get("en")} for s in items]
    write("/catalog.json", json.dumps({"updated": TODAY, "actors": catalogue}, indent=2, ensure_ascii=False))
    (OUT / ".nojekyll").write_text("")
    print(f"Built {len(urls)} pages for {len(items)} actors into {OUT}")


if __name__ == "__main__":
    main()
