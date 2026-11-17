"""Unified Multi-Asset Intraday Trading Manager.

Orchestrates:
1. Bitcoin Engine (BTC/USD 1M Scalper & 15M Asian Range Sweeps)
2. Indian Equities Engine (NSE Nifty 50 ORB, CPR, Options PCR, 03:15 PM Auto-Exit)
3. Gold Engine (XAU/USD London/NY Momentum, DXY Inverse Correlation, Dynamic Lot Sizing)
"""

import time
import threading
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone, timedelta

from backend.database.db import save_signal, get_active_signals, save_trade, get_recent_candles
from backend.live_engine import LiveTradingEngine
from indian_engine.nse_feed import NSEMarketFeed
from indian_engine.indicators import CPRLevels
from indian_engine.setups.orb_strategy import NiftyORBStrategy
from indian_engine.setups.nifty_trend_expansion_5m import NiftyTrendExpansion5M
from indian_engine.auto_exit_sentinel import IndianAutoExitSentinel
from gold_engine.gold_feed import GoldMarketFeed
from gold_engine.setups.gold_momentum import GoldMomentumStrategy
from gold_engine.setups.gold_trend_expansion_5m import GoldTrendExpansion5M

IST = timezone(timedelta(hours=5, minutes=30))


class MultiAssetManager:
    def __init__(self):
        # 1. Bitcoin Engine
        self.btc_engine = LiveTradingEngine(symbol="BTCUSDT")

        # 2. Indian Equities Engine
        self.nse_feed = NSEMarketFeed(symbol="NIFTY 50", base_price=24150.0, poll_interval=1.0)
        self.nifty_orb = NiftyORBStrategy(symbol="NIFTY 50", min_rr=2.0)
        self.nifty_expansion_5m = NiftyTrendExpansion5M(symbol="NIFTY 50", min_rr=2.2)
        self.nse_auto_exit = IndianAutoExitSentinel(auto_exit_hour=15, auto_exit_minute=15)

        # 3. Gold Engine
        self.gold_feed = GoldMarketFeed(symbol="XAU/USD", base_price=4068.89, poll_interval=1.0)
        self.gold_momentum = GoldMomentumStrategy(min_rr=2.5)
        self.gold_expansion_5m = GoldTrendExpansion5M(min_rr=2.3, default_sl_usd=5.0)

        self.running = False
        self.subscribers: List[Callable[[Dict[str, Any]], None]] = []
        self._lock = threading.Lock()

    def start(self):
        if self.running:
            return
        self.running = True

        print("=" * 80)
        print(" 🌐 BOOTING MULTI-ASSET INTRADAY TRADING PLATFORM")
        print("    1. Bitcoin Engine (BTC/USD Perpetual) -> Active")
        print("    2. Indian Equities Engine (NSE Nifty/BankNifty) -> Active (03:15 PM Auto-Exit)")
        print("    3. Gold Engine (XAU/USD & DXY Correlation) -> Active (Dynamic Lot Sizing)")
        print("=" * 80)

        # Start Bitcoin Engine
        self.btc_engine.start()

        # Start Indian NSE Feed & Callbacks
        self.nse_feed.on_tick = self._on_nse_tick
        self.nse_feed.start()

        # Start Gold Feed & Callbacks
        self.gold_feed.on_tick = self._on_gold_tick
        self.gold_feed.start()

    def stop(self):
        self.running = False
        self.btc_engine.stop()
        self.nse_feed.stop()
        self.gold_feed.stop()
        print("\n🛑 ALL MULTI-ASSET ENGINES STOPPED.")

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]):
        with self._lock:
            self.subscribers.append(callback)
            self.btc_engine.subscribe(callback)

    def unsubscribe(self, callback: Callable[[Dict[str, Any]], None]):
        with self._lock:
            if callback in self.subscribers:
                self.subscribers.remove(callback)
            self.btc_engine.unsubscribe(callback)

    def _broadcast(self, event_type: str, data: Dict[str, Any]):
        payload = {'type': event_type, 'data': data, 'timestamp': int(time.time() * 1000)}
        with self._lock:
            for cb in self.subscribers:
                try:
                    cb(payload)
                except Exception:
                    pass

    def _on_nse_tick(self, tick: Dict[str, Any]):
        # Check 03:15 PM Auto-Exit Sentinel
        dt_ist = datetime.now(IST)
        is_exit, exit_desc = self.nse_auto_exit.is_auto_exit_time(dt_ist)

        tick['auto_exit_status'] = exit_desc
        tick['is_auto_exit'] = is_exit
        self._broadcast('nse_tick', tick)

    def _on_gold_tick(self, tick: Dict[str, Any]):
        self._broadcast('gold_tick', tick)

    def get_multi_status(self) -> Dict[str, Any]:
        dt_ist = datetime.now(IST)
        is_exit, exit_desc = self.nse_auto_exit.is_auto_exit_time(dt_ist)

        return {
            'timestamp': int(time.time() * 1000),
            'dt_str': dt_ist.strftime('%Y-%m-%d %H:%M:%S IST'),
            'btc': {
                'price': self.btc_engine.feed.current_price if self.btc_engine.feed else 0.0,
                'cvd': getattr(self.btc_engine.feed, 'cvd', getattr(self.btc_engine.feed, 'cum_cvd', 0.0)) if self.btc_engine.feed else 0.0,
                'funding': getattr(self.btc_engine.feed, 'funding_rate', getattr(self.btc_engine.feed, 'current_funding_rate', 0.0001)) if self.btc_engine.feed else 0.0001,
                'status': 'RUNNING',
                'active_signals': get_active_signals()
            },
            'nifty': {
                'price': self.nse_feed.current_price,
                'cpr_pivot': self.nse_feed.cpr.pivot,
                'cpr_tc': self.nse_feed.cpr.tc,
                'cpr_bc': self.nse_feed.cpr.bc,
                'cpr_regime': self.nse_feed.cpr.regime,
                'pcr': self.nse_feed.options_snap.pcr,
                'pcr_sentiment': self.nse_feed.options_snap.sentiment,
                'call_wall': self.nse_feed.options_snap.call_wall_strike,
                'put_wall': self.nse_feed.options_snap.put_wall_strike,
                'auto_exit_desc': exit_desc,
                'is_auto_exit': is_exit,
                'session_hours': "09:15 AM - 03:15 PM IST"
            },
            'gold': {
                'price': self.gold_feed.current_price,
                'dxy_price': self.gold_feed.dxy_status.dxy_price,
                'dxy_trend': self.gold_feed.dxy_status.trend,
                'dxy_tailwind': self.gold_feed.dxy_status.gold_tailwind,
                'asian_high': self.gold_feed.asian_high,
                'asian_low': self.gold_feed.asian_low,
                'lot_sizing': "0.01 Lots (1 oz = $1.00 PnL per $1.00 move)",
                'session_hours': "01:30 PM - 09:30 PM IST (London/NY Overlap)"
            }
        }
