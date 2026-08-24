# Sistema de trading de 4 capas — motor de señales y backtest

Reescritura del prototipo del brief (`engine.py`, solo cierres y dos tickers) como
un paquete completo: indicadores sobre OHLCV real, las cuatro capas del sistema,
backtest walk-forward multi-ticker con stop-loss por ATR, métricas de hit rate y
export con el mismo esquema que el historial de Firestore.

```bash
pip install -r requirements.txt
python -m fourlayer.cli ingest                 # data/raw/*.json -> cache de precios
python -m fourlayer.cli scan --top 20          # veredicto vigente por ticker
python -m fourlayer.cli backtest --start 2025-06-16
python scripts/run_analysis.py --start 2025-06-16   # informe completo en reports/
python -m pytest tests -q
```

## Las 4 capas

| Capa | Qué mira | De dónde sale |
|---|---|---|
| 1. Macro | condiciones económicas/políticas generales | proveedor intercambiable (`providers.py`) |
| 2. Fundamental | ratios y resultados, marca `structural_issue` | proveedor intercambiable (Finnhub o panel CSV) |
| 3. Técnico largo | RSI/MACD/StochRSI en ventanas de 2 meses y 1 mes | `layers.technical_layers` |
| 4. Técnico corto | los mismos en 2 semanas y 1 semana + medias 20/50/200 | `layers.technical_layers` |

Cada capa emite **+1 / 0 / −1**, el compuesto es la suma → rango **[−4, +4]**, que
es lo que hace que los umbrales del brief signifiquen lo que dicen: ≥4 comprar
pleno, ≤−4 vender pleno, ≥2 / ≤−2 versión débil. En modo `scanner` solo se usan
las capas 3 y 4, así que el compuesto no puede pasar de ±2 y el veredicto queda
topado en "débil" — exactamente la regla del brief.

**Dónde van los extras aprobados.** Zonas absolutas de RSI, confirmación por
volumen, divergencias precio/RSI y el bono por caída >15% desde el máximo de 63
días alimentan el sub-score continuo de la capa técnica que les corresponde, y
la capa entera se discretiza después a ±1. No se suman por fuera. Si se sumaran
(que es lo que hacía el prototipo del chat), el compuesto podría pasar de ±2 sin
que las dos capas estuvieran alineadas y los umbrales dejarían de medir lo que
prometen. Esa variante se conserva como `--aggregation prototype` justamente
para poder contrastar los números de la prueba de concepto; la del brief es
`--aggregation layers`, que es el default.

El bono por caída se anula cuando el fundamental marca `structural_issue`, tal
como pide el brief: ahí la caída es información, no descuento.

## Sesgo retrospectivo en la capa macro

Es el punto 3 del brief y la decisión está tomada de forma explícita: **el
backtest histórico corre con `NeutralMacro` y `NeutralFundamental` (voto 0)**.
Preguntarle hoy a un LLM "¿cómo estaba el macro en marzo de 2025?" mete
look-ahead por la puerta de atrás, porque el modelo ya sabe cómo terminó esa
historia. Las alternativas honestas están implementadas y hay que elegirlas a
mano:

- `SeriesMacro(csv)` — una serie point-in-time que *usted* escribió en su momento.
- `ConstantMacro(±1)` — para análisis de sensibilidad ("¿y si el macro hubiera
  estado en +1 todo el período?").
- `CallbackMacro(fn)` — la evaluación por IA con caché de 24 h, marcada como **no
  apta para backtest** y pensada para producción.

Lo mismo con la capa 2: `PanelFundamental` acepta un panel fechado por
`filedDate` (lo genera `scripts/fetch_finnhub.py --pit`), que es la única forma
limpia de meter fundamentales en un backtest.

## Walk-forward: qué garantiza exactamente

1. Todos los indicadores son causales. Hay un test que calcula la serie completa
   y la serie truncada en t y exige que coincidan valor a valor
   (`test_indicators_are_causal`, `test_signals_are_walk_forward_safe`).
2. La señal de la barra t se ejecuta en **t+1 a la apertura**, nunca al cierre de
   t. Hay un test que lo verifica con una apertura distinta del cierre anterior.
3. El stop 2×ATR se evalúa contra el mínimo real de la barra y respeta el hueco
   de apertura: si abre por debajo del stop, se sale a la apertura, no al stop.
4. Comisión y slippage se cobran en ambos lados.

## Datos

El motor no habla con la red: lee un cache local de OHLCV en `data/prices/`.
Hay dos formas de llenarlo, y las dos terminan en el mismo sitio:

```bash
# A) automática, contra el Client Portal Gateway de IBKR corriendo en local
python scripts/fetch_ibkr_gateway.py --insecure --only-missing

# B) manual: volcar la respuesta de la herramienta MCP get_price_history en
#    data/raw/<TICKER>.json y normalizar
python -m fourlayer.cli ingest
```

Los volcados aceptan `"time_ref": "SPY"` en vez de repetir el vector de fechas:
todas las cotizadas de EE.UU. comparten calendario. `data/positions.csv` tiene
las 83 posiciones reales de la cartera con su `contract_id`, que es lo que
consume el fetcher; `data/universe.json` es la lista de tickers del backtest.

Finnhub (calendario de earnings + panel fundamental) necesita `FINNHUB_API_KEY`:

```bash
export FINNHUB_API_KEY=...
python scripts/fetch_finnhub.py --pit
```

Sin clave el cliente degrada a `None` sin lanzar y el sistema corre en modo
solo-técnico.

**Higiene de datos.** IBKR consolida el cierre por separado del rango intradía,
así que en algunas barras el cierre queda unos céntimos fuera del high/low. El
parser ensancha el rango para contener open y close en vez de tocar el cierre:
si no, el ATR y el stop se calcularían sobre un rango que no contiene el precio
al que realmente se operó.

## Salidas

`scripts/run_analysis.py` escribe en `reports/`:

- `resultados.md` — informe legible con el barrido, el desglose por ticker y el scan.
- `sweep.csv` — las 16 combinaciones de (alineación × agregación × acuerdo entre
  ventanas × modo de RSI).
- `trades_<cfg>.csv`, `equity_<cfg>.csv` — operaciones y curva de capital.
- `backtest_<cfg>.json`, `scan.json`, `history.json` — documentos con el esquema
  de Firestore (`fourlayer/firestore.py`, `schema_version` `4layer-1.0`, tope de
  200 entradas por ticker) para que un veredicto simulado y uno de producción
  sean comparables fila a fila.

## Estructura

```
fourlayer/
  indicators.py   RSI, MACD, StochRSI, ATR, medias, volumen, divergencias
  config.py       ventanas, umbrales, pesos, costes — todo parametrizable
  layers.py       las 4 capas, el compuesto y el veredicto
  providers.py    macro y fundamental intercambiables + calendario de earnings
  backtest.py     motor walk-forward multi-ticker con stop 2xATR
  metrics.py      hit rate, Sharpe, Sortino, drawdown, alpha/beta
  firestore.py    serialización al esquema del historial
  runner.py       orquestación y barrido de sensibilidad
  cli.py          ingest / scan / backtest / sweep
  data/           IBKR, Finnhub y cache de precios
scripts/          fetchers y el informe completo
tests/            62 tests, incluidos los de causalidad y ejecución
```
