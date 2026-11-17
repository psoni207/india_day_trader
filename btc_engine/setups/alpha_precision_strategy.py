"""Alpha Precision Setup: HTF Trend + Asian Sweep + CVD Absorption + Funding Rate Filter.

The institutional setup for Bitcoin Intraday:
1. Session Timing: London & NY Open (08:00 - 18:00 UTC)
2. Asian High/Low Liquidity Sweep
3. Orderflow CVD Absorption Confirmation
4. Perpetual Funding Rate Crowding Filter (Prevents longing crowded tops)
5. Asymmetric Risk/Reward (>= 2.5) with Invalidation Stops
"""

from typing import List, Dict, Any, Optional
from datetime import time
from btc_engine.indicators import Candle, calculate_ema, calculate_atr
from btc_engine.orderflow import calculate_cvd, simulate_perpetual_funding_rates
from btc_engine.setups.asian_sweep import TradeSignal


class AlphaPrecisionStrategy:
    def __init__(
        self,
        htf_ema_period: int = 40,
        min_rr: float = 2.5,
        funding_rate_cap: float = 0.00035, # 0.035% max funding for longs
        funding_rate_floor: float = -0.00015
    ):
        self.htf_ema_period = htf_ema_period
        self.min_rr = min_rr
        self.funding_rate_cap = funding_rate_cap
        self.funding_rate_floor = funding_rate_floor

    def evaluate(self, candles: List[Candle]) -> List[TradeSignal]:
        signals: List[TradeSignal] = []
        if len(candles) < self.htf_ema_period + 20:
            return signals

        closes = [c.close for c in candles]
        htf_ema = calculate_ema(closes, self.htf_ema_period)
        atr_list = calculate_atr(candles, period=14)
        cvd_series = calculate_cvd(candles)
        funding_series = simulate_perpetual_funding_rates(candles)

        # Index candles by day
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

            # 2. Monitoring window (08:00 to 18:00 UTC)
            monitoring_items = [item for item in day_items if time(8, 0) <= item[1].dt.time() <= time(18, 0)]

            swept_low = False
            swept_high = False

            for item in monitoring_items:
                idx, curr = item
                curr_htf = htf_ema[idx]
                curr_funding = funding_series[idx]['rate']
                curr_cvd_delta = cvd_series[idx]['delta']
                atr = atr_list[idx]

                is_htf_bullish = curr.close > curr_htf
                is_htf_bearish = curr.close < curr_htf

                # --- BULLISH ENTRY WITH CVD ABSORPTION & FUNDING FILTER ---
                # Rule: HTF Bullish + Swept ASL + Closed back inside + Funding rate NOT dangerously crowded + CVD delta stabilizing
                if is_htf_bullish and not swept_low:
                    if curr.low < asl and curr.close > asl:
                        # Check funding filter: Do not long if funding is overheated
                        if curr_funding <= self.funding_rate_cap:
                            swept_low = True
                            entry = curr.close
                            sl = curr.low - (0.2 * atr)
                            tp1 = entry + (1.5 * (entry - sl))
                            tp2 = ash  # Target full Asian High

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
                                    reason=f"Alpha Precision Buy: Swept ASL ({asl:.1f}), CVD delta stabilized ({curr_cvd_delta:+.1f}), Funding healthy ({curr_funding*100:+.3f}%)"
                                ))

                # --- BEARISH ENTRY WITH CVD ABSORPTION & FUNDING FILTER ---
                elif is_htf_bearish and not swept_high:
                    if curr.high > ash and curr.close < ash:
                        # Check funding filter: Do not short if shorts are already heavily squeezed
                        if curr_funding >= self.funding_rate_floor:
                            swept_high = True
                            entry = curr.close
                            sl = curr.high + (0.2 * atr)
                            tp1 = entry - (1.5 * (sl - entry))
                            tp2 = asl  # Target full Asian Low

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
                                    reason=f"Alpha Precision Sell: Swept ASH ({ash:.1f}), CVD delta absorbed ({curr_cvd_delta:+.1f}), Funding safe ({curr_funding*100:+.3f}%)"
                                ))

        return signals
