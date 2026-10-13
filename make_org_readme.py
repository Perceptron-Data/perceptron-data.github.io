#!/usr/bin/env python3
"""Write the GitHub organisation profile (../dotgithub/profile/README.md) from content.py — the same sections,
canonical names, card texts and live prices (with start fee) as the home page."""
from pathlib import Path

from build import BASE, FLAGSHIPS, T, actor_url, default_memory, display_name, fetch_store, mcp_url, money, price_info
from content import ACTORS, HOME, SECTIONS


def price_text(p: dict, unit: str) -> str:
    if p["free"]:
        return "Free"
    text = f"{money(p['per1000'], 'en')} per 1,000 {unit}"
    if p["from1000"] < p["per1000"]:
        text += f" (from {money(p['from1000'], 'en')})"
    return text + (" " + T["en"]["startfee"].format(fee=money(p["start"], "en")) if p.get("start") else "")


store = fetch_store()
items = {a["name"]: {**a, "url": actor_url(a["name"]), "defaultMemoryMbytes": default_memory(a["name"])} for a in store}
out = ['<p align="center"><img src="https://perceptron-data.github.io/assets/logo-256.png" width="88" alt="Perceptron Data"></p>',
       '<h2 align="center">Check, don\'t guess.</h2>',
       '<p align="center">Company checks and data from public sources, as <a href="https://apify.com/perceptr0n">Apify</a> '
       'actors. Built in Germany. Focused on DACH and the EU.<br>'
       '<a href="https://perceptron-data.github.io/">Website</a> · <a href="https://perceptron-data.github.io/de/">Deutsch</a> · '
       '<a href="https://perceptron-data.github.io/quality/">Weekly checks</a> · '
       '<a href="https://apify.com/perceptr0n">All actors on Apify</a></p>', "",
       HOME["en"]["lead"] + " Paid per result, plus a small start fee per run.", "",
       "**Measured, not promised:** " + " · ".join(f"{n} {what} ({src})" for n, what, src, _ in HOME["en"]["proof"]), "",
       f"**For AI agents:** every actor is a tool on Apify's MCP server — `{mcp_url(FLAGSHIPS[:2])}` · "
       f"[setup for Claude Code, Cursor and the API]({BASE}/agents/)", ""]
for section in SECTIONS:
    slugs = [s for s in section["actors"] if s in items]
    out += [("## " if section["level"] == 2 else "### ") + section["en"]["heading"], "", section["en"]["intro"], ""]
    if not slugs:
        continue
    out += ["| | Actor | What you get | Price (Apify free plan) |", "|---|---|---|---|"]
    for s in slugs:
        a = ACTORS[s]
        icon = f'<img src="https://perceptron-data.github.io/assets/icons/{a["icon"]}" width="32" alt="">'
        p = price_info(items[s], a.get("price_event"))
        out.append(f"| {icon} | [{display_name(s, items[s], 'en')}]({BASE}/actors/{s}/) | {a['en']['card']} | "
                   f"{price_text(p, a['unit']['en'])} |")
    out.append("")
out += ["### Auf Deutsch", "",
        "**Prüfen statt raten.** Firmen-Checks und Daten aus öffentlichen Quellen: Wer wirbt bei Google und Bing, wer "
        "steht hinter einer Website (USt-IdNr. über die EU-Prüfung VIES), dazu Register, Stellen, Messen, Dokumente und "
        "Recherche für KI — [zur deutschen Übersicht](https://perceptron-data.github.io/de/).", "",
        "<sub>[Impressum](https://perceptron-data.github.io/impressum/) · "
        "[Datenschutz](https://perceptron-data.github.io/datenschutz/) · Independent provider, not affiliated with Apify "
        "or the data sources named. Bug reports are welcome.</sub>", ""]
target = Path(__file__).resolve().parent.parent / "dotgithub" / "profile" / "README.md"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text("\n".join(out), encoding="utf-8")
print("geschrieben:", target, len(out), "Zeilen")
