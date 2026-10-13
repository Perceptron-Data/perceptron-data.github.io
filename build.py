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
import os
import re
import shutil
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from content import ACTORS, AGENT_TASKS, AGENTS, FLAGSHIPS, HOME, SECTIONS

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site"
BASE = "https://perceptron-data.github.io"
APIFY_USER = "perceptr0n"
STORE_API = f"https://api.apify.com/v2/store?username={APIFY_USER}&limit=100"
GITHUB_ORG = "https://github.com/Perceptron-Data"
APIFY_PROFILE = f"https://apify.com/{APIFY_USER}"
TODAY = datetime.now(tz=UTC).strftime("%Y-%m-%d")
# IndexNow (Bing, Yandex, Seznam, Naver, Yep): the key is public by design, the file at the root proves the site.
INDEXNOW_KEY = "3f9c5e08e6adb7bb9527f5ec9193afe0"
LASTMOD = "@@LASTMOD@@"      # replaced by the date of the page's last real change (see finish_dates)
MCP = "https://mcp.apify.com"

T = {
    "en": {"lang": "en", "home": "Home", "actors": "Actors", "run": "Run on Apify", "details": "Details",
           "features": "What you get", "uses": "Use cases", "example": "Example input", "faq": "FAQ",
           "price": "Price", "free": "Free", "per": "per 1,000", "cheaper": "Billed by Apify per result plus a small start fee per run — cheaper on paid Apify plans.",
           "title": "Perceptron Data – company checks from public sources",
           "meta": "Check, don't guess: company checks and data from public sources on Apify – who advertises on Google and Bing, who is behind a website. Built in Germany.",
           "related": "Related actors", "legal": "Legal notice", "privacy": "Privacy", "other": "Deutsch",
           "claim": "Check, don't guess.", "descriptor": "Company checks and data from public sources.",
           "origin": "Built in Germany. Focused on DACH and the EU.",
           "subline": "Paste a list of companies or domains and get one row per company with a traceable answer. Today there are two checks: whether a company advertises on Google or Microsoft Bing, and who is legally behind a website, with the EU VAT ID checked against VIES.",
           "cta_primary": "Try the Advertiser Check", "cta_secondary": "All actors on Apify",
           "how_title": "How it works",
           "how_steps": ["Paste your list of company domains or names – or set filters for the other actors.",
                         "Start the run on Apify – no login or API key for the data sources needed.",
                         "Get one row per company or record. Export to Excel, CSV or JSON, schedule it, or call it via API and MCP."],
           "how_note": "Pricing: paid per company checked or per record, plus a small start fee per run; on most actors, paid Apify plans pay less. A company that does not advertise or has no imprint is an answer and is charged.",
           "checks_note": "Every Sunday a watchdog runs the actors with inputs whose correct answers are known and publishes the result, failures included:",
           "updated": "Prices and catalogue updated daily from the Apify Store. Last update:",
           "disclaimer": "Independent provider, not affiliated with Apify or the data sources named.",
           "builtin": "Built in Germany",
           "allactors": "All actors", "start": "from", "checks": "Weekly checks",
           "startfee": "+ {fee} start fee per run", "startfee_unknown": "+ a small start fee per run",
           "agents_nav": "For AI agents", "updated_label": "Updated", "per_one": "per", "startfee_short": "+ {fee} per run",
           "code": "Run it from an AI agent or code", "mcp_tool": "MCP tool (Apify MCP server):", "curl": "HTTP API:",
           "agents_more": "Setup for Claude Code, Cursor and other agents"},
    "de": {"lang": "de", "home": "Start", "actors": "Actors", "run": "Auf Apify starten", "details": "Details",
           "features": "Das bekommen Sie", "uses": "Anwendungsfälle", "example": "Beispiel-Eingabe", "faq": "Häufige Fragen",
           "price": "Preis", "free": "Kostenlos", "per": "pro 1.000", "cheaper": "Abrechnung über Apify pro Ergebnis plus eine kleine Startgebühr je Lauf — günstiger in bezahlten Apify-Tarifen.",
           "title": "Perceptron Data – Firmen-Checks aus öffentlichen Quellen",
           "meta": "Prüfen statt raten: Firmen-Checks und Daten aus öffentlichen Quellen auf Apify – wer bei Google und Bing wirbt, wer hinter einer Website steht. Aus Deutschland.",
           "related": "Ähnliche Actors", "legal": "Impressum", "privacy": "Datenschutz", "other": "English",
           "claim": "Prüfen statt raten.", "descriptor": "Firmen-Checks und Daten aus öffentlichen Quellen.",
           "origin": "Aus Deutschland. Schwerpunkt DACH und EU.",
           "subline": "Firmen- oder Domainliste einfügen und je Firma eine Zeile mit nachvollziehbarer Antwort erhalten. Heute gibt es zwei Checks: ob eine Firma bei Google oder Microsoft Bing wirbt, und wer rechtlich hinter einer Website steht – mit gegen VIES geprüfter EU-USt-IdNr.",
           "cta_primary": "Werbe-Check ausprobieren", "cta_secondary": "Alle Actors auf Apify",
           "how_title": "So funktioniert es",
           "how_steps": ["Liste mit Domains oder Firmennamen einfügen – oder bei den übrigen Actors Filter setzen.",
                         "Den Lauf auf Apify starten – ohne Login oder API-Schlüssel bei den Datenquellen.",
                         "Eine Zeile je Firma oder Datensatz erhalten. Als Excel, CSV oder JSON exportieren, per Zeitplan wiederholen oder über API und MCP abrufen."],
           "how_note": "Preis: je geprüfter Firma oder je Datensatz plus einer kleinen Startgebühr je Lauf; bei den meisten Actors zahlen bezahlte Apify-Tarife weniger. Wirbt eine Firma nicht oder hat sie kein Impressum, ist das eine Antwort und wird berechnet.",
           "checks_note": "Jeden Sonntag führt ein Wachposten die Actors mit Eingaben aus, deren richtige Antworten bekannt sind, und veröffentlicht das Ergebnis, Fehlschläge eingeschlossen:",
           "updated": "Preise und Katalog täglich aus dem Apify Store aktualisiert. Stand:",
           "disclaimer": "Unabhängiger Anbieter, nicht verbunden mit Apify oder den genannten Datenquellen.",
           "builtin": "Aus Deutschland",
           "allactors": "Alle Actors", "start": "ab", "checks": "Prüfnachweis",
           "startfee": "+ {fee} Startgebühr je Lauf", "startfee_unknown": "+ eine kleine Startgebühr je Lauf",
           "agents_nav": "Für KI-Agenten", "updated_label": "Aktualisiert", "per_one": "je", "startfee_short": "+ {fee} je Lauf",
           "code": "Aus einem KI-Agenten oder per Code starten", "mcp_tool": "MCP-Werkzeug (Apify-MCP-Server):", "curl": "HTTP-API:",
           "agents_more": "Einrichtung für Claude Code, Cursor und andere Agenten"},
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


def default_memory(name: str) -> int | None:
    """Default run memory of an actor (public actor endpoint) — the start fee is charged per GB."""
    for attempt in range(3):
        try:
            with urllib.request.urlopen(f"https://api.apify.com/v2/acts/{APIFY_USER}~{name}", timeout=30) as response:
                return (json.load(response)["data"].get("defaultRunOptions") or {}).get("memoryMbytes")
        except Exception:  # network hiccup: retry, then show the fee without an amount
            time.sleep(3 * (attempt + 1))
    return None


def price_info(item: dict, event: str | None = None) -> dict:
    """Per-result price on the Free plan and on the cheapest tier: the Store's primary event, or the event the
    page text names (the advertiser check bills per company checked, while the Store's primary event is per ad)."""
    info = item.get("currentPricingInfo") or {}
    events = (info.get("pricingPerEvent") or {}).get("actorChargeEvents") or {}
    if info.get("pricingModel") != "PAY_PER_EVENT" or not events:
        return {"free": True}
    start = (events.get("apify-actor-start") or {}).get("eventPriceUsd")
    candidates = [(k, v) for k, v in events.items() if k != "apify-actor-start"]
    main = next(((k, v) for k, v in candidates if k == event), None) or \
        next(((k, v) for k, v in candidates if v.get("isPrimaryEvent")), candidates[0] if candidates else None)
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
    # Apify charges the start event once per GB of run memory (at least once): the default memory decides.
    gb = max(1, round((item.get("defaultMemoryMbytes") or 1024) / 1024))
    return {"free": False, "per1000": high * 1000, "from1000": low * 1000,
            "start": None if start is None else start * gb}


def money(value: float, lang: str) -> str:
    # $5.00, $0.01, $0.015, $0.0005 — never rounded away (a price of $0.015 shown as $0.01 would be wrong)
    text = f"{value:,.2f}" if value >= 1 or value == 0 else f"{value:.6f}".rstrip("0")
    if value and value < 1 and len(text.split(".")[1]) < 2:
        text = f"{value:.2f}"
    if lang == "de":
        return text.replace(",", "X").replace(".", ",").replace("X", ".") + " $"
    return "$" + text


# ------------------------------------------------------------------ html

def esc(text) -> str:
    return html.escape(str(text), quote=True)


VERIFY = ROOT / "data" / "verification.json"   # {"google": "<content of the meta tag>", "bing": "…"} from Tom


def verification_tags() -> str:
    tags = load_data(VERIFY)
    names = {"google": "google-site-verification", "bing": "msvalidate.01"}
    return "\n".join(f'<meta name="{names[k]}" content="{esc(v)}">' for k, v in tags.items() if k in names and v)


def page(lang: str, path: str, alt_path: str, title: str, desc: str, body: str,
         jsonld: list[dict], og_image: str = "/assets/og/default.png", robots: str | None = None,
         markdown: bool = True, dated: bool = True) -> str:
    t = T[lang]
    en_path, de_path = (path, alt_path) if lang == "en" else (alt_path, path)
    ld = "\n".join(f'<script type="application/ld+json">{json.dumps(d, ensure_ascii=False)}</script>' for d in jsonld)
    md = f'<link rel="alternate" type="text/markdown" href="{path}index.md">' if markdown and path.endswith("/") else ""
    updated = (f'<p class="updated-line muted">{t["updated_label"]} <time class="updated" datetime="{LASTMOD}">{LASTMOD}</time></p>'
               if dated else "")
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{f'<meta name="robots" content="{esc(robots)}">' if robots else ''}
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
{md}
{verification_tags() if path in ("/", "/de/") else ""}
{ld}
</head>
<body>
<header class="top"><div class="wrap">
  <a class="brand" href="{'/' if lang == 'en' else '/de/'}"><img src="/assets/logo-64.png" alt="" width="32" height="32">Perceptron Data</a>
  <nav><a href="{'/' if lang == 'en' else '/de/'}#actors">{t['actors']}</a><a href="{'/agents/' if lang == 'en' else '/de/agents/'}">{t['agents_nav']}</a><a href="{'/quality/' if lang == 'en' else '/de/quality/'}">{t['checks']}</a><a href="{alt_path}" hreflang="{'de' if lang == 'en' else 'en'}" lang="{'de' if lang == 'en' else 'en'}">{t['other']}</a></nav>
</div></header>
<main class="wrap">
{body}
{updated}
</main>
<footer><div class="wrap">
  <p>Perceptron Data · {T[lang]['claim']} · {t['builtin']} · {t['disclaimer']}</p>
  <p class="built">{t['updated']} {TODAY}.</p>
  <p><a href="{APIFY_PROFILE}">Apify</a> · <a href="{GITHUB_ORG}">GitHub</a> · <a href="/impressum/">{t['legal']}</a> · <a href="/datenschutz/">{t['privacy']}</a> · <a href="{alt_path}" hreflang="{'de' if lang == 'en' else 'en'}" lang="{'de' if lang == 'en' else 'en'}">{t['other']}</a></p>
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
    # Brand rule: a price per result is never shown without the start fee.
    fee = t["startfee"].format(fee=money(p["start"], lang)) if p.get("start") else t["startfee_unknown"]
    return f'<span class="price">{main}</span> <span class="muted">{fee}</span>'


SINGULAR = {"companies checked": "company checked", "queries": "query", "Websites": "Website", "Fragen": "Frage",
            "Seiten": "Seite", "geprüfte Firmen": "geprüfte Firma", "Datensätze": "Datensatz", "Stellen": "Stelle",
            "Ausschreibungen": "Ausschreibung", "Anlagen": "Anlage", "Anfragen": "Anfrage", "Apps": "App"}


def price_text(p: dict, unit: str, lang: str) -> str:
    """Price of one result for an agent: "$0.005 per website + $0.01 per run" (plain text, no HTML)."""
    t = T[lang]
    if p["free"]:
        return t["free"]
    one = SINGULAR.get(unit) or (unit[:-1] if lang == "en" and unit.endswith("s") else unit)
    text = f"{money(p['per1000'] / 1000, lang)} {t['per_one']} {one}"
    return text + (" " + t["startfee_short"].format(fee=money(p["start"], lang)) if p.get("start") else "")


def run_snippets(slug: str, example: dict) -> tuple[str, str]:
    """MCP tool name and a curl call that starts a run and returns the rows (run-sync-get-dataset-items)."""
    body = json.dumps(example, ensure_ascii=False)
    curl = (f'curl -X POST "https://api.apify.com/v2/acts/{APIFY_USER}~{slug}/run-sync-get-dataset-items" \\\n'
            f'  -H "Authorization: Bearer $APIFY_TOKEN" -H "Content-Type: application/json" \\\n'
            f"  -d '{body}'")
    return mcp_tool(slug), curl


def mcp_tool(slug: str) -> str:
    """Name of the actor's tool on Apify's MCP server (checked 13.10.2026: "perceptr0n--research-agent")."""
    return f"{APIFY_USER}--{slug}"


def card(slug: str, a: dict, item: dict, p: dict, lang: str) -> str:
    c = a.get(lang) or {}
    t = T[lang]
    href = f"/actors/{slug}/" if lang == "en" else f"/de/actors/{slug}/"
    title = c.get("h1") or item["title"]
    return f"""<article class="card">
  <img src="/assets/icons/{esc(a.get('icon', 'logo-256.png'))}" alt="" width="56" height="56" loading="lazy">
  <div><h3><a href="{href}">{esc(title)}</a></h3>
  <p>{esc(c.get('card') or c.get('desc') or item.get('description', ''))}</p>
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
    # Brand texts carry their full title (EN "<name> – Perceptron Data", DE keyword-first); others get the suffix.
    title = c.get("title") or f"{item['title']} – Perceptron Data"
    feats = "".join(f"<li>{esc(x)}</li>" for x in c.get("features", []))
    uses = "".join(f"<li>{esc(x)}</li>" for x in c.get("uses", []))
    faq = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(ans)}</p></details>" for q, ans in c.get("faq", []))
    related = [s for s, o in ACTORS.items() if o["group"] == a["group"] and s != slug and s in all_items][:3]
    rel = "".join(f'<li><a href="{"/actors/" if lang == "en" else "/de/actors/"}{s}/">{esc(display_name(s, all_items[s], lang))}</a></li>' for s in related)
    body = f"""<nav class="crumbs"><a href="{'/' if lang == 'en' else '/de/'}">{t['home']}</a> › {esc(h1)}</nav>
<section class="hero actor">
  <img src="/assets/icons/{esc(a.get('icon', 'logo-256.png'))}" alt="" width="96" height="96">
  <div><h1>{esc(h1)}</h1><p class="lead">{esc(c.get('intro') or item.get('description', ''))}</p>
  <p><a class="button" href="{actor_url(slug)}">{t['run']}</a> {price_html(p, unit, lang)}</p></div>
</section>
{f'<section><h2>{t["features"]}</h2><ul class="ticks">{feats}</ul></section>' if feats else ''}
{f'<section><h2>{t["uses"]}</h2><ul>{uses}</ul></section>' if uses else ''}
{code_section(slug, a, lang)}
<section><h2>{t['price']}</h2><p>{price_html(p, unit, lang)}</p><p class="muted">{esc(c.get('price_note') or t['cheaper'])}</p></section>
{quality_html(slug, lang)}
{f'<section><h2>{t["faq"]}</h2>{faq}</section>' if faq else ''}
{f'<section><h2>{t["related"]}</h2><ul>{rel}</ul></section>' if rel else ''}
<p><a class="button" href="{actor_url(slug)}">{t['run']}</a></p>"""
    offer = {"@type": "Offer", "priceCurrency": "USD", "url": actor_url(slug),
             "price": 0 if p["free"] else round(p["per1000"], 2)}
    if not p["free"]:
        offer["priceSpecification"] = {"@type": "UnitPriceSpecification", "price": round(p["per1000"], 2), "priceCurrency": "USD",
                                       "referenceQuantity": {"@type": "QuantitativeValue", "value": 1000, "unitText": unit}}
    ld = [{"@context": "https://schema.org", "@type": "SoftwareApplication", "name": h1, "description": desc,
           "applicationCategory": "DeveloperApplication", "operatingSystem": "Web (Apify platform)", "url": f"{BASE}{path}",
           "sameAs": actor_url(slug), "dateModified": LASTMOD,
           "image": f"{BASE}/assets/icons/{a.get('icon', 'logo-256.png')}", "offers": offer,
           "publisher": {"@type": "Organization", "name": "Perceptron Data", "url": BASE}},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": t["home"], "item": BASE + ("/" if lang == "en" else "/de/")},
              {"@type": "ListItem", "position": 2, "name": h1, "item": f"{BASE}{path}"}]}]
    if c.get("faq"):
        ld.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in c["faq"]]})
    og = f"/assets/og/{slug}.png" if (ROOT / "assets" / "og" / f"{slug}.png").exists() else "/assets/og/default.png"
    return page(lang, path, alt, title, desc, body, ld, og, robots=c.get("robots"))


def code_section(slug: str, a: dict, lang: str) -> str:
    """Example input, plus how an agent (MCP) or a program (HTTP) starts the same run."""
    example = (AGENT_TASKS.get(slug) or {}).get("input") or a.get("example")
    if not example:
        return ""
    t = T[lang]
    tool, curl = run_snippets(slug, example)
    agents = "/agents/" if lang == "en" else "/de/agents/"
    return (f'<section><h2>{t["code"]}</h2><p>{t["example"]}:</p><pre><code>{esc(json.dumps(example, indent=2, ensure_ascii=False))}</code></pre>'
            f'<p>{t["mcp_tool"]} <code>{esc(tool)}</code></p><p>{t["curl"]}</p><pre><code>{esc(curl)}</code></pre>'
            f'<p><a href="{agents}">{t["agents_more"]} →</a></p></section>')


def display_name(slug: str, item: dict, lang: str) -> str:
    """Canonical product name (brand texts), else the Store title."""
    return ((ACTORS.get(slug) or {}).get(lang) or {}).get("h1") or item["title"]


QUALITY = ROOT / "data" / "quality.json"     # written by the watchdog after its Sunday check
SAMPLES = ROOT / "data" / "samples.json"     # field-by-field comparison with the original source (by hand, dated)
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

Q = {
    "en": {"h1": "Weekly checks against known answers", "page_h1": "Weekly check: {title}",
           "lead": "Every Sunday an automated watchdog runs the live actors on Apify with fixed inputs whose correct "
                   "answers are known, and checks the content of the results — not only whether the run succeeded. The "
                   "results are published here as they are, failures included.",
           "planned": "First public check on {date}. Until then this page lists what will be checked.",
           "last": "Last check on {date}: {passed} of {checked} cases passed", "notes": ", {n} of them with a note",
           "since": "Checked weekly since {date}.", "case": "Case", "result": "Result", "time": "Time",
           "what": "What is checked", "details": "Details", "open": "Failures and notes from the last check",
           "none_open": "None — every case gave the known answer.", "history": "Earlier checks", "date": "Date",
           "passed": "Passed", "sample": "Sample against the original source",
           "sample_text": "On {date} we took {rows} result rows and compared {compared} field values one by one with the "
                          "original source: {matched} matched ({rate}).",
           "row": "Row", "field": "Field", "ours": "Actor output", "source": "Original source", "cause": "Cause",
           "no_miss": "No differences found.", "misses": "Every difference and its cause",
           "matched_col": "Matched", "rate_col": "Rate",
           "precision": "Of the values the actor delivered, {correct} of {delivered} were correct ({rate}); {missing} values that the source shows were not delivered.",
           "limits": "What this shows: on the day of the check, the live actor gave the known answers for these inputs. "
                     "It does not prove that every result is correct.",
           "limits_sample": "The sample against the original source measures accuracy on real result rows.",
           "see": "See every case and result", "see_planned": "See what will be checked", "actor": "Actor",
           "last_col": "Last check", "not_yet": "first check on {date}", "sources": "{n} sources, strongest evidence: {level}",
           "example": "published example", "others": "Not in the content check yet: {names}. They are run once a week with "
                                                     "an empty input like Apify's own test (does it run and return data?), "
                                                     "but their results are not checked against known answers.",
           "labels": {"ok": "✅ passed", "note": "⚠️ passed with a note", "fail": "❌ failed", None: "– not checked yet"},
           "back": "Back to the actor", "title_suffix": "Weekly check"},
    "de": {"h1": "Wöchentliche Prüfung mit bekannten Antworten", "page_h1": "Wöchentliche Prüfung: {title}",
           "lead": "Jeden Sonntag führt ein automatischer Wachposten die Live-Actors auf Apify mit festen Eingaben aus, "
                   "deren richtige Antworten bekannt sind, und prüft den Inhalt der Ergebnisse — nicht nur, ob der Lauf "
                   "gelang. Die Ergebnisse stehen hier so, wie sie sind — Fehlschläge eingeschlossen.",
           "planned": "Erste öffentliche Prüfung am {date}. Bis dahin steht hier, was geprüft wird.",
           "last": "Letzte Prüfung am {date}: {passed} von {checked} Fällen bestanden", "notes": ", davon {n} mit Hinweis",
           "since": "Wöchentlich geprüft seit {date}.", "case": "Fall", "result": "Ergebnis", "time": "Dauer",
           "what": "Was geprüft wird", "details": "Einzelheiten", "open": "Fehler und Hinweise aus der letzten Prüfung",
           "none_open": "Keine — jeder Fall lieferte die bekannte Antwort.", "history": "Frühere Prüfungen", "date": "Datum",
           "passed": "Bestanden", "sample": "Stichprobe gegen die Originalquelle",
           "sample_text": "Am {date} haben wir {rows} Ergebniszeilen genommen und {compared} Feldwerte einzeln mit der "
                          "Originalquelle verglichen: {matched} stimmten ({rate}).",
           "row": "Zeile", "field": "Feld", "ours": "Ausgabe des Actors", "source": "Originalquelle", "cause": "Ursache",
           "no_miss": "Keine Abweichung gefunden.", "misses": "Jede Abweichung mit Ursache",
           "matched_col": "Stimmt", "rate_col": "Quote",
           "precision": "Von den Werten, die der Actor geliefert hat, stimmten {correct} von {delivered} ({rate}); {missing} Werte, die die Quelle zeigt, fehlten.",
           "limits": "Was das zeigt: Am Prüftag lieferte der Live-Actor für diese Eingaben die bekannten Antworten. Dass "
                     "jedes Ergebnis stimmt, beweist es nicht.",
           "limits_sample": "Die Stichprobe gegen die Originalquelle misst die Genauigkeit an echten Ergebniszeilen.",
           "see": "Alle Fälle und Ergebnisse ansehen", "see_planned": "Ansehen, was geprüft wird", "actor": "Actor",
           "last_col": "Letzte Prüfung", "not_yet": "erste Prüfung am {date}", "sources": "{n} Quellen, stärkste Evidenz: {level}",
           "example": "veröffentlichtes Beispiel", "others": "Noch nicht in der inhaltlichen Prüfung: {names}. Sie laufen einmal "
                                                             "wöchentlich mit leerer Eingabe wie Apifys eigener Test (läuft er, "
                                                             "liefert er Daten?), ihre Ergebnisse werden aber nicht mit bekannten "
                                                             "Antworten verglichen.",
           "labels": {"ok": "✅ bestanden", "note": "⚠️ bestanden mit Hinweis", "fail": "❌ fehlgeschlagen", None: "– noch nicht geprüft"},
           "back": "Zurück zum Actor", "title_suffix": "Wöchentliche Prüfung"},
}


def load_data(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def fmt_date(iso: str | None, lang: str) -> str:
    if not iso:
        return "–"
    y, m, d = (int(x) for x in iso[:10].split("-"))
    return f"{d} {MONTHS[m - 1]} {y}" if lang == "en" else f"{d:02d}.{m:02d}.{y}"


def fmt_rate(rate: float, lang: str) -> str:
    text = f"{100 * rate:.1f}"
    return f"{text}%" if lang == "en" else text.replace(".", ",") + " %"


def quality_path(slug: str, lang: str) -> str:
    return f"/actors/{slug}/quality/" if lang == "en" else f"/de/actors/{slug}/quality/"


def quality_summary(q: dict, lang: str) -> str:
    """One sentence: planned date, or last result and since when."""
    L = Q[lang]
    if not q.get("date"):
        return L["planned"].format(date=fmt_date(q.get("planned"), lang))
    notes = sum(1 for e in q.get("examples") or [] if e.get("result") == "note")
    text = L["last"].format(date=fmt_date(q["date"], lang), passed=q.get("passed", 0), checked=q.get("checked", 0))
    text += (L["notes"].format(n=notes) if notes else "") + "."
    since = q.get("since") or ((q.get("history") or [{}])[-1]).get("date")
    return text + (" " + L["since"].format(date=fmt_date(since, lang)) if since else "")


def sample_summary(s: dict, lang: str) -> str:
    return Q[lang]["sample_text"].format(date=fmt_date(s.get("date"), lang), rows=s.get("rows"), compared=s.get("compared"),
                                          matched=s.get("matched"), rate=fmt_rate(s.get("rate") or 0, lang))


def quality_html(slug: str, lang: str) -> str:
    """Short section on the actor page; the details live on the proof page."""
    q = load_data(QUALITY).get(slug)
    sample = load_data(SAMPLES).get(slug)
    if not q and not sample:
        return ""
    L = Q[lang]
    head = "Wöchentliche Qualitätsprüfung" if lang == "de" else "Weekly quality check"
    parts = []
    if q:
        parts.append(f"<p>{esc(L['lead'])}</p><p><strong>{esc(quality_summary(q, lang))}</strong></p>")
    if sample:
        parts.append(f"<p>{esc(L['sample'])}: {esc(sample_summary(sample, lang))}</p>")
    link = L["see"] if (q or {}).get("date") or not q else L["see_planned"]
    return (f'<section><h2>{head}</h2>{"".join(parts)}'
            f'<p><a href="{quality_path(slug, lang)}">{esc(link)} →</a></p></section>')


def _case_details(e: dict, lang: str) -> str:
    L = Q[lang]
    bits = []
    checks = (e.get("checks") or {}).get(lang) or []
    if checks:
        bits.append("<ul>" + "".join(f"<li>{esc(c)}</li>" for c in checks) + "</ul>")
    if e.get("sources") is not None or e.get("strongest"):
        bits.append(f"<p>{esc(L['sources'].format(n=e.get('sources') if e.get('sources') is not None else '–', level=e.get('strongest') or '–'))}</p>")
    if e.get("link"):
        bits.append(f'<p><a href="{esc(e["link"])}">{esc(L["example"])} →</a></p>')
    return "".join(bits) or "–"


def build_quality_page(slug: str, item: dict, q: dict | None, sample: dict | None, lang: str) -> str:
    L = Q[lang]
    t = T[lang]
    path, alt = quality_path(slug, lang), quality_path(slug, "de" if lang == "en" else "en")
    actor_path = f"/actors/{slug}/" if lang == "en" else f"/de/actors/{slug}/"
    title = display_name(slug, item, lang)
    sections = []
    if q:
        examples = q.get("examples") or []
        rows = "".join(
            f'<tr id="{esc(e.get("slug"))}"><td>{esc(e.get("title_de") if lang == "de" and e.get("title_de") else e.get("title"))}</td>'
            f'<td>{esc(L["labels"].get(e.get("result"), "–"))}</td>'
            f'<td>{"–" if e.get("result") is None else str(round(e.get("seconds") or 0)) + " s"}</td>'
            f'<td>{_case_details(e, lang)}</td></tr>' for e in examples)
        sections.append(f'<section><p class="lead"><strong>{esc(quality_summary(q, lang))}</strong></p>'
                        f'<div class="table"><table><thead><tr><th>{L["case"]}</th><th>{L["result"]}</th><th>{L["time"]}</th>'
                        f'<th>{L["what"]}</th></tr></thead><tbody>{rows}</tbody></table></div></section>')
        if q.get("date"):
            problems = [e for e in examples if e.get("result") in ("fail", "note")]
            if problems:
                items_html = "".join(
                    f'<li><strong>{esc(L["labels"][e["result"]])}</strong> — '
                    f'{esc(e.get("title_de") if lang == "de" and e.get("title_de") else e.get("title"))}: '
                    f'{esc("; ".join(((e.get("reasons") or {}).get(lang)) or []) or "–")}</li>' for e in problems)
                sections.append(f'<section><h2>{L["open"]}</h2><ul>{items_html}</ul></section>')
            else:
                sections.append(f'<section><h2>{L["open"]}</h2><p>{esc(L["none_open"])}</p></section>')
        history = q.get("history") or []
        if len(history) > 1:
            rows = "".join(f'<tr><td>{fmt_date(h.get("date"), lang)}</td><td>{h.get("passed")} / {h.get("checked")}</td></tr>'
                           for h in history)
            sections.append(f'<section><h2>{L["history"]}</h2><div class="table"><table><thead><tr><th>{L["date"]}</th>'
                            f'<th>{L["passed"]}</th></tr></thead><tbody>{rows}</tbody></table></div></section>')
    if sample:
        misses = sample.get("misses") or []
        method = (sample.get("method") or {}).get(lang) or ""
        body = f"<p><strong>{esc(sample_summary(sample, lang))}</strong></p>"
        if sample.get("delivered"):
            body += f"<p>{esc(L['precision'].format(correct=sample['deliveredCorrect'], delivered=sample['delivered'], rate=fmt_rate(sample['deliveredRate'], lang), missing=sample.get('missing', 0)))}</p>"
        body += f"<p>{esc(method)}</p>" if method else ""
        breakdown = sample.get("breakdown") or {}
        if breakdown.get("items"):
            rows = "".join(
                f'<tr><td>{esc(b.get("name"))}</td><td>{b.get("matched")} / {b.get("compared")}</td>'
                f'<td>{fmt_rate((b.get("matched") or 0) / b["compared"], lang) if b.get("compared") else "–"}</td></tr>'
                for b in breakdown["items"])
            body += (f'<div class="table"><table><thead><tr><th>{esc((breakdown.get("label") or {}).get(lang, ""))}</th>'
                     f'<th>{L["matched_col"]}</th><th>{L["rate_col"]}</th></tr></thead><tbody>{rows}</tbody></table></div>')
        if misses:
            rows = "".join(f'<tr><td>{esc(m.get("row"))}</td><td>{esc(m.get("field"))}</td><td>{esc(m.get("ours") if m.get("ours") not in (None, "") else "–")}</td>'
                           f'<td>{esc(m.get("source") if m.get("source") not in (None, "") else "–")}</td><td>{esc((m.get("cause") or {}).get(lang) or "–")}</td></tr>'
                           for m in misses)
            body += (f'<h3>{L["misses"]}</h3><div class="table"><table><thead><tr><th>{L["row"]}</th><th>{L["field"]}</th>'
                     f'<th>{L["ours"]}</th><th>{L["source"]}</th><th>{L["cause"]}</th></tr></thead><tbody>{rows}</tbody></table></div>')
        else:
            body += f"<p>{esc(L['no_miss'])}</p>"
        sections.append(f'<section><h2>{L["sample"]}</h2>{body}</section>')
    sections.append(f'<section><p class="muted">{esc(L["limits"] + (" " + L["limits_sample"] if sample else ""))}</p></section>')
    body = f"""<nav class="crumbs"><a href="{'/' if lang == 'en' else '/de/'}">{t['home']}</a> › <a href="{actor_path}">{esc(title)}</a> › {esc(L['title_suffix'])}</nav>
<section class="hero"><h1>{esc(L['page_h1'].format(title=title))}</h1><p class="lead">{esc(L['lead'])}</p></section>
{''.join(sections)}
<p><a class="button" href="{actor_url(slug)}">{t['run']}</a> <a href="{actor_path}">{esc(L['back'])}</a></p>"""
    desc = quality_summary(q, lang) if q else sample_summary(sample, lang)
    ld = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": t["home"], "item": BASE + ("/" if lang == "en" else "/de/")},
        {"@type": "ListItem", "position": 2, "name": title, "item": f"{BASE}{actor_path}"},
        {"@type": "ListItem", "position": 3, "name": L["title_suffix"], "item": f"{BASE}{path}"}]}]
    return page(lang, path, alt, f"{L['title_suffix']}: {title} | Perceptron Data", desc, body, ld, markdown=False)


def build_quality_index(lang: str, items: dict) -> str:
    L = Q[lang]
    quality, samples = load_data(QUALITY), load_data(SAMPLES)
    path, alt = ("/quality/", "/de/quality/") if lang == "en" else ("/de/quality/", "/quality/")
    rows = []
    for slug in [s for s in ACTORS if s in items and (s in quality or s in samples)] + \
                [s for s in items if s not in ACTORS and (s in quality or s in samples)]:
        q, sample = quality.get(slug) or {}, samples.get(slug)
        if q.get("date"):
            last = f'{fmt_date(q["date"], lang)}: {q.get("passed")} / {q.get("checked")}'
        elif q.get("planned"):
            last = L["not_yet"].format(date=fmt_date(q["planned"], lang))
        else:
            last = "–"
        rate = f'{fmt_rate(sample.get("rate") or 0, lang)} ({sample.get("matched")} / {sample.get("compared")})' if sample else "–"
        rows.append(f'<tr><td><a href="{quality_path(slug, lang)}">{esc(display_name(slug, items[slug], lang))}</a></td><td>{esc(last)}</td><td>{esc(rate)}</td></tr>')
    others = [display_name(s, items[s], lang) for s in items if s not in quality and s not in samples]
    body = f"""<section class="hero"><h1>{esc(L['h1'])}</h1><p class="lead">{esc(L['lead'])}</p></section>
<section><div class="table"><table><thead><tr><th>{L['actor']}</th><th>{L['last_col']}</th><th>{L['sample']}</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div></section>
{f'<section><p class="muted">{esc(L["others"].format(names=", ".join(others)))}</p></section>' if others else ''}
<section><p class="muted">{esc(L['limits'] + (' ' + L['limits_sample'] if samples else ''))}</p></section>"""
    return page(lang, path, alt, f"{L['h1']} | Perceptron Data", L["lead"], body, [], markdown=False)


def mcp_url(slugs: list[str]) -> str:
    return f"{MCP}?tools=" + ",".join(f"{APIFY_USER}/{s}" for s in slugs)


def flagship(slug: str, item: dict, p: dict, lang: str) -> str:
    """A larger card: what the actor returns, its price and two ways in."""
    a, t = ACTORS[slug], T[lang]
    c = a.get(lang) or {}
    href = f"/actors/{slug}/" if lang == "en" else f"/de/actors/{slug}/"
    feats = "".join(f"<li>{esc(x)}</li>" for x in (c.get("features") or [])[:3])
    return f"""<article class="flag">
  <div class="flag-head"><img src="/assets/icons/{esc(a.get('icon', 'logo-256.png'))}" alt="" width="56" height="56" loading="lazy">
  <h3><a href="{href}">{esc(display_name(slug, item, lang))}</a></h3></div>
  <p>{esc(c.get('card') or c.get('desc') or '')}</p>
  <ul class="ticks">{feats}</ul>
  <p class="meta">{price_html(p, a.get('unit', {}).get(lang, 'results'), lang)}</p>
  <p><a class="button small" href="{actor_url(slug)}">{t['run']}</a> <a href="{href}">{t['details']} →</a></p>
</article>"""


def build_index(lang: str, items: dict, prices: dict) -> str:
    t, h = T[lang], HOME[lang]
    path, alt = ("/", "/de/") if lang == "en" else ("/de/", "/")
    prefix = "/" if lang == "en" else "/de/"
    sections = []
    for sec in SECTIONS:
        slugs = [s for s in sec["actors"] if s in items]
        tag = f"h{sec['level'] + 1}"
        cards = f'<div class="grid">{"".join(card(s, ACTORS[s], items[s], prices[s], lang) for s in slugs)}</div>' if slugs else ""
        if slugs or sec["level"] == 2:
            sections.append(f'<section id="{sec["key"]}" class="family l{sec["level"]}"><{tag}>{esc(sec[lang]["heading"])}</{tag}>'
                            f'<p class="muted">{esc(sec[lang]["intro"])}</p>{cards}</section>')
    listed = {s for sec in SECTIONS for s in sec["actors"]}
    extra = [s for s in items if s not in listed]  # published on Apify but no texts yet
    if extra:
        cards = "\n".join(card(s, {"icon": "logo-256.png", "group": "", "unit": {}}, items[s], prices[s], lang) for s in extra)
        sections.append(f'<section><h3>{t["allactors"]}</h3><div class="grid">{cards}</div></section>')
    steps = "".join(f"<li>{esc(x)}</li>" for x in t["how_steps"])
    quality = "/quality/" if lang == "en" else "/de/quality/"
    def source(src: str, link: str | None) -> str:
        return f'<a href="{quality_path(link, lang)}">{esc(src)}</a>' if link else esc(src)

    proof = "".join(f'<div class="proof-item"><strong>{esc(n)}</strong><span>{esc(what)}</span>'
                    f'<small>{source(src, link)}</small></div>' for n, what, src, link in h["proof"])
    flags = "".join(flagship(s, items[s], prices[s], lang) for s in FLAGSHIPS if s in items)
    rows = "".join("<tr>" + "".join(f"<td>{esc(cell)}</td>" for cell in row) + "</tr>" for row in h["rows"])
    head = "".join(f"<th>{esc(x)}</th>" for x in h["rows_head"])
    faq = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(ans)}</p></details>" for q, ans in h["faq"])
    agents = "/agents/" if lang == "en" else "/de/agents/"
    research = "/actors/research-agent/" if lang == "en" else "/de/actors/research-agent/"
    body = f"""<section class="hero home"><h1>{esc(t['claim'])}</h1>
<p class="descriptor">{esc(t['descriptor'])}</p>
<p class="lead">{esc(h['lead'])}</p>
<p class="muted">{esc(t['origin'])}</p>
<p class="ctas"><a class="button" href="{actor_url('imprint-impressum-website-contact-scraper')}">{esc(h['cta_primary'])}</a>
<a class="button ghost" href="{research}">{esc(h['cta_research'])}</a> <a href="{agents}">{esc(h['cta_agents'])} →</a></p></section>
<section id="proof"><h2>{esc(h['proof_title'])}</h2><div class="proof">{proof}</div>
<p class="muted">{esc(h['proof_note'])} <a href="{quality}">{esc(t['checks'])} →</a></p></section>
<section id="start"><h2>{esc(h['flag_title'])}</h2><p class="muted">{esc(h['flag_intro'])}</p><div class="flags">{flags}</div></section>
<section id="rows"><h2>{esc(h['rows_title'])}</h2><p>{esc(h['rows_intro'])}</p>
<div class="table"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>
<p class="muted">{esc(h['research_row'])}</p></section>
<section id="agents" class="band"><h2>{esc(h['agents_title'])}</h2><p>{esc(h['agents_text'])}</p>
<pre><code>{esc(mcp_url(FLAGSHIPS[:2]))}</code></pre><p><a href="{agents}">{esc(h['agents_link'])} →</a></p></section>
<section id="how"><h2>{esc(t['how_title'])}</h2><ol>{steps}</ol><p class="muted">{esc(t['how_note'])}</p></section>
<section id="actors"><h2>{esc(h['all_title'])}</h2>{''.join(sections)}</section>
<section id="faq"><h2>{esc(h['faq_title'])}</h2>{faq}</section>"""
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": "Perceptron Data", "url": BASE + "/",
           "inLanguage": lang},
          {"@context": "https://schema.org", "@type": "Organization", "name": "Perceptron Data", "url": BASE,
           "slogan": t["claim"], "description": t["descriptor"],
           "logo": f"{BASE}/assets/logo-256.png", "sameAs": [APIFY_PROFILE, GITHUB_ORG]},
          {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
              {"@type": "ListItem", "position": i + 1, "url": f"{BASE}{prefix}actors/{s}/",
               "name": display_name(s, items[s], lang)} for i, s in enumerate(items)]},
          {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
              {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in h["faq"]]}]
    return page(lang, path, alt, t["title"], t["meta"], body, ld)


def agent_rows(items: dict, prices: dict, lang: str) -> list[tuple[str, str, str, str, str]]:
    """(slug, task, MCP tool, example input as JSON, price per result) — flagships first."""
    order = [s for s in FLAGSHIPS if s in items] + [s for s in AGENT_TASKS if s in items and s not in FLAGSHIPS]
    rows = []
    for slug in order:
        task = AGENT_TASKS[slug]
        example = task.get("input") or ACTORS.get(slug, {}).get("example") or {}
        unit = ACTORS.get(slug, {}).get("unit", {}).get(lang, "results")
        rows.append((slug, task[lang], mcp_tool(slug), json.dumps(example, ensure_ascii=False),
                     price_text(prices[slug], unit, lang)))
    return rows


def agents_snippets() -> dict:
    url = mcp_url(FLAGSHIPS)
    config = json.dumps({"mcpServers": {"perceptron-data": {"url": url}}}, indent=2)
    tool, curl = run_snippets("imprint-impressum-website-contact-scraper", AGENT_TASKS["imprint-impressum-website-contact-scraper"]["input"])
    return {"url": url, "claude": f'claude mcp add --transport http perceptron-data "{url}"', "json": config, "curl": curl}


def build_agents(lang: str, items: dict, prices: dict) -> str:
    g, t = AGENTS[lang], T[lang]
    path, alt = ("/agents/", "/de/agents/") if lang == "en" else ("/de/agents/", "/agents/")
    sn = agents_snippets()
    prefix = "/actors/" if lang == "en" else "/de/actors/"
    rows = "".join(f'<tr><td><a href="{prefix}{slug}/">{esc(task)}</a></td><td><code>{esc(tool)}</code></td>'
                   f'<td><code>{esc(example)}</code></td><td>{esc(price)}</td></tr>'
                   for slug, task, tool, example, price in agent_rows(items, prices, lang))
    head = "".join(f"<th>{esc(x)}</th>" for x in g["head"])
    notes = "".join(f"<li>{esc(x)}</li>" for x in g["notes"])
    links = ["/llms.txt", "/catalog.json", path + "index.md"]
    machine = "".join(f'<li><a href="{href}">{esc(label)}</a> – {esc(text)}</li>'
                      for href, (label, text) in zip(links, g["machine_items"]))
    body = f"""<nav class="crumbs"><a href="{'/' if lang == 'en' else '/de/'}">{t['home']}</a> › {esc(g['h1'])}</nav>
<section class="hero"><h1>{esc(g['h1'])}</h1><p class="lead">{esc(g['lead'])}</p></section>
<section><h2>{esc(g['connect'])}</h2>
<p>{esc(g['mcp_url'])}</p><pre><code>{esc(sn['url'])}</code></pre>
<p>{esc(g['claude'])}</p><pre><code>{esc(sn['claude'])}</code></pre>
<p>{esc(g['json'])}</p><pre><code>{esc(sn['json'])}</code></pre>
<p class="muted">{esc(g['token'])}</p>
<p>{esc(g['api'])}</p><pre><code>{esc(sn['curl'])}</code></pre>
<p class="muted">{esc(g['search'])}</p></section>
<section><h2>{esc(g['table'])}</h2><div class="table"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div></section>
<section><h2>{esc(g['know'])}</h2><ul>{notes}</ul></section>
<section><h2>{esc(g['machine'])}</h2><ul>{machine}</ul></section>"""
    ld = [{"@context": "https://schema.org", "@type": "TechArticle", "headline": g["h1"], "description": g["desc"],
           "inLanguage": lang, "url": f"{BASE}{path}", "dateModified": LASTMOD,
           "publisher": {"@type": "Organization", "name": "Perceptron Data", "url": BASE}},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": t["home"], "item": BASE + ("/" if lang == "en" else "/de/")},
              {"@type": "ListItem", "position": 2, "name": g["h1"], "item": f"{BASE}{path}"}]}]
    return page(lang, path, alt, g["title"], g["desc"], body, ld)


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
    return page("de", path, path, f"{title} | Perceptron Data", title, f'<section class="prose">{inner}</section>', [],
                markdown=False, dated=False)


# ------------------------------------------------------------------ Markdown twins (for agents that read pages)

def md_actor(slug: str, item: dict, p: dict, lang: str) -> str:
    a, t = ACTORS.get(slug) or {}, T[lang]
    c = a.get(lang) or {}
    unit = a.get("unit", {}).get(lang, "results")
    example = (AGENT_TASKS.get(slug) or {}).get("input") or a.get("example")
    tool, curl = run_snippets(slug, example or {})
    out = [f"# {display_name(slug, item, lang)}", "", c.get("intro") or item.get("description", ""), "",
           f"- {t['run']}: {actor_url(slug)}", f"- {t['mcp_tool']} `{tool}`", f"- {t['price']}: {price_text(p, unit, lang)}", ""]
    if c.get("features"):
        out += [f"## {t['features']}", ""] + [f"- {x}" for x in c["features"]] + [""]
    if c.get("uses"):
        out += [f"## {t['uses']}", ""] + [f"- {x}" for x in c["uses"]] + [""]
    if example:
        out += [f"## {t['code']}", "", "```json", json.dumps(example, indent=2, ensure_ascii=False), "```", "", "```sh", curl, "```", ""]
    q, sample = load_data(QUALITY).get(slug), load_data(SAMPLES).get(slug)
    if q or sample:
        out += [f"## {'Wöchentliche Qualitätsprüfung' if lang == 'de' else 'Weekly quality check'}", ""]
        out += [quality_summary(q, lang)] if q else []
        out += [Q[lang]["sample"] + ": " + sample_summary(sample, lang)] if sample else []
        out += [""]
    if c.get("faq"):
        out += [f"## {t['faq']}", ""]
        for question, answer in c["faq"]:
            out += [f"### {question}", "", answer, ""]
    out += [f"{t['updated_label']}: {LASTMOD}", ""]
    return "\n".join(out)


def md_home(lang: str, items: dict, prices: dict) -> str:
    t, h = T[lang], HOME[lang]
    out = [f"# Perceptron Data – {t['claim']}", "", t["descriptor"], "", h["lead"], "", t["origin"], "",
           f"## {h['proof_title']}", ""]
    out += [f"- **{n}** {what} ({src})" for n, what, src, _ in h["proof"]] + ["", f"## {h['flag_title']}", ""]
    prefix = BASE + ("/actors/" if lang == "en" else "/de/actors/")
    for s in [s for s in FLAGSHIPS if s in items]:
        c = ACTORS[s].get(lang) or {}
        out.append(f"- [{display_name(s, items[s], lang)}]({prefix}{s}/index.md): {c.get('desc', '')} "
                   f"{t['price']}: {price_text(prices[s], ACTORS[s].get('unit', {}).get(lang, 'results'), lang)}. {actor_url(s)}")
    out += ["", f"## {h['agents_title']}", "", h["agents_text"], "", f"`{mcp_url(FLAGSHIPS)}`", "",
            f"{h['agents_link']}: {BASE}{'/agents/' if lang == 'en' else '/de/agents/'}index.md", "", f"## {h['all_title']}", ""]
    for s in items:
        c = (ACTORS.get(s) or {}).get(lang) or {}
        out.append(f"- [{display_name(s, items[s], lang)}]({prefix}{s}/index.md): {c.get('desc') or items[s].get('description', '')}")
    out += ["", f"## {h['faq_title']}", ""]
    for question, answer in h["faq"]:
        out += [f"### {question}", "", answer, ""]
    out += [f"{t['updated_label']}: {LASTMOD}", ""]
    return "\n".join(out)


def md_agents(lang: str, items: dict, prices: dict) -> str:
    g, t = AGENTS[lang], T[lang]
    sn = agents_snippets()
    out = [f"# {g['h1']}", "", g["lead"], "", f"## {g['connect']}", "", g["mcp_url"], "", f"`{sn['url']}`", "",
           g["claude"], "", "```sh", sn["claude"], "```", "", g["json"], "", "```json", sn["json"], "```", "", g["token"], "",
           g["api"], "", "```sh", sn["curl"], "```", "", g["search"], "", f"## {g['table']}", "",
           "| " + " | ".join(g["head"]) + " |", "|---|---|---|---|"]
    out += [f"| {task} | `{tool}` | `{example}` | {price} |" for _, task, tool, example, price in agent_rows(items, prices, lang)]
    out += ["", f"## {g['know']}", ""] + [f"- {x}" for x in g["notes"]] + ["", f"## {g['machine']}", ""]
    out += [f"- {BASE}/{label} – {text}" if label != "index.md" else f"- index.md – {text}" for label, text in g["machine_items"]]
    out += ["", f"{t['updated_label']}: {LASTMOD}", ""]
    return "\n".join(out)


# ------------------------------------------------------------------ honest dates and IndexNow

def normalise(text: str) -> str:
    """A page without its dates: the build date in the footer and the page's own change date."""
    text = re.sub(r'<time class="updated" datetime="[^"]*">[^<]*</time>', '<time class="updated"></time>', text)
    text = re.sub(r'"dateModified": "[^"]*"', '"dateModified": ""', text)
    return re.sub(r'<p class="built">[^<]*</p>', '<p class="built"></p>', text)


def fetch_text(url: str) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            return response.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 — not live yet, or the site is down: the page counts as changed
        return None


def live_state(paths: list[str]) -> dict[str, tuple[str | None, str | None]]:
    """Per path the live sitemap's lastmod and the live page, to tell a real change from a rebuild."""
    sitemap = fetch_text(f"{BASE}/sitemap.xml") or ""
    lastmods = {loc[len(BASE):]: mod for loc, mod in re.findall(r"<loc>([^<]+)</loc><lastmod>([^<]+)</lastmod>", sitemap)}
    with ThreadPoolExecutor(max_workers=8) as pool:
        pages = dict(zip(paths, pool.map(lambda path: fetch_text(BASE + path), paths)))
    return {path: (lastmods.get(path), pages.get(path)) for path in paths}


def human_date(iso: str, lang: str) -> str:
    return fmt_date(iso, lang)


def finish_dates(html_pages: dict[str, tuple[str, str]]) -> tuple[dict[str, str], list[str]]:
    """The date of each page's last real change (kept from the live site when only the build date differs);
    returns the dates and the paths that really changed (for IndexNow)."""
    live = live_state(list(html_pages))
    dates, changed = {}, []
    for path, (_, text) in html_pages.items():
        old_mod, old_text = live.get(path, (None, None))
        if old_mod and old_text is not None and normalise(old_text) == normalise(text):
            dates[path] = old_mod
        else:
            dates[path] = TODAY
            changed.append(path)
    return dates, changed


def stamp(text: str, iso: str, lang: str) -> str:
    text = text.replace(f'datetime="{LASTMOD}">{LASTMOD}</time>', f'datetime="{iso}">{human_date(iso, lang)}</time>')
    return text.replace(LASTMOD, iso)


# ------------------------------------------------------------------ output

def main() -> None:
    store = fetch_store()
    items = {a["name"]: {**a, "url": actor_url(a["name"]), "defaultMemoryMbytes": default_memory(a["name"])} for a in store}
    prices = {s: price_info(a, (ACTORS.get(s) or {}).get("price_event")) for s, a in items.items()}
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

    html_pages: dict[str, tuple[str, str]] = {}     # path → (language, page); dated in finish_dates
    md_pages: dict[str, tuple[str, str]] = {}       # path of the HTML page → (language, Markdown twin)

    def write_page(rel: str, text: str, lang: str, md: str | None = None) -> None:
        html_pages[rel] = (lang, text)
        if md is not None:
            md_pages[rel] = (lang, md)

    urls = []
    noindex = {f"{'' if lang == 'en' else '/de'}/actors/{s}/" for s in items for lang in ("en", "de")
               if "noindex" in (((ACTORS.get(s) or {}).get(lang) or {}).get("robots") or "")}
    for lang in ("en", "de"):
        prefix = "" if lang == "en" else "/de"
        write_page(f"{prefix}/", build_index(lang, items, prices), lang, md_home(lang, items, prices))
        urls.append((f"{prefix}/", "/de/" if lang == "en" else "/"))
        write_page(f"{prefix}/agents/", build_agents(lang, items, prices), lang, md_agents(lang, items, prices))
        urls.append((f"{prefix}/agents/", f"{'/de' if lang == 'en' else ''}/agents/"))
        for slug, item in items.items():
            a = ACTORS.get(slug, {"icon": "logo-256.png", "group": "research", "unit": {}})
            write_page(f"{prefix}/actors/{slug}/", build_actor(slug, a, item, prices[slug], lang, items), lang,
                       md_actor(slug, item, prices[slug], lang))
            urls.append((f"{prefix}/actors/{slug}/", f"{'/de' if lang == 'en' else ''}/actors/{slug}/"))
    quality, samples = load_data(QUALITY), load_data(SAMPLES)
    for lang in ("en", "de"):
        write_page("/quality/" if lang == "en" else "/de/quality/", build_quality_index(lang, items), lang)
        urls.append(("/quality/" if lang == "en" else "/de/quality/", "/de/quality/" if lang == "en" else "/quality/"))
        for slug, item in items.items():
            if slug in quality or slug in samples:
                write_page(quality_path(slug, lang), build_quality_page(slug, item, quality.get(slug), samples.get(slug), lang), lang)
                urls.append((quality_path(slug, lang), quality_path(slug, "de" if lang == "en" else "en")))
    write("/impressum/", simple_page("/impressum/", "Impressum", imp))
    write("/datenschutz/", simple_page("/datenschutz/", "Datenschutz", priv))
    write("/404.html", page("en", "/404.html", "/de/", "Not found | Perceptron Data", "Page not found",
                             '<section class="hero"><h1>Not found</h1><p><a href="/">Back to the catalogue</a></p></section>', [],
                             markdown=False, dated=False))

    # honest dates: a page keeps the date of its last real change (Google uses lastmod only when it is accurate)
    dates, changed = finish_dates(html_pages)
    for rel, (lang, text) in html_pages.items():
        write(rel, stamp(text, dates[rel], lang))
    for rel, (lang, text) in md_pages.items():
        write(rel + "index.md", stamp(text, dates[rel], lang))

    # sitemap with hreflang pairs
    entries = []
    for path, alt in urls:
        if path in noindex:          # English product pages that only repeat the Store page (SEO-UMSETZUNG §2.1)
            continue
        en, de = (path, alt) if not path.startswith("/de/") else (alt, path)
        entries.append(f"""  <url><loc>{BASE}{path}</loc><lastmod>{dates.get(path, TODAY)}</lastmod>
    <xhtml:link rel="alternate" hreflang="en" href="{BASE}{en}"/>
    <xhtml:link rel="alternate" hreflang="de" href="{BASE}{de}"/></url>""")
    write("/sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
          'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(entries) + "\n</urlset>\n")
    write("/robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")
    write(f"/{INDEXNOW_KEY}.txt", INDEXNOW_KEY)
    # Pages that really changed (for the IndexNow step after the deploy): only those in the sitemap.
    in_sitemap = [p for p, _ in urls if p not in noindex]
    announce = [BASE + p for p in in_sitemap if p in changed]
    (ROOT / "indexnow-changed.txt").write_text("\n".join(announce) + ("\n" if announce else ""))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as out:
            out.write(f"changed={' '.join(announce)}\n")

    # llms.txt: a plain summary for AI assistants and LLM-based search
    lines = ["# Perceptron Data", "", f"> {T['en']['claim']} {T['en']['descriptor']} {T['en']['origin']}", "",
             "Self-service actors on Apify. Paid actors charge per result plus a small start fee per run. "
             f"Weekly checks against known answers: {BASE}/quality/", "",
             "## For AI agents", "",
             f"- [Setup for MCP clients and the API]({BASE}/agents/index.md): Claude Code, Cursor, JSON config, curl",
             f"- MCP server with the flagship tools: {mcp_url(FLAGSHIPS)}",
             f"- [Machine-readable catalogue]({BASE}/catalog.json): names, prices, MCP tool names, example inputs",
             "- Every page of the site is available as Markdown: add index.md to its address", ""]
    for sec in SECTIONS:
        slugs = [s for s in sec["actors"] if s in items]
        if slugs:
            lines.append(f"{'#' * sec['level']} {sec['en']['heading']}")
            for s in slugs:
                lines.append(f"- [{display_name(s, items[s], 'en')}]({actor_url(s)}): {ACTORS[s]['en']['desc']} "
                             f"MCP tool: {mcp_tool(s)}. Price: {price_text(prices[s], ACTORS[s].get('unit', {}).get('en', 'results'), 'en')}.")
            lines.append("")
    write("/llms.txt", "\n".join(lines))

    # machine-readable catalogue
    catalogue = [{"name": s, "title": items[s]["title"], "productName": display_name(s, items[s], "en"), "url": actor_url(s),
                  "page": f"{BASE}/actors/{s}/",
                  "description": ACTORS.get(s, {}).get("en", {}).get("desc") or items[s].get("description"),
                  "pricePer1000Usd": None if prices[s]["free"] else round(prices[s]["per1000"], 4),
                  "unit": ACTORS.get(s, {}).get("unit", {}).get("en"),
                  "qualityPage": f"{BASE}{quality_path(s, 'en')}" if s in quality or s in samples else None,
                  "actor": f"{APIFY_USER}/{s}", "mcpTool": mcp_tool(s), "markdown": f"{BASE}/actors/{s}/index.md",
                  "task": (AGENT_TASKS.get(s) or {}).get("en"),
                  "exampleInput": (AGENT_TASKS.get(s) or {}).get("input") or ACTORS.get(s, {}).get("example"),
                  "price": price_text(prices[s], ACTORS.get(s, {}).get("unit", {}).get("en", "results"), "en")} for s in items]
    write("/catalog.json", json.dumps({"updated": TODAY, "mcpServer": mcp_url(FLAGSHIPS), "agents": f"{BASE}/agents/",
                                       "actors": catalogue}, indent=2, ensure_ascii=False))
    (OUT / ".nojekyll").write_text("")
    print(f"Built {len(urls)} pages for {len(items)} actors into {OUT}")


if __name__ == "__main__":
    main()
