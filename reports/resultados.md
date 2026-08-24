# Resultados del backtest del sistema de 4 capas

- Universo operable: **7 tickers** (AAL, AAPL, ABNB, CRM, MSFT, NOW, ORCL)
- Benchmark: SPY (no se opera, solo se compara)
- Ventana: 2025-06-16 -> ultimo dato
- Modo: **scanner** (solo capas 3 y 4). Macro y fundamental en 0 para no
  meter sesgo retrospectivo; ver README.
- Ejecucion walk-forward: senal en t, orden a la apertura de t+1.
- Costes: 1 pb de comision + 5 pb de slippage por lado. Stop 2x ATR(14).

## Barrido de configuraciones

| config                        |   n_trades |   total_return_pct |   benchmark_return_pct |   excess_return_pct |   hit_rate_pct |   max_drawdown_pct |    sharpe |   exposure_pct |   stops_hit |
|:------------------------------|-----------:|-------------------:|-----------------------:|--------------------:|---------------:|-------------------:|----------:|---------------:|------------:|
| loose_prototype_any_zones     |         62 |               4.38 |                  26.91 |              -22.53 |          40.32 |              -7.15 |  0.637555 |          20.74 |          28 |
| loose_layers_any_midline      |         35 |               2.19 |                  26.91 |              -24.72 |          34.29 |              -4.52 |  0.390092 |          17.84 |           8 |
| loose_prototype_any_midline   |         65 |               0.88 |                  26.91 |              -26.03 |          36.92 |              -6.96 |  0.148961 |          21.37 |          15 |
| strict_layers_any_midline     |          7 |               0.58 |                  26.91 |              -26.32 |          14.29 |              -1.47 |  0.356953 |           2.04 |           6 |
| strict_prototype_any_zones    |         43 |               0.03 |                  26.91 |              -26.87 |          25.58 |              -9.24 |  0.033506 |          21.79 |          25 |
| strict_layers_any_zones       |          0 |               0    |                  26.91 |              -26.91 |         nan    |               0    |  0        |           0    |           0 |
| strict_layers_both_midline    |          0 |               0    |                  26.91 |              -26.91 |         nan    |               0    |  0        |           0    |           0 |
| strict_layers_both_zones      |          0 |               0    |                  26.91 |              -26.91 |         nan    |               0    |  0        |           0    |           0 |
| loose_layers_both_zones       |          0 |               0    |                  26.91 |              -26.91 |         nan    |               0    |  0        |           0    |           0 |
| loose_layers_any_zones        |         15 |              -1.07 |                  26.91 |              -27.98 |          20    |              -4.04 | -0.350593 |           4.28 |          11 |
| loose_layers_both_midline     |         16 |              -1.97 |                  26.91 |              -28.88 |          12.5  |              -3.58 | -0.659958 |           7.11 |          12 |
| loose_prototype_both_zones    |         43 |              -2.07 |                  26.91 |              -28.98 |          32.56 |              -8.94 | -0.288502 |          20.62 |          24 |
| loose_prototype_both_midline  |         49 |              -4.04 |                  26.91 |              -30.95 |          20.41 |              -8.46 | -0.531585 |          21.8  |          23 |
| strict_prototype_both_zones   |         38 |              -4.24 |                  26.91 |              -31.15 |          21.05 |              -9.51 | -0.655086 |          20.78 |          23 |
| strict_prototype_any_midline  |         37 |              -4.5  |                  26.91 |              -31.41 |          18.92 |              -8.98 | -0.735203 |          19.86 |          22 |
| strict_prototype_both_midline |         37 |              -5.07 |                  26.91 |              -31.98 |          18.92 |              -9.51 | -0.815704 |          20.28 |          23 |

## Mejor configuracion del barrido

`loose_prototype_any_zones` - 62 operaciones, 4.38% frente al 26.91% de SPY (-22.53 pp), hit rate 40.32%, exposicion media 20.74%.

### Desglose por ticker

| ticker   |   n_trades |   hit_rate_pct |     pnl |   avg_return_pct |
|:---------|-----------:|---------------:|--------:|-----------------:|
| AAL      |          9 |          33.33 | 1891.76 |             4.43 |
| AAPL     |          5 |          60    | 1363.05 |             5.38 |
| ABNB     |          8 |          25    | 1016.44 |             2.73 |
| CRM      |          8 |          50    |  783.5  |             1.94 |
| NOW      |         13 |          46.15 |   17.04 |            -0    |
| MSFT     |          9 |          44.44 |   -4.33 |             0.02 |
| ORCL     |         10 |          30    | -631.47 |            -1.25 |

## Lecturas

- **Ninguna de las 16 configuraciones bate al benchmark** en esta ventana.
- 4 configuraciones no dispararon ni una sola operacion. Todas usan la agregacion `layers` con acuerdo exigido entre las dos ventanas de la capa: pedir que RSI, MACD y StochRSI apunten al mismo lado en dos horizontes a la vez es un filtro que casi nunca se cumple. Es el mismo resultado que aparecio en la prueba de concepto del chat.
- La exposicion media de las configuraciones que si operan es 16.5%: el sistema pasa la mayor parte del tiempo en efectivo. Contra un benchmark que sube, eso solo ya explica casi toda la diferencia de rentabilidad, independientemente de si las senales aciertan.
- Hit rate entre 12.5% y 40.3%. Por debajo del 50% no es descalificante por si solo (una estrategia puede ganar con pocas operaciones muy buenas), pero aqui el profit factor tampoco compensa: ver `sweep.csv`.
- Muestra: 7 tickers. El brief pide las ~83 posiciones reales; con este tamano los numeros son indicativos, no concluyentes. `scripts/fetch_ibkr_gateway.py` completa el resto en una pasada.

## Veredicto vigente (scan de la ultima barra)

| ticker   | verdict   |   score |   L3 |   L4 |   close |   stop_2atr |   rsi14 |   dd63_pct |
|:---------|:----------|--------:|-----:|-----:|--------:|------------:|--------:|-----------:|
| AAPL     | NEUTRAL   |       1 |    0 |    1 |  311.42 |      296.68 |    49.2 |       -8.4 |
| CRM      | NEUTRAL   |       1 |    0 |    1 |  209.53 |      193.74 |    66.3 |       -0   |
| SPY      | NEUTRAL   |       1 |    0 |    1 |  764.85 |      751.47 |    53.4 |       -1.7 |
| MSFT     | NEUTRAL   |       1 |    0 |    1 |  488.84 |      464.69 |    64.6 |       -3.4 |
| ABNB     | NEUTRAL   |       0 |    0 |    0 |  191.75 |      180.2  |    74.3 |        0   |
| AAL      | NEUTRAL   |       0 |    0 |    0 |   13.66 |       12.54 |    36.8 |      -24.7 |
| NOW      | NEUTRAL   |       0 |    0 |    0 |  128.06 |      116.09 |    61.8 |       -5.7 |
| ORCL     | NEUTRAL   |       0 |    0 |    0 |  144.23 |      130.39 |    50.6 |      -41.9 |
