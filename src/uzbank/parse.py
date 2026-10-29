"""Strict parser for the CBU's two bank-level published table layouts."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from lxml import html
from .fetch import clean, reporting_date

OVERVIEW = ("assets", "loans", "capital", "deposits")
SEGMENTS = ("loans", "retail_loans", "corporate_loans", "deposits", "retail_deposits", "corporate_deposits")


def number(value: str) -> float | None:
    value = clean(value).replace(" ", "").replace(",", ".").replace("−", "-")
    if value in ("", "-", "—", "–", "n/a"):
        return None
    try:
        return float(Decimal(value))
    except InvalidOperation as exc:
        raise ValueError(f"Unexpected number: {value!r}") from exc


def name_key(name: str) -> str:
    return "".join(c for c in name.lower().replace("ё", "е") if c.isalnum())


def parse_publication(body: bytes, kind: str, expected_date: str):
    if kind not in ("overview", "segments"):
        raise ValueError(f"Unknown publication kind {kind}")
    doc = html.fromstring(body.decode("utf-8"))
    title = clean(" ".join(doc.xpath("//h1//text()")))
    if reporting_date(title + " " + " ".join(doc.xpath("//table//text()"))) != expected_date:
        raise ValueError("Publication date does not match manifest")
    tables = [t for t in doc.xpath("//table") if "Наименование банка" in clean(t.text_content())]
    if len(tables) != 1:
        raise ValueError(f"Expected exactly one bank table, found {len(tables)}")
    table = tables[0]
    if "млрд." not in table.text_content().lower() or "сум" not in table.text_content().lower():
        raise ValueError("Expected published units: UZS billion")
    fields = OVERVIEW if kind == "overview" else SEGMENTS
    rows, totals = [], []
    group = None
    for tr in table.xpath(".//tr"):
        cells = [clean(c.text_content()) for c in tr.xpath("./th|./td")]
        if not cells:
            continue
        label = cells[0].lower()
        is_bank = cells[0].isdigit()
        if not is_bank:
            if label == "всего":
                row_group = "total"
            elif "государствен" in label and "без" not in label:
                group = row_group = "state"
            elif "другие банки" in label or ("банки" in label and "без" in label):
                group = row_group = "other"
            else:
                continue
        elif group is None:
            raise ValueError("Bank row has no ownership group")
        start = 2 if is_bank else 1
        step = 2 if kind == "overview" else 1
        indices = list(range(start, start + len(fields) * step, step))
        if len(cells) <= max(indices):
            raise ValueError(f"Unexpected table layout: {cells}")
        metrics = {field: number(cells[idx]) for field, idx in zip(fields, indices)}
        if is_bank:
            rows.append({"date": expected_date, "source_name": cells[1], "ownership": group, **metrics})
        else:
            totals.append({"date": expected_date, "ownership": row_group, **metrics})
    if len(rows) < 20 or {x['ownership'] for x in totals} != {"total", "state", "other"}:
        raise ValueError("Incomplete bank table")
    return rows, totals
