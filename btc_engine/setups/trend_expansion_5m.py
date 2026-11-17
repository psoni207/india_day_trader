"""5-Minute Intraday Trend Expansion Strategy for Bitcoin (BTC/USD).

Tactical Quant Model:
- Timeframe: 5-Minute Candles (Holding: 15 to 45 minutes)
- Concept: Institutional VWAP + Dynamic 20/50 EMA Ribbon Pullback + CVD Absorption
- Execution: Post-Only Maker limit orders at dynamic value zone
- Stop Loss: -0.35% (~$265 on BTC) anchored below 50 EMA / swing pivot
- Target (TP): +0.78% (~$590 on BTC) for asymmetric 1:2.25+ Risk-to-Reward
- Trailing Stop: 1R Breakeven Trailing armed at +0.25% profit
- Filters: Cumulative Volume Delta (CVD) absorption + Perpetual Funding Rate extremes
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from btc_engine.indicators import Candle, calculate_ema, calculate_atr
from btc_engine.setups.asian_sweep import TradeSignal

IST = timezone(timedelta(hours=5, minutes=30))


@dataclass
class TrendExpansionOrderSpec:
    """Execution parameters tailored for 5M Intraday Trend Expansion."""
    order_type: str = "LIMIT_MAKER"
    time_in_force: str = "GTX"
    limit_price: float = 0.0
    breakeven_trigger_pct: float = 0.0025   # +0.25% profit (1R) drags SL to Entry + buffer
    breakeven_offset_usd: float = 25.0      # Fee buffer ($25 profit lock)
    maker_fee_pct: float = 0.00015
    cvd_delta: float = 0.0
    funding_rate: float = 0.0001


class TrendExpansion5M:
    def __init__(
        self,
        min_rr: float = 2.25,
        max_stop_pct: float = 0.0040,       # Max 0.40% SL ($300 max on BTC)
        min_target_pct: float = 0.0060,     # Min 0.60% TP ($450 on BTC)
        breakeven_pct: float = 0.0025,      # 1R Breakeven trigger (+0.25%)
        max_bull_funding: float = 0.00035,  # +0.035% (crowded long filter)
        min_bear_funding: float = -0.00015  # -0.015% (short squeeze filter)
    ):
        self.min_rr = min_rr
        self.max_stop_pct = max_stop_pct
        self.min_target_pct = min_target_pct
        self.breakeven_pct = breakeven_pct
        self.max_bull_funding = max_bull_funding
        self.min_bear_funding = min_bear_funding

    def evaluate_5m(
        self,
        candles_5m: List[Candle],
        cvd_delta: float = 0.0,
        funding_rate: float = 0.0001
    ) -> List[TradeSignal]:
        signals: List[TradeSignal] = []
        if len(candles_5m) < 25:
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

        # Calculate Intraday Session VWAP
        total_vol = sum(c.volume for c in candles_5m)
        if total_vol > 0:
            vwap = sum(((c.high + c.low + c.close) / 3.0) * c.volume for c in candles_5m) / total_vol
        else:
            vwap = curr_ema20

        latest = candles_5m[-1]
        prev = candles_5m[-2]
        dt_ist = latest.dt.astimezone(IST)
        price = latest.close

        # ------------------------------------------------------------------
        # 1. BULLISH 5M TREND EXPANSION:
        # Conditions:
        # - Macro Trend: Price > VWAP and EMA 20 > EMA 50
        # - Pullback: Candle low dipped into or near value zone (EMA 20 / VWAP)
        # - Bullish confirmation: Close above open and close above EMA 20
        # - Delta/Funding: CVD > -10.0 (no panic dump) and funding <= 0.035%
        # ------------------------------------------------------------------
        if (
            price > vwap and
            curr_ema20 > curr_ema50 and
            latest.low <= max(curr_ema20, vwap) * 1.001 and
            latest.close > latest.open and
            latest.close >= curr_ema20 and
            funding_rate <= self.max_bull_funding and
            cvd_delta > -15.0
        ):
            sl = round(max(curr_ema50 - (0.5 * curr_atr), price * (1.0 - self.max_stop_pct)), 2)
            sl_dist = price - sl

            if sl_dist > 50.0:  # Minimum valid stop
                tp1 = round(price + (1.2 * sl_dist), 2)
                tp2 = round(price + (self.min_rr * sl_dist), 2)
                rr = round((tp2 - price) / sl_dist, 2)

                reason = (
                    f"🎯 BTC 5M TREND EXPANSION: 20/50 EMA Ribbon Pullback & Reclaim (${curr_ema20:,.2f}) | "
                    f"VWAP: ${vwap:,.2f} | CVD: +{cvd_delta:.1f} | 1R Breakeven Armed (+0.25%)"
                )

                signals.append(TradeSignal(
                    timestamp=latest.timestamp,
                    dt_str=dt_ist.strftime('%Y-%m-%d %H:%M:%S IST'),
                    symbol="BTC/USD (Perpetual)",
                    direction="BUY",
                    entry_price=round(price, 2),
                    stop_loss=sl,
                    take_profit_1=tp1,
                    take_profit_2=tp2,
                    risk_reward=rr,
                    reason=reason
                ))

        # ------------------------------------------------------------------
        # 2. BEARISH 5M TREND EXPANSION:
        # Conditions:
        # - Macro Trend: Price < VWAP and EMA 20 < EMA 50
        # - Retracement: Candle high tested EMA 20 / VWAP resistance band
        # - Bearish confirmation: Close below open and close below EMA 20
        # - Delta/Funding: CVD negative / sell pressure and funding >= -0.015%
        # ------------------------------------------------------------------
        elif (
            price < vwap and
            curr_ema20 < curr_ema50 and
            latest.high >= min(curr_ema20, vwap) * 0.999 and
            latest.close < latest.open and
            latest.close <= curr_ema20 and
            funding_rate >= self.min_bear_funding and
            cvd_delta < 15.0
        ):
            sl = round(min(curr_ema50 + (0.5 * curr_atr), price * (1.0 + self.max_stop_pct)), 2)
            sl_dist = sl - price

            if sl_dist > 50.0:
                tp1 = round(price - (1.2 * sl_dist), 2)
                tp2 = round(price - (self.min_rr * sl_dist), 2)
                rr = round((price - tp2) / sl_dist, 2)

                reason = (
                    f"🎯 BTC 5M SHORT EXPANSION: 20/50 EMA Ribbon Pullback & Rejection (${curr_ema20:,.2f}) | "
                    f"VWAP: ${vwap:,.2f} | CVD: {cvd_delta:.1f} | 1R Breakeven Armed (+0.25%)"
                )

                signals.append(TradeSignal(
                    timestamp=latest.timestamp,
                    dt_str=dt_ist.strftime('%Y-%m-%d %H:%M:%S IST'),
                    symbol="BTC/USD (Perpetual)",
                    direction="SELL",
                    entry_price=round(price, 2),
                    stop_loss=sl,
                    take_profit_1=tp1,
                    take_profit_2=tp2,
                    risk_reward=rr,
                    reason=reason
                ))

        return signals
