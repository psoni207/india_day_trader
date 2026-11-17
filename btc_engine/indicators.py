"""Technical Indicators and Microstructure Calculators for Bitcoin Intraday.

Pure Python implementation designed for high speed, zero external C-dependencies,
and deterministic execution.
"""

from typing import List, Dict, Optional, Tuple
import math
from datetime import datetime, timezone


class Candle:
    __slots__ = ('timestamp', 'open', 'high', 'low', 'close', 'volume', 'dt')

    def __init__(self, timestamp: int, open_: float, high: float, low: float, close: float, volume: float):
        self.timestamp = timestamp  # unix ms or seconds
        self.open = float(open_)
        self.high = float(high)
        self.low = float(low)
        self.close = float(close)
        self.volume = float(volume)
        # normalize to UTC datetime
        ts_sec = timestamp / 1000.0 if timestamp > 10_000_000_000 else float(timestamp)
        self.dt = datetime.fromtimestamp(ts_sec, tz=timezone.utc)

    def __repr__(self):
        return f"<Candle {self.dt.strftime('%Y-%m-%d %H:%M')} O:{self.open:.1f} H:{self.high:.1f} L:{self.low:.1f} C:{self.close:.1f} V:{self.volume:.1f}>"


def calculate_ema(closes: List[float], length: int) -> List[float]:
    """Calculate Exponential Moving Average."""
    if not closes:
        return []
    ema = [closes[0]]
    multiplier = 2.0 / (length + 1)
    for price in closes[1:]:
        new_val = (price - ema[-1]) * multiplier + ema[-1]
        ema.append(new_val)
    return ema


def calculate_atr(candles: List[Candle], period: int = 14) -> List[float]:
    """Calculate Average True Range."""
    if len(candles) < 2:
        return [0.0] * len(candles)

    tr_list = [candles[0].high - candles[0].low]
    for i in range(1, len(candles)):
        h = candles[i].high
        l = candles[i].low
        prev_c = candles[i - 1].close
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        tr_list.append(tr)

    atr_list = []
    # Simple rolling / Wilder's smoothed ATR
    rolling_sum = sum(tr_list[:period])
    for i in range(len(tr_list)):
        if i < period - 1:
            atr_list.append(rolling_sum / period)
        elif i == period - 1:
            atr_list.append(rolling_sum / period)
        else:
            prev_atr = atr_list[-1]
            curr_atr = (prev_atr * (period - 1) + tr_list[i]) / period
            atr_list.append(curr_atr)
    return atr_list


def calculate_rsi(closes: List[float], period: int = 14) -> List[float]:
    """Calculate Relative Strength Index."""
    if len(closes) <= period:
        return [50.0] * len(closes)

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    rsi = [50.0] * period
    if avg_loss == 0:
        rsi.append(100.0)
    else:
        rs = avg_gain / avg_loss
        rsi.append(100.0 - (100.0 / (1.0 + rs)))

    for i in range(period, len(deltas)):
        gain = gains[i]
        loss = losses[i]
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0:
            rsi.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100.0 - (100.0 / (1.0 + rs)))

    return rsi


def calculate_anchored_vwap(candles: List[Candle]) -> List[Dict[str, float]]:
    """
    Calculate Daily Anchored VWAP (resets daily at 00:00 UTC) with standard deviation bands (+-1.0, +-2.0, +-2.5).
    """
    results = []
    current_day = None
    cum_vol = 0.0
    cum_tp_vol = 0.0
    typical_prices: List[Tuple[float, float]] = []  # (typical_price, volume)

    for c in candles:
        candle_day = c.dt.date()
        tp = (c.high + c.low + c.close) / 3.0

        if current_day != candle_day:
            # Reset on new UTC day
            current_day = candle_day
            cum_vol = 0.0
            cum_tp_vol = 0.0
            typical_prices = []

        vol = c.volume if c.volume > 0 else 1.0
        cum_vol += vol
        cum_tp_vol += tp * vol
        typical_prices.append((tp, vol))

        vwap = cum_tp_vol / cum_vol

        # Calculate volume-weighted variance
        variance_sum = sum(v * ((p - vwap) ** 2) for p, v in typical_prices)
        stdev = math.sqrt(variance_sum / cum_vol) if cum_vol > 0 else 0.0

        results.append({
            'vwap': vwap,
            'upper_1': vwap + (1.0 * stdev),
            'lower_1': vwap - (1.0 * stdev),
            'upper_2': vwap + (2.0 * stdev),
            'lower_2': vwap - (2.0 * stdev),
            'upper_2_5': vwap + (2.5 * stdev),
            'lower_2_5': vwap - (2.5 * stdev),
            'stdev': stdev
        })

    return results


def calculate_bollinger_and_keltner_squeeze(
    candles: List[Candle],
    bb_length: int = 20,
    bb_mult: float = 2.0,
    kc_mult: float = 1.5,
    atr_period: int = 20
) -> List[Dict[str, float]]:
    """
    Computes Bollinger Bands and Keltner Channels to identify TTM Volatility Squeeze.
    When BB is inside KC, squeeze is ON (compression).
    When BB expands outside KC, squeeze FIRES (explosive expansion).
    """
    closes = [c.close for c in candles]
    atr_list = calculate_atr(candles, period=atr_period)
    results = []

    for i in range(len(candles)):
        if i < bb_length - 1:
            results.append({
                'bb_upper': closes[i], 'bb_lower': closes[i], 'bb_mid': closes[i],
                'kc_upper': closes[i], 'kc_lower': closes[i],
                'squeeze_on': False, 'squeeze_fired': False
            })
            continue

        window = closes[i - bb_length + 1 : i + 1]
        mean = sum(window) / bb_length
        variance = sum((x - mean) ** 2 for x in window) / bb_length
        std = math.sqrt(variance)

        bb_upper = mean + (bb_mult * std)
        bb_lower = mean - (bb_mult * std)

        atr = atr_list[i]
        kc_upper = mean + (kc_mult * atr)
        kc_lower = mean - (kc_mult * atr)

        # Squeeze is active when Bollinger Bands are completely inside Keltner Channel
        squeeze_on = (bb_upper < kc_upper) and (bb_lower > kc_lower)
        squeeze_fired = (bb_upper >= kc_upper) or (bb_lower <= kc_lower)

        results.append({
            'bb_upper': bb_upper,
            'bb_lower': bb_lower,
            'bb_mid': mean,
            'kc_upper': kc_upper,
            'kc_lower': kc_lower,
            'squeeze_on': squeeze_on,
            'squeeze_fired': squeeze_fired
        })

    return results


def find_fair_value_gaps(candles: List[Candle], min_gap_percent: float = 0.001) -> List[Dict]:
    """
    Identify 3-candle Fair Value Gaps (FVG) / Imbalances.
    Bullish FVG: Candle 1 High < Candle 3 Low (gap left uncovered by Candle 2).
    Bearish FVG: Candle 1 Low > Candle 3 High.
    """
    fvgs = []
    for i in range(2, len(candles)):
        c1 = candles[i - 2]
        c2 = candles[i - 1]
        c3 = candles[i]

        # Bullish FVG
        if c3.low > c1.high:
            gap_size = c3.low - c1.high
            if (gap_size / c2.close) >= min_gap_percent:
                fvgs.append({
                    'index': i - 1,
                    'type': 'BULLISH',
                    'top': c3.low,
                    'bottom': c1.high,
                    'midpoint': (c3.low + c1.high) / 2.0,
                    'created_at': c2.dt
                })

        # Bearish FVG
        elif c3.high < c1.low:
            gap_size = c1.low - c3.high
            if (gap_size / c2.close) >= min_gap_percent:
                fvgs.append({
                    'index': i - 1,
                    'type': 'BEARISH',
                    'top': c1.low,
                    'bottom': c3.high,
                    'midpoint': (c1.low + c3.high) / 2.0,
                    'created_at': c2.dt
                })

    return fvgs
