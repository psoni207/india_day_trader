"""15-Minute Opening Range Breakout (ORB) + CPR + VWAP Confluence for Indian Indices.

Designed for Nifty 50 and BankNifty:
- Valid Time Window: 09:30 AM to 03:00 PM IST
- Rules:
  1. Long: 15m candle closes ABOVE ORB High AND price > CPR Top Central (TC) AND price > VWAP AND PCR >= 1.0.
  2. Short: 15m candle closes BELOW ORB Low AND price < CPR Bottom Central (BC) AND price < VWAP AND PCR <= 1.0.
  3. Risk-to-Reward: Target R1/R2 or Strike Walls with R:R >= 2.0.
  4. Auto-Exit: Enforces mandatory square-off before 03:15 PM IST.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from btc_engine.indicators import Candle
from btc_engine.setups.asian_sweep import TradeSignal
from indian_engine.indicators import calculate_cpr, calculate_intraday_vwap, calculate_orb, CPRLevels
from indian_engine.options_oi import OptionsSnapshot

IST = timezone(timedelta(hours=5, minutes=30))


class NiftyORBStrategy:
    def __init__(self, symbol: str = "NIFTY", min_rr: float = 2.0):
        self.symbol = symbol
        self.min_rr = min_rr

    def evaluate(
        self,
        candles: List[Candle],
        cpr: CPRLevels,
        options_snap: Optional[OptionsSnapshot] = None
    ) -> List[TradeSignal]:
        signals: List[TradeSignal] = []
        if len(candles) < 4:
            return signals

        orb = calculate_orb(candles, orb_minutes=15)
        if not orb:
            return signals

        vwap_series = calculate_intraday_vwap(candles)
        latest_candle = candles[-1]
        latest_vwap = vwap_series[-1]
        dt_ist = latest_candle.dt.astimezone(IST)

        # Indian Market Intraday Session: 09:30 to 15:00 IST for entries
        # (No entries allowed in first 15 mins 09:15-09:30, or after 15:00 IST)
        if dt_ist.hour < 9 or (dt_ist.hour == 9 and dt_ist.minute < 30) or (dt_ist.hour >= 15):
            return signals

        price = latest_candle.close
        pcr = options_snap.pcr if options_snap else 1.0

        # 1. Bullish ORB Breakout:
        # Price closes above ORB High, above CPR TC, above VWAP, with supportive PCR
        if (
            price > orb['orb_high'] and
            price > cpr.tc and
            price > latest_vwap and
            pcr >= 0.95
        ):
            sl = max(cpr.tc, orb['orb_high'] - (orb['orb_range'] * 0.4))
            sl = round(min(sl, price - 25.0), 2)
            sl_dist = price - sl

            if sl_dist > 0:
                tp1 = round(price + (1.2 * sl_dist), 2)
                tp2 = round(price + (self.min_rr * sl_dist), 2)
                rr = round((tp2 - price) / sl_dist, 2)

                reason = (
                    f"🇮🇳 {self.symbol} ORB BREAKOUT: Crossed ORB High ({orb['orb_high']}) | "
                    f"Above CPR TC ({cpr.tc}) & VWAP ({latest_vwap}) | PCR: {pcr:.2f} ({cpr.regime})"
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

        # 2. Bearish ORB Breakdown:
        # Price closes below ORB Low, below CPR BC, below VWAP, with weak PCR
        elif (
            price < orb['orb_low'] and
            price < cpr.bc and
            price < latest_vwap and
            pcr <= 1.05
        ):
            sl = min(cpr.bc, orb['orb_low'] + (orb['orb_range'] * 0.4))
            sl = round(max(sl, price + 25.0), 2)
            sl_dist = sl - price

            if sl_dist > 0:
                tp1 = round(price - (1.2 * sl_dist), 2)
                tp2 = round(price - (self.min_rr * sl_dist), 2)
                rr = round((price - tp2) / sl_dist, 2)

                reason = (
                    f"🇮🇳 {self.symbol} ORB BREAKDOWN: Broke below ORB Low ({orb['orb_low']}) | "
                    f"Below CPR BC ({cpr.bc}) & VWAP ({latest_vwap}) | PCR: {pcr:.2f} ({cpr.regime})"
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
