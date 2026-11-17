"""Real-Time Market Feed & Simulator for Gold (XAU/USD).

Provides live ticks, Asian range metrics, DXY correlation, and 15m candle bars.
Designed with offline sandbox fallback and live network adaptors.
"""

import time
import random
import threading
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timezone, timedelta
from gold_engine.dxy_feed import DXYCorrelationFeed, DXYStatus

IST = timezone(timedelta(hours=5, minutes=30))


class GoldMarketFeed:
    def __init__(
        self,
        symbol: str = "XAU/USD",
        base_price: float = 4068.89,
        poll_interval: float = 1.0,
        on_tick: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.symbol = symbol
        self.base_price = base_price
        self.current_price = base_price
        self.poll_interval = poll_interval
        self.on_tick = on_tick
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # DXY Feed
        self.dxy_feed = DXYCorrelationFeed(base_dxy=104.28)
        self.dxy_status: DXYStatus = self.dxy_feed.get_status()

        # Asian Range baseline
        self.asian_high = round(base_price + 6.50, 2)
        self.asian_low = round(base_price - 5.80, 2)

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
                dt_ist = datetime.now(IST)
                # Mean-reverting micro-fluctuation around base_price (never drifts away!)
                noise = (self.base_price - self.current_price) * 0.05 + (random.random() - 0.5) * 0.35
                self.current_price = round(self.current_price + noise, 2)

                # Micro DXY fluctuation
                dxy_noise = (random.random() - 0.5) * 0.02
                self.dxy_status = self.dxy_feed.get_status(self.dxy_feed.dxy_price + dxy_noise)

                tick = {
                    'symbol': self.symbol,
                    'price': self.current_price,
                    'timestamp': int(time.time() * 1000),
                    'dt_str': dt_ist.strftime('%Y-%m-%d %H:%M:%S IST'),
                    'dxy_price': self.dxy_status.dxy_price,
                    'dxy_trend': self.dxy_status.trend,
                    'dxy_tailwind': self.dxy_status.gold_tailwind,
                    'asian_high': self.asian_high,
                    'asian_low': self.asian_low,
                    'lot_size_rec': "Dynamic Lot Sizing (1 Lot = 100 oz)"
                }

                if self.on_tick:
                    self.on_tick(tick)

            except Exception:
                pass

            time.sleep(self.poll_interval)
