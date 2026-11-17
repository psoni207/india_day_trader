"""TTM Volatility Squeeze Breakout Strategy for Bitcoin Intraday.

Detects volatility compression (Bollinger Bands inside Keltner Channels)
and trades directional breakout when compression releases with momentum.
"""

from typing import List
from btc_engine.indicators import (
    Candle, calculate_bollinger_and_keltner_squeeze,
    calculate_ema, calculate_atr
)
from btc_engine.setups.asian_sweep import TradeSignal


class VolatilitySqueezeStrategy:
    def __init__(self, ema_fast: int = 9, ema_slow: int = 21, min_rr: float = 2.0):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.min_rr = min_rr

    def evaluate(self, candles: List[Candle]) -> List[TradeSignal]:
        signals: List[TradeSignal] = []
        if len(candles) < 30:
            return signals

        closes = [c.close for c in candles]
        squeeze_info = calculate_bollinger_and_keltner_squeeze(candles)
        ema_f = calculate_ema(closes, self.ema_fast)
        ema_s = calculate_ema(closes, self.ema_slow)
        atr_list = calculate_atr(candles, period=14)

        for i in range(2, len(candles)):
            prev_squeeze = squeeze_info[i - 1]
            curr_squeeze = squeeze_info[i]
            curr = candles[i]
            atr = atr_list[i]

            # Trigger condition: Squeeze was ON in previous candles, now FIRES
            if prev_squeeze['squeeze_on'] and not curr_squeeze['squeeze_on']:
                # Direction determined by fast/slow EMA and candle close
                is_bullish = curr.close > curr_squeeze['kc_upper'] and ema_f[i] > ema_s[i]
                is_bearish = curr.close < curr_squeeze['kc_lower'] and ema_f[i] < ema_s[i]

                if is_bullish:
                    entry = curr.close
                    sl = entry - (1.5 * atr)
                    tp1 = entry + (2.0 * atr)
                    tp2 = entry + (3.5 * atr)  # Squeeze moves often trend 3-4 ATRs

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
                            reason=f"Volatility Squeeze fired BULLISH above KC ({curr_squeeze['kc_upper']:.1f}) with 9 EMA > 21 EMA"
                        ))

                elif is_bearish:
                    entry = curr.close
                    sl = entry + (1.5 * atr)
                    tp1 = entry - (2.0 * atr)
                    tp2 = entry - (3.5 * atr)

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
                            reason=f"Volatility Squeeze fired BEARISH below KC ({curr_squeeze['kc_lower']:.1f}) with 9 EMA < 21 EMA"
                        ))

        return signals
