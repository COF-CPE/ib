# Resultados del backtest del sistema de 4 capas

- Universo declarado: **32 tickers** de la cartera IBKR
- Universo operable: **31 tickers** (AAL, AAPL, ABNB, AMZN, ARKG, AUNA, BABA, BMNR, CMG, CRM, DT, HUBS, INTU, MELI, META, MSFT, MSTR, NET, NOW, NVO, ORCL, P, PATH, SE, SHOP, SNOW, SOFI, TEAM, VEEV, WDAY, ZS)
- Benchmark: SPY (no se opera, solo se compara)
- Ventana: desde el primer dato utilizable -> ultimo dato
- Modo: **scanner** (solo capas 3 y 4). Macro y fundamental en 0 para no
  meter sesgo retrospectivo; ver README.
- Ejecucion walk-forward: senal en t, orden a la apertura de t+1.
- Costes: 1 pb de comision + 5 pb de slippage por lado. Stop 2x ATR(14).

## Barrido de configuraciones

| config                        |   n_trades |   total_return_pct |   benchmark_return_pct |   excess_return_pct |   hit_rate_pct |   max_drawdown_pct |    sharpe |   exposure_pct |   stops_hit |
|:------------------------------|-----------:|-------------------:|-----------------------:|--------------------:|---------------:|-------------------:|----------:|---------------:|------------:|
| loose_layers_any_midline      |        157 |               0.14 |                  36.39 |              -36.25 |          22.93 |             -26.04 |  0.075384 |          38.07 |          56 |
| loose_prototype_any_zones     |        225 |               0.04 |                  36.39 |              -36.35 |          34.22 |             -34.02 |  0.086948 |          50.3  |         120 |
| strict_layers_both_zones      |          0 |               0    |                  36.39 |              -36.39 |         nan    |               0    |  0        |           0    |           0 |
| strict_layers_both_midline    |          0 |               0    |                  36.39 |              -36.39 |         nan    |               0    |  0        |           0    |           0 |
| loose_layers_both_zones       |          0 |               0    |                  36.39 |              -36.39 |         nan    |               0    |  0        |           0    |           0 |
| strict_layers_any_midline     |         26 |              -0.65 |                  36.39 |              -37.04 |          19.23 |              -7.8  | -0.058636 |           7.45 |          21 |
| loose_prototype_any_midline   |        242 |              -0.68 |                  36.39 |              -37.07 |          28.93 |             -27.68 |  0.062485 |          48.02 |          75 |
| strict_layers_any_zones       |          6 |              -1.47 |                  36.39 |              -37.86 |          16.67 |              -5.64 | -0.28433  |           4.19 |           5 |
| loose_prototype_both_zones    |        147 |              -3.2  |                  36.39 |              -39.59 |          29.93 |             -35.51 | -0.015323 |          50.21 |          87 |
| strict_prototype_any_zones    |        163 |              -3.64 |                  36.39 |              -40.03 |          28.22 |             -34.83 | -0.026092 |          50.18 |          97 |
| strict_prototype_both_zones   |        127 |              -4.21 |                  36.39 |              -40.6  |          25.98 |             -34    | -0.040791 |          51.14 |          75 |
| loose_layers_both_midline     |         70 |              -4.62 |                  36.39 |              -41.01 |          15.71 |             -16.83 | -0.229485 |          21.25 |          48 |
| strict_prototype_both_midline |        122 |              -4.84 |                  36.39 |              -41.23 |          25.41 |             -33.92 | -0.062277 |          50.77 |          72 |
| strict_prototype_any_midline  |        127 |              -5.21 |                  36.39 |              -41.59 |          25.98 |             -33.84 | -0.079453 |          50.05 |          75 |
| loose_layers_any_zones        |         63 |              -8.1  |                  36.39 |              -44.49 |          19.05 |             -18.89 | -0.499374 |          19.01 |          49 |
| loose_prototype_both_midline  |        177 |             -10.41 |                  36.39 |              -46.8  |          25.99 |             -34.81 | -0.235365 |          51.34 |          86 |

## Mejor configuracion del barrido

`loose_layers_any_midline` - 157 operaciones, 0.14% frente al 36.39% de SPY (-36.25 pp), hit rate 22.93%, exposicion media 38.07%.

### Desglose por ticker

| ticker   |   n_trades |   hit_rate_pct |      pnl |   avg_return_pct |
|:---------|-----------:|---------------:|---------:|-----------------:|
| SOFI     |          3 |          66.67 |  3290.84 |            22.31 |
| TEAM     |          2 |          50    |  2959    |            33.44 |
| ARKG     |          7 |          28.57 |  2144.23 |             6.84 |
| SHOP     |          5 |          40    |  1964.48 |             7.72 |
| AAPL     |          4 |          50    |  1653.89 |             8.37 |
| BABA     |          3 |          33.33 |   976.78 |             6.1  |
| SNOW     |          4 |          25    |   639.3  |             4.18 |
| ABNB     |          9 |          22.22 |   512.06 |             1.52 |
| NET      |          6 |          33.33 |   461.11 |             2.09 |
| AAL      |          5 |          60    |   185.4  |             1.44 |
| NOW      |          6 |          33.33 |   178.86 |             0.97 |
| DT       |          5 |          20    |   166.82 |             1.24 |
| WDAY     |          5 |          20    |   141.52 |             4.38 |
| CMG      |          7 |          28.57 |  -118.29 |            -0.46 |
| CRM      |          5 |          20    |  -219.67 |            -0.43 |
| MSFT     |          3 |          33.33 |  -291.22 |            -2.12 |
| VEEV     |          5 |          20    |  -354.34 |            -0.8  |
| BMNR     |          1 |           0    |  -359.37 |            -7.6  |
| P        |         10 |          30    |  -432.1  |            -0.88 |
| INTU     |          5 |          20    |  -492.72 |            -1.69 |
| ZS       |          4 |          25    |  -641.52 |             0.24 |
| PATH     |          3 |           0    |  -723.34 |            -4.52 |
| ORCL     |          2 |           0    |  -754.53 |            -7.89 |
| SE       |          7 |          14.29 |  -771.98 |            -1.81 |
| META     |          5 |           0    |  -836.51 |            -3.43 |
| MSTR     |          3 |           0    | -1065.75 |            -9.75 |
| AUNA     |          5 |          20    | -1224.43 |            -5.17 |
| MELI     |          8 |          12.5  | -1423.36 |            -3.05 |
| NVO      |          6 |          16.67 | -1681.21 |            -5.56 |
| AMZN     |         10 |           0    | -1791.86 |            -3.61 |
| HUBS     |          4 |           0    | -1811.36 |            -9.92 |

## Lecturas

- **Ninguna de las 16 configuraciones bate al benchmark** en esta ventana.
- 3 configuraciones no dispararon ni una sola operacion. Todas usan la agregacion `layers` con acuerdo exigido entre las dos ventanas de la capa: pedir que RSI, MACD y StochRSI apunten al mismo lado en dos horizontes a la vez es un filtro que casi nunca se cumple. Es el mismo resultado que aparecio en la prueba de concepto del chat.
- La exposicion media de las configuraciones que si operan es 37.8%: el sistema pasa la mayor parte del tiempo en efectivo. Contra un benchmark que sube, eso solo ya explica casi toda la diferencia de rentabilidad, independientemente de si las senales aciertan.
- Hit rate entre 15.7% y 34.2%. Por debajo del 50% no es descalificante por si solo (una estrategia puede ganar con pocas operaciones muy buenas), pero aqui el profit factor tampoco compensa: ver `sweep.csv`.
- Muestra: 31 tickers. El brief pide las ~83 posiciones reales; con este tamano los numeros son indicativos, no concluyentes. `scripts/fetch_ibkr_gateway.py` completa el resto en una pasada.

## Veredicto vigente (scan de la ultima barra)

| ticker   | verdict   |   score |   L3 |   L4 |   close |   stop_2atr |   rsi14 |   dd63_pct |
|:---------|:----------|--------:|-----:|-----:|--------:|------------:|--------:|-----------:|
| AAPL     | NEUTRAL   |       1 |    0 |    1 |  311.42 |      296.68 |    49.2 |       -8.4 |
| AMZN     | NEUTRAL   |       1 |    0 |    1 |  262.57 |      248    |    52.9 |       -7.6 |
| AUNA     | NEUTRAL   |       1 |    0 |    1 |    5.27 |        4.8  |    52.2 |       -2.9 |
| CMG      | NEUTRAL   |       1 |    0 |    1 |   37.87 |       35.05 |    65.3 |       -1.7 |
| MSFT     | NEUTRAL   |       1 |    0 |    1 |  488.84 |      464.69 |    64.6 |       -3.4 |
| DT       | NEUTRAL   |       1 |    0 |    1 |   49.34 |       45.53 |    58.6 |       -3   |
| CRM      | NEUTRAL   |       1 |    0 |    1 |  209.53 |      193.74 |    66.3 |       -0   |
| NET      | NEUTRAL   |       1 |    0 |    1 |  283.78 |      251.76 |    48.4 |      -14.2 |
| SHOP     | NEUTRAL   |       1 |    0 |    1 |  150.1  |      137.54 |    61.6 |       -5.3 |
| SNOW     | NEUTRAL   |       1 |    0 |    1 |  326    |      300.24 |    62.9 |       -3.4 |
| SPY      | NEUTRAL   |       1 |    0 |    1 |  764.85 |      751.47 |    53.4 |       -1.7 |
| VEEV     | NEUTRAL   |       1 |    0 |    1 |  246.84 |      230.41 |    68.5 |       -2.3 |
| WDAY     | NEUTRAL   |       1 |    0 |    1 |  199.83 |      179.16 |    66.7 |       -3.2 |
| SE       | NEUTRAL   |       1 |    0 |    1 |  116.24 |      107.1  |    53.6 |      -11.6 |
| P        | NEUTRAL   |       1 |    0 |    1 |  101.68 |       90.55 |    56.6 |      -13.9 |
| AAL      | NEUTRAL   |       0 |    0 |    0 |   13.66 |       12.54 |    36.8 |      -24.7 |
| META     | NEUTRAL   |       0 |    0 |    0 |  558.42 |      519.1  |    42.1 |      -18   |
| MELI     | NEUTRAL   |       0 |    0 |    0 | 1981.73 |     1847.15 |    63.7 |        0   |
| INTU     | NEUTRAL   |       0 |    0 |    0 |  371.26 |      343.19 |    69.3 |        0   |
| HUBS     | NEUTRAL   |       0 |    0 |    0 |  240.61 |      207.74 |    55.9 |       -8.2 |
| ABNB     | NEUTRAL   |       0 |    0 |    0 |  191.75 |      180.2  |    74.3 |        0   |
| ARKG     | NEUTRAL   |       0 |    0 |    0 |   47.83 |       44.38 |    66.8 |       -3.3 |
| BABA     | NEUTRAL   |       0 |    0 |    0 |  118.81 |      109.82 |    45.4 |      -10.2 |
| BMNR     | NEUTRAL   |       0 |    0 |    0 |   24.46 |       21.9  |    77.3 |        0   |
| PATH     | NEUTRAL   |       0 |    0 |    0 |   16.5  |       14.88 |    70.1 |       -1.1 |
| ORCL     | NEUTRAL   |       0 |    0 |    0 |  144.23 |      130.39 |    50.6 |      -41.9 |
| NOW      | NEUTRAL   |       0 |    0 |    0 |  128.06 |      116.09 |    61.8 |       -5.7 |
| NVO      | NEUTRAL   |       0 |    0 |    0 |   46.81 |       44.05 |    48.9 |       -9.3 |
| MSTR     | NEUTRAL   |       0 |    0 |    0 |  122.14 |      108.32 |    67.7 |      -23.6 |
| SOFI     | NEUTRAL   |       0 |    0 |    0 |   18.4  |       16.72 |    53.9 |       -2.7 |
| TEAM     | NEUTRAL   |       0 |    0 |    0 |  171.19 |      153.92 |    75.9 |       -2.1 |
| ZS       | NEUTRAL   |       0 |    0 |    0 |  176.33 |      160.5  |    57.7 |       -6.3 |

Descartados por datos insuficientes: AAL, AAPL, ABNB, AMZN, ARKG, AUNA, BABA, BMNR, CMG, CRM, DT, HUBS, INTU, MELI, META, MSFT, MSTR, NET, NOW, NVO, ORCL, P, PATH, SE, SHOP, SNOW, SOFI, SPCX, SPY, TEAM, VEEV, WDAY, ZS
