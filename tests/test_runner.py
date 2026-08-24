

def test_first_liquid_bar_skips_dead_period():
    import pandas as pd
    from fourlayer.runner import first_liquid_bar

    idx = pd.date_range("2024-01-01", periods=10, freq="D")
    vol = pd.Series([0, 0, 5, 0, 1, 1, 1, 1, 1, 1], index=idx)
    # 4 barras seguidas con volumen empiezan en el indice 4 -> cierran en el 7
    assert first_liquid_bar(vol, 4) == idx[7]
    assert first_liquid_bar(vol, 9) is None


def test_neutralize_before_leaves_later_verdicts():
    import pandas as pd
    from fourlayer.config import SystemConfig
    from fourlayer.runner import neutralize_before

    idx = pd.date_range("2024-01-01", periods=4, freq="D")
    s = pd.DataFrame(
        {"composite": [2, -2, 2, -2], "verdict": ["COMPRAR_DEBIL", "VENDER_DEBIL"] * 2},
        index=idx,
    )
    out = neutralize_before(s, idx[2], SystemConfig())
    assert list(out["verdict"]) == ["NEUTRAL", "NEUTRAL", "COMPRAR_DEBIL", "VENDER_DEBIL"]
    assert list(out["composite"]) == [0, 0, 2, -2]
