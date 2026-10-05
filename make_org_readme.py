#!/usr/bin/env python3
"""Write the GitHub organisation profile (../dotgithub/profile/README.md) from content.py."""
import json, urllib.request
from pathlib import Path
from content import ACTORS, GROUPS
from build import GROUP_ORDER, BASE, STORE_API

items = {a["name"]: a for a in json.load(urllib.request.urlopen(STORE_API, timeout=30))["data"]["items"]}
out = ['<p align="center"><img src="https://perceptron-data.github.io/assets/logo-256.png" width="88" alt="Perceptron Data"></p>',
       '<h2 align="center">Data APIs for AI, sales and research</h2>',
       '<p align="center">Clean, structured data from public and official sources — on <a href="https://apify.com/perceptr0n">Apify</a>. '
       'No login or API key needed; paid actors charge per result.<br>'
       '<a href="https://perceptron-data.github.io/">Website</a> · <a href="https://perceptron-data.github.io/de/">Deutsch</a> · '
       '<a href="https://apify.com/perceptr0n">All actors on Apify</a></p>', ""]
for g in GROUP_ORDER:
    slugs = [s for s, a in ACTORS.items() if a["group"] == g and s in items]
    if not slugs:
        continue
    out += [f"### {GROUPS[g]['en']}", "", "| | Actor | What it does |", "|---|---|---|"]
    for s in slugs:
        a = ACTORS[s]
        icon = f'<img src="https://perceptron-data.github.io/assets/icons/{a["icon"]}" width="32" alt="">'
        out.append(f"| {icon} | [{items[s]['title']}]({BASE}/actors/{s}/) | {a['en']['desc']} |")
    out.append("")
out += ["### Auf Deutsch", "",
        "Daten für KI, Vertrieb und Marktforschung aus öffentlichen und amtlichen Quellen: PDF und Word in Markdown "
        "umwandeln, prüfen, welche Firmen Google-Werbung schalten, Firmendaten aus dem Impressum, Stellenangebote der "
        "Arbeitsagentur, kununu-Bewertungen, Messe-Ausstellerlisten, EU-Ausschreibungen, Marktstammdatenregister und "
        "EUDAMED — [zur deutschen Übersicht](https://perceptron-data.github.io/de/).", "",
        "<sub>[Impressum](https://perceptron-data.github.io/impressum/) · "
        "[Datenschutz](https://perceptron-data.github.io/datenschutz/) · Independent developer, not affiliated with Apify.</sub>", ""]
target = Path(__file__).resolve().parent.parent / "dotgithub" / "profile" / "README.md"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text("\n".join(out), encoding="utf-8")
print("geschrieben:", target, len(out), "Zeilen")
