# Resultados del backtest del sistema de 4 capas

- Universo operable: **19 tickers** (AAL, AAPL, ABNB, AMZN, CRM, DT, INTU, MELI, META, MSFT, NET, NOW, ORCL, SHOP, SNOW, TEAM, VEEV, WDAY, ZS)
- Benchmark: SPY (no se opera, solo se compara)
- Ventana: 2025-06-16 -> ultimo dato
- Modo: **scanner** (solo capas 3 y 4). Macro y fundamental en 0 para no
  meter sesgo retrospectivo; ver README.
- Ejecucion walk-forward: senal en t, orden a la apertura de t+1.
- Costes: 1 pb de comision + 5 pb de slippage por lado. Stop 2x ATR(14).

## Barrido de configuraciones

| config                        |   n_trades |   total_return_pct |   benchmark_return_pct |   excess_return_pct |   hit_rate_pct |   max_drawdown_pct |    sharpe |   exposure_pct |   stops_hit |
|:------------------------------|-----------:|-------------------:|-----------------------:|--------------------:|---------------:|-------------------:|----------:|---------------:|------------:|
| loose_layers_any_midline      |        101 |               3.71 |                  26.91 |              -23.2  |          23.76 |             -15.14 |  0.305331 |          43.01 |          31 |
| strict_layers_any_midline     |         19 |               0.88 |                  26.91 |              -26.03 |          21.05 |              -4.59 |  0.216568 |           8.8  |          15 |
| strict_layers_both_midline    |          0 |               0    |                  26.91 |              -26.91 |         nan    |               0    |  0        |           0    |           0 |
| strict_layers_both_zones      |          0 |               0    |                  26.91 |              -26.91 |         nan    |               0    |  0        |           0    |           0 |
| loose_layers_both_zones       |          0 |               0    |                  26.91 |              -26.91 |         nan    |               0    |  0        |           0    |           0 |
| loose_prototype_any_midline   |        169 |              -1.24 |                  26.91 |              -28.15 |          29.59 |             -21.06 |  0.012887 |          54    |          46 |
| loose_prototype_any_zones     |        158 |              -1.85 |                  26.91 |              -28.76 |          31.65 |             -27.53 | -0.015276 |          55.47 |          87 |
| strict_layers_any_zones       |          5 |              -2.71 |                  26.91 |              -29.62 |           0    |              -3.76 | -0.980923 |           3.26 |           5 |
| loose_layers_both_midline     |         50 |              -4.6  |                  26.91 |              -31.5  |          14    |             -12    | -0.538732 |          19.28 |          35 |
| loose_layers_any_zones        |         46 |              -6.06 |                  26.91 |              -32.96 |          17.39 |             -13.05 | -0.716223 |          19.21 |          36 |
| loose_prototype_both_zones    |        119 |             -10.62 |                  26.91 |              -37.53 |          26.89 |             -27.78 | -0.563786 |          54.81 |          75 |
| strict_prototype_any_zones    |        115 |             -11.15 |                  26.91 |              -38.06 |          22.61 |             -28.25 | -0.587068 |          55.19 |          75 |
| strict_prototype_any_midline  |        101 |             -12.36 |                  26.91 |              -39.27 |          19.8  |             -26.54 | -0.722311 |          52.6  |          66 |
| strict_prototype_both_zones   |        102 |             -13.46 |                  26.91 |              -40.36 |          19.61 |             -28.18 | -0.750132 |          54.8  |          68 |
| loose_prototype_both_midline  |        134 |             -13.47 |                  26.91 |              -40.38 |          19.4  |             -29.3  | -0.701687 |          55.85 |          69 |
| strict_prototype_both_midline |        100 |             -14.82 |                  26.91 |              -41.72 |          18    |             -28.65 | -0.852869 |          54.14 |          68 |

## Mejor configuracion del barrido

`loose_layers_any_midline` - 101 operaciones, 3.71% frente al 26.91% de SPY (-23.20 pp), hit rate 23.76%, exposicion media 43.01%.

### Desglose por ticker

| ticker   |   n_trades |   hit_rate_pct |      pnl |   avg_return_pct |
|:---------|-----------:|---------------:|---------:|-----------------:|
| TEAM     |          2 |          50    |  3081.81 |            33.44 |
| AAPL     |          4 |          50    |  1630.3  |             8.37 |
| SHOP     |          5 |          40    |  1406.69 |             5.41 |
| WDAY     |          5 |          20    |   980.04 |             4.38 |
| SNOW     |          4 |          25    |   714.76 |             4.18 |
| ABNB     |          9 |          22.22 |   588.72 |             1.52 |
| NET      |          6 |          33.33 |   546.71 |             2.09 |
| AAL      |          5 |          60    |   398.34 |             1.59 |
| NOW      |          6 |          33.33 |   218.86 |             0.97 |
| MSFT     |          4 |          50    |    99.83 |             0.56 |
| DT       |          6 |          16.67 |   -63.93 |             0.13 |
| ZS       |          4 |          25    |  -138.47 |            -0.46 |
| CRM      |          5 |          20    |  -156.84 |            -0.43 |
| INTU     |          5 |          20    |  -418.69 |            -1.69 |
| VEEV     |          6 |          16.67 |  -535.92 |            -1.52 |
| ORCL     |          2 |           0    |  -752.39 |            -7.89 |
| META     |          5 |           0    |  -829.2  |            -3.43 |
| MELI     |          8 |          12.5  | -1237.91 |            -3.05 |
| AMZN     |         10 |           0    | -1737.92 |            -3.58 |

## Lecturas

- **Ninguna de las 16 configuraciones bate al benchmark** en esta ventana.
- 3 configuraciones no dispararon ni una sola operacion. Todas usan la agregacion `layers` con acuerdo exigido entre las dos ventanas de la capa: pedir que RSI, MACD y StochRSI apunten al mismo lado en dos horizontes a la vez es un filtro que casi nunca se cumple. Es el mismo resultado que aparecio en la prueba de concepto del chat.
- La exposicion media de las configuraciones que si operan es 40.8%: el sistema pasa la mayor parte del tiempo en efectivo. Contra un benchmark que sube, eso solo ya explica casi toda la diferencia de rentabilidad, independientemente de si las senales aciertan.
- Hit rate entre 0.0% y 31.6%. Por debajo del 50% no es descalificante por si solo (una estrategia puede ganar con pocas operaciones muy buenas), pero aqui el profit factor tampoco compensa: ver `sweep.csv`.
- Muestra: 19 tickers. El brief pide las ~83 posiciones reales; con este tamano los numeros son indicativos, no concluyentes. `scripts/fetch_ibkr_gateway.py` completa el resto en una pasada.

## Veredicto vigente (scan de la ultima barra)

| ticker   | verdict   |   score |   L3 |   L4 |   close |   stop_2atr |   rsi14 |   dd63_pct |
|:---------|:----------|--------:|-----:|-----:|--------:|------------:|--------:|-----------:|
| AAPL     | NEUTRAL   |       1 |    0 |    1 |  311.42 |      296.68 |    49.2 |       -8.4 |
| AMZN     | NEUTRAL   |       1 |    0 |    1 |  262.57 |      248    |    52.9 |       -7.6 |
| DT       | NEUTRAL   |       1 |    0 |    1 |   49.34 |       45.53 |    58.6 |       -3   |
| CRM      | NEUTRAL   |       1 |    0 |    1 |  209.53 |      193.74 |    66.3 |       -0   |
| WDAY     | NEUTRAL   |       1 |    0 |    1 |  199.83 |      179.16 |    66.7 |       -3.2 |
| SPY      | NEUTRAL   |       1 |    0 |    1 |  764.85 |      751.47 |    53.4 |       -1.7 |
| NET      | NEUTRAL   |       1 |    0 |    1 |  283.78 |      251.76 |    48.4 |      -14.2 |
| MSFT     | NEUTRAL   |       1 |    0 |    1 |  488.84 |      464.69 |    64.6 |       -3.4 |
| VEEV     | NEUTRAL   |       1 |    0 |    1 |  246.84 |      230.41 |    68.5 |       -2.3 |
| SHOP     | NEUTRAL   |       1 |    0 |    1 |  150.1  |      137.54 |    61.6 |       -5.3 |
| SNOW     | NEUTRAL   |       1 |    0 |    1 |  326    |      300.24 |    62.9 |       -3.4 |
| AAL      | NEUTRAL   |       0 |    0 |    0 |   13.66 |       12.54 |    36.8 |      -24.7 |
| ABNB     | NEUTRAL   |       0 |    0 |    0 |  191.75 |      180.2  |    74.3 |        0   |
| META     | NEUTRAL   |       0 |    0 |    0 |  558.42 |      519.1  |    42.1 |      -18   |
| INTU     | NEUTRAL   |       0 |    0 |    0 |  371.26 |      343.19 |    69.3 |        0   |
| MELI     | NEUTRAL   |       0 |    0 |    0 | 1981.73 |     1847.15 |    63.7 |        0   |
| NOW      | NEUTRAL   |       0 |    0 |    0 |  128.06 |      116.09 |    61.8 |       -5.7 |
| ORCL     | NEUTRAL   |       0 |    0 |    0 |  144.23 |      130.39 |    50.6 |      -41.9 |
| TEAM     | NEUTRAL   |       0 |    0 |    0 |  171.19 |      153.92 |    75.9 |       -2.1 |
| ZS       | NEUTRAL   |       0 |    0 |    0 |  176.33 |      160.5  |    57.7 |       -6.3 |
