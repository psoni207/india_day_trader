"""London/New York Overlap Gold (XAU/USD) Momentum Strategy.

Trading Parameters:
- Target Session: 01:30 PM to 09:30 PM IST (London 08:00 UTC to NY 16:00 UTC)
- Invalidation Stop: $2.00 to $2.50 per ounce ($20 to $25 points on Gold)
- Profit Target: $5.00 to $8.00 per ounce (R:R >= 2.5:1)
- 1R Breakeven Trigger: At +$2.50 gain, drag Stop Loss to Breakeven
- DXY Filter: Blocks longs if DXY is breaking out; blocks shorts if DXY is plunging
- Institutional Sizing: Dynamic Lots (1 Lot = 100 oz)
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from btc_engine.indicators import Candle, calculate_ema, calculate_atr
from btc_engine.setups.asian_sweep import TradeSignal
from gold_engine.dxy_feed import DXYStatus

IST = timezone(timedelta(hours=5, minutes=30))


class GoldMomentumStrategy:
    def __init__(self, min_rr: float = 2.5):
        self.min_rr = min_rr

    def evaluate(
        self,
        candles_15m: List[Candle],
        dxy_status: Optional[DXYStatus] = None
    ) -> List[TradeSignal]:
        signals: List[TradeSignal] = []
        if len(candles_15m) < 20:
            return signals

        latest = candles_15m[-1]
        dt_ist = latest.dt.astimezone(IST)

        # Gold Institutional Session Window: 13:30 to 21:30 IST (London Open to NY peak)
        hour = dt_ist.hour
        minute = dt_ist.minute
        if hour < 13 or (hour == 13 and minute < 30) or hour >= 22:
            return signals

        closes = [c.close for c in candles_15m]
        ema_20 = calculate_ema(closes, 20)
        atr_series = calculate_atr(candles_15m, 14)
        atr = atr_series[-1]

        # Calculate Asian Session Gold Range (05:30 to 13:30 IST)
        asian_candles = []
        for c in candles_15m:
            c_ist = c.dt.astimezone(IST)
            if 5 <= c_ist.hour < 13 or (c_ist.hour == 13 and c_ist.minute < 30):
                asian_candles.append(c)

        if not asian_candles:
            asian_candles = candles_15m[-10:-1]

        asian_high = max(c.high for c in asian_candles)
        asian_low = min(c.low for c in asian_candles)

        price = latest.close
        dxy_tailwind = dxy_status.gold_tailwind if dxy_status else "BALANCED"

        # 1. Bullish Gold Breakout (London/NY Momentum):
        # Price closes above Asian High + above 20 EMA + DXY not bullish
        if (
            price > asian_high and
            price > ema_20[-1] and
            "SHORT_FAVORED" not in dxy_tailwind
        ):
            sl = round(max(asian_high - 2.50, price - 2.50), 2)
            sl_dist = price - sl
            if 1.50 <= sl_dist <= 3.50:
                tp1 = round(price + (1.5 * sl_dist), 2)
                tp2 = round(price + (self.min_rr * sl_dist), 2)
                rr = round((tp2 - price) / sl_dist, 2)

                reason = (
                    f"🥇 XAU/USD LONDON/NY BREAKOUT: Cleared Asian High (${asian_high:,.2f}) | "
                    f"EMA 20 (${ema_20[-1]:.2f}) | DXY: {dxy_tailwind} | 0.01 Lot ($1/pt)"
                )

                signals.append(TradeSignal(
                    timestamp=latest.timestamp,
                    dt_str=dt_ist.strftime('%Y-%m-%d %H:%M:%S IST'),
                    symbol="XAU/USD (Gold)",
                    direction="BUY",
                    entry_price=round(price, 2),
                    stop_loss=sl,
                    take_profit_1=tp1,
                    take_profit_2=tp2,
                    risk_reward=rr,
                    reason=reason
                ))

        # 2. Bearish Gold Breakdown (London/NY Momentum):
        # Price closes below Asian Low + below 20 EMA + DXY not bearish
        elif (
            price < asian_low and
            price < ema_20[-1] and
            "LONG_FAVORED" not in dxy_tailwind
        ):
            sl = round(min(asian_low + 2.50, price + 2.50), 2)
            sl_dist = sl - price
            if 1.50 <= sl_dist <= 3.50:
                tp1 = round(price - (1.5 * sl_dist), 2)
                tp2 = round(price - (self.min_rr * sl_dist), 2)
                rr = round((price - tp2) / sl_dist, 2)

                reason = (
                    f"🥇 XAU/USD LONDON/NY BREAKDOWN: Lost Asian Low (${asian_low:,.2f}) | "
                    f"EMA 20 (${ema_20[-1]:.2f}) | DXY: {dxy_tailwind} | 0.01 Lot ($1/pt)"
                )

                signals.append(TradeSignal(
                    timestamp=latest.timestamp,
                    dt_str=dt_ist.strftime('%Y-%m-%d %H:%M:%S IST'),
                    symbol="XAU/USD (Gold)",
                    direction="SELL",
                    entry_price=round(price, 2),
                    stop_loss=sl,
                    take_profit_1=tp1,
                    take_profit_2=tp2,
                    risk_reward=rr,
                    reason=reason
                ))

        return signals
