import json

import pandas as pd
import pytest

from conftest import make_ohlcv
from fourlayer.config import SystemConfig
from fourlayer.data.finnhub import FinnhubClient, score_fundamentals
from fourlayer.data.ibkr import ingest_raw_dir, parse_positions, parse_price_history
from fourlayer.data.store import PriceStore, load_universe, save_universe
from fourlayer.firestore import HISTORY_LIMIT, backtest_record, history_for
from fourlayer.layers import SignalContext, compute_signals
from fourlayer.providers import (
    ConstantMacro, EarningsCalendar, NeutralFundamental, NeutralMacro,
    PanelFundamental, SeriesMacro,
)

IBKR_PAYLOAD = {
    "chart_step": 86400,
    "time": ["2026-07-27T13:30:00Z", "2026-07-28T13:30:00Z"],
    "open": [334.99, 340.14], "close": [336.91, 340.08],
    "high": [339.57, 342.89], "low": [334.02, 335.60],
    "volume": [28966574, 30890505],
}


def test_parse_price_history_normalizes_to_dates():
    df = parse_price_history(IBKR_PAYLOAD)
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df.index[0] == pd.Timestamp("2026-07-27")
    assert df.index.tz is None
    assert df["close"].iloc[-1] == pytest.approx(340.08)


def test_parse_price_history_rejects_ragged_columns():
    bad = {**IBKR_PAYLOAD, "volume": [1]}
    with pytest.raises(ValueError, match="volume"):
        parse_price_history(bad)


def test_parse_price_history_rejects_missing_field():
    bad = {k: v for k, v in IBKR_PAYLOAD.items() if k != "high"}
    with pytest.raises(ValueError, match="high"):
        parse_price_history(bad)


def test_parse_positions_strips_exchange_suffix():
    df = parse_positions(
        {"positions": [
            {"contract_description": "NTDOY @PINK", "contract_id": 1, "position": 10.0},
            {"contract_description": "MSFT", "contract_id": 2, "position": 5.0},
        ]}
    )
    assert sorted(df["ticker"]) == ["MSFT", "NTDOY"]


def test_store_roundtrip(tmp_path):
    store = PriceStore(tmp_path)
    df = make_ohlcv(n=50)
    store.save("XYZ", df)
    back = store.load("XYZ")
    pd.testing.assert_frame_equal(df, back, rtol=1e-5, check_freq=False)
    assert store.available() == ["XYZ"]


def test_store_load_many_reports_missing(tmp_path):
    store = PriceStore(tmp_path)
    store.save("AAA", make_ohlcv(n=30))
    ok, skipped = store.load_many(["AAA", "ZZZ"])
    assert list(ok) == ["AAA"] and "ZZZ" in skipped


def test_ingest_raw_dir(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "AAPL.json").write_text(json.dumps(IBKR_PAYLOAD))
    (raw / "BROKEN.json").write_text(json.dumps({"time": [1]}))
    report = ingest_raw_dir(raw, PriceStore(tmp_path / "prices"))
    assert report["ingested"] == {"AAPL": 2}
    assert "BROKEN" in report["failed"]


def test_universe_roundtrip(tmp_path):
    p = tmp_path / "u.json"
    save_universe(["b", "a", "a"], p, meta={"src": "test"})
    assert load_universe(p) == ["a", "b"]


def test_series_macro_is_point_in_time(tmp_path):
    p = tmp_path / "macro.csv"
    pd.DataFrame(
        {"date": ["2025-01-01", "2025-06-01"], "score": [1, -1]}
    ).to_csv(p, index=False)
    m = SeriesMacro(p)
    assert m.score_on(pd.Timestamp("2025-03-01")) == 1
    assert m.score_on(pd.Timestamp("2025-07-01")) == -1
    assert m.score_on(pd.Timestamp("2024-01-01")) == 0  # antes del primer dato


def test_constant_macro_validates_range():
    with pytest.raises(ValueError):
        ConstantMacro(2)


def test_panel_fundamental_forward_fills_per_ticker(tmp_path):
    p = tmp_path / "panel.csv"
    pd.DataFrame({
        "date": ["2025-01-15", "2025-04-20"], "ticker": ["AAA", "AAA"],
        "score": [1, -1], "structural_issue": [False, True],
    }).to_csv(p, index=False)
    panel = PanelFundamental(p)
    assert panel.reading_on("AAA", pd.Timestamp("2025-02-01")).score == 1
    r = panel.reading_on("AAA", pd.Timestamp("2025-05-01"))
    assert r.score == -1 and r.structural_issue
    assert panel.reading_on("ZZZ", pd.Timestamp("2025-05-01")).score == 0


def test_earnings_calendar_days_to_report(tmp_path):
    p = tmp_path / "e.csv"
    pd.DataFrame({"ticker": ["AAA"], "date": ["2025-03-10"]}).to_csv(p, index=False)
    cal = EarningsCalendar(p)
    assert cal.days_to_earnings("AAA", pd.Timestamp("2025-03-01")) == 9
    assert cal.warning("AAA", pd.Timestamp("2025-03-01"), 14)
    assert not cal.warning("AAA", pd.Timestamp("2025-01-01"), 14)
    assert cal.days_to_earnings("BBB", pd.Timestamp("2025-03-01")) is None


def test_finnhub_client_degrades_without_key(tmp_path, monkeypatch):
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    c = FinnhubClient(cache_dir=tmp_path)
    assert not c.enabled
    assert c.basic_financials("AAPL") is None
    assert "FINNHUB_API_KEY" in c.last_error


def test_score_fundamentals_flags_structural_issue():
    score, structural, _ = score_fundamentals(
        {"metric": {"operatingMarginTTM": -30, "roeTTM": -40,
                    "totalDebt/totalEquityQuarterly": 500}}
    )
    assert score == -1 and structural


def test_firestore_history_shape_and_limit():
    df = make_ohlcv(n=520)
    ctx = SignalContext("AAA", df, NeutralMacro(), NeutralFundamental(), EarningsCalendar())
    cfg = SystemConfig()
    s = compute_signals(ctx, cfg)
    records = history_for("AAA", s, cfg.mode)
    assert len(records) <= HISTORY_LIMIT
    r = records[0]
    assert r["ticker"] == "AAA"
    assert set(r["layers"]) == {"macro", "fundamental", "technical_long", "technical_short"}
    assert r["risk"]["stop_atr_multiple"] == 2.0
    assert records[0]["date"] > records[-1]["date"]  # mas reciente primero
    json.dumps(records)  # debe ser serializable tal cual


def test_backtest_record_captures_config():
    rec = backtest_record({"total_return_pct": 1.0}, SystemConfig(), ["AAA"], notes="x")
    assert rec["config"]["execution"] == "t+1 @ open"
    assert rec["universe"] == ["AAA"]
    json.dumps(rec)


def test_ingest_resolves_time_ref(tmp_path):
    """Una serie puede reutilizar el calendario de otra ya ingerida."""
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "SPY.json").write_text(json.dumps(IBKR_PAYLOAD))
    (raw / "AAA.json").write_text(json.dumps({
        "time_ref": "SPY", "open": [1.0, 2.0], "high": [1.5, 2.5],
        "low": [0.5, 1.5], "close": [1.2, 2.2], "volume": [10, 20],
    }))
    store = PriceStore(tmp_path / "prices")
    report = ingest_raw_dir(raw, store)
    assert report["failed"] == {}
    assert store.load("AAA").index.equals(store.load("SPY").index)


def test_ingest_reports_unresolved_time_ref(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "AAA.json").write_text(json.dumps({
        "time_ref": "NOPE", "open": [1.0], "high": [1.0],
        "low": [1.0], "close": [1.0], "volume": [1],
    }))
    report = ingest_raw_dir(raw, PriceStore(tmp_path / "prices"))
    assert "AAA" in report["failed"] and "NOPE" in report["failed"]["AAA"]


def test_parser_widens_range_to_contain_open_and_close():
    payload = {**IBKR_PAYLOAD, "close": [336.91, 350.0]}  # cierre por encima del high
    df = parse_price_history(payload)
    assert df["high"].iloc[-1] == pytest.approx(350.0)
    assert (df["high"] >= df["close"]).all() and (df["low"] <= df["close"]).all()
