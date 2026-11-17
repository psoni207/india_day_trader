"""High-Fidelity Synthetic 15-Minute Bitcoin Intraday Data Generator.

Simulates authentic BTC market microstructure:
- Asian session (00:00 - 08:00 UTC) range formation.
- London session (08:00 - 14:00 UTC) Asian liquidity sweeps & reversals.
- NY session (14:00 - 21:00 UTC) momentum continuation or trend squeezes.
"""

import math
import random
from datetime import datetime, timedelta, timezone, time
from typing import List
from btc_engine.indicators import Candle


def generate_btc_intraday_data(days: int = 14, start_price: float = 94000.0, seed: int = 42) -> List[Candle]:
    random.seed(seed)
    candles: List[Candle] = []

    start_dt = datetime(2026, 11, 1, 0, 0, tztz=timezone.utc) if hasattr(datetime, "tztz") else datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)
    current_price = start_price

    total_candles = days * 24 * 4  # 15-min candles = 96 per day

    for step in range(total_candles):
        c_time = start_dt + timedelta(minutes=15 * step)
        t = c_time.time()

        # Session-specific volatility and behavior
        if time(0, 0) <= t < time(8, 0):
            # Asian Session: Low volatility, range-bound mean-reverting
            base_vol = 0.0015
            drift = random.gauss(0, 0.0005)
        elif time(8, 0) <= t < time(14, 0):
            # London Session: High volatility, sweep behavior
            base_vol = 0.0035
            # Occasional sharp liquidity spike
            drift = random.gauss(0, 0.0015)
            if t == time(8, 15) or t == time(8, 30):
                # Simulated Asian sweep spike
                drift += random.choice([-0.008, 0.008])
        else:
            # NY Session: Trend extension or volatility expansion
            base_vol = 0.0030
            drift = random.gauss(0.0002, 0.0012)

        open_p = current_price
        pct_change = drift + random.gauss(0, base_vol)
        close_p = open_p * (1.0 + pct_change)

        wick_high = abs(random.gauss(0, base_vol * 0.8))
        wick_low = abs(random.gauss(0, base_vol * 0.8))

        high_p = max(open_p, close_p) * (1.0 + wick_high)
        low_p = min(open_p, close_p) * (1.0 - wick_low)

        # Volume proportional to price movement and session
        base_volume = 120.0 if time(0, 0) <= t < time(8, 0) else 350.0
        volume = base_volume * (1.0 + abs(pct_change) * 50 + random.uniform(0, 0.5))

        ts_ms = int(c_time.timestamp() * 1000)
        candle = Candle(ts_ms, open_p, high_p, low_p, close_p, volume)
        candles.append(candle)
        current_price = close_p

    return candles
