# Ingesta de precios IBKR — estado

Formato por ticker: `data/raw/<TICKER>.json` con
`{"time_ref":"SPY","volume":[...],"open":[...],"close":[...],"high":[...],"low":[...]}`
(500 barras diarias, 2024-08-26 -> 2026-08-24; el calendario vive en `data/raw/SPY.json`).

Llamada: `get_price_history(contract_id=<id>, security_type="STK", step="ONE_DAY", period="TWO_YEARS", outside_rth=false)`

Tras cada ticker: `python3 -m fourlayer.cli ingest`. Commit/push cada 2.

## Pendientes (orden por peso en cartera)
DXYZ 692783792
MSOS 443224436
DHI 268627
SMCI 731466419
NEE 75960201
MSCI 47101335
TSLA 76792991
FCX 7089
NVDA 4815747
COPX 211651700
OXY 10880
QBTS 578031277
PFE 11031
LUV 9282
UBER 365207014
ISRG 9063285
CCJ 1447060
GEV 691984365
PAM 69342639
JD 152486141
GLOB 160756766
VST 254457731
IREN 526906130
PDD 326398585
DPZ 29831612
CEPU 305095834
ALB 4347
CRWV 771759702
REMX 415578518
OKLO 500073396
ENPH 105368327
ASTS 480745767
TTD 248755440
NKE 10291
BIDU 35359385
LOMA 294363537
BBAR 390462028
BLDP 56935150
MBGL 893054611
SOLS 822454680
NTDOY 41208978

## Notas de calidad detectadas durante la ingesta
- **BMNR**: 49 barras con volumen cero y un salto diario de +695% antes de julio de 2025
  (era una shell ilíquida antes del giro a tesorería cripto). Pendiente: aplicar una puerta
  de liquidez por ticker para que solo entre en el universo operable cuando acumule
  `warmup_bars` barras con volumen > 0.
- **SPCX**: solo 50 barras (empieza a cotizar el 2026-06-12). Por debajo de las 200 barras
  de calentamiento: queda en el universo declarado pero no puede generar señal en esta ventana.
- **KD**: caida del -54.9% el 2026-02-09 con 45M de volumen frente a ~2M habitual.
  Tiene toda la pinta de una accion corporativa (spin-off / dividendo extraordinario)
  que IBKR no retroajusto, no de un desplome real. Pendiente: listar en el reporte
  todos los movimientos diarios por encima del 25% para que se vean, en vez de
  operarlos como si fueran retornos reales.
- **SPGI**: frontera de retroajuste el 2026-07-01. Todo el historico anterior viene
  retroajustado (volumen con decimales) y las ultimas 38 barras vienen en crudo, lo que
  fabrica un +7.7% en un dia con volumen plano. Detectado y cortado automaticamente
  (`fourlayer.data.store.scale_break`); se conserva el tramo largo hasta 2026-06-30.
