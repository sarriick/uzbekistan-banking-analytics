import duckdb
import pandas as pd
import pytest

from uzbank.analytics import indexed_series, latest_at
from uzbank.fetch import ROOT


@pytest.fixture
def con():
    rows = []
    for date, assets in [("2024-01-01", [100,100,100,100]), ("2025-01-01", [200,100,100,100])]:
        for bank, amount in zip("abcd", assets):
            rows.append(dict(date=pd.Timestamp(date), bank_id=bank, bank_name=bank, ownership="other",
                             assets=amount, deposits=0 if bank=="d" else 50, loans=50, capital=10,
                             retail_loans=25, retail_deposits=25))
    # A new bank has no year-ago observation, so it must not get invented growth.
    rows.append(dict(date=pd.Timestamp("2025-01-01"),bank_id="new",bank_name="new",ownership="other",
                     assets=0,deposits=0,loans=0,capital=0,retail_loans=0,retail_deposits=0))
    facts = pd.DataFrame(rows)
    totals = []
    for date, data in facts.groupby("date"):
        for group in ("total", "state"):
            totals.append({"date":date,"ownership":group, **{m:float(data[m].sum()) if group=="total" else 0 for m in ("assets","deposits","loans","capital")}})
    sector = pd.DataFrame(totals)
    conn = duckdb.connect()
    conn.register("f", facts)
    conn.register("s", sector)
    conn.execute("CREATE TABLE fact_bank_month AS SELECT * REPLACE(CAST(date AS DATE) AS date) FROM f")
    conn.execute("CREATE TABLE sector_totals AS SELECT * REPLACE(CAST(date AS DATE) AS date) FROM s")
    conn.execute((ROOT / "sql/01_marts.sql").read_text(encoding="utf-8"))
    yield conn
    conn.close()


def test_market_shares_keep_sector_denominator_after_filter(con):
    share = con.execute("SELECT asset_share_pct FROM bank_month WHERE bank_id='a' AND date='2025-01-01'").fetchone()[0]
    assert share == pytest.approx(40)


def test_growth_and_zero_denominator(con):
    assert con.execute("SELECT assets_yoy_pct FROM bank_month WHERE bank_id='a' AND date='2025-01-01'").fetchone()[0] == pytest.approx(100)
    assert con.execute("SELECT loan_to_deposit_pct FROM bank_month WHERE bank_id='d' LIMIT 1").fetchone()[0] is None
    assert con.execute("SELECT assets_yoy_pct FROM bank_month WHERE bank_id='new'").fetchone()[0] is None


def test_missing_calendar_baseline_does_not_use_previous_row(con):
    con.execute("UPDATE fact_bank_month SET date='2024-02-01' WHERE bank_id='a' AND date='2024-01-01'")
    assert con.execute("SELECT assets_yoy_pct FROM bank_month WHERE bank_id='a' AND date='2025-01-01'").fetchone()[0] is None


def test_known_concentration_example(con):
    hhi, cr5 = con.execute("SELECT hhi,cr5_pct FROM concentration WHERE date='2024-01-01'").fetchone()
    assert hhi == pytest.approx(2500)
    assert cr5 == pytest.approx(100)


def test_index_does_not_invent_zero_baseline():
    frame = pd.DataFrame({"bank_id":["a","a"],"date":pd.to_datetime(["2024-01-01","2025-01-01"]),"assets":[0,100]})
    assert indexed_series(frame,"assets")["index"].isna().all()
    assert latest_at(frame, "2024-02-01").empty
