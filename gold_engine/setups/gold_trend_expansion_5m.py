"""5-Minute Intraday Trend Expansion Strategy for Gold (XAU/USD).

Institutional Model:
- Timeframe: 5-Minute Candles (Holding: 20 to 60 minutes)
- Concept: ICT Session Judas Sweep + 5M Market Structure Shift (MSS) + Fair Value Gap (FVG)
- Target Session: London Open & NY Overlap (13:30 to 21:30 IST)
- Macro Filter: US Dollar Index (DXY) inverse correlation
- Invalidation Stop Loss: $4.50 to $5.50 per ounce anchored behind sweep wick
- Profit Target: $11.00 to $13.50 per ounce (R:R >= 2.3:1)
- Breakeven Trailing: 1R Rule (At +$4.00 profit, drag SL to Entry + $0.50 buffer)
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from btc_engine.indicators import Candle, calculate_ema, calculate_atr
from btc_engine.setups.asian_sweep import TradeSignal
from gold_engine.dxy_feed import DXYStatus

IST = timezone(timedelta(hours=5, minutes=30))


class GoldTrendExpansion5M:
    def __init__(self, min_rr: float = 2.3, default_sl_usd: float = 5.0):
        self.min_rr = min_rr
        self.default_sl_usd = default_sl_usd

    def evaluate_5m(
        self,
        candles_5m: List[Candle],
        dxy_status: Optional[DXYStatus] = None
    ) -> List[TradeSignal]:
        signals: List[TradeSignal] = []
        if len(candles_5m) < 20:
            return signals

        latest = candles_5m[-1]
        prev = candles_5m[-2]
        dt_ist = latest.dt.astimezone(IST)

        # Institutional Session Window: 13:30 to 21:30 IST (London Open to NY peak)
        hour = dt_ist.hour
        minute = dt_ist.minute
        if hour < 13 or (hour == 13 and minute < 30) or hour >= 22:
            return signals

        closes = [c.close for c in candles_5m]
        ema_20 = calculate_ema(closes, 20)
        ema_50 = calculate_ema(closes, 50)
        atr_series = calculate_atr(candles_5m, 14)

        if not ema_20 or not ema_50 or not atr_series:
            return signals

        curr_ema20 = ema_20[-1]
        curr_ema50 = ema_50[-1]
        curr_atr = atr_series[-1]

        # Calculate Session Opening Range (First 15-30m of London Session)
        session_candles = []
        for c in candles_5m:
            c_ist = c.dt.astimezone(IST)
            if c_ist.hour >= 13 and (c_ist.hour > 13 or c_ist.minute >= 30):
                session_candles.append(c)

        if len(session_candles) < 3:
            session_candles = candles_5m[-12:-1]

        session_high = max(c.high for c in session_candles[:-1])
        session_low = min(c.low for c in session_candles[:-1])

        price = latest.close
        dxy_tailwind = dxy_status.gold_tailwind if dxy_status else "BALANCED"

        # ------------------------------------------------------------------
        # 1. BULLISH 5M EXPANSION (Judas Low Sweep & MSS Reclaim):
        # Conditions:
        # - Sweep: Previous candle or current candle dipped below session low / 50 EMA
        # - Market Structure Shift: Reclaims above EMA 20 with bullish displacement
        # - Macro: DXY is not pumping ("SHORT_FAVORED" absent)
        # ------------------------------------------------------------------
        if (
            (latest.low < session_low or prev.low < session_low or latest.low <= curr_ema50) and
            latest.close > curr_ema20 and
            latest.close > latest.open and
            "SHORT_FAVORED" not in dxy_tailwind
        ):
            sweep_extreme = min(latest.low, prev.low)
            sl = round(min(sweep_extreme - 1.0, price - self.default_sl_usd), 2)
            sl_dist = price - sl

            if 3.0 <= sl_dist <= 7.0:
                tp1 = round(price + (1.2 * sl_dist), 2)
                tp2 = round(price + (self.min_rr * sl_dist), 2)
                rr = round((tp2 - price) / sl_dist, 2)

                reason = (
                    f"🥇 XAU/USD 5M TREND EXPANSION: Judas Sweep Reclaim (${sweep_extreme:,.2f}) | "
                    f"EMA 20 (${curr_ema20:.2f}) | DXY: {dxy_tailwind} | 1R Breakeven Armed (+$4.00)"
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

        # ------------------------------------------------------------------
        # 2. BEARISH 5M EXPANSION (Judas High Sweep & MSS Breakdown):
        # Conditions:
        # - Sweep: Candle spiked above session high / 50 EMA
        # - Market Structure Shift: Rejects back down below EMA 20 with bearish displacement
        # - Macro: DXY is not dumping ("LONG_FAVORED" absent)
        # ------------------------------------------------------------------
        elif (
            (latest.high > session_high or prev.high > session_high or latest.high >= curr_ema50) and
            latest.close < curr_ema20 and
            latest.close < latest.open and
            "LONG_FAVORED" not in dxy_tailwind
        ):
            sweep_extreme = max(latest.high, prev.high)
            sl = round(max(sweep_extreme + 1.0, price + self.default_sl_usd), 2)
            sl_dist = sl - price

            if 3.0 <= sl_dist <= 7.0:
                tp1 = round(price - (1.2 * sl_dist), 2)
                tp2 = round(price - (self.min_rr * sl_dist), 2)
                rr = round((price - tp2) / sl_dist, 2)

                reason = (
                    f"🥇 XAU/USD 5M SHORT EXPANSION: Judas High Rejection (${sweep_extreme:,.2f}) | "
                    f"EMA 20 (${curr_ema20:.2f}) | DXY: {dxy_tailwind} | 1R Breakeven Armed (+$4.00)"
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
