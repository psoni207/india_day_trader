"""Asian Range Liquidity Sweep & Reversal Setup (Smart Money Concepts / ICT).

Tracks Asian Session (00:00 - 08:00 UTC) range.
Detects liquidity grabs above Asian High or below Asian Low during London/NY open,
followed by rejection and Market Structure Shift (MSS).
"""

from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import time
from btc_engine.indicators import Candle, calculate_atr


@dataclass
class TradeSignal:
    timestamp: int
    dt_str: str
    symbol: str
    direction: str  # 'BUY' or 'SELL'
    entry_price: float
    stop_loss: float
    take_profit_1: float  # Partial exit (50%)
    take_profit_2: float  # Final exit
    risk_reward: float
    reason: str


class AsianRangeSweepStrategy:
    def __init__(
        self,
        min_rr: float = 2.0,
        max_risk_pct: float = 0.015,  # 1.5% max SL distance
        min_sweep_pct: float = 0.0005 # 0.05% minimum sweep depth
    ):
        self.min_rr = min_rr
        self.max_risk_pct = max_risk_pct
        self.min_sweep_pct = min_sweep_pct

    def evaluate(self, candles: List[Candle]) -> List[TradeSignal]:
        """Scans candles for valid Asian session liquidity sweep trades."""
        signals: List[TradeSignal] = []
        if len(candles) < 40:
            return signals

        # Group candles by UTC calendar day
        days_candles: Dict[str, List[Candle]] = {}
        for c in candles:
            d_str = c.dt.strftime('%Y-%m-%d')
            if d_str not in days_candles:
                days_candles[d_str] = []
            days_candles[d_str].append(c)

        for d_str, day_c in days_candles.items():
            # 1. Extract Asian session (00:00 to 08:00 UTC)
            asian_candles = [c for c in day_c if time(0, 0) <= c.dt.time() < time(8, 0)]
            if len(asian_candles) < 8:
                continue

            ash = max(c.high for c in asian_candles)
            asl = min(c.low for c in asian_candles)
            asian_mid = (ash + asl) / 2.0
            range_span = ash - asl

            # If Asian range is excessively small or erratic, skip
            if range_span / asian_mid < 0.003:
                continue

            # 2. Monitor London and NY session (08:00 to 20:00 UTC)
            monitoring_candles = [c for c in day_c if time(8, 0) <= c.dt.time() <= time(20, 0)]

            swept_high = False
            swept_low = False
            sweep_high_price = 0.0
            sweep_low_price = 0.0

            for i in range(1, len(monitoring_candles)):
                prev = monitoring_candles[i - 1]
                curr = monitoring_candles[i]

                # --- Bearish Sweep of Asian High ---
                if not swept_high and curr.high > ash * (1.0 + self.min_sweep_pct):
                    # Price went above Asian High
                    sweep_high_price = max(sweep_high_price, curr.high)
                    # Check for rejection: close back below Asian High
                    if curr.close < ash:
                        swept_high = True
                        entry = curr.close
                        sl = sweep_high_price * 1.001  # Tight SL above sweep high
                        tp1 = asian_mid
                        tp2 = asl  # Target full liquidity pool at Asian Low

                        risk = sl - entry
                        reward = entry - tp2
                        if risk > 0 and (risk / entry) <= self.max_risk_pct:
                            rr = reward / risk
                            if rr >= self.min_rr:
                                signals.append(TradeSignal(
                                    timestamp=curr.timestamp,
                                    dt_str=curr.dt.strftime('%Y-%m-%d %H:%M UTC'),
                                    symbol="BTC/USD",
                                    direction="SELL",
                                    entry_price=round(entry, 2),
                                    stop_loss=round(sl, 2),
                                    take_profit_1=round(tp1, 2),
                                    take_profit_2=round(tp2, 2),
                                    risk_reward=round(rr, 2),
                                    reason=f"Asian High swept at {sweep_high_price:.1f}, rejection closed below ASH ({ash:.1f})"
                                ))

                # --- Bullish Sweep of Asian Low ---
                if not swept_low and curr.low < asl * (1.0 - self.min_sweep_pct):
                    # Price pierced below Asian Low
                    sweep_low_price = min(sweep_low_price if sweep_low_price > 0 else curr.low, curr.low)
                    # Check for rejection: close back above Asian Low
                    if curr.close > asl:
                        swept_low = True
                        entry = curr.close
                        sl = sweep_low_price * 0.999  # Tight SL below sweep low
                        tp1 = asian_mid
                        tp2 = ash  # Target Asian High liquidity pool

                        risk = entry - sl
                        reward = tp2 - entry
                        if risk > 0 and (risk / entry) <= self.max_risk_pct:
                            rr = reward / risk
                            if rr >= self.min_rr:
                                signals.append(TradeSignal(
                                    timestamp=curr.timestamp,
                                    dt_str=curr.dt.strftime('%Y-%m-%d %H:%M UTC'),
                                    symbol="BTC/USD",
                                    direction="BUY",
                                    entry_price=round(entry, 2),
                                    stop_loss=round(sl, 2),
                                    take_profit_1=round(tp1, 2),
                                    take_profit_2=round(tp2, 2),
                                    risk_reward=round(rr, 2),
                                    reason=f"Asian Low swept at {sweep_low_price:.1f}, rejection closed above ASL ({asl:.1f})"
                                ))

        return signals
