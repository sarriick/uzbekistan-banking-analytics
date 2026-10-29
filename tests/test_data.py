import gzip
import hashlib
import json
import shutil

import pandas as pd
import pytest

from uzbank.build import extract
from uzbank.fetch import ROOT
from uzbank.parse import number, reporting_date


@pytest.mark.parametrize("raw, expected", [("12\u00a0345", 12345), ("1 234,5", 1234.5), ("0", 0), ("—", None), ("", None)])
def test_localized_numbers_preserve_missing_and_zero(raw, expected):
    assert number(raw) == expected


def test_bad_numeric_value_fails_loudly():
    with pytest.raises(ValueError):
        number("12abc")


def test_reporting_date_is_not_publication_date():
    assert reporting_date("Сведения по состоянию на 1 января 2025 года 24 января 2025") == "2025-01-01"


def test_all_archived_sources_reconcile():
    fact, sector, checks, sources = extract(ROOT)
    assert fact.date.nunique() == 25
    assert len(sources) == 50
    assert not fact.duplicated(["date", "bank_id"]).any()
    assert fact.date.min() == "2024-01-01"
    assert fact.date.max() == "2026-01-01"
    assert (checks.status == "pass").all()
    assert not fact[["assets", "loans", "deposits", "retail_deposits"]].isna().any().any()
    # Independently published year-end sector controls (CBU 2122860).
    jan25 = sector[(sector.date == "2025-01-01") & (sector.ownership == "total")].iloc[0]
    assert jan25.assets == 769330
    assert jan25.deposits == 308692


def test_renaming_does_not_create_a_new_bank():
    fact, *_ = extract(ROOT)
    openbank = fact[fact.bank_id == "open"]
    assert openbank.date.nunique() == 25
    assert {"Смарт банк", "Опен банк"}.issubset(set(openbank.source_name))


def test_tampered_source_is_rejected(tmp_path):
    (tmp_path / "data/raw").mkdir(parents=True)
    shutil.copy(ROOT / "data/banks.csv", tmp_path / "data/banks.csv")
    sources = json.loads((ROOT / "data/sources.json").read_text(encoding="utf-8"))[:1]
    (tmp_path / "data/sources.json").write_text(json.dumps(sources), encoding="utf-8")
    (tmp_path / sources[0]["path"]).write_bytes(gzip.compress(b"changed"))
    with pytest.raises(ValueError, match="hash mismatch"):
        extract(tmp_path)
