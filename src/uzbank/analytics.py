"""Small, testable helpers for presentation. Core metrics live in SQL."""
from __future__ import annotations
import pandas as pd


def indexed_series(frame: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Index each bank to its own first available observation; never divide by 0."""
    result = frame.sort_values(["bank_id", "date"]).copy()
    base = result.groupby("bank_id")[metric].transform("first")
    result["index"] = 100 * result[metric] / base.where(base.ne(0))
    return result


def latest_at(frame: pd.DataFrame, as_of) -> pd.DataFrame:
    """Select an exact snapshot, never carry absent banks forward."""
    return frame.loc[frame.date.eq(pd.Timestamp(as_of))].copy()
