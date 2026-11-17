"""Agentic Market Regime and Strategy Orchestrator for Bitcoin Intraday.

Inspired by the TauricResearch/TradingAgents and AI4Finance-Foundation architectures.
Synthesizes market structure, volatility metrics, and session context to determine:
1. Current Market Regime (Trending vs. Choppy/Ranging vs. High-Risk Macro)
2. Active Strategy Selection (Disables strategies that fail in the current regime)
3. Dynamic Risk Multiplier and Bull/Bear Consensus
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from btc_engine.indicators import Candle, calculate_atr, calculate_ema


@dataclass
class AgenticRegimeDecision:
    regime: str  # 'RANGE_CONSOLIDATION', 'TRENDING_EXPANSION', 'HIGH_RISK_VOLATILITY'
    recommended_setups: List[str]
    suppressed_setups: List[str]
    risk_multiplier: float
    bullish_case: str
    bearish_case: str
    synthesis: str


class MarketRegimeAgent:
    """Agent that governs which intraday setups are allowed to fire."""

    def __init__(self, atr_lookback: int = 24):
        self.atr_lookback = atr_lookback

    def analyze(self, candles: List[Candle], upcoming_macro_event: bool = False) -> AgenticRegimeDecision:
        if len(candles) < 30:
            return AgenticRegimeDecision(
                regime="RANGE_CONSOLIDATION",
                recommended_setups=["AsianRangeSweepStrategy"],
                suppressed_setups=[],
                risk_multiplier=1.0,
                bullish_case="Insufficient data; maintaining baseline caution.",
                bearish_case="Insufficient data; maintaining baseline caution.",
                synthesis="Defaulting to conservative range-bound liquidity sweeps."
            )

        closes = [c.close for c in candles]
        atr_list = calculate_atr(candles, period=14)
        ema_20 = calculate_ema(closes, 20)
        ema_50 = calculate_ema(closes, 50)

        recent_atr = atr_list[-1]
        baseline_atr = sum(atr_list[-self.atr_lookback:]) / self.atr_lookback
        atr_ratio = recent_atr / baseline_atr if baseline_atr > 0 else 1.0

        current_close = closes[-1]
        trend_direction = "BULLISH" if ema_20[-1] > ema_50[-1] else "BEARISH"
        trend_spread = abs(ema_20[-1] - ema_50[-1]) / current_close

        # 1. Macro High-Risk Scenario
        if upcoming_macro_event or atr_ratio > 2.5:
            return AgenticRegimeDecision(
                regime="HIGH_RISK_VOLATILITY",
                recommended_setups=["AsianRangeSweepStrategy"],
                suppressed_setups=["VWAPMeanReversionStrategy", "VolatilitySqueezeStrategy"],
                risk_multiplier=0.5,
                bullish_case="Extreme volatility could trigger rapid upward squeeze.",
                bearish_case="High slippage and whipsaws can trigger multiple stop-losses in seconds.",
                synthesis="Reduce risk to 0.5x; suppress mean-reversion due to catastrophic blowout risk."
            )

        # 2. Trending Regime
        if trend_spread > 0.008 and atr_ratio >= 1.0:
            bull_case = f"Price maintaining steady structure above 50 EMA ({ema_50[-1]:.1f}) with expanding ATR."
            bear_case = f"Overextended from mean; vulnerable to sharp pullback if volume drops."
            return AgenticRegimeDecision(
                regime="TRENDING_EXPANSION",
                recommended_setups=["VolatilitySqueezeStrategy"],
                suppressed_setups=["VWAPMeanReversionStrategy"],
                risk_multiplier=1.0,
                bullish_case=bull_case,
                bearish_case=bear_case,
                synthesis=f"Market is {trend_direction} trending. Firing trend-following squeeze breakouts; suppressing counter-trend mean reversion."
            )

        # 3. Range-Bound / Consolidation Regime
        bull_case = f"Defending lower session liquidity pools; range-bound absorption."
        bear_case = f"Failed breakout at session highs; lack of institutional follow-through."
        return AgenticRegimeDecision(
            regime="RANGE_CONSOLIDATION",
            recommended_setups=["AsianRangeSweepStrategy", "VWAPMeanReversionStrategy"],
            suppressed_setups=["VolatilitySqueezeStrategy"],
            risk_multiplier=1.0,
            bullish_case=bull_case,
            bearish_case=bear_case,
            synthesis="Market is in low-volatility consolidation. Favor Asian sweep liquidity grabs and VWAP +-2σ mean-reversion."
        )
