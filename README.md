# Africa FX Board

A free, no-API-key exchange-rate dashboard for every African currency
against USD, EUR and GBP. A GitHub Actions job fetches rates once daily,
derives EUR/GBP cross-rates, appends to a running history, and a static page
(served by GitHub Pages) renders it with sparklines and a movers strip.

**Cost: $0.** No billing account, no signup keys, nothing to rotate.

## Data source

[ExchangeRate-API's Open Access endpoint](https://www.exchangerate-api.com/docs/free)
(`open.er-api.com`) — free, keyless, updates once every 24 hours. Their
terms require attribution (already in the footer) and **do not permit
redistributing the raw feed** — which is why this repo doesn't expose a
"download raw JSON" link the way the earlier news-tracker project did. The
page only *displays* the data, transformed into per-currency history, which
is within their terms.

This gives you a **market/interbank reference rate**, not necessarily the
exact figure your specific central bank stamps on its daily bulletin —
those (CBK, BoU, BoT, NBE, etc.) publish as PDFs or scattered HTML tables
with no clean API, which would make a scraper for each one fragile and
high-maintenance. The dashboard says so in its subhead; link out to your
central bank's site if you need the exact official print.

## 1. Get this running (5 minutes)

1. Create a new **public** GitHub repo (public repos get unlimited free
   Actions minutes).
2. Push everything in this folder to the repo root.
3. **Settings → Pages** → Source: **Deploy from a branch** → branch `main`,
   folder `/ (root)` → Save.
4. **Settings → Actions → General → Workflow permissions** → select
   **Read and write permissions** → Save.
5. **Actions** tab → **Update Africa FX Board** → **Run workflow** to
   trigger the first fetch manually.
6. After ~20–30 seconds, refresh **Settings → Pages** — your site is live
   at `https://<your-username>.github.io/<repo-name>/`.

After that it runs itself once a day. There's nothing to maintain — running
it more than once a day is pointless since the source data itself only
refreshes every 24 hours (the workflow is already set to `0 6 * * *` UTC).

## 2. Repo layout

```
.
├── .github/workflows/update.yml   # the daily cron job
├── scripts/fetch_forex.py         # fetch + cross-rate + history logic
├── data/rates.json                # generated data (committed by the bot)
├── index.html                     # the dashboard (no build step)
└── requirements.txt
```

## 3. Currency coverage

42 African currencies are tracked, including shared currencies (the West
and Central African CFA francs cover multiple countries each). A couple of
ISO codes changed recently — Sierra Leone's redenomination (SLL → SLE) and
Zimbabwe's move to ZiG (ZWL → ZWG) — the script tries the current code
first and falls back to the old one automatically if the provider hasn't
caught up, so nothing breaks either way.

If the provider is ever missing a specific currency on a given day, the
script logs a warning and skips just that one — it doesn't fail the whole
run.

## 4. Customizing

- **Add/remove currencies**: edit `AFRICAN_CURRENCIES` at the top of
  `scripts/fetch_forex.py`.
- **Add more reference currencies** (e.g. CNY, AED for trade-corridor
  relevance): add the code to the cross-rate math in `main()` — follow the
  same pattern as the EUR/GBP derivation.
- **History length**: `MAX_HISTORY_POINTS` in `scripts/fetch_forex.py`
  controls how many daily points are kept per currency (default ~120 days,
  used for the 14-day sparklines).
- **Add each central bank's official page as a link**: the countries array
  per currency in `AFRICAN_CURRENCIES` is a natural place to hang a
  `official_url` field if you want to extend the row cards later.

## 5. Known limitations

- **Once-daily granularity** — this isn't a live/tick-by-tick forex feed;
  it's a daily snapshot, appropriate for trend-watching and day-to-day
  context, not trading.
- **Reference rate, not official rate** — see the note above. Good for
  "is the shilling weakening this month," not for "what rate will my bank
  give me today."
- **Currency unions** — CFA franc entries (XOF, XAF) apply to several
  countries at once; the rate is identical across all of them by design
  (they're pegged to the euro).

## 6. Running the fetch locally (optional)

```bash
pip install -r requirements.txt
python scripts/fetch_forex.py
python -m http.server 8000   # then open http://localhost:8000
```
