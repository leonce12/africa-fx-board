#!/usr/bin/env python3
"""
Africa FX Board — free-tier data pipeline.

Data source: open.er-api.com (ExchangeRate-API's free, keyless, Open Access
endpoint). Updates once every 24 hours. Free for personal/commercial display
use with attribution; redistribution of the raw feed is not permitted by
their terms — which is why this repo doesn't expose a "download raw data"
link on the page (see README).

We fetch one snapshot (base=USD), pull out every African currency we know
about, and derive EUR/GBP cross-rates arithmetically from the same snapshot
so all three reference currencies are internally consistent.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "rates.json"
API_URL = "https://open.er-api.com/v6/latest/USD"
REQUEST_TIMEOUT = 20
MAX_HISTORY_POINTS = 120  # ~4 months of daily points per currency
USER_AGENT = "africa-fx-board/1.0 (+https://github.com/; free, non-commercial FX display)"

# code -> (display name, [countries]). Where a currency circulates in
# several countries (CFA francs, common monetary area, etc.) all are listed.
# Some entries have a "fallback" code because ISO codes changed recently
# (e.g. Sierra Leone's redenomination, Zimbabwe's ZiG) and not every
# provider has caught up yet — we try the current code first.
AFRICAN_CURRENCIES = {
    "DZD": ("Algerian Dinar", ["Algeria"]),
    "AOA": ("Angolan Kwanza", ["Angola"]),
    "XOF": ("West African CFA Franc", ["Benin", "Burkina Faso", "Côte d'Ivoire", "Guinea-Bissau", "Mali", "Niger", "Senegal", "Togo"]),
    "BWP": ("Botswana Pula", ["Botswana"]),
    "BIF": ("Burundian Franc", ["Burundi"]),
    "CVE": ("Cape Verdean Escudo", ["Cabo Verde"]),
    "XAF": ("Central African CFA Franc", ["Cameroon", "Central African Republic", "Chad", "Republic of the Congo", "Equatorial Guinea", "Gabon"]),
    "KMF": ("Comorian Franc", ["Comoros"]),
    "CDF": ("Congolese Franc", ["DR Congo"]),
    "DJF": ("Djiboutian Franc", ["Djibouti"]),
    "EGP": ("Egyptian Pound", ["Egypt"]),
    "ERN": ("Eritrean Nakfa", ["Eritrea"]),
    "SZL": ("Eswatini Lilangeni", ["Eswatini"]),
    "ETB": ("Ethiopian Birr", ["Ethiopia"]),
    "GMD": ("Gambian Dalasi", ["Gambia"]),
    "GHS": ("Ghanaian Cedi", ["Ghana"]),
    "GNF": ("Guinean Franc", ["Guinea"]),
    "KES": ("Kenyan Shilling", ["Kenya"]),
    "LSL": ("Lesotho Loti", ["Lesotho"]),
    "LRD": ("Liberian Dollar", ["Liberia"]),
    "LYD": ("Libyan Dinar", ["Libya"]),
    "MGA": ("Malagasy Ariary", ["Madagascar"]),
    "MWK": ("Malawian Kwacha", ["Malawi"]),
    "MRU": ("Mauritanian Ouguiya", ["Mauritania"]),
    "MUR": ("Mauritian Rupee", ["Mauritius"]),
    "MAD": ("Moroccan Dirham", ["Morocco"]),
    "MZN": ("Mozambican Metical", ["Mozambique"]),
    "NAD": ("Namibian Dollar", ["Namibia"]),
    "NGN": ("Nigerian Naira", ["Nigeria"]),
    "RWF": ("Rwandan Franc", ["Rwanda"]),
    "STN": ("São Tomé & Príncipe Dobra", ["São Tomé and Príncipe"]),
    "SCR": ("Seychellois Rupee", ["Seychelles"]),
    "SLE": ("Sierra Leonean Leone", ["Sierra Leone"]),
    "SOS": ("Somali Shilling", ["Somalia"]),
    "ZAR": ("South African Rand", ["South Africa"]),
    "SSP": ("South Sudanese Pound", ["South Sudan"]),
    "SDG": ("Sudanese Pound", ["Sudan"]),
    "TZS": ("Tanzanian Shilling", ["Tanzania"]),
    "TND": ("Tunisian Dinar", ["Tunisia"]),
    "UGX": ("Ugandan Shilling", ["Uganda"]),
    "ZMW": ("Zambian Kwacha", ["Zambia"]),
    "ZWG": ("Zimbabwe Gold", ["Zimbabwe"]),
}

# code -> fallback code, tried if the primary isn't in the provider's table
FALLBACKS = {
    "SLE": "SLL",   # pre-2022 Sierra Leonean leone
    "ZWG": "ZWL",   # pre-2024 Zimbabwean dollar
}


def log(msg):
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", file=sys.stderr)


def load_existing():
    if DATA_PATH.exists():
        try:
            return json.loads(DATA_PATH.read_text())
        except Exception:
            pass
    return {"updated": None, "currencies": {}}


def main():
    log(f"Fetching {API_URL}")
    resp = requests.get(API_URL, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    payload = resp.json()

    if payload.get("result") != "success":
        log(f"ERROR: provider returned non-success result: {payload.get('result')}")
        sys.exit(1)

    rates = payload["rates"]  # units of CUR per 1 USD
    eur_per_usd = rates.get("EUR")
    gbp_per_usd = rates.get("GBP")
    if not eur_per_usd or not gbp_per_usd:
        log("ERROR: EUR or GBP missing from provider response, cannot derive crosses")
        sys.exit(1)

    # Use the provider's own "last update" date so every currency in this
    # run is stamped with the same trading day, even if we run the script
    # again later the same day (manual re-run, retry, etc.)
    try:
        snapshot_date = datetime.strptime(
            payload["time_last_update_utc"], "%a, %d %b %Y %H:%M:%S %z"
        ).date().isoformat()
    except Exception:
        snapshot_date = datetime.now(timezone.utc).date().isoformat()

    existing = load_existing()
    existing_currencies = existing.get("currencies", {})

    resolved = 0
    missing = []

    for code, (name, countries) in AFRICAN_CURRENCIES.items():
        rate = rates.get(code)
        used_code = code
        if rate is None and code in FALLBACKS:
            fb = FALLBACKS[code]
            rate = rates.get(fb)
            used_code = fb
        if rate is None:
            missing.append(code)
            continue

        point = {
            "date": snapshot_date,
            "usd": round(rate, 6),
            "eur": round(rate / eur_per_usd, 6),
            "gbp": round(rate / gbp_per_usd, 6),
        }

        entry = existing_currencies.get(code, {"name": name, "countries": countries, "history": []})
        entry["name"] = name
        entry["countries"] = countries
        entry["provider_code"] = used_code  # note if we used a fallback code
        history = entry.get("history", [])

        if history and history[-1]["date"] == snapshot_date:
            history[-1] = point  # overwrite same-day point on re-run
        else:
            history.append(point)

        entry["history"] = history[-MAX_HISTORY_POINTS:]
        existing_currencies[code] = entry
        resolved += 1

    if missing:
        log(f"WARNING: provider had no rate for: {', '.join(missing)} (skipped this run)")
    log(f"Resolved {resolved}/{len(AFRICAN_CURRENCIES)} currencies for {snapshot_date}")

    output = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "snapshot_date": snapshot_date,
        "next_update_utc": payload.get("time_next_update_utc"),
        "provider": "https://www.exchangerate-api.com",
        "currencies": existing_currencies,
    }

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    log(f"Wrote {DATA_PATH}")


if __name__ == "__main__":
    main()
