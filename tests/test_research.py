"""Independent controls and accounting invariants for the completed study."""
import gzip
import json
import shutil

import duckdb
import pandas as pd
import pytest

from uzbank.fetch import ROOT
from uzbank.research import prepare_research, source_documents


@pytest.fixture(scope="module")
def research_data(tmp_path_factory):
    root = tmp_path_factory.mktemp("research")
    shutil.copytree(ROOT / "data/research", root / "data/research")
    (root / "data/processed").mkdir()
    shutil.copy(ROOT / "data/processed/sector_totals.csv", root / "data/processed/sector_totals.csv")
    return prepare_research(root)


def test_archived_research_controls(research_data):
    context, macro, checks, sources = research_data
    assert len(sources) == 6
    assert len(checks) == 14 and (checks.status == "pass").all()
    jan26 = context.set_index("date").loc["2026-01-01"]
    # Independent year-end controls in CBU publications 3326238/3326259/3326264.
    assert jan26.lcr_pct == 207.5
    assert jan26.nsfr_pct == 119.9
    assert jan26.deposits_fx == 87336
    assert jan26.liabilities == 789424
    assert jan26.balance_capital == 135339
    assert jan26.regulatory_capital == 150862
    assert macro["cpi_dec_to_dec_pct"] == 7.3


def test_research_source_tampering_is_rejected(tmp_path):
    shutil.copytree(ROOT / "data/research", tmp_path / "data/research")
    sources = json.loads((tmp_path / "data/research/sources.json").read_text(encoding="utf-8"))
    (tmp_path / sources[0]["path"]).write_bytes(gzip.compress(b"altered"))
    with pytest.raises(ValueError, match="hash mismatch"):
        source_documents(tmp_path)


@pytest.fixture(scope="module")
def db(research_data):
    context, macro, *_ = research_data
    tables = {
        "fact_bank_month": pd.read_csv(ROOT / "data/processed/bank_month.csv"),
        "sector_totals": pd.read_csv(ROOT / "data/processed/sector_totals.csv"),
        "sector_context": context,
        "macro_context": pd.DataFrame([macro]),
    }
    connection = duckdb.connect()
    for name, frame in tables.items():
        if "date" in frame:
            frame["date"] = pd.to_datetime(frame.date).dt.date
        connection.register("input_frame", frame)
        connection.execute(f"CREATE TABLE {name} AS SELECT * FROM input_frame")
    for script in ("01_marts.sql", "03_completed_research.sql"):
        connection.execute((ROOT / "sql" / script).read_text(encoding="utf-8"))
    yield connection
    connection.close()


def test_each_deposit_dimension_reconciles_independently(db):
    totals = db.sql("SELECT dimension,SUM(change),SUM(contribution_pct) FROM deposit_growth_bridge GROUP BY dimension").fetchall()
    assert len(totals) == 3
    for _, amount, percentage in totals:
        assert amount == pytest.approx(108566, abs=1)
        assert percentage == pytest.approx(100, abs=.001)
    local = db.execute("SELECT contribution_pct FROM deposit_growth_bridge WHERE component='local'").fetchall()[0][0]
    assert local == pytest.approx(98688/108566*100)


def test_state_share_decomposition_closes_and_identifies_reclassification(db):
    bridge = db.sql("SELECT * FROM state_share_bridge").df().iloc[0]
    assert bridge.growth_effect_pp + bridge.reclassification_effect_pp == pytest.approx(bridge.closing_share_pct-bridge.opening_share_pct)
    changed = db.sql("""SELECT a.bank_id,a.assets FROM fact_bank_month a JOIN fact_bank_month b USING(bank_id)
                        WHERE a.date='2026-01-01' AND b.date='2024-01-01' AND a.ownership<>b.ownership""").fetchall()
    assert changed == [("poytaxt", 557)]
    assert bridge.reclassification_effect_pp == pytest.approx(-557/bridge.closing_sector_assets*100)
    transition = db.execute("SELECT MIN(date) FROM fact_bank_month WHERE bank_id='poytaxt' AND ownership='other'").fetchall()[0][0]
    assert str(transition) == "2024-10-01"


def test_funding_identity_and_real_growth(db):
    invalid = db.execute("""SELECT COUNT(*) FROM funding_structure
                            WHERE ABS(assets-balance_capital-liabilities)>.00001
                               OR ABS(deposits+other_liabilities-liabilities)>.00001
                               OR ABS(deposit_liability_share_pct+other_liability_share_pct-100)>.00001""").fetchall()[0][0]
    assert invalid == 0
    real, contribution = db.execute("SELECT real_deposit_growth_pct,deposit_liability_growth_contribution_pct FROM sector_research WHERE date='2026-01-01'").fetchall()[0]
    assert real == pytest.approx((417258/308692/1.073-1)*100)
    assert contribution == pytest.approx(108566/134886*100)


def test_concentration_cohorts_and_deposit_leaders(db):
    opening, closing = db.execute("SELECT SUM(opening_assets),SUM(closing_assets) FROM initial_top5_growth").fetchall()[0]
    assert opening == 652159
    assert closing == 924765
    cohort = db.sql("SELECT cohort,growth_pct FROM initial_top5_growth ORDER BY growth_pct DESC").fetchall()
    assert cohort[0][0] == "outside_initial_top5"
    assert db.execute("SELECT bank_id FROM bank_deposit_growth WHERE date='2026-01-01' ORDER BY total_change DESC LIMIT 1").fetchall()[0][0] == "agrobank"
    assert db.execute("SELECT bank_id FROM bank_deposit_growth WHERE date='2026-01-01' ORDER BY deposit_share_yoy_pp DESC LIMIT 1").fetchall()[0][0] == "octobank"
    assert db.execute("SELECT COUNT(*) FROM bank_deposit_growth WHERE date='2026-01-01'").fetchall()[0][0] == 35
