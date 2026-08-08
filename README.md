# Africa FX Board

## What it does

Africa FX Board is a daily-updating exchange-rate dashboard for African
currencies. It shows, for each of 42 African currencies, the current rate
against USD, EUR, and GBP, a 24-hour percent change, and a 14-day sparkline
trend — plus a "movers" strip highlighting the currencies strengthening and
weakening the most against the dollar. Users can filter the board by
country, currency name, or code, and sort by A–Z, biggest gainers, or
biggest losers.

Once a day, the system fetches a fresh USD-based rate snapshot, derives the
EUR and GBP cross-rates arithmetically from that same snapshot (so all
three reference currencies stay internally consistent), and appends the new
data point to each currency's running history. The static page then reads
that history and renders the table, sparklines, and movers strip entirely
in the browser.

## What it's made of

**Data source**
- [`open.er-api.com`](https://www.exchangerate-api.com/docs/free) — a free,
  keyless exchange-rate API, queried once per day with `base=USD`.

**Fetch/merge logic**
- `scripts/fetch_forex.py` — a Python script that requests the daily USD
  snapshot, pulls out the 42 tracked African currency codes (with automatic
  fallback to older ISO codes for Sierra Leone and Zimbabwe where needed),
  derives EUR/GBP cross-rates, and merges the new day's point into each
  currency's history, capped at 120 daily points.
- `requests` — the only Python dependency, used to call the API.

**Automation**
- `.github/workflows/update.yml` — a GitHub Actions workflow that runs the
  fetch script on a daily cron schedule (or on manual trigger), then commits
  and pushes the updated data file back to the repository.

**Data storage**
- `data/rates.json` — the generated file holding, per currency, its name,
  countries, and full price history. This is the only artifact the workflow
  writes; it's what the front end reads at page load.

**Front end**
- `index.html` — a single static HTML/CSS/JavaScript file with no build
  step. On load, it fetches `data/rates.json`, computes percent changes and
  sparkline paths client-side, and renders the board, movers strip, search,
  and sort controls.

**Hosting**
- GitHub Pages serves `index.html` and `data/rates.json` directly from the
  repository — no server, no database, no external hosting.
