"""Cumulative Volume Delta (CVD) and Perpetual Funding Rate Analyzers.

Provides institutional orderflow metrics:
- Buyer vs Seller aggression imbalance (CVD divergence)
- Perpetual futures funding rate overheating / liquidation squeeze detection
"""

from typing import List, Dict, Tuple, Any
from btc_engine.indicators import Candle


def calculate_cvd(candles: List[Candle]) -> List[Dict[str, float]]:
    """
    Computes Cumulative Volume Delta (CVD) from candlestick microstructure.
    Estimates aggressor volume using candle range, close position relative to high/low,
    and volume weighting.
    """
    cvd_series = []
    cum_delta = 0.0

    for c in candles:
        candle_range = c.high - c.low
        if candle_range <= 0:
            delta = 0.0
        else:
            # Bullish pressure: close near high
            # Bearish pressure: close near low
            buyer_ratio = (c.close - c.low) / candle_range
            seller_ratio = (c.high - c.close) / candle_range
            delta = c.volume * (buyer_ratio - seller_ratio)

        cum_delta += delta
        cvd_series.append({
            'delta': delta,
            'cvd': cum_delta,
            'timestamp': c.timestamp
        })

    return cvd_series


def detect_cvd_divergence(
    candles: List[Candle],
    cvd_series: List[Dict[str, float]],
    lookback: int = 12
) -> List[Dict[str, Any]]:
    """
    Detects CVD Absorption / Exhaustion Divergences:
    - Bearish Divergence: Price makes Higher High while CVD makes Lower High (Absorption by limit sellers).
    - Bullish Divergence: Price makes Lower Low while CVD makes Higher Low (Absorption by limit buyers).
    """
    divergences = []
    if len(candles) < lookback + 2:
        return divergences

    for i in range(lookback, len(candles)):
        p_window = candles[i - lookback : i + 1]
        c_window = cvd_series[i - lookback : i + 1]

        curr_p = p_window[-1]
        curr_cvd = c_window[-1]['cvd']

        # Find previous swing high/low in window
        prev_p_high = max(c.high for c in p_window[:-2])
        prev_p_low = min(c.low for c in p_window[:-2])

        prev_cvd_high = max(x['cvd'] for x in c_window[:-2])
        prev_cvd_low = min(x['cvd'] for x in c_window[:-2])

        # Bearish Absorption: Price pushed above previous high, but CVD failed to exceed prev CVD high
        if curr_p.high >= prev_p_high and curr_cvd < prev_cvd_high * 0.98:
            divergences.append({
                'index': i,
                'timestamp': curr_p.timestamp,
                'type': 'BEARISH_ABSORPTION',
                'description': 'Price tested higher liquidity, but aggressive buyer delta was absorbed.'
            })

        # Bullish Absorption: Price broke lower low, but CVD held higher (sellers exhausted)
        elif curr_p.low <= prev_p_low and curr_cvd > prev_cvd_low * 1.02:
            divergences.append({
                'index': i,
                'timestamp': curr_p.timestamp,
                'type': 'BULLISH_ABSORPTION',
                'description': 'Price swept lower liquidity, but aggressive selling dried up.'
            })

    return divergences


def simulate_perpetual_funding_rates(candles: List[Candle]) -> List[Dict[str, float]]:
    """
    Simulates 8-hour perpetual funding rate cycles (Binance/Bybit style).
    Positive (> +0.01%): Longs pay Shorts (bullish crowding).
    Extreme Positive (> +0.035%): Extreme leverage -> High risk of long squeeze.
    Negative (< -0.01%): Shorts pay Longs -> Short squeeze potential.
    """
    funding_records = []
    # Base funding rate fluctuates with recent 24-candle momentum
    for i in range(len(candles)):
        if i < 24:
            funding_records.append({'rate': 0.0001, 'timestamp': candles[i].timestamp, 'crowding': 'NEUTRAL'})
            continue

        pct_change_24h = (candles[i].close - candles[i - 24].close) / candles[i - 24].close
        # Funding rate formula: base 0.01% + premium scaled by 24h trend
        funding_rate = 0.0001 + (pct_change_24h * 0.005)

        # Cap between -0.05% and +0.08%
        funding_rate = max(-0.0005, min(0.0008, funding_rate))

        crowding = "NEUTRAL"
        if funding_rate >= 0.00035:
            crowding = "LONG_CROWDED_DANGER"
        elif funding_rate <= -0.00015:
            crowding = "SHORT_CROWDED_SQUEEZE"

        funding_records.append({
            'rate': funding_rate,
            'rate_pct': funding_rate * 100.0,
            'timestamp': candles[i].timestamp,
            'crowding': crowding
        })

    return funding_records
