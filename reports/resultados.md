# Resultados del backtest del sistema de 4 capas

- Universo declarado: **44 tickers** de la cartera IBKR
- Universo operable: **43 tickers** (AAL, AAPL, ABNB, ABT, ADBE, AFRM, AMZN, ARKG, AUNA, BABA, BMNR, CBOE, CME, CMG, CRM, DT, GDDY, HUBS, INTU, KD, MCO, MELI, META, MSFT, MSTR, NET, NFLX, NOW, NVDA, NVO, ORCL, P, PATH, SE, SHOP, SNOW, SOFI, SPGI, TEAM, TSLA, VEEV, WDAY, ZS)
- Benchmark: SPY (no se opera, solo se compara)
- Ventana: desde el primer dato utilizable -> ultimo dato
- Modo: **scanner** (solo capas 3 y 4). Macro y fundamental en 0 para no
  meter sesgo retrospectivo; ver README.
- Ejecucion walk-forward: senal en t, orden a la apertura de t+1.
- Costes: 1 pb de comision + 5 pb de slippage por lado. Stop 2x ATR(14).

## Barrido de configuraciones

| config                        |   n_trades |   total_return_pct |   benchmark_return_pct |   excess_return_pct |   hit_rate_pct |   max_drawdown_pct |    sharpe |   exposure_pct |   stops_hit |
|:------------------------------|-----------:|-------------------:|-----------------------:|--------------------:|---------------:|-------------------:|----------:|---------------:|------------:|
| strict_prototype_both_midline |        131 |              11.78 |                  36.39 |              -24.61 |          28.24 |             -26.12 |  0.417343 |          57.2  |          69 |
| strict_prototype_both_zones   |        128 |              10.07 |                  36.39 |              -26.32 |          27.34 |             -27.36 |  0.369324 |          57.17 |          70 |
| strict_prototype_any_midline  |        140 |               5.74 |                  36.39 |              -30.64 |          27.14 |             -28.18 |  0.252086 |          56.88 |          77 |
| strict_prototype_any_zones    |        164 |               5.6  |                  36.39 |              -30.79 |          28.66 |             -26.82 |  0.25225  |          57.26 |          96 |
| loose_prototype_any_zones     |        213 |               5.26 |                  36.39 |              -31.13 |          34.74 |             -26.59 |  0.240786 |          56.01 |         113 |
| loose_prototype_both_zones    |        147 |               2.73 |                  36.39 |              -33.66 |          29.25 |             -28.34 |  0.165586 |          56.7  |          86 |
| strict_layers_both_midline    |          0 |               0    |                  36.39 |              -36.39 |         nan    |               0    |  0        |           0    |           0 |
| strict_layers_both_zones      |          0 |               0    |                  36.39 |              -36.39 |         nan    |               0    |  0        |           0    |           0 |
| loose_layers_both_zones       |          0 |               0    |                  36.39 |              -36.39 |         nan    |               0    |  0        |           0    |           0 |
| strict_layers_any_zones       |          6 |              -1.47 |                  36.39 |              -37.86 |          16.67 |              -5.64 | -0.28433  |           4.19 |           5 |
| strict_layers_any_midline     |         36 |              -2.82 |                  36.39 |              -39.21 |          16.67 |             -10.64 | -0.228533 |          12.15 |          29 |
| loose_prototype_any_midline   |        280 |              -4.56 |                  36.39 |              -40.94 |          28.93 |             -26.55 | -0.06512  |          54.37 |          90 |
| loose_layers_any_zones        |         90 |              -6.22 |                  36.39 |              -42.61 |          23.33 |             -21.39 | -0.234842 |          33.06 |          67 |
| loose_prototype_both_midline  |        208 |              -6.94 |                  36.39 |              -43.33 |          23.56 |             -30    | -0.122186 |          57.69 |         101 |
| loose_layers_both_midline     |        105 |             -11.33 |                  36.39 |              -47.72 |          15.24 |             -20.91 | -0.521792 |          32.32 |          72 |
| loose_layers_any_midline      |        212 |             -12.51 |                  36.39 |              -48.9  |          20.75 |             -27.38 | -0.415394 |          45.29 |          78 |

## Mejor configuracion del barrido

`strict_prototype_both_midline` - 131 operaciones, 11.78% frente al 36.39% de SPY (-24.61 pp), hit rate 28.24%, exposicion media 57.2%.

### Desglose por ticker

| ticker   |   n_trades |   hit_rate_pct |      pnl |   avg_return_pct |
|:---------|-----------:|---------------:|---------:|-----------------:|
| TEAM     |          1 |         100    |  7023    |           158.9  |
| ARKG     |          4 |          50    |  2981.1  |            16.7  |
| AFRM     |          2 |          50    |  2354.37 |            26.54 |
| NET      |          2 |         100    |  2166.3  |            26.48 |
| CBOE     |          1 |         100    |  1760.24 |            35.2  |
| AAPL     |          1 |         100    |  1700.43 |            36.51 |
| SNOW     |          3 |          33.33 |  1206.99 |             7.8  |
| ADBE     |          3 |          33.33 |  1147.14 |             8.36 |
| ABNB     |          7 |          14.29 |  1056.63 |             2.85 |
| CME      |          7 |          42.86 |   877.62 |             2.72 |
| SHOP     |          1 |         100    |   857.87 |            17.16 |
| SOFI     |          1 |         100    |   770.93 |            15.42 |
| DT       |          3 |          33.33 |   429    |             2.98 |
| NVDA     |          4 |          50    |   114.95 |             0.9  |
| MCO      |          7 |          42.86 |   102.84 |             0.45 |
| CMG      |          3 |          33.33 |   100.76 |             1.37 |
| BABA     |          2 |          50    |   -52.45 |            -0.35 |
| NFLX     |          6 |          16.67 |  -117.92 |            -0.31 |
| MSFT     |          2 |           0    |  -165.81 |            -4.95 |
| NOW      |          1 |           0    |  -195.33 |            -3.91 |
| P        |          7 |          14.29 |  -200.11 |            -0.33 |
| KD       |          1 |           0    |  -263.9  |            -5.28 |
| NVO      |          1 |           0    |  -273.96 |            -5.78 |
| SPGI     |          3 |           0    |  -278.21 |            -3.33 |
| PATH     |          1 |           0    |  -309.74 |            -9.26 |
| VEEV     |          3 |          33.33 |  -311.77 |            -1.75 |
| AMZN     |          4 |          50    |  -337.58 |            -1.2  |
| ZS       |          1 |           0    |  -398.53 |            -7.86 |
| ABT      |          6 |          33.33 |  -401.78 |            -1.33 |
| META     |          4 |          25    |  -430.92 |            -2.66 |
| SE       |          3 |          33.33 |  -495.01 |            -1.83 |
| CRM      |          3 |          33.33 |  -528.63 |            -3.68 |
| GDDY     |          4 |          25    |  -585.96 |            -9.83 |
| ORCL     |          5 |          20    |  -597.19 |            -3.43 |
| MELI     |          2 |           0    |  -633.25 |            -6.69 |
| AUNA     |          5 |           0    |  -997.44 |            -6.95 |
| INTU     |          4 |          25    | -1150.69 |            -6.51 |
| AAL      |          4 |           0    | -1273.29 |            -6.45 |
| TSLA     |          7 |           0    | -1335.09 |            -5.79 |
| MSTR     |          2 |           0    | -1430.62 |           -14.01 |

## Lecturas

- **Ninguna de las 16 configuraciones bate al benchmark** en esta ventana.
- 3 configuraciones no dispararon ni una sola operacion. Todas usan la agregacion `layers` con acuerdo exigido entre las dos ventanas de la capa: pedir que RSI, MACD y StochRSI apunten al mismo lado en dos horizontes a la vez es un filtro que casi nunca se cumple. Es el mismo resultado que aparecio en la prueba de concepto del chat.
- La exposicion media de las configuraciones que si operan es 44.6%: el sistema pasa la mayor parte del tiempo en efectivo. Contra un benchmark que sube, eso solo ya explica casi toda la diferencia de rentabilidad, independientemente de si las senales aciertan.
- Hit rate entre 15.2% y 34.7%. Por debajo del 50% no es descalificante por si solo (una estrategia puede ganar con pocas operaciones muy buenas), pero aqui el profit factor tampoco compensa: ver `sweep.csv`.
- Muestra: 43 tickers. El brief pide las ~83 posiciones reales; con este tamano los numeros son indicativos, no concluyentes. `scripts/fetch_ibkr_gateway.py` completa el resto en una pasada.

## Veredicto vigente (scan de la ultima barra)

| ticker   | verdict   |   score |   L3 |   L4 |   close |   stop_2atr |   rsi14 |   dd63_pct |
|:---------|:----------|--------:|-----:|-----:|--------:|------------:|--------:|-----------:|
| AAPL     | NEUTRAL   |       1 |    0 |    1 |  311.42 |      296.68 |    49.2 |       -8.4 |
| CBOE     | NEUTRAL   |       1 |    0 |    1 |  308.34 |      286.67 |    61.6 |      -13   |
| AMZN     | NEUTRAL   |       1 |    0 |    1 |  262.57 |      248    |    52.9 |       -7.6 |
| AFRM     | NEUTRAL   |       1 |    0 |    1 |   76.98 |       69.94 |    52.2 |      -10.3 |
| AUNA     | NEUTRAL   |       1 |    0 |    1 |    5.27 |        4.8  |    52.2 |       -2.9 |
| MCO      | NEUTRAL   |       1 |    0 |    1 |  508.45 |      485.6  |    65.2 |       -2   |
| NET      | NEUTRAL   |       1 |    0 |    1 |  283.78 |      251.76 |    48.4 |      -14.2 |
| MSFT     | NEUTRAL   |       1 |    0 |    1 |  488.84 |      464.69 |    64.6 |       -3.4 |
| GDDY     | NEUTRAL   |       1 |    0 |    1 |  100.43 |       90.98 |    58.8 |       -4.4 |
| DT       | NEUTRAL   |       1 |    0 |    1 |   49.34 |       45.53 |    58.6 |       -3   |
| CRM      | NEUTRAL   |       1 |    0 |    1 |  209.53 |      193.74 |    66.3 |       -0   |
| CMG      | NEUTRAL   |       1 |    0 |    1 |   37.87 |       35.05 |    65.3 |       -1.7 |
| SPY      | NEUTRAL   |       1 |    0 |    1 |  764.85 |      751.47 |    53.4 |       -1.7 |
| VEEV     | NEUTRAL   |       1 |    0 |    1 |  246.84 |      230.41 |    68.5 |       -2.3 |
| WDAY     | NEUTRAL   |       1 |    0 |    1 |  199.83 |      179.16 |    66.7 |       -3.2 |
| SNOW     | NEUTRAL   |       1 |    0 |    1 |  326    |      300.24 |    62.9 |       -3.4 |
| SE       | NEUTRAL   |       1 |    0 |    1 |  116.24 |      107.1  |    53.6 |      -11.6 |
| SHOP     | NEUTRAL   |       1 |    0 |    1 |  150.1  |      137.54 |    61.6 |       -5.3 |
| P        | NEUTRAL   |       1 |    0 |    1 |  101.68 |       90.55 |    56.6 |      -13.9 |
| NVDA     | NEUTRAL   |       1 |    0 |    1 |  209.37 |      196.76 |    45.5 |       -7.1 |
| BMNR     | NEUTRAL   |       0 |    0 |    0 |   24.46 |       21.9  |    77.3 |        0   |
| BABA     | NEUTRAL   |       0 |    0 |    0 |  118.81 |      109.82 |    45.4 |      -10.2 |
| ADBE     | NEUTRAL   |       0 |    0 |    0 |  276.24 |      254.9  |    62.9 |        0   |
| ARKG     | NEUTRAL   |       0 |    0 |    0 |   47.83 |       44.38 |    66.8 |       -3.3 |
| ABNB     | NEUTRAL   |       0 |    0 |    0 |  191.75 |      180.2  |    74.3 |        0   |
| AAL      | NEUTRAL   |       0 |    0 |    0 |   13.66 |       12.54 |    36.8 |      -24.7 |
| ABT      | NEUTRAL   |       0 |    0 |    0 |  116.65 |      111.52 |    77.8 |        0   |
| CME      | NEUTRAL   |       0 |    0 |    0 |  278.26 |      265.64 |    67.7 |       -1.5 |
| NOW      | NEUTRAL   |       0 |    0 |    0 |  128.06 |      116.09 |    61.8 |       -5.7 |
| NFLX     | NEUTRAL   |       0 |    0 |    0 |   80.39 |       75.8  |    63.4 |       -8.3 |
| MSTR     | NEUTRAL   |       0 |    0 |    0 |  122.14 |      108.32 |    67.7 |      -23.6 |
| META     | NEUTRAL   |       0 |    0 |    0 |  558.42 |      519.1  |    42.1 |      -18   |
| MELI     | NEUTRAL   |       0 |    0 |    0 | 1981.73 |     1847.15 |    63.7 |        0   |
| HUBS     | NEUTRAL   |       0 |    0 |    0 |  240.61 |      207.74 |    55.9 |       -8.2 |
| INTU     | NEUTRAL   |       0 |    0 |    0 |  371.26 |      343.19 |    69.3 |        0   |
| KD       | NEUTRAL   |       0 |    0 |    0 |   13.03 |       11.6  |    51.5 |      -11.3 |
| PATH     | NEUTRAL   |       0 |    0 |    0 |   16.5  |       14.88 |    70.1 |       -1.1 |
| ORCL     | NEUTRAL   |       0 |    0 |    0 |  144.23 |      130.39 |    50.6 |      -41.9 |
| NVO      | NEUTRAL   |       0 |    0 |    0 |   46.81 |       44.05 |    48.9 |       -9.3 |
| SOFI     | NEUTRAL   |       0 |    0 |    0 |   18.4  |       16.72 |    53.9 |       -2.7 |
| TSLA     | NEUTRAL   |       0 |    0 |    0 |  349.28 |      321.41 |    51.5 |      -21   |
| TEAM     | NEUTRAL   |       0 |    0 |    0 |  171.19 |      153.92 |    75.9 |       -2.1 |
| ZS       | NEUTRAL   |       0 |    0 |    0 |  176.33 |      160.5  |    57.7 |       -6.3 |
| SPGI     | NEUTRAL   |      -1 |    0 |   -1 |  385.23 |      362    |    45.6 |       -9.3 |

Descartados por datos insuficientes: AAL, AAPL, ABNB, ABT, ADBE, AFRM, AMZN, ARKG, AUNA, BABA, BMNR, CBOE, CME, CMG, CRM, DT, GDDY, HUBS, INTU, KD, MCO, MELI, META, MSFT, MSTR, NET, NFLX, NOW, NVDA, NVO, ORCL, P, PATH, SE, SHOP, SNOW, SOFI, SPCX, SPGI, SPY, TEAM, TSLA, VEEV, WDAY, ZS
