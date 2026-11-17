"""1-Minute High-Leverage Micro-Scalping Engine for Bitcoin (Hardened Execution).

Designed specifically for high-leverage execution (100:1 to 500:1):
- Timeframe: 1-Minute / Micro-Structure
- Order Type: LIMIT_MAKER (Post-Only at 50% Fair Value Gap equilibrium)
- Time In Force: GTX (Good-Till-Cancelled Maker Only, zero taker slippage, 0.015% maker fee)
- Holding Duration: 45 seconds to 5 minutes maximum
- Stop Loss: Ultra-tight 0.08% to 0.12% ($60 - $90 on BTC)
- Breakeven Trailing Stop: 1R Rule (+0.12% gain automatically drags SL to Entry + $15 buffer)
- Take Profit: Rapid 0.20% to 0.35% ($150 - $265 on BTC)
- Filters: Cumulative Volume Delta (CVD) Absorption + Perpetual Funding Rate Extremes
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from btc_engine.indicators import Candle, calculate_ema, calculate_atr
from btc_engine.setups.asian_sweep import TradeSignal


@dataclass
class ScalpOrderSpec:
    """Execution parameters tailored for 100x-500x high-leverage scalping."""
    order_type: str = "LIMIT_MAKER"       # Strictly Post-Only Maker order
    time_in_force: str = "GTX"             # Post-Only: Rejected if would take liquidity
    limit_price: float = 0.0               # 50% FVG Equilibrium Retest Price
    breakeven_trigger_pct: float = 0.0012   # +0.12% profit (1R) drags SL to BE
    breakeven_offset_usd: float = 15.0      # Fee buffer ($15 profit lock)
    maker_fee_pct: float = 0.00015         # 0.015% maker fee vs 0.05% taker
    cvd_delta: float = 0.0
    funding_rate: float = 0.0001


class MicroScalper1M:
    def __init__(
        self,
        min_rr: float = 2.2,
        max_stop_pct: float = 0.0015,       # Max 0.15% SL ($110 max on BTC)
        min_target_pct: float = 0.0020,     # Min 0.20% TP ($150 on BTC)
        breakeven_pct: float = 0.0012,      # 1R Breakeven trigger (+0.12%)
        max_bull_funding: float = 0.00035,  # +0.035% (crowded long filter)
        min_bear_funding: float = -0.00015  # -0.015% (short squeeze filter)
    ):
        self.min_rr = min_rr
        self.max_stop_pct = max_stop_pct
        self.min_target_pct = min_target_pct
        self.breakeven_pct = breakeven_pct
        self.max_bull_funding = max_bull_funding
        self.min_bear_funding = min_bear_funding

    def evaluate_1m(
        self,
        candles_1m: List[Candle],
        cvd_delta: float = 0.0,
        funding_rate: float = 0.0001
    ) -> List[TradeSignal]:
        signals: List[TradeSignal] = []
        if len(candles_1m) < 15:
            return signals

        closes = [c.close for c in candles_1m]
        ema_9 = calculate_ema(closes, 9)
        ema_21 = calculate_ema(closes, 21)
        atr_1m = calculate_atr(candles_1m, period=7)

        # Scan the last 3 completed 1-minute candles for micro-displacement & FVG
        for i in range(len(candles_1m) - 2, len(candles_1m)):
            if i < 3:
                continue

            c1 = candles_1m[i - 2]
            c2 = candles_1m[i - 1]
            c3 = candles_1m[i]
            atr = atr_1m[i]

            # 1. Bullish Micro-Scalp: Bullish 1m Displacement + Fair Value Gap (FVG)
            # Candle 2 is strong green; Candle 3 low does not touch Candle 1 high (FVG)
            if c3.low > c1.high and c2.close > c2.open and c3.close > ema_9[i]:
                # CVD Filter: Ensure aggressive selling isn't absorbing the pump
                if cvd_delta < -25.0:
                    continue
                # Funding Filter: Block longs if funding is excessively crowded (> +0.035%)
                if funding_rate >= self.max_bull_funding:
                    continue

                fvg_gap = c3.low - c1.high
                if fvg_gap >= 15.0:  # Minimum $15 imbalance
                    # HARDENED RULE 1: Post-Only Maker limit placed at 50% FVG Equilibrium
                    fvg_midpoint = round((c1.high + c3.low) / 2.0, 2)
                    entry = fvg_midpoint

                    # Ultra-tight SL below the displacement candle low
                    sl = round(c2.low - 10.0, 2)
                    sl_dist = entry - sl
                    sl_pct = sl_dist / entry

                    if 0 < sl_pct <= self.max_stop_pct:
                        # 2.2x to 2.8x risk target (typically $140 - $220 gain)
                        tp1 = round(entry + (1.5 * sl_dist), 2)
                        tp2 = round(entry + (self.min_rr * sl_dist), 2)
                        rr = round((tp2 - entry) / sl_dist, 2)

                        reason = (
                            f"⚡ 1M MAKER SCALP: Limit @ 50% FVG (${fvg_midpoint:,.2f}) | "
                            f"9 EMA ({ema_9[i]:.1f}) | CVD: {cvd_delta:+.1f} | Funding: {funding_rate*100:.3f}%"
                        )

                        sig = TradeSignal(
                            timestamp=c3.timestamp,
                            dt_str=c3.dt.strftime('%Y-%m-%d %H:%M:%S UTC'),
                            symbol="BTC/USD (1M Scalp)",
                            direction="BUY",
                            entry_price=entry,
                            stop_loss=sl,
                            take_profit_1=tp1,
                            take_profit_2=tp2,
                            risk_reward=rr,
                            reason=reason
                        )
                        sig.order_spec = ScalpOrderSpec(
                            order_type="LIMIT_MAKER",
                            time_in_force="GTX",
                            limit_price=entry,
                            breakeven_trigger_pct=self.breakeven_pct,
                            breakeven_offset_usd=15.0,
                            cvd_delta=cvd_delta,
                            funding_rate=funding_rate
                        )
                        signals.append(sig)

            # 2. Bearish Micro-Scalp: Bearish 1m Displacement + Fair Value Gap (FVG)
            elif c3.high < c1.low and c2.close < c2.open and c3.close < ema_9[i]:
                # CVD Filter: Ensure aggressive buyers aren't absorbing the dump
                if cvd_delta > 25.0:
                    continue
                # Funding Filter: Block shorts if funding is negative (< -0.015%, short squeeze hazard)
                if funding_rate <= self.min_bear_funding:
                    continue

                fvg_gap = c1.low - c3.high
                if fvg_gap >= 15.0:
                    fvg_midpoint = round((c1.low + c3.high) / 2.0, 2)
                    entry = fvg_midpoint

                    sl = round(c2.high + 10.0, 2)
                    sl_dist = sl - entry
                    sl_pct = sl_dist / entry

                    if 0 < sl_pct <= self.max_stop_pct:
                        tp1 = round(entry - (1.5 * sl_dist), 2)
                        tp2 = round(entry - (self.min_rr * sl_dist), 2)
                        rr = round((entry - tp2) / sl_dist, 2)

                        reason = (
                            f"⚡ 1M MAKER SCALP: Limit @ 50% FVG (${fvg_midpoint:,.2f}) | "
                            f"9 EMA ({ema_9[i]:.1f}) | CVD: {cvd_delta:+.1f} | Funding: {funding_rate*100:.3f}%"
                        )

                        sig = TradeSignal(
                            timestamp=c3.timestamp,
                            dt_str=c3.dt.strftime('%Y-%m-%d %H:%M:%S UTC'),
                            symbol="BTC/USD (1M Scalp)",
                            direction="SELL",
                            entry_price=entry,
                            stop_loss=sl,
                            take_profit_1=tp1,
                            take_profit_2=tp2,
                            risk_reward=rr,
                            reason=reason
                        )
                        sig.order_spec = ScalpOrderSpec(
                            order_type="LIMIT_MAKER",
                            time_in_force="GTX",
                            limit_price=entry,
                            breakeven_trigger_pct=self.breakeven_pct,
                            breakeven_offset_usd=15.0,
                            cvd_delta=cvd_delta,
                            funding_rate=funding_rate
                        )
                        signals.append(sig)

        return signals
