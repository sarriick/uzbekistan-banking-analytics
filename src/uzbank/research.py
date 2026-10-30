"""Parse the six archived sources that complete the banking-sector analysis."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import re

from lxml import html
import pandas as pd

from .fetch import ROOT, clean, request_bytes
from .parse import number


def source_documents(root: Path):
    sources = json.loads((root / "data/research/sources.json").read_text(encoding="utf-8"))
    documents = {}
    for source in sources:
        body = gzip.decompress((root / source["path"]).read_bytes())
        if hashlib.sha256(body).hexdigest() != source["sha256"]:
            raise ValueError(f"Research source hash mismatch: {source['source_id']}")
        if source["kind"] in documents:
            raise ValueError(f"Duplicate research source kind: {source['kind']}")
        doc = html.fromstring(body.decode("utf-8"))
        rows = []
        for tr in doc.xpath("//table//tr"):
            row = [clean(c.text_content()) for c in tr.xpath("./th|./td")]
            while row and not row[-1]:
                row.pop()
            if row:
                rows.append(row)
        documents[source["kind"]] = (source, doc, rows)
    required = {"liquidity", "capital_adequacy", "maturity", "sector_indicators", "balance", "monetary_policy"}
    if set(documents) != required:
        raise ValueError("The completed study needs all six selected research sources")
    return documents, sources


def find_row(rows, label):
    matches = [r for r in rows if r[0] == label]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one research row: {label}")
    return matches[0]


def numeric_cell(value):
    result = number(value.rstrip("%"))
    if result is None:
        raise ValueError("Missing research value")
    return result


def prepare_research(root: Path = ROOT):
    documents, sources = source_documents(root)
    dates = ("2025-01-01", "2026-01-01")
    records = {d: {"date": d} for d in dates}

    def put(kind, label, field, positions):
        source, _, rows = documents[kind]
        header_text = " ".join(" ".join(r) for r in rows[:5])
        if not all(d in header_text for d in ("01.01.2025", "01.01.2026")):
            raise ValueError(f"Unexpected research comparison dates: {kind}")
        row = find_row(rows, label)
        for date, position in zip(dates, positions):
            records[date][field] = numeric_cell(row[position])

    for label, field in (("Депозиты", "deposits"), ("Сумма активов", "assets"), ("Кредитные вложения", "loans")):
        put("sector_indicators", label, field, (1, 4))
        put("sector_indicators", label, f"{field}_fx", (2, 5))
    for label, field in (("Итого обязательств", "liabilities"), ("Итого собственного капитала", "balance_capital"),
                         ("Кредиты и лизинговые операции к оплате", "borrowings_leasing"),
                         ("Выпущенные ценные бумаги", "debt_securities"),
                         ("К оплате в банки-резиденты", "due_resident_banks"),
                         ("К оплате в банки-нерезиденты", "due_nonresident_banks"),
                         ("К оплате в Центральный банк", "due_central_bank"),
                         ("Субординированные долговые обязательства", "subordinated_debt"),
                         ("Инвестиции и другие ценные бумаги", "investment_securities"),
                         ("Кредиты, чистые", "net_loans")):
        put("balance", label, field, (1, 3))
    for label, field in (("Коэффициент покрытия ликвидности (мин. значение 100%)", "lcr_pct"),
                         ("Коэффициент чистого стабильного финансирования (мин. значение 100%)", "nsfr_pct"),
                         ("Высоколиквидные активы (млрд. cум)", "high_liquidity_assets")):
        put("liquidity", label, field, (1, 2))
    put("capital_adequacy", "Коэффициент достаточности капитала", "car_pct", (1, 2))
    put("capital_adequacy", "Всего регулятивный капитал", "regulatory_capital", (1, 3))
    _, _, rows = documents["maturity"]
    for date, label in zip(dates, ("01.01.2025 г.", "01.01.2026 г.")):
        row = find_row(rows, label)
        fields = ("maturity_total", "demand_deposits", "term_1_30", "term_31_180", "term_181_365", "term_over_365")
        records[date].update({field: numeric_cell(row[i]) for i, field in enumerate(fields, 1)})
    context = pd.DataFrame(records.values())
    context["deposits_local"] = context.deposits - context.deposits_fx
    context["term_deposits"] = context.deposits - context.demand_deposits
    context["other_liabilities"] = context.liabilities - context.deposits

    _, policy_doc, _ = documents["monetary_policy"]
    policy_text = clean(policy_doc.text_content())
    inflation = re.search(r"В декабре 2025 года общая инфляция.{0,120}?до ([\d,]+)%", policy_text)
    if not inflation or "положительные реальные процентные ставки" not in policy_text:
        raise ValueError("The archived policy statement no longer matches the cited evidence")
    macro = {
        "year": 2025, "cpi_dec_to_dec_pct": numeric_cell(inflation.group(1)),
        "source_id": documents["monetary_policy"][0]["source_id"],
        "source_url": documents["monetary_policy"][0]["url"],
        "interpretation": "CBU identifies positive real interest rates as supporting national-currency savings.",
    }
    sector = pd.read_csv(root / "data/processed/sector_totals.csv")
    checks = []

    def check(date, name, actual, expected, tolerance):
        residual = float(actual - expected)
        checks.append(dict(date=date, check=name, actual=float(actual), expected=float(expected),
                           residual=residual, tolerance=tolerance, status="pass" if abs(residual) <= tolerance else "fail"))

    for row in context.itertuples():
        base = sector[(sector.date == row.date) & (sector.ownership == "total")].iloc[0]
        for field in ("assets", "loans", "deposits"):
            check(row.date, f"{field}_agrees_with_bank_archive", getattr(row, field), base[field], 1)
        check(row.date, "balance_capital_agrees_with_bank_archive", row.balance_capital, base.capital, 1)
        check(row.date, "balance_equation", row.liabilities + row.balance_capital, row.assets, 1.5)
        check(row.date, "maturity_total_agrees_with_sector", row.maturity_total, row.deposits, 1)
        check(row.date, "maturity_buckets_reconcile", row.demand_deposits + row.term_1_30 + row.term_31_180 + row.term_181_365 + row.term_over_365, row.deposits, 3)
        if not 0 <= row.deposits_fx <= row.deposits:
            raise ValueError("Invalid foreign-currency deposit component")
    quality = pd.DataFrame(checks)
    if not (quality.status == "pass").all():
        raise ValueError(f"Research reconciliation failed:\n{quality[quality.status != 'pass']}")
    p = root / "data/processed"
    context.to_csv(p / "sector_context.csv", index=False, lineterminator="\n")
    quality.to_csv(p / "research_checks.csv", index=False, lineterminator="\n")
    (p / "macro_context.json").write_text(json.dumps(macro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return context, macro, quality, sources


def restore_research_sources(root: Path = ROOT):
    """Restore missing frozen evidence only; existing hashes remain authoritative."""
    sources = json.loads((root / "data/research/sources.json").read_text(encoding="utf-8"))
    for source in sources:
        path = root / source["path"]
        if path.exists():
            continue
        body = request_bytes(source["url"])
        if hashlib.sha256(body).hexdigest() != source["sha256"]:
            raise ValueError(f"Source revision requires review: {source['url']}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.compress(body, mtime=0))


if __name__ == "__main__":
    prepare_research()
