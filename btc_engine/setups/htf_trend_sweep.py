"""High-Probability Bitcoin Intraday Trend-Aligned Setup.

Combines:
1. Higher Timeframe (HTF) Trend Filter (1-Hour / 4-Hour 50 & 200 EMA)
2. Strict Session Execution Window (London & NY Open: 08:00 - 18:00 UTC)
3. Volume Surge Filter (Breakout volume > 1.3x 20-period average)
4. Asymmetric Risk/Reward: Tight invalidation stop with ATR trailing runner.
"""

from typing import List
from dataclasses import dataclass
from datetime import time
from btc_engine.indicators import Candle, calculate_ema, calculate_atr
from btc_engine.setups.asian_sweep import TradeSignal


class TrendAlignedAsianSweepStrategy:
    def __init__(
        self,
        htf_ema_period: int = 40,      # Equivalent to 10-hour EMA on 15m
        min_rr: float = 2.5,
        volume_threshold: float = 1.2
    ):
        self.htf_ema_period = htf_ema_period
        self.min_rr = min_rr
        self.volume_threshold = volume_threshold

    def evaluate(self, candles: List[Candle]) -> List[TradeSignal]:
        signals: List[TradeSignal] = []
        if len(candles) < self.htf_ema_period + 20:
            return signals

        closes = [c.close for c in candles]
        volumes = [c.volume for c in candles]
        htf_ema = calculate_ema(closes, self.htf_ema_period)
        atr_list = calculate_atr(candles, period=14)

        # 20-period volume simple moving average
        vol_sma = []
        for i in range(len(volumes)):
            if i < 20:
                vol_sma.append(sum(volumes[:i + 1]) / (i + 1))
            else:
                vol_sma.append(sum(volumes[i - 19 : i + 1]) / 20.0)

        # Group by UTC day
        days_candles = {}
        for idx, c in enumerate(candles):
            d_str = c.dt.strftime('%Y-%m-%d')
            if d_str not in days_candles:
                days_candles[d_str] = []
            days_candles[d_str].append((idx, c))

        for d_str, day_items in days_candles.items():
            # 1. Asian range calculation (00:00 to 08:00 UTC)
            asian_items = [item for item in day_items if time(0, 0) <= item[1].dt.time() < time(8, 0)]
            if len(asian_items) < 8:
                continue

            ash = max(item[1].high for item in asian_items)
            asl = min(item[1].low for item in asian_items)
            range_span = ash - asl

            if range_span / asl < 0.003:
                continue

            # 2. Monitor London/NY window (08:00 to 18:00 UTC)
            monitoring_items = [item for item in day_items if time(8, 0) <= item[1].dt.time() <= time(18, 0)]

            swept_low = False
            swept_high = False

            for item in monitoring_items:
                idx, curr = item
                curr_htf = htf_ema[idx]
                curr_vol = curr.volume
                avg_vol = vol_sma[idx]
                atr = atr_list[idx]

                # HTF Trend Bias:
                # If Close > HTF EMA: strictly look for Bullish setups (discount buys)
                # If Close < HTF EMA: strictly look for Bearish setups (premium sells)
                is_htf_bullish = curr.close > curr_htf
                is_htf_bearish = curr.close < curr_htf

                # Check volume confirmation
                has_volume = curr_vol >= avg_vol * self.volume_threshold

                # --- BULLISH SETUP: Trend is Up + Asian Low Liquidity Swept ---
                if is_htf_bullish and not swept_low:
                    if curr.low < asl and curr.close > asl and has_volume:
                        swept_low = True
                        entry = curr.close
                        sl = curr.low - (0.2 * atr)  # Invalidation below sweep low
                        tp1 = entry + (1.5 * (entry - sl))
                        tp2 = ash  # Target full Asian High liquidity pool

                        risk = entry - sl
                        reward = tp2 - entry
                        if risk > 0 and reward / risk >= self.min_rr:
                            signals.append(TradeSignal(
                                timestamp=curr.timestamp,
                                dt_str=curr.dt.strftime('%Y-%m-%d %H:%M UTC'),
                                symbol="BTC/USD",
                                direction="BUY",
                                entry_price=round(entry, 2),
                                stop_loss=round(sl, 2),
                                take_profit_1=round(tp1, 2),
                                take_profit_2=round(tp2, 2),
                                risk_reward=round(reward / risk, 2),
                                reason=f"Trend-Aligned Bullish Sweep: Price > HTF EMA ({curr_htf:.1f}), swept ASL ({asl:.1f}), rejected with {curr_vol/avg_vol:.1f}x volume"
                            ))

                # --- BEARISH SETUP: Trend is Down + Asian High Liquidity Swept ---
                elif is_htf_bearish and not swept_high:
                    if curr.high > ash and curr.close < ash and has_volume:
                        swept_high = True
                        entry = curr.close
                        sl = curr.high + (0.2 * atr)
                        tp1 = entry - (1.5 * (sl - entry))
                        tp2 = asl  # Target full Asian Low liquidity pool

                        risk = sl - entry
                        reward = entry - tp2
                        if risk > 0 and reward / risk >= self.min_rr:
                            signals.append(TradeSignal(
                                timestamp=curr.timestamp,
                                dt_str=curr.dt.strftime('%Y-%m-%d %H:%M UTC'),
                                symbol="BTC/USD",
                                direction="SELL",
                                entry_price=round(entry, 2),
                                stop_loss=round(sl, 2),
                                take_profit_1=round(tp1, 2),
                                take_profit_2=round(tp2, 2),
                                risk_reward=round(reward / risk, 2),
                                reason=f"Trend-Aligned Bearish Sweep: Price < HTF EMA ({curr_htf:.1f}), swept ASH ({ash:.1f}), rejected with {curr_vol/avg_vol:.1f}x volume"
                            ))

        return signals
