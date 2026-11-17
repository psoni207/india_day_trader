"""Technical Indicators for Indian Equities & Indices (Nifty 50 & BankNifty).

Includes:
- Central Pivot Range (CPR: Pivot, TC, BC, Width classification, R1/R2/S1/S2)
- Daily Volume Weighted Average Price (VWAP)
- Opening Range Breakout (ORB: 15-minute range)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from btc_engine.indicators import Candle, calculate_ema, calculate_atr

IST = timezone(timedelta(hours=5, minutes=30))


@dataclass
class CPRLevels:
    pivot: float
    tc: float             # Top Central
    bc: float             # Bottom Central
    cpr_width: float      # Absolute width
    cpr_width_pct: float  # Percentage width relative to pivot
    regime: str           # 'NARROW_TRENDING' (< 0.18%) or 'WIDE_RANGEBOUND' (> 0.40%) or 'NORMAL'
    r1: float
    r2: float
    s1: float
    s2: float


def calculate_cpr(prev_high: float, prev_low: float, prev_close: float) -> CPRLevels:
    """Calculates Central Pivot Range (CPR) from previous day's High, Low, Close."""
    pivot = round((prev_high + prev_low + prev_close) / 3.0, 2)
    bc = round((prev_high + prev_low) / 2.0, 2)
    tc = round((2 * pivot) - bc, 2)

    # Ensure TC is top and BC is bottom for consistent range checking
    top = max(tc, bc)
    bottom = min(tc, bc)
    width = round(top - bottom, 2)
    width_pct = round((width / pivot) * 100.0, 3)

    if width_pct < 0.18:
        regime = "NARROW_TRENDING"
    elif width_pct > 0.40:
        regime = "WIDE_RANGEBOUND"
    else:
        regime = "NORMAL"

    r1 = round((2 * pivot) - prev_low, 2)
    r2 = round(pivot + (prev_high - prev_low), 2)
    s1 = round((2 * pivot) - prev_high, 2)
    s2 = round(pivot - (prev_high - prev_low), 2)

    return CPRLevels(
        pivot=pivot, tc=top, bc=bottom,
        cpr_width=width, cpr_width_pct=width_pct,
        regime=regime, r1=r1, r2=r2, s1=s1, s2=s2
    )


def calculate_intraday_vwap(candles: List[Candle]) -> List[float]:
    """Calculates intraday VWAP for current session candles."""
    vwap_values = []
    cum_vol_price = 0.0
    cum_vol = 0.0

    for c in candles:
        typical_price = (c.high + c.low + c.close) / 3.0
        cum_vol_price += typical_price * c.volume
        cum_vol += c.volume
        vwap = (cum_vol_price / cum_vol) if cum_vol > 0 else typical_price
        vwap_values.append(round(vwap, 2))

    return vwap_values


def calculate_orb(candles: List[Candle], orb_minutes: int = 15) -> Optional[Dict[str, float]]:
    """
    Computes 15-Minute Opening Range (09:15 AM to 09:30 AM IST).
    Assumes candles are sorted chronologically.
    """
    orb_candles = []
    for c in candles:
        dt_ist = c.dt.astimezone(IST)
        # Check if candle falls between 09:15 and 09:30 IST
        if dt_ist.hour == 9 and 15 <= dt_ist.minute < (15 + orb_minutes):
            orb_candles.append(c)

    if not orb_candles:
        # Fallback: take the first candle if session start
        if candles:
            orb_candles = [candles[0]]
        else:
            return None

    orb_high = max(c.high for c in orb_candles)
    orb_low = min(c.low for c in orb_candles)

    return {
        'orb_high': round(orb_high, 2),
        'orb_low': round(orb_low, 2),
        'orb_range': round(orb_high - orb_low, 2)
    }
