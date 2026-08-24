# Resultados del backtest del sistema de 4 capas

- Universo declarado: **58 tickers** de la cartera IBKR
- Universo operable: **57 tickers** (AAL, AAPL, ABNB, ABT, ADBE, AFRM, AMZN, ARKG, AUNA, BABA, BMNR, CBOE, CME, CMG, COPX, CRM, DHI, DT, DXYZ, FCX, GDDY, HUBS, INTU, ISRG, KD, LUV, MCO, MELI, META, MSCI, MSFT, MSOS, MSTR, NEE, NET, NFLX, NOW, NVDA, NVO, ORCL, OXY, P, PATH, PFE, QBTS, SE, SHOP, SMCI, SNOW, SOFI, SPGI, TEAM, TSLA, UBER, VEEV, WDAY, ZS)
- Benchmark: SPY (no se opera, solo se compara)
- Ventana: desde el primer dato utilizable -> ultimo dato
- Modo: **scanner** (solo capas 3 y 4). Macro y fundamental en 0 para no
  meter sesgo retrospectivo; ver README.
- Ejecucion walk-forward: senal en t, orden a la apertura de t+1.
- Costes: 1 pb de comision + 5 pb de slippage por lado. Stop 2x ATR(14).

## Barrido de configuraciones

| config                        |   n_trades |   total_return_pct |   benchmark_return_pct |   excess_return_pct |   hit_rate_pct |   max_drawdown_pct |    sharpe |   exposure_pct |   stops_hit |
|:------------------------------|-----------:|-------------------:|-----------------------:|--------------------:|---------------:|-------------------:|----------:|---------------:|------------:|
| strict_prototype_any_midline  |        121 |               7.78 |                  36.39 |              -28.6  |          26.45 |             -29.4  |  0.290152 |          59.37 |          67 |
| strict_prototype_both_midline |        117 |               7.04 |                  36.39 |              -29.34 |          27.35 |             -27.81 |  0.27293  |          59.44 |          65 |
| loose_prototype_both_midline  |        170 |               6.62 |                  36.39 |              -29.77 |          23.53 |             -26.83 |  0.261578 |          59.17 |          75 |
| strict_prototype_any_zones    |        173 |               3.76 |                  36.39 |              -32.63 |          26.01 |             -27.04 |  0.193312 |          59.04 |          99 |
| strict_prototype_both_zones   |        126 |               3.14 |                  36.39 |              -33.25 |          25.4  |             -28.97 |  0.177482 |          59.4  |          71 |
| loose_prototype_both_zones    |        147 |               1.76 |                  36.39 |              -34.63 |          27.21 |             -26.4  |  0.139338 |          59.08 |          84 |
| loose_prototype_any_zones     |        206 |               1.47 |                  36.39 |              -34.92 |          33.01 |             -31.42 |  0.12761  |          58.7  |         119 |
| strict_layers_both_midline    |          0 |               0    |                  36.39 |              -36.39 |         nan    |               0    |  0        |           0    |           0 |
| strict_layers_both_zones      |          0 |               0    |                  36.39 |              -36.39 |         nan    |               0    |  0        |           0    |           0 |
| loose_layers_both_zones       |          0 |               0    |                  36.39 |              -36.39 |         nan    |               0    |  0        |           0    |           0 |
| strict_layers_any_zones       |          6 |              -1.47 |                  36.39 |              -37.86 |          16.67 |              -5.64 | -0.28433  |           4.19 |           5 |
| loose_prototype_any_midline   |        256 |              -3.42 |                  36.39 |              -39.81 |          28.52 |             -25.16 | -0.008531 |          57.92 |          87 |
| strict_layers_any_midline     |         54 |              -8.9  |                  36.39 |              -45.29 |          12.96 |             -21.6  | -0.366953 |          19.93 |          46 |
| loose_layers_any_midline      |        235 |              -9.82 |                  36.39 |              -46.21 |          22.98 |             -23.57 | -0.247832 |          54.46 |          88 |
| loose_layers_any_zones        |        111 |             -12    |                  36.39 |              -48.39 |          18.92 |             -26.75 | -0.361724 |          42.94 |          87 |
| loose_layers_both_midline     |        142 |             -14.52 |                  36.39 |              -50.91 |          14.08 |             -27.34 | -0.419853 |          46.38 |          97 |

## Mejor configuracion del barrido

`strict_prototype_any_midline` - 121 operaciones, 7.78% frente al 36.39% de SPY (-28.60 pp), hit rate 26.45%, exposicion media 59.37%.

### Desglose por ticker

| ticker   |   n_trades |   hit_rate_pct |      pnl |   avg_return_pct |
|:---------|-----------:|---------------:|---------:|-----------------:|
| COPX     |          2 |          50    |  4222.21 |            36.17 |
| ARKG     |          3 |          66.67 |  3100.08 |            19.9  |
| FCX      |          3 |          33.33 |  2297.9  |            22.59 |
| AFRM     |          2 |          50    |  1909.16 |            24.78 |
| NET      |          3 |          66.67 |  1798.93 |            13.84 |
| CBOE     |          1 |         100    |  1760.24 |            35.2  |
| ABNB     |          5 |          20    |  1554.96 |             6.07 |
| AAPL     |          1 |         100    |  1441.57 |            37.56 |
| SNOW     |          2 |          50    |  1440.76 |            15.72 |
| QBTS     |          1 |         100    |  1154.03 |            23.08 |
| ADBE     |          3 |          33.33 |  1088.31 |             8.98 |
| SHOP     |          1 |         100    |   857.87 |            17.16 |
| SOFI     |          1 |         100    |   770.93 |            15.42 |
| CMG      |          2 |          50    |   437.05 |             4.45 |
| CME      |          6 |          16.67 |   407.24 |             1.28 |
| BABA     |          1 |         100    |   389.08 |             7.41 |
| INTU     |          2 |          50    |   331.04 |             6.87 |
| MCO      |          3 |          66.67 |   322.3  |             2.35 |
| META     |          2 |          50    |     1.66 |             1.04 |
| NVDA     |          3 |          66.67 |   -24.71 |             0.14 |
| SPGI     |          1 |           0    |   -85.28 |            -3.41 |
| PFE      |          1 |           0    |  -117.15 |            -2.92 |
| NOW      |          1 |           0    |  -195.33 |            -3.91 |
| AAL      |          2 |          50    |  -197.72 |            -2.31 |
| ISRG     |          1 |           0    |  -254.54 |            -5.76 |
| KD       |          1 |           0    |  -263.9  |            -5.28 |
| MSFT     |          2 |           0    |  -265.82 |            -3.14 |
| MELI     |          1 |           0    |  -291.11 |            -5.82 |
| LUV      |          5 |          20    |  -301.4  |             0.88 |
| SE       |          2 |          50    |  -304.89 |            -2.6  |
| NVO      |          1 |           0    |  -404.1  |            -8.58 |
| ABT      |          4 |          25    |  -404.9  |            -1.98 |
| OXY      |          1 |           0    |  -413.97 |            -8.63 |
| AMZN     |          5 |          20    |  -430.81 |            -1.36 |
| ORCL     |          2 |           0    |  -461.06 |            -8.25 |
| MSTR     |          1 |           0    |  -464.27 |            -9.29 |
| NEE      |          3 |           0    |  -521.12 |            -3.45 |
| AUNA     |          3 |           0    |  -537.33 |            -7.95 |
| NFLX     |          3 |           0    |  -560.54 |            -3.82 |
| DT       |          3 |           0    |  -590.17 |            -3.97 |
| TSLA     |          3 |           0    |  -618.11 |            -5.07 |
| GDDY     |          2 |           0    |  -651.33 |           -10.37 |
| P        |          6 |          16.67 |  -722.77 |            -3.2  |
| MSCI     |          4 |           0    |  -754.87 |            -3.99 |
| CRM      |          2 |           0    |  -778.98 |            -7.57 |
| DHI      |          3 |           0    |  -779.85 |            -5.07 |
| PATH     |          2 |           0    | -1393.15 |           -13.22 |
| DXYZ     |          4 |          25    | -1481.18 |           -11.81 |
| SMCI     |          2 |           0    | -1506.77 |           -15.33 |
| MSOS     |          3 |          33.33 | -1630.82 |            -8.2  |

## Lecturas

- **Ninguna de las 16 configuraciones bate al benchmark** en esta ventana.
- 3 configuraciones no dispararon ni una sola operacion. Todas usan la agregacion `layers` con acuerdo exigido entre las dos ventanas de la capa: pedir que RSI, MACD y StochRSI apunten al mismo lado en dos horizontes a la vez es un filtro que casi nunca se cumple. Es el mismo resultado que aparecio en la prueba de concepto del chat.
- La exposicion media de las configuraciones que si operan es 49.2%: el sistema pasa la mayor parte del tiempo en efectivo. Contra un benchmark que sube, eso solo ya explica casi toda la diferencia de rentabilidad, independientemente de si las senales aciertan.
- Hit rate entre 13.0% y 33.0%. Por debajo del 50% no es descalificante por si solo (una estrategia puede ganar con pocas operaciones muy buenas), pero aqui el profit factor tampoco compensa: ver `sweep.csv`.
- Muestra: 57 tickers. El brief pide las ~83 posiciones reales; con este tamano los numeros son indicativos, no concluyentes. `scripts/fetch_ibkr_gateway.py` completa el resto en una pasada.

## Veredicto vigente (scan de la ultima barra)

| ticker   | verdict   |   score |   L3 |   L4 |   close |   stop_2atr |   rsi14 |   dd63_pct |
|:---------|:----------|--------:|-----:|-----:|--------:|------------:|--------:|-----------:|
| AAPL     | NEUTRAL   |       1 |    0 |    1 |  311.42 |      296.68 |    49.2 |       -8.4 |
| AFRM     | NEUTRAL   |       1 |    0 |    1 |   76.98 |       69.94 |    52.2 |      -10.3 |
| AUNA     | NEUTRAL   |       1 |    0 |    1 |    5.27 |        4.8  |    52.2 |       -2.9 |
| AMZN     | NEUTRAL   |       1 |    0 |    1 |  262.57 |      248    |    52.9 |       -7.6 |
| DXYZ     | NEUTRAL   |       1 |    0 |    1 |   32.34 |       27.81 |    60   |      -46.3 |
| DT       | NEUTRAL   |       1 |    0 |    1 |   49.34 |       45.53 |    58.6 |       -3   |
| COPX     | NEUTRAL   |       1 |    0 |    1 |   94.42 |       88.85 |    69.4 |       -0.2 |
| CRM      | NEUTRAL   |       1 |    0 |    1 |  209.53 |      193.74 |    66.3 |       -0   |
| CMG      | NEUTRAL   |       1 |    0 |    1 |   37.87 |       35.05 |    65.3 |       -1.7 |
| CBOE     | NEUTRAL   |       1 |    0 |    1 |  308.34 |      286.67 |    61.6 |      -13   |
| GDDY     | NEUTRAL   |       1 |    0 |    1 |  100.43 |       90.98 |    58.8 |       -4.4 |
| SNOW     | NEUTRAL   |       1 |    0 |    1 |  326    |      300.24 |    62.9 |       -3.4 |
| P        | NEUTRAL   |       1 |    0 |    1 |  101.68 |       90.55 |    56.6 |      -13.9 |
| SMCI     | NEUTRAL   |       1 |    0 |    1 |   35.37 |       30.34 |    55.7 |      -29.5 |
| VEEV     | NEUTRAL   |       1 |    0 |    1 |  246.84 |      230.41 |    68.5 |       -2.3 |
| WDAY     | NEUTRAL   |       1 |    0 |    1 |  199.83 |      179.16 |    66.7 |       -3.2 |
| SPY      | NEUTRAL   |       1 |    0 |    1 |  764.85 |      751.47 |    53.4 |       -1.7 |
| SHOP     | NEUTRAL   |       1 |    0 |    1 |  150.1  |      137.54 |    61.6 |       -5.3 |
| SE       | NEUTRAL   |       1 |    0 |    1 |  116.24 |      107.1  |    53.6 |      -11.6 |
| MSOS     | NEUTRAL   |       1 |    0 |    1 |    4.89 |        4.45 |    61.2 |      -15   |
| MSFT     | NEUTRAL   |       1 |    0 |    1 |  488.84 |      464.69 |    64.6 |       -3.4 |
| NVDA     | NEUTRAL   |       1 |    0 |    1 |  209.37 |      196.76 |    45.5 |       -7.1 |
| NET      | NEUTRAL   |       1 |    0 |    1 |  283.78 |      251.76 |    48.4 |      -14.2 |
| MCO      | NEUTRAL   |       1 |    0 |    1 |  508.45 |      485.6  |    65.2 |       -2   |
| BABA     | NEUTRAL   |       0 |    0 |    0 |  118.81 |      109.82 |    45.4 |      -10.2 |
| ARKG     | NEUTRAL   |       0 |    0 |    0 |   47.83 |       44.38 |    66.8 |       -3.3 |
| SOFI     | NEUTRAL   |       0 |    0 |    0 |   18.4  |       16.72 |    53.9 |       -2.7 |
| OXY      | NEUTRAL   |       0 |    0 |    0 |   60.26 |       57.14 |    61.2 |       -2   |
| KD       | NEUTRAL   |       0 |    0 |    0 |   13.03 |       11.6  |    51.5 |      -11.3 |
| LUV      | NEUTRAL   |       0 |    0 |    0 |   40.72 |       37.92 |    33.4 |      -21.8 |
| HUBS     | NEUTRAL   |       0 |    0 |    0 |  240.61 |      207.74 |    55.9 |       -8.2 |
| FCX      | NEUTRAL   |       0 |    0 |    0 |   77.47 |       71.51 |    70.2 |        0   |
| CME      | NEUTRAL   |       0 |    0 |    0 |  278.26 |      265.64 |    67.7 |       -1.5 |
| INTU     | NEUTRAL   |       0 |    0 |    0 |  371.26 |      343.19 |    69.3 |        0   |
| BMNR     | NEUTRAL   |       0 |    0 |    0 |   24.46 |       21.9  |    77.3 |        0   |
| ABT      | NEUTRAL   |       0 |    0 |    0 |  116.65 |      111.52 |    77.8 |        0   |
| AAL      | NEUTRAL   |       0 |    0 |    0 |   13.66 |       12.54 |    36.8 |      -24.7 |
| ABNB     | NEUTRAL   |       0 |    0 |    0 |  191.75 |      180.2  |    74.3 |        0   |
| ADBE     | NEUTRAL   |       0 |    0 |    0 |  276.24 |      254.9  |    62.9 |        0   |
| NOW      | NEUTRAL   |       0 |    0 |    0 |  128.06 |      116.09 |    61.8 |       -5.7 |
| MSTR     | NEUTRAL   |       0 |    0 |    0 |  122.14 |      108.32 |    67.7 |      -23.6 |
| MELI     | NEUTRAL   |       0 |    0 |    0 | 1981.73 |     1847.15 |    63.7 |        0   |
| UBER     | NEUTRAL   |       0 |    0 |    0 |   79.09 |       73.78 |    62.6 |        0   |
| PATH     | NEUTRAL   |       0 |    0 |    0 |   16.5  |       14.88 |    70.1 |       -1.1 |
| NVO      | NEUTRAL   |       0 |    0 |    0 |   46.81 |       44.05 |    48.9 |       -9.3 |
| ORCL     | NEUTRAL   |       0 |    0 |    0 |  144.23 |      130.39 |    50.6 |      -41.9 |
| NFLX     | NEUTRAL   |       0 |    0 |    0 |   80.39 |       75.8  |    63.4 |       -8.3 |
| META     | NEUTRAL   |       0 |    0 |    0 |  558.42 |      519.1  |    42.1 |      -18   |
| NEE      | NEUTRAL   |       0 |    0 |    0 |   84.05 |       81.11 |    35.1 |       -6.4 |
| QBTS     | NEUTRAL   |       0 |    0 |    0 |   18.89 |       16.01 |    45.6 |      -37.3 |
| ZS       | NEUTRAL   |       0 |    0 |    0 |  176.33 |      160.5  |    57.7 |       -6.3 |
| TSLA     | NEUTRAL   |       0 |    0 |    0 |  349.28 |      321.41 |    51.5 |      -21   |
| PFE      | NEUTRAL   |       0 |    0 |    0 |   28.02 |       26.84 |    69.4 |       -0.8 |
| TEAM     | NEUTRAL   |       0 |    0 |    0 |  171.19 |      153.92 |    75.9 |       -2.1 |
| ISRG     | NEUTRAL   |      -1 |    0 |   -1 |  373.58 |      347.81 |    45.2 |      -14.4 |
| DHI      | NEUTRAL   |      -1 |    0 |   -1 |  149.04 |      139.96 |    50.3 |      -10.7 |
| MSCI     | NEUTRAL   |      -1 |    0 |   -1 |  570.98 |      541.4  |    49.2 |      -11.3 |
| SPGI     | NEUTRAL   |      -1 |    0 |   -1 |  385.23 |      362    |    45.6 |       -9.3 |

Descartados por datos insuficientes: AAL, AAPL, ABNB, ABT, ADBE, AFRM, AMZN, ARKG, AUNA, BABA, BMNR, CBOE, CME, CMG, COPX, CRM, DHI, DT, DXYZ, FCX, GDDY, HUBS, INTU, ISRG, KD, LUV, MCO, MELI, META, MSCI, MSFT, MSOS, MSTR, NEE, NET, NFLX, NOW, NVDA, NVO, ORCL, OXY, P, PATH, PFE, QBTS, SE, SHOP, SMCI, SNOW, SOFI, SPCX, SPGI, SPY, TEAM, TSLA, UBER, VEEV, WDAY, ZS
