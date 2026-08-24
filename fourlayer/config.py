"""Configuracion del sistema de 4 capas.

Todo lo que en el brief aparece como un numero magico (ventanas, umbrales,
pesos de las medias moviles, multiplo de ATR del stop) vive aqui, para poder
barrer parametros en el backtest en vez de reescribir codigo.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal

RsiMode = Literal["zones", "midline"]
Alignment = Literal["strict", "loose"]
Aggregation = Literal["layers", "prototype"]


@dataclass(frozen=True)
class Window:
    """Un horizonte temporal con sus tres indicadores calibrados."""

    name: str
    bars: int
    rsi_period: int
    macd: tuple[int, int, int]
    stoch_period: int
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    stoch_low: float = 0.20
    stoch_high: float = 0.80

    @property
    def warmup(self) -> int:
        """Barras necesarias antes de que el peor indicador este formado."""
        return max(self.rsi_period, self.macd[1] + self.macd[2], self.stoch_period * 2)


# Calibracion por defecto: la del prototipo del brief.
W_1W = Window("1w", bars=5, rsi_period=5, macd=(3, 6, 3), stoch_period=5)
W_2W = Window("2w", bars=10, rsi_period=10, macd=(5, 10, 4), stoch_period=10)
W_1M = Window("1m", bars=21, rsi_period=21, macd=(6, 13, 5), stoch_period=21)
W_2M = Window("2m", bars=42, rsi_period=42, macd=(12, 26, 9), stoch_period=42)


@dataclass(frozen=True)
class TechnicalConfig:
    """Capas 3 y 4."""

    short_windows: tuple[Window, Window] = (W_1W, W_2W)
    long_windows: tuple[Window, Window] = (W_1M, W_2M)

    #: Cuantos de los 3 indicadores deben coincidir dentro de una ventana.
    #: "strict" = 3 de 3 (criterio original), "loose" = 2 de 3.
    alignment: Alignment = "strict"
    #: Si True, las dos ventanas de la capa deben coincidir en signo.
    require_both_windows: bool = True
    #: Como vota el RSI dentro de una ventana.
    rsi_mode: RsiMode = "zones"

    # --- Medias moviles diarias (capa 4) ---
    ma_periods: tuple[int, int, int] = (20, 50, 200)
    ma_weights: tuple[float, float, float] = (0.2, 0.3, 0.5)  # 20, 50, 200
    ma_vote_threshold: float = 0.6

    # --- Extras aprobados ---
    dip_window: int = 63
    dip_threshold: float = -0.15   # caida >15% desde el maximo de 63 dias
    rsi_zone_period: int = 14
    rsi_zone_oversold: float = 30.0
    rsi_zone_overbought: float = 70.0
    volume_period: int = 20
    volume_confirm_ratio: float = 1.2
    divergence_lookback_short: int = 20
    divergence_lookback_long: int = 60

    # --- Pesos dentro de cada capa (la suma se recorta a [-1, 1]) ---
    w_short_alignment: float = 0.55
    w_ma: float = 0.50
    w_dip: float = 0.25
    w_rsi_zone: float = 0.20
    w_volume: float = 0.15
    w_divergence_short: float = 0.15

    w_long_alignment: float = 0.75
    w_long_rsi_zone: float = 0.15
    w_divergence_long: float = 0.20

    #: A partir de que sub-score continuo la capa emite su voto discreto +-1.
    layer_vote_threshold: float = 0.50

    #: Como se agrega el compuesto.
    #: "layers"    -> suma de los votos de las 4 capas, rango [-4, +4]. Es la
    #:               lectura literal del brief y la que da sentido a los
    #:               umbrales >=4 / >=2.
    #: "prototype" -> reproduce el motor del chat: las capas 3 y 4 mas los
    #:               extras sumados por fuera. El compuesto puede pasar de +-2
    #:               sin que las dos capas esten alineadas. Se conserva para
    #:               poder contrastar los numeros de la prueba de concepto.
    aggregation: Aggregation = "layers"


@dataclass(frozen=True)
class VerdictConfig:
    """Umbrales del veredicto compuesto (brief: >=4 pleno, >=2 debil)."""

    full: int = 4
    weak: int = 2
    #: El Scanner solo usa capas 3+4 y por tanto nunca puede llegar a +-4.
    scanner_caps_at_weak: bool = True


@dataclass(frozen=True)
class RiskConfig:
    """Gestion de riesgo del backtest."""

    atr_period: int = 14
    stop_atr_multiple: float = 2.0
    trailing_stop: bool = False
    earnings_warning_days: int = 14
    #: Si True, no se abren posiciones nuevas con earnings dentro de la ventana.
    block_entry_on_earnings: bool = False


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 100_000.0
    max_positions: int = 20
    sizing: Literal["equal_weight", "atr_risk"] = "equal_weight"
    #: Solo para sizing="atr_risk": fraccion del equity arriesgada por posicion.
    risk_per_trade: float = 0.01
    #: Fraccion maxima del equity en un solo ticker.
    max_weight: float = 0.10
    commission_bps: float = 1.0
    slippage_bps: float = 5.0
    #: Barras entre la senal y su ejecucion. 1 = se opera en la apertura
    #: siguiente. Nunca 0: eso seria mirar el futuro.
    execution_lag: int = 1
    execution_price: Literal["open", "close"] = "open"
    benchmark: str = "SPY"
    #: Umbral de score para abrir / cerrar. None = usa VerdictConfig.
    entry_score: int | None = None
    exit_score: int | None = None


@dataclass(frozen=True)
class SystemConfig:
    technical: TechnicalConfig = field(default_factory=TechnicalConfig)
    verdict: VerdictConfig = field(default_factory=VerdictConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    #: "scanner" = solo capas 3+4. "full" = las 4 capas.
    mode: Literal["scanner", "full"] = "scanner"

    def with_alignment(self, alignment: Alignment) -> "SystemConfig":
        return replace(self, technical=replace(self.technical, alignment=alignment))

    @property
    def warmup_bars(self) -> int:
        t = self.technical
        return max(
            max(w.warmup for w in t.short_windows + t.long_windows),
            max(t.ma_periods),
            t.dip_window,
            t.divergence_lookback_long,
        )
