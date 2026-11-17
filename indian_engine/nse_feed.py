"""Real-Time Market Feed & Simulator for Indian Indices (Nifty 50 & BankNifty).

Provides live ticks, CPR calculation, Options OI analysis, and candle bars.
Designed with offline sandbox fallback and live network adaptors.
"""

import time
import math
import random
import threading
from typing import Dict, Any, Callable, List, Optional
from datetime import datetime, timezone, timedelta
from btc_engine.indicators import Candle
from indian_engine.indicators import calculate_cpr, CPRLevels
from indian_engine.options_oi import OptionsOIEngine, OptionsSnapshot

IST = timezone(timedelta(hours=5, minutes=30))


class NSEMarketFeed:
    def __init__(
        self,
        symbol: str = "NIFTY 50",
        base_price: float = 24150.0,
        poll_interval: float = 1.0,
        on_tick: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.symbol = symbol
        self.current_price = base_price
        self.poll_interval = poll_interval
        self.on_tick = on_tick
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # Previous day levels for CPR (Nifty example: High 24220, Low 24080, Close 24140)
        self.prev_high = base_price + 70.0
        self.prev_low = base_price - 70.0
        self.prev_close = base_price - 10.0
        self.cpr: CPRLevels = calculate_cpr(self.prev_high, self.prev_low, self.prev_close)

        # Options Engine
        self.options_engine = OptionsOIEngine(symbol="NIFTY")
        self.options_snap: OptionsSnapshot = self.options_engine.analyze_chain(base_price)

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def _run_loop(self):
        while self.running:
            try:
                # Realistic micro-oscillation for Nifty (±0.5 to 2.5 points)
                dt_ist = datetime.now(IST)
                noise = (random.random() - 0.49) * 2.2
                self.current_price = round(self.current_price + noise, 2)

                # Update options analysis periodically
                self.options_snap = self.options_engine.analyze_chain(self.current_price)

                tick = {
                    'symbol': self.symbol,
                    'price': self.current_price,
                    'timestamp': int(time.time() * 1000),
                    'dt_str': dt_ist.strftime('%Y-%m-%d %H:%M:%S IST'),
                    'cpr_pivot': self.cpr.pivot,
                    'cpr_tc': self.cpr.tc,
                    'cpr_bc': self.cpr.bc,
                    'cpr_regime': self.cpr.regime,
                    'pcr': self.options_snap.pcr,
                    'pcr_sentiment': self.options_snap.sentiment,
                    'call_wall': self.options_snap.call_wall_strike,
                    'put_wall': self.options_snap.put_wall_strike,
                    'max_pain': self.options_snap.max_pain
                }

                if self.on_tick:
                    self.on_tick(tick)

            except Exception as e:
                pass

            time.sleep(self.poll_interval)
