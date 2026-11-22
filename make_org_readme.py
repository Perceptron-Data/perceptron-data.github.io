#!/usr/bin/env python3
"""Write the GitHub organisation profile (../dotgithub/profile/README.md) from content.py — the same order, canonical
names, card texts, measured figures and live prices (with start fee) as the home page. Withdrawn actors (content.RETIRED)
never appear: fetch_store() drops them."""
from pathlib import Path

from build import (BASE, CATEGORIES, FLAGSHIPS, T, actor_url, built_md, default_memory, display_name, fetch_store, flow_md,
                   mcp_url, money, price_info, proof_items)
from content import ACTORS, CUSTOM, CUSTOM_EMAIL, HOME

SITE = "https://perceptron-data.github.io"


def price_text(p: dict, unit: str) -> str:
    if p["free"]:
        return "Free"
    text = f"{money(p['per1000'], 'en')} per 1,000 {unit}"
    if p["from1000"] < p["per1000"]:
        text += f" (from {money(p['from1000'], 'en')})"
    return text + (" " + T["en"]["startfee"].format(fee=money(p["start"], "en")) if p.get("start") else "")


def table(slugs: list[str], items: dict) -> list[str]:
    out = ["| | Actor | What you get | Price (Apify free plan) |", "|---|---|---|---|"]
    for s in slugs:
        a = ACTORS[s]
        icon = f'<img src="{SITE}/assets/icons/{a["icon"]}" width="32" alt="">'
        p = price_info(items[s], a.get("price_event"))
        out.append(f"| {icon} | [{display_name(s, items[s], 'en')}]({BASE}/actors/{s}/) | {a['en']['card']} | "
                   f"{price_text(p, a['unit']['en'])} |")
    return out + [""]


store = fetch_store()
items = {a["name"]: {**a, "url": actor_url(a["name"]), "defaultMemoryMbytes": default_memory(a["name"])} for a in store}
h = HOME["en"]
out = [f'<p align="center"><img src="{SITE}/assets/logo-256.png" width="88" alt="Perceptron Data"></p>',
       '<h2 align="center">Check, don\'t guess.</h2>',
       '<p align="center">Company checks and data from public sources, as <a href="https://apify.com/perceptr0n">Apify</a> '
       'actors. Built in Germany. Focused on DACH and the EU.<br>'
       f'<a href="{SITE}/">Website</a> · <a href="{SITE}/de/">Deutsch</a> · '
       f'<a href="{SITE}/agents/">For AI agents</a> · <a href="{SITE}/quality/">Weekly checks</a> · '
       '<a href="https://apify.com/perceptr0n">All actors on Apify</a></p>', "",
       h["lead"] + " Paid per result, plus a small start fee per run.", "",
       f"**{h['proof_title']}**", ""]
out += [f"- **{n}** {what} ({src})" for n, what, src, _ in proof_items("en")]
out += ["", f"## {h['flag_title']}", "", h["flag_intro"], ""] + table([s for s in FLAGSHIPS if s in items], items)
out += flow_md("en", items)
out += [f"## {h['agents_title']}", "", h["agents_text"], "", "```", mcp_url(FLAGSHIPS), "```", "",
        f"[{h['agents_link']}]({BASE}/agents/)", "", f"## {h['all_title']}", ""]
for section in CATEGORIES:
    slugs = [s for s in section["actors"] if s in items]
    if slugs:
        out += [f"### {section['en']['heading']}", "", section["en"]["intro"], ""] + table(slugs, items)
out += built_md("en", items)
out += ["## Auf Deutsch", "",
        "**Prüfen statt raten.** Firmen-Checks und Daten aus öffentlichen Quellen: Lead-Listen zu einer Zeile je Firma "
        "zusammenführen, sehen, wer hinter einer Website steht (USt-IdNr. über die EU-Prüfung VIES), Firmen auf Insolvenz- "
        "und Registerbekanntmachungen beobachten – dazu Stellen, Messen, Register und Dokumente. "
        f"[Zur deutschen Übersicht]({SITE}/de/)", "",
        f"**{CUSTOM['de']['title']}:** {CUSTOM['de']['contact'].format(email=CUSTOM_EMAIL)}", "",
        f"<sub>[Impressum]({SITE}/impressum/) · [Datenschutz]({SITE}/datenschutz/) · Independent provider, not affiliated "
        "with Apify or the data sources named. Bug reports are welcome.</sub>", ""]
target = Path(__file__).resolve().parent.parent / "dotgithub" / "profile" / "README.md"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text("\n".join(out), encoding="utf-8")
print("geschrieben:", target, len(out), "Zeilen")
