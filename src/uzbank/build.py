"""Build validated CSVs and a DuckDB analytical database entirely offline."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import duckdb
import pandas as pd

from .fetch import ROOT
from .parse import OVERVIEW, SEGMENTS, name_key, parse_publication


def extract(root: Path):
    manifest = json.loads((root / "data/sources.json").read_text(encoding="utf-8"))
    mapping = pd.read_csv(root / "data/banks.csv")
    aliases = {name_key(r.source_name): (r.bank_id, r.bank_name) for r in mapping.itertuples()}
    facts = {"overview": [], "segments": []}
    totals = {"overview": [], "segments": []}
    checks = []
    seen = set()
    for source in manifest:
        key = (source["date"], source["kind"])
        if key in seen:
            raise ValueError(f"Duplicate publication: {key}")
        seen.add(key)
        body = gzip.decompress((root / source["path"]).read_bytes())
        if hashlib.sha256(body).hexdigest() != source["sha256"]:
            raise ValueError(f"Source hash mismatch: {source['path']}")
        rows, published = parse_publication(body, source["kind"], source["date"])
        for row in rows:
            name = name_key(row["source_name"])
            if name not in aliases:
                raise ValueError(f"Add an explicitly reviewed bank alias: {row['source_name']}")
            row["bank_id"], row["bank_name"] = aliases[name]
            row["source_url"] = source["url"]
        frame = pd.DataFrame(rows)
        if frame["bank_id"].duplicated().any():
            raise ValueError(f"Duplicate bank in {key}")
        fields = OVERVIEW if source["kind"] == "overview" else SEGMENTS
        if (frame[list(fields)] < 0).any().any():
            raise ValueError(f"Negative balance in {key}")
        # Published tables round every individual balance to UZS billion.
        # A rounded sum of N values can differ by at most (N+1)/2.
        for total in published:
            group = total["ownership"]
            selected = frame if group == "total" else frame[frame.ownership == group]
            for field in fields:
                missing = int(selected[field].isna().sum())
                actual = selected[field].sum(min_count=len(selected))
                expected = total[field]
                residual = float(actual - expected) if expected is not None and not pd.isna(actual) else None
                tolerance = (len(selected) + 1) * 0.5 + 1e-6
                checks.append({
                    "date": source["date"], "kind": source["kind"], "ownership": group,
                    "metric": field, "published": expected,
                    "bank_sum": None if pd.isna(actual) else float(actual),
                    "residual": residual, "tolerance": round(tolerance, 6), "missing_count": missing,
                    "status": "pass" if residual is not None and abs(residual) <= tolerance else "fail",
                    "source_url": source["url"],
                })
        facts[source["kind"]].extend(rows)
        totals[source["kind"]].extend(published)
    if not seen:
        raise ValueError("Empty source manifest")
    dates = sorted({x[0] for x in seen})
    expected_dates = pd.date_range(dates[0], dates[-1], freq="MS").strftime("%Y-%m-%d").tolist()
    if dates != expected_dates or seen != {(d, k) for d in dates for k in facts}:
        raise ValueError("Missing monthly source; no interpolation is permitted")
    overview, segments = (pd.DataFrame(facts[k]) for k in ("overview", "segments"))
    keys = ["date", "bank_id"]
    merged = overview.merge(segments, on=keys, suffixes=("", "_segment"), how="outer", validate="one_to_one", indicator=True)
    if not (merged._merge == "both").all():
        raise ValueError("Bank coverage differs across publications")
    if not (merged.ownership == merged.ownership_segment).all():
        raise ValueError("Ownership differs across publications")
    for field in ("loans", "deposits"):
        difference = (merged[field] - merged[f"{field}_segment"]).abs()
        if difference.isna().any() or (difference > 1.000001).any():
            raise ValueError(f"Cross-publication {field} mismatch")
        residual = merged[field] - merged[f"retail_{field}"] - merged[f"corporate_{field}"]
        if residual.isna().any() or (residual.abs() > 1.500001).any():
            raise ValueError(f"Retail/corporate {field} do not reconcile")
    fact = merged[keys + ["bank_name", "source_name", "ownership"] + list(OVERVIEW)
                  + ["retail_loans", "corporate_loans", "retail_deposits", "corporate_deposits", "source_url", "source_url_segment"]].copy()
    fact = fact.rename(columns={"source_url": "overview_url", "source_url_segment": "segments_url"})
    sector = pd.DataFrame(totals["overview"])
    segment_totals = pd.DataFrame(totals["segments"])
    sector = sector.merge(segment_totals.drop(columns=["loans", "deposits"]), on=["date", "ownership"], validate="one_to_one")
    quality = pd.DataFrame(checks)
    return fact.sort_values(keys), sector.sort_values(["date", "ownership"]), quality, manifest


def build(root: Path = ROOT):
    out = root / "data/processed"
    out.mkdir(parents=True, exist_ok=True)
    fact, sector, quality, manifest = extract(root)
    quality.to_csv(out / "quality_checks.csv", index=False, float_format="%.6f", lineterminator="\n")
    if not (quality.status == "pass").all():
        failed = quality[quality.status != "pass"]
        raise ValueError(f"Reconciliation failed; see quality_checks.csv:\n{failed.to_string(index=False)}")
    fact.to_csv(out / "bank_month.csv", index=False, lineterminator="\n")
    sector.to_csv(out / "sector_totals.csv", index=False, lineterminator="\n")
    from .research import prepare_research
    context, macro, research_quality, research_sources = prepare_research(root)
    macro_frame = pd.DataFrame([macro])
    context["date"] = pd.to_datetime(context.date)
    fact["date"] = pd.to_datetime(fact.date)
    sector["date"] = pd.to_datetime(sector.date)
    with duckdb.connect(str(out / "banking.duckdb")) as con:
        con.register("input_banks", fact)
        con.register("input_sector", sector)
        con.execute("CREATE OR REPLACE TABLE fact_bank_month AS SELECT * REPLACE(CAST(date AS DATE) AS date) FROM input_banks")
        con.execute("CREATE OR REPLACE TABLE sector_totals AS SELECT * REPLACE(CAST(date AS DATE) AS date) FROM input_sector")
        con.execute((root / "sql/01_marts.sql").read_text(encoding="utf-8"))
        con.register("input_context", context)
        con.register("input_macro", macro_frame)
        con.execute("CREATE OR REPLACE TABLE sector_context AS SELECT * REPLACE(CAST(date AS DATE) AS date) FROM input_context")
        con.execute("CREATE OR REPLACE TABLE macro_context AS SELECT * FROM input_macro")
        con.execute((root / "sql/03_completed_research.sql").read_text(encoding="utf-8"))
        for view, order in (("bank_month", "date, bank_id"), ("sector_month", "date"),
                            ("ownership_month", "date, ownership"), ("concentration", "date")):
            con.sql(f"SELECT * FROM {view} ORDER BY {order}").df().to_csv(out / f"{view}_metrics.csv", index=False, float_format="%.8f", lineterminator="\n")
        for view, order in (("sector_research", "date"), ("deposit_growth_bridge", "dimension, component"),
                            ("state_share_bridge", "opening_sector_assets"), ("funding_structure", "date, ownership"),
                            ("bank_deposit_growth", "date, bank_id"), ("initial_top5_growth", "cohort")):
            con.sql(f"SELECT * FROM {view} ORDER BY {order}").df().to_csv(out / f"{view}.csv", index=False, float_format="%.8f", lineterminator="\n")
    summary = {
        "start": str(fact.date.min().date()), "end": str(fact.date.max().date()),
        "snapshots": int(fact.date.nunique()), "bank_observations": len(fact),
        "distinct_banks": int(fact.bank_id.nunique()), "source_publications": len(manifest)+len(research_sources),
        "bank_source_publications": len(manifest), "research_source_publications": len(research_sources),
        "reconciliation_checks": len(quality)+len(research_quality),
        "checks_passed": int((quality.status == 'pass').sum())+int((research_quality.status == 'pass').sum()),
        "bank_reconciliation_checks": len(quality), "research_reconciliation_checks": len(research_quality),
        "source_hashes_verified": len(manifest)+len(research_sources), "unit": "UZS billion",
        "retrieved_at": max(s["retrieved_at"] for s in manifest+research_sources),
    }
    (out / "build_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    build()
