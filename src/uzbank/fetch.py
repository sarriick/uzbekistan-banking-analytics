"""Download dated CBU HTML tables with immutable source evidence.

The offline build never makes network requests. This module is the explicit
refresh step. Publication month and balance-sheet date are kept separate.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from lxml import html

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://cbu.uz"
MONTHS = dict(zip(
    "января февраля марта апреля мая июня июля августа сентября октября ноября декабря".split(),
    range(1, 13),
))


def clean(text: str) -> str:
    return " ".join(text.replace("\u200b", "").split())


def reporting_date(text: str) -> str:
    match = re.search(r"по состоянию на\s+(\d+)\s+([а-я]+)\s+(\d{4})", clean(text).lower())
    if not match:
        raise ValueError(f"Missing reporting date: {text}")
    day, month, year = match.groups()
    return date(int(year), MONTHS[month], int(day)).isoformat()


def request_bytes(url: str) -> bytes:
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": "UzBankPortfolio/1.0 (public statistical research)"})
            with urlopen(req, timeout=45) as response:
                return response.read()
        except OSError:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("Unreachable")


def month_range(start: str, end: str):
    year, month = map(int, start.split("-"))
    while f"{year:04d}-{month:02d}" <= end:
        yield year, month
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def fetch(start: str, end: str, root: Path = ROOT) -> None:
    raw_dir = root / "data/raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "data/sources.json"
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    cached = {item["url"]: item for item in previous}
    found = {}
    # CBU usually publishes in the reporting month. Also scan the next month
    # to catch delayed publications; filter using the table's own as-of date.
    end_year, end_month = map(int, end.split("-"))
    next_month = f"{end_year + (end_month == 12):04d}-{1 if end_month == 12 else end_month + 1:02d}"
    for year, month in month_range(start, next_month):
        query = urlencode({"year": year, "month": f"{month:02d}", "set_filter": "Y"})
        listing_url = f"{BASE}/ru/statistics/bankstats/?{query}"
        doc = html.fromstring(request_bytes(listing_url).decode("utf-8"))
        links = {}
        for a in doc.xpath("//a[@href]"):
            title = clean(a.text_content())
            lowered = title.lower()
            kind = None
            if "основных показателях коммерческих банков" in lowered:
                kind = "overview"
            elif "о кредитах и депозитах коммерческих банков" in lowered:
                kind = "segments"
            if kind is None:
                continue
            try:
                as_of = reporting_date(title)
            except ValueError:
                as_of = None  # Some archive link titles omit the table's date.
            if as_of and not start <= as_of[:7] <= end:
                continue
            url = urljoin(BASE, a.get("href"))
            links[url] = (kind, as_of)
        for url, (kind, as_of) in links.items():
            if url in cached and (root / cached[url]["path"]).exists():
                item = cached[url]
                as_of = item["date"]
            else:
                body = request_bytes(url)
                page = html.fromstring(body.decode("utf-8"))
                title = clean(" ".join(page.xpath("//h1//text()")))
                actual_date = reporting_date(title + " " + " ".join(page.xpath("//table//text()")))
                if as_of is not None and actual_date != as_of:
                    raise ValueError(f"Listing/table date mismatch: {url}")
                as_of = actual_date
                if not start <= as_of[:7] <= end:
                    continue
                relative = f"data/raw/{as_of}_{kind}_{url.rstrip('/').split('/')[-1]}.html.gz"
                (root / relative).write_bytes(gzip.compress(body, mtime=0))
                item = {
                    "date": as_of, "kind": kind, "title": title, "url": url,
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "path": relative, "sha256": hashlib.sha256(body).hexdigest(),
                    "unit": "UZS billion", "format": "CBU published HTML table",
                }
                time.sleep(0.25)
            key = (as_of, kind)
            if not start <= as_of[:7] <= end:
                continue
            if key in found and found[key]["url"] != url:
                raise ValueError(f"Multiple publications need review for {key}")
            found[key] = item
        # Checkpoint downloads. A repeated refresh can reuse already stored pages.
        checkpoint = {**cached, **{item['url']: item for item in found.values()}}
        manifest_path.write_text(json.dumps(sorted(checkpoint.values(), key=lambda x: (x['date'], x['kind'])), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Scanned {year}-{month:02d}: {len(found)} source tables", flush=True)
        time.sleep(0.25)
    expected = {(f"{y:04d}-{m:02d}-01", kind) for y, m in month_range(start, end) for kind in ("overview", "segments")}
    missing = expected - found.keys()
    if missing:
        raise ValueError(f"Missing monthly sources (no interpolation): {sorted(missing)}")
    manifest_path.write_text(json.dumps(sorted(found.values(), key=lambda x: (x['date'], x['kind'])), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(found)} verified source publications.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2024-01")
    parser.add_argument("--end", default="2026-01")
    args = parser.parse_args()
    fetch(args.start, args.end)
