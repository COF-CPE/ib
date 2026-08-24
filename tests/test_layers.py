import numpy as np
import pandas as pd
import pytest
from dataclasses import replace

from conftest import make_ohlcv
from fourlayer.config import SystemConfig
from fourlayer.layers import (
    SignalContext, align, compute_signals, technical_layers, verdict_changes, verdicts,
)
from fourlayer.providers import (
    EarningsCalendar, FundamentalReading, NeutralFundamental, NeutralMacro,
    StaticFundamental, ConstantMacro,
)


def ctx_for(df, ticker="TEST", fundamental=None, macro=None, earnings=None):
    return SignalContext(
        ticker, df, macro or NeutralMacro(), fundamental or NeutralFundamental(),
        earnings or EarningsCalendar(),
    )


def test_align_strict_needs_all_three():
    v = pd.DataFrame({"a": [1, 1, 1, -1], "b": [1, 1, 0, -1], "c": [1, 0, 0, -1]})
    strict = align(v, "strict")
    assert list(strict) == [1, 0, 0, -1]


def test_align_loose_needs_two_and_no_opposition():
    v = pd.DataFrame({"a": [1, 1, 1], "b": [1, 0, -1], "c": [0, 0, 1]})
    loose = align(v, "loose")
    # fila 0: 2 arriba, 0 abajo -> +1 | fila 1: solo 1 arriba -> 0
    # fila 2: 2 arriba pero 1 en contra -> 0
    assert list(loose) == [1, 0, 0]


def test_align_rejects_unknown_mode():
    with pytest.raises(ValueError):
        align(pd.DataFrame({"a": [1]}), "medium")


def test_layer_votes_are_in_range(ohlcv):
    cfg = SystemConfig().technical
    t = technical_layers(ohlcv, cfg)
    for col in ("layer3_long", "layer4_short"):
        assert set(t[col].unique()) <= {-1, 0, 1}
    assert t["short_soft"].between(-1, 1).all()
    assert t["long_soft"].between(-1, 1).all()


def test_missing_ohlcv_columns_raise(ohlcv):
    with pytest.raises(ValueError, match="faltan columnas"):
        technical_layers(ohlcv[["close"]], SystemConfig().technical)


def test_structural_issue_cancels_dip_bonus():
    df = make_ohlcv(n=400, seed=3)
    # Fuerza una caida >15% desde el maximo de 63 dias en el ultimo tramo.
    df = df.copy()
    df.iloc[-40:, df.columns.get_loc("close")] *= 0.7
    for c in ("open", "high", "low"):
        df.iloc[-40:, df.columns.get_loc(c)] *= 0.7

    cfg = SystemConfig().technical
    clean = technical_layers(df, cfg)
    assert clean["dip_bonus"].iloc[-1] == 1

    flagged = technical_layers(df, cfg, structural_issue=pd.Series(True, index=df.index))
    assert flagged["dip_bonus"].iloc[-1] == 0


def test_scanner_never_gives_full_verdict(ohlcv):
    cfg = SystemConfig()  # mode="scanner"
    s = compute_signals(ctx_for(ohlcv), cfg)
    assert set(s["verdict"].unique()) <= {"NEUTRAL", "COMPRAR_DEBIL", "VENDER_DEBIL"}
    assert s["composite"].abs().max() <= 2


def test_scanner_zeroes_macro_and_fundamental(ohlcv):
    cfg = SystemConfig()
    s = compute_signals(
        ctx_for(ohlcv, macro=ConstantMacro(1),
                fundamental=StaticFundamental({"TEST": FundamentalReading(1)})),
        cfg,
    )
    assert (s["layer1_macro"] == 0).all()
    assert (s["layer2_fundamental"] == 0).all()


def test_full_mode_uses_all_four_layers(ohlcv):
    cfg = replace(SystemConfig(), mode="full")
    s = compute_signals(
        ctx_for(ohlcv, macro=ConstantMacro(1),
                fundamental=StaticFundamental({"TEST": FundamentalReading(1)})),
        cfg,
    )
    assert (s["layer1_macro"] == 1).all()
    assert (s["layer2_fundamental"] == 1).all()
    expected = s["layer1_macro"] + s["layer2_fundamental"] + s["layer3_long"] + s["layer4_short"]
    pd.testing.assert_series_equal(
        s["composite"].astype("int64"), expected.astype("int64"), check_names=False
    )
    assert s["composite"].abs().max() <= 4


def test_verdict_thresholds():
    cfg = replace(SystemConfig(), mode="full")
    comp = pd.Series([-4, -3, -2, -1, 0, 1, 2, 3, 4])
    assert list(verdicts(comp, cfg)) == [
        "VENDER", "VENDER_DEBIL", "VENDER_DEBIL", "NEUTRAL", "NEUTRAL",
        "NEUTRAL", "COMPRAR_DEBIL", "COMPRAR_DEBIL", "COMPRAR",
    ]


def test_verdict_change_alerts():
    v = pd.Series(["NEUTRAL", "NEUTRAL", "COMPRAR_DEBIL", "COMPRAR_DEBIL", "NEUTRAL"])
    assert list(verdict_changes(v)) == [False, False, True, False, True]


def test_stop_is_two_atr_below_close(ohlcv):
    cfg = SystemConfig()
    s = compute_signals(ctx_for(ohlcv), cfg)
    row = s.dropna(subset=["atr"]).iloc[-1]
    assert row["stop_suggested"] == pytest.approx(row["close"] - 2.0 * row["atr"])


def test_earnings_warning_within_14_days(tmp_path):
    df = make_ohlcv(n=300)
    cal_path = tmp_path / "earnings.csv"
    report_day = df.index[-5]
    pd.DataFrame({"ticker": ["TEST"], "date": [report_day]}).to_csv(cal_path, index=False)
    s = compute_signals(ctx_for(df, earnings=EarningsCalendar(cal_path)), SystemConfig())
    assert bool(s["earnings_warning"].iloc[-10])   # a 5 barras habiles del reporte
    assert not bool(s["earnings_warning"].iloc[0])  # muy lejos


def test_signals_are_walk_forward_safe():
    """La senal de la fecha t es identica si el motor solo ve datos <= t."""
    full = make_ohlcv(n=450, seed=21)
    cut = 380
    cfg = SystemConfig().with_alignment("loose")
    a = compute_signals(ctx_for(full), cfg).iloc[:cut]
    b = compute_signals(ctx_for(full.iloc[:cut]), cfg)
    for col in ("layer3_long", "layer4_short", "composite", "verdict", "atr", "stop_suggested"):
        pd.testing.assert_series_equal(a[col], b[col], check_names=False, rtol=1e-9)
