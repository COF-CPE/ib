# Resultados del backtest del sistema de 4 capas

- Universo operable: **6 tickers** (AAL, AAPL, ABNB, MSFT, NOW, ORCL)
- Benchmark: SPY (no se opera, solo se compara)
- Ventana: 2025-06-16 -> ultimo dato
- Modo: **scanner** (solo capas 3 y 4). Macro y fundamental en 0 para no
  meter sesgo retrospectivo; ver README.
- Ejecucion walk-forward: senal en t, orden a la apertura de t+1.
- Costes: 1 pb de comision + 5 pb de slippage por lado. Stop 2x ATR(14).

## Barrido de configuraciones

| config                        |   n_trades |   total_return_pct |   benchmark_return_pct |   excess_return_pct |   hit_rate_pct |   max_drawdown_pct |    sharpe |   exposure_pct |   stops_hit |
|:------------------------------|-----------:|-------------------:|-----------------------:|--------------------:|---------------:|-------------------:|----------:|---------------:|------------:|
| loose_prototype_any_zones     |         54 |               3.62 |                  26.91 |              -23.29 |          38.89 |              -6.48 |  0.598024 |          18.63 |          25 |
| loose_layers_any_midline      |         30 |               2.35 |                  26.91 |              -24.56 |          36.67 |              -3.78 |  0.447374 |          16.58 |           6 |
| loose_prototype_any_midline   |         54 |               1.54 |                  26.91 |              -25.37 |          38.89 |              -6.04 |  0.254788 |          19.78 |          11 |
| strict_layers_any_midline     |          7 |               0.58 |                  26.91 |              -26.32 |          14.29 |              -1.47 |  0.356953 |           2.04 |           6 |
| loose_layers_both_zones       |          0 |               0    |                  26.91 |              -26.91 |         nan    |               0    |  0        |           0    |           0 |
| strict_layers_both_zones      |          0 |               0    |                  26.91 |              -26.91 |         nan    |               0    |  0        |           0    |           0 |
| strict_layers_both_midline    |          0 |               0    |                  26.91 |              -26.91 |         nan    |               0    |  0        |           0    |           0 |
| strict_layers_any_zones       |          0 |               0    |                  26.91 |              -26.91 |         nan    |               0    |  0        |           0    |           0 |
| loose_layers_any_zones        |         13 |              -0.55 |                  26.91 |              -27.46 |          23.08 |              -3.54 | -0.211969 |           3.43 |          10 |
| strict_prototype_any_zones    |         37 |              -1.09 |                  26.91 |              -28    |          21.62 |              -8.27 | -0.157372 |          19.49 |          22 |
| loose_prototype_both_zones    |         37 |              -1.4  |                  26.91 |              -28.31 |          29.73 |              -7.95 | -0.20196  |          19.12 |          21 |
| loose_layers_both_midline     |         15 |              -1.68 |                  26.91 |              -28.59 |          13.33 |              -3.3  | -0.565061 |           7.06 |          11 |
| loose_prototype_both_midline  |         41 |              -3.37 |                  26.91 |              -30.28 |          19.51 |              -6.79 | -0.485576 |          19.75 |          19 |
| strict_prototype_both_zones   |         32 |              -3.58 |                  26.91 |              -30.49 |          15.62 |              -8.68 | -0.594116 |          19.29 |          20 |
| strict_prototype_any_midline  |         31 |              -3.62 |                  26.91 |              -30.53 |          16.13 |              -7.91 | -0.631661 |          18.47 |          19 |
| strict_prototype_both_midline |         31 |              -4.42 |                  26.91 |              -31.32 |          12.9  |              -8.68 | -0.76773  |          18.79 |          20 |

## Mejor configuracion del barrido

`loose_prototype_any_zones` - 54 operaciones, 3.62% frente al 26.91% de SPY (-23.29 pp), hit rate 38.89%, exposicion media 18.63%.

### Desglose por ticker

| ticker   |   n_trades |   hit_rate_pct |     pnl |   avg_return_pct |
|:---------|-----------:|---------------:|--------:|-----------------:|
| AAL      |          9 |          33.33 | 1893.42 |             4.43 |
| AAPL     |          5 |          60    | 1358.92 |             5.38 |
| ABNB     |          8 |          25    | 1030.17 |             2.73 |
| NOW      |         13 |          46.15 |   25.32 |            -0    |
| MSFT     |          9 |          44.44 |   -2.14 |             0.02 |
| ORCL     |         10 |          30    | -633.14 |            -1.25 |

## Veredicto vigente (scan de la ultima barra)

| ticker   | verdict   |   score |   L3 |   L4 |   close |   stop_2atr |   rsi14 |   dd63_pct |
|:---------|:----------|--------:|-----:|-----:|--------:|------------:|--------:|-----------:|
| AAPL     | NEUTRAL   |       1 |    0 |    1 |  311.42 |      296.68 |    49.2 |       -8.4 |
| SPY      | NEUTRAL   |       1 |    0 |    1 |  764.85 |      751.47 |    53.4 |       -1.7 |
| MSFT     | NEUTRAL   |       1 |    0 |    1 |  488.84 |      464.69 |    64.6 |       -3.4 |
| ABNB     | NEUTRAL   |       0 |    0 |    0 |  191.75 |      180.2  |    74.3 |        0   |
| AAL      | NEUTRAL   |       0 |    0 |    0 |   13.66 |       12.54 |    36.8 |      -24.7 |
| NOW      | NEUTRAL   |       0 |    0 |    0 |  128.06 |      116.09 |    61.8 |       -5.7 |
| ORCL     | NEUTRAL   |       0 |    0 |    0 |  144.23 |      130.39 |    50.6 |      -41.9 |
