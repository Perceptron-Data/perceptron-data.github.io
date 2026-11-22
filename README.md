<p align="center"><img src="assets/logo-256.png" width="96" alt="Perceptron Data"></p>

<h1 align="center">Perceptron Data – company checks and data from public sources</h1>

<p align="center">
  <a href="https://perceptron-data.github.io/">Website</a> ·
  <a href="https://perceptron-data.github.io/de/">Deutsch</a> ·
  <a href="https://perceptron-data.github.io/agents/">For AI agents</a> ·
  <a href="https://apify.com/perceptr0n">Apify</a> ·
  <a href="https://perceptron-data.github.io/catalog.json">catalog.json</a> ·
  <a href="https://perceptron-data.github.io/llms.txt">llms.txt</a>
</p>

Source of the catalogue site **[perceptron-data.github.io](https://perceptron-data.github.io/)** –
an overview of the Perceptron Data actors on [Apify](https://apify.com/perceptr0n): merge lead lists
into one row per company, see who is legally behind a website (EU VAT ID checked against VIES), watch
companies for insolvency and register notices, and read the job board of the Bundesagentur für Arbeit –
plus XING jobs, companies that are hiring, kununu employer data, trade-fair exhibitor lists, ads on
Google and Microsoft Bing, App Store and Google Play data, EU tenders (TED), the German
Marktstammdatenregister and documents to Markdown.
The home page also describes custom actors built to order (contact: thom.ehr@gmail.com).

## How it works

- `content.py` – hand-written page texts in English and German, the four actors shown first
  (`FLAGSHIPS`) and the withdrawn actors that must never be listed (`RETIRED`)
- `build.py` – reads actors and prices live from the public Apify Store API and writes a static
  site with sitemap, `hreflang`, structured data (schema.org), Open Graph tags, `llms.txt`,
  Markdown versions of the home, agent and actor pages and a machine-readable `catalog.json`;
  Python standard library only
- `assets/style.css`, `assets/site.js` – the design and the site's one script (copy buttons on code
  blocks, the category filter of the catalogue); no dependencies, no tracking, nothing loaded from
  other hosts
- `data/quality.json` – written by the [watchdog](https://github.com/Perceptron-Data/wachposten)
  after its weekly check; the home page counts its figures from this file
- `.github/workflows/pages.yml` – rebuilds and deploys every day, so new actors and price changes
  appear without manual work
- `indexnow.py` – after the deploy, reports the pages whose content changed to IndexNow
- `make_og.py` – renders the social preview images (run locally when an actor, a name or an icon changes)
- `make_org_readme.py` – writes the organisation profile from the same texts and live prices

The build stops instead of publishing an empty catalogue or a site without a legal notice.

## Legal

[Impressum](https://perceptron-data.github.io/impressum/) ·
[Datenschutz](https://perceptron-data.github.io/datenschutz/) – independent developer, not
affiliated with Apify or the data sources named.
