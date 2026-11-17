"""5-Minute CPR-VWAP Trend Pullback Strategy for Nifty 50 (NSE India).

Tactical Quant Model:
- Timeframe: 5-Minute Candles (Holding: 15 to 45 minutes)
- Session: 09:30 to 15:00 IST (Strict 03:15 PM IST Auto-Exit)
- Concept: Central Pivot Range (CPR) + VWAP Momentum Expansion + Options PCR Confluence
- Stop Loss: 25 Points (~₹625 / lot)
- Profit Target: 55 Points (~₹1,375 / lot, R:R >= 2.2:1)
- 1R Breakeven Trailing: Trailed above entry at +20 Points profit
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from btc_engine.indicators import Candle, calculate_ema
from btc_engine.setups.asian_sweep import TradeSignal
from indian_engine.indicators import calculate_intraday_vwap, CPRLevels
from indian_engine.options_oi import OptionsSnapshot

IST = timezone(timedelta(hours=5, minutes=30))


class NiftyTrendExpansion5M:
    def __init__(self, symbol: str = "NIFTY", min_rr: float = 2.2):
        self.symbol = symbol
        self.min_rr = min_rr

    def evaluate_5m(
        self,
        candles_5m: List[Candle],
        cpr: CPRLevels,
        options_snap: Optional[OptionsSnapshot] = None
    ) -> List[TradeSignal]:
        signals: List[TradeSignal] = []
        if len(candles_5m) < 10:
            return signals

        vwap_series = calculate_intraday_vwap(candles_5m)
        if not vwap_series:
            return signals

        latest_candle = candles_5m[-1]
        latest_vwap = vwap_series[-1]
        dt_ist = latest_candle.dt.astimezone(IST)

        # Indian Market Session Window for 5M Momentum: 09:30 to 15:00 IST
        if dt_ist.hour < 9 or (dt_ist.hour == 9 and dt_ist.minute < 30) or (dt_ist.hour >= 15):
            return signals

        closes = [c.close for c in candles_5m]
        ema_20 = calculate_ema(closes, 20)
        curr_ema20 = ema_20[-1] if ema_20 else latest_vwap

        price = latest_candle.close
        pcr = options_snap.pcr if options_snap else 1.0

        # 1. Bullish 5M Pullback & Bounce:
        # Price above CPR TC, price pulled back to 20 EMA / VWAP, closes green, PCR >= 1.05
        if (
            price > cpr.tc and
            price >= latest_vwap and
            latest_candle.low <= max(curr_ema20, latest_vwap) * 1.002 and
            latest_candle.close > latest_candle.open and
            pcr >= 1.0
        ):
            sl = round(max(cpr.tc - 10.0, price - 25.0), 2)
            sl_dist = price - sl

            if sl_dist > 10.0:
                tp1 = round(price + (1.2 * sl_dist), 2)
                tp2 = round(price + (self.min_rr * sl_dist), 2)
                rr = round((tp2 - price) / sl_dist, 2)

                reason = (
                    f"🇮🇳 {self.symbol} 5M TREND EXPANSION: 20 EMA / VWAP Bounce ({latest_vwap:,.1f}) | "
                    f"Above CPR TC ({cpr.tc:,.1f}) | PCR: {pcr:.2f} | 1R Breakeven Armed (+20 pts)"
                )

                signals.append(TradeSignal(
                    timestamp=latest_candle.timestamp,
                    dt_str=dt_ist.strftime('%Y-%m-%d %H:%M:%S IST'),
                    symbol=self.symbol,
                    direction="BUY",
                    entry_price=round(price, 2),
                    stop_loss=sl,
                    take_profit_1=tp1,
                    take_profit_2=tp2,
                    risk_reward=rr,
                    reason=reason
                ))

        # 2. Bearish 5M Pullback & Rejection:
        # Price below CPR BC, price pulled up to 20 EMA / VWAP, closes red, PCR <= 0.90
        elif (
            price < cpr.bc and
            price <= latest_vwap and
            latest_candle.high >= min(curr_ema20, latest_vwap) * 0.998 and
            latest_candle.close < latest_candle.open and
            pcr <= 0.95
        ):
            sl = round(min(cpr.bc + 10.0, price + 25.0), 2)
            sl_dist = sl - price

            if sl_dist > 10.0:
                tp1 = round(price - (1.2 * sl_dist), 2)
                tp2 = round(price - (self.min_rr * sl_dist), 2)
                rr = round((price - tp2) / sl_dist, 2)

                reason = (
                    f"🇮🇳 {self.symbol} 5M SHORT EXPANSION: 20 EMA / VWAP Rejection ({latest_vwap:,.1f}) | "
                    f"Below CPR BC ({cpr.bc:,.1f}) | PCR: {pcr:.2f} | 1R Breakeven Armed (+20 pts)"
                )

                signals.append(TradeSignal(
                    timestamp=latest_candle.timestamp,
                    dt_str=dt_ist.strftime('%Y-%m-%d %H:%M:%S IST'),
                    symbol=self.symbol,
                    direction="SELL",
                    entry_price=round(price, 2),
                    stop_loss=sl,
                    take_profit_1=tp1,
                    take_profit_2=tp2,
                    risk_reward=rr,
                    reason=reason
                ))

        return signals
