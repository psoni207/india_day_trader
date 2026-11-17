"""Daily Anchored VWAP Standard Deviation Bands Mean Reversion Strategy.

Anchored to 00:00 UTC daily open.
Triggers counter-trend mean reversion trades when price stretches to +-2.0 to 2.5 sigma
with RSI divergence/exhaustion, targeting the central VWAP.
"""

from typing import List
from btc_engine.indicators import Candle, calculate_anchored_vwap, calculate_rsi
from btc_engine.setups.asian_sweep import TradeSignal


class VWAPMeanReversionStrategy:
    def __init__(self, rsi_period: int = 14, min_rr: float = 1.8):
        self.rsi_period = rsi_period
        self.min_rr = min_rr

    def evaluate(self, candles: List[Candle]) -> List[TradeSignal]:
        signals: List[TradeSignal] = []
        if len(candles) < 30:
            return signals

        closes = [c.close for c in candles]
        vwap_bands = calculate_anchored_vwap(candles)
        rsi_series = calculate_rsi(closes, period=self.rsi_period)

        for i in range(1, len(candles)):
            curr = candles[i]
            prev = candles[i - 1]
            bands = vwap_bands[i]
            rsi = rsi_series[i]

            # Minimum standard deviation requirement (avoid zero volatility flat lines)
            if bands['stdev'] / bands['vwap'] < 0.002:
                continue

            # --- Bearish Mean Reversion (Overextended to Upper 2.0 Sigma) ---
            if prev.high >= bands['upper_2'] and rsi > 68:
                # Reversal confirmation: current candle closes below prev candle low or below upper_2
                if curr.close < prev.low and curr.close < bands['upper_2']:
                    entry = curr.close
                    sl = max(prev.high, curr.high) * 1.001
                    tp1 = bands['upper_1']
                    tp2 = bands['vwap']  # Target central VWAP

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
                            reason=f"VWAP +2.0σ rejection at {prev.high:.1f} with RSI {rsi:.1f}, targeting central VWAP {bands['vwap']:.1f}"
                        ))

            # --- Bullish Mean Reversion (Overextended to Lower 2.0 Sigma) ---
            elif prev.low <= bands['lower_2'] and rsi < 32:
                # Reversal confirmation: current candle closes above prev candle high or above lower_2
                if curr.close > prev.low and curr.close > bands['lower_2']:
                    entry = curr.close
                    sl = min(prev.low, curr.low) * 0.999
                    tp1 = bands['lower_1']
                    tp2 = bands['vwap']

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
                            reason=f"VWAP -2.0σ bounce at {prev.low:.1f} with RSI {rsi:.1f}, targeting central VWAP {bands['vwap']:.1f}"
                        ))

        return signals
