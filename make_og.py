#!/usr/bin/env python3
"""Social preview images (1200x630) per actor. Run locally after adding an actor:
needs cairosvg, which the daily GitHub build does not — missing images fall back
to assets/og/default.png."""
import base64, html, sys, textwrap
from pathlib import Path
import cairosvg
from content import ACTORS

ROOT = Path(__file__).resolve().parent

def svg(title: str, sub: str, icon: Path) -> str:
    data = base64.b64encode(icon.read_bytes()).decode()
    lines = textwrap.wrap(title, 21, break_long_words=False)[:4]
    y0 = 300 - (len(lines) - 1) * 30
    text = "".join(f'<text x="420" y="{y0 + i * 60}" font-family="DejaVu Sans" font-weight="bold" font-size="48" fill="#ffffff">{html.escape(l)}</text>' for i, l in enumerate(lines))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1200" height="630">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#312E81"/><stop offset="1" stop-color="#0F172A"/></linearGradient></defs>
<rect width="1200" height="630" fill="url(#g)"/>
<image x="90" y="175" width="280" height="280" xlink:href="data:image/png;base64,{data}"/>
{text}
<text x="420" y="{y0 + len(lines) * 60 + 6}" font-family="DejaVu Sans" font-size="30" fill="#FDE047">{html.escape(sub)}</text>
<text x="90" y="575" font-family="DejaVu Sans" font-size="26" fill="#A5B4FC">perceptron-data.github.io · on Apify</text>
</svg>'''

out = ROOT / "assets" / "og"
out.mkdir(parents=True, exist_ok=True)
cairosvg.svg2png(bytestring=svg("Data APIs for AI, sales and research", "Perceptron Data", ROOT / "assets/icons/logo-256.png").encode(),
                 write_to=str(out / "default.png"))
for slug, a in ACTORS.items():
    cairosvg.svg2png(bytestring=svg(a["en"]["title"], "Perceptron Data · Apify actor", ROOT / "assets/icons" / a["icon"]).encode(),
                     write_to=str(out / f"{slug}.png"))
print("OG-Bilder:", len(list(out.glob("*.png"))))
