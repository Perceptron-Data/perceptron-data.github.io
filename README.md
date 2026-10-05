<p align="center"><img src="assets/logo-256.png" width="96" alt="Perceptron Data"></p>

<h1 align="center">Perceptron Data — Data APIs for AI, sales and research</h1>

<p align="center">
  <a href="https://perceptron-data.github.io/">Website</a> ·
  <a href="https://perceptron-data.github.io/de/">Deutsch</a> ·
  <a href="https://apify.com/perceptr0n">Apify</a> ·
  <a href="https://perceptron-data.github.io/catalog.json">catalog.json</a> ·
  <a href="https://perceptron-data.github.io/llms.txt">llms.txt</a>
</p>

Source of the catalogue site **[perceptron-data.github.io](https://perceptron-data.github.io/)** —
an overview of the Perceptron Data actors on [Apify](https://apify.com/perceptr0n): PDF and Office
to Markdown for AI, Google Ads Transparency checks for company lists, DACH company data from the
Impressum, kununu employer data, Arbeitsagentur jobs, trade-fair exhibitor lists, App Store and
Google Play data, EU tenders (TED), the German Marktstammdatenregister and EUDAMED.

## How it works

- `content.py` — hand-written page texts in English and German
- `build.py` — reads actors and prices live from the public Apify Store API and writes a static
  site with sitemap, `hreflang`, structured data (schema.org), Open Graph images, `llms.txt` and a
  machine-readable `catalog.json`; Python standard library only
- `.github/workflows/pages.yml` — rebuilds and deploys every day, so new actors and price changes
  appear without manual work
- `make_og.py` — renders the social preview images (run locally when an actor is added)

The build stops instead of publishing an empty catalogue or a site without a legal notice.

## Legal

[Impressum](https://perceptron-data.github.io/impressum/) ·
[Datenschutz](https://perceptron-data.github.io/datenschutz/) — independent developer, not
affiliated with Apify or the data sources named.
