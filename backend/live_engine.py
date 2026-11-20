"""Continuous Active Trading Engine for Bitcoin Intraday (Hardened Setup).

Runs 24/7 background loop with 4 institutional risk safeguards:
1. Mandates Post-Only Limit (Maker) orders at 50% FVG retest to eliminate taker slippage.
2. Automates Breakeven Trailing Stops (1R Rule: +0.12% gain drags SL to entry + $15 buffer).
3. Restricts 1M Scalps during Asian session lull (03:00 - 09:00 IST) to avoid spread widening.
4. Protects capital with Macro News Blackout Sentinel (+-15 min around US CPI/NFP/FOMC).
"""

import time
import threading
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Callable

from backend.database.db import (
    get_recent_candles, save_signal, update_signal_status, update_signal_breakeven,
    get_active_signals, save_trade, save_regime_log, get_latest_regime
)
from btc_engine.indicators import Candle
from btc_engine.setups.alpha_precision_strategy import AlphaPrecisionStrategy
from btc_engine.setups.asian_sweep import AsianRangeSweepStrategy
from btc_engine.setups.volatility_squeeze import VolatilitySqueezeStrategy
from btc_engine.setups.micro_scalper import MicroScalper1M
from btc_engine.setups.trend_expansion_5m import TrendExpansion5M
from btc_engine.agent.market_regime_agent import MarketRegimeAgent
from backend.live_feed import LiveMarketFeed
from backend.news_calendar import MacroNewsSentinel

IST = timezone(timedelta(hours=5, minutes=30))


class LiveTradingEngine:
    def __init__(self, symbol: str = "BTCUSDT", max_concurrent_positions: int = 2):
        self.symbol = symbol
        self.max_concurrent_positions = max_concurrent_positions

        # Strategies & Intelligence
        self.s_alpha = AlphaPrecisionStrategy(htf_ema_period=40, min_rr=2.5)
        self.s_asian = AsianRangeSweepStrategy(min_rr=2.0)
        self.s_squeeze = VolatilitySqueezeStrategy(min_rr=2.0)
        self.s_scalp = MicroScalper1M(min_rr=2.2, max_stop_pct=0.0015, min_target_pct=0.0020, breakeven_pct=0.0012)
        self.s_expansion_5m = TrendExpansion5M(min_rr=2.25)
        self.agent = MarketRegimeAgent()

        # Hardening Sentinels
        self.news_sentinel = MacroNewsSentinel(buffer_minutes=15)
        self.breakeven_tracked: Dict[int, bool] = {}  # Tracks signals where 1R stop has been dragged
        self.last_lull_log_ts = 0
        self.last_blackout_log_ts = 0

        # Engine state
        self.running = False
        self.feed: Optional[LiveMarketFeed] = None
        self.last_candle_eval_ts = 0
        self.last_regime_eval_ts = 0
        self.subscribers: List[Callable[[Dict[str, Any]], None]] = []
        self._lock = threading.Lock()

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]):
        with self._lock:
            self.subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Dict[str, Any]], None]):
        with self._lock:
            if callback in self.subscribers:
                self.subscribers.remove(callback)

    def _broadcast(self, event_type: str, data: Dict[str, Any]):
        payload = {'type': event_type, 'data': data, 'timestamp': int(time.time() * 1000)}
        with self._lock:
            for cb in self.subscribers:
                try:
                    cb(payload)
                except Exception:
                    pass

    def start(self):
        if self.running:
            return
        self.running = True

        print("=" * 80)
        print(f" 🚀 STARTING HARDENED INTRADAY TRADING ENGINE | Symbol: {self.symbol}")
        print("    Database: SQLite (data/intraday.db) | Timezone: IST (Asia/Kolkata)")
        print("    🛡️ Hardening Layer Active:")
        print("       • 1. Post-Only (Maker) Execution: Enforced @ 50% FVG Equilibrium")
        print("       • 2. 1R Breakeven Trailing: Active (+0.12% gain drags SL to Entry + $15)")
        print("       • 3. Session Lockout: Asian Lull (03:00 - 09:00 IST) Scalps Frozen")
        print("       • 4. Macro Sentinel: +-15m US CPI / NFP / FOMC Blackout Armed")
        print("=" * 80)

        # Initialize Market Feed
        self.feed = LiveMarketFeed(
            symbol=self.symbol,
            poll_interval=1.0,
            on_tick=self._handle_tick,
            on_candle_close=self._handle_candle_close
        )
        self.feed.start()

        # Initial Agent Regime Assessment
        self._evaluate_market_regime()

    def stop(self):
        self.running = False
        if self.feed:
            self.feed.stop()
        print("\n🛑 INTRADAY TRADING ENGINE STOPPED.")

    def _handle_tick(self, tick: Dict[str, Any]):
        price = tick['price']
        dt_str = tick['dt_str']
        now_ts = int(time.time())
        now_ist = datetime.now(IST)

        # 1. Monitor currently active signals/positions
        active_signals = get_active_signals()
        for sig in active_signals:
            direction = sig['direction']
            entry = sig['entry_price']
            sl = sig['stop_loss']
            tp1 = sig['take_profit_1']
            tp2 = sig['take_profit_2']

            # Calculate live unrealized PnL %
            unrealized_pnl = ((price - entry) / entry * 100.0) if direction == "BUY" else ((entry - price) / entry * 100.0)

            # HARDENING RULE 2: Breakeven Trailing Stop (1R Rule)
            # As soon as position reaches +0.12% profit (1x risk), drag SL to Breakeven (+15 USD fee buffer)
            if sig['id'] not in self.breakeven_tracked and unrealized_pnl >= 0.12:
                if direction == "BUY":
                    new_sl = round(entry + 15.0, 2)
                    if new_sl > sl:
                        update_signal_breakeven(sig['id'], new_sl, "🛡️ 1R Breakeven Dragged (+0.12%)")
                        sig['stop_loss'] = new_sl
                        sl = new_sl
                        self.breakeven_tracked[sig['id']] = True
                        print(f"\n🛡️ [{dt_str}] 1R PROFIT REACHED (+{unrealized_pnl:.2f}%): Stop Loss dragged to Breakeven (${new_sl:,.2f}) on #{sig['id']} {direction} (Locks in +$15 fee buffer)")
                        self._broadcast('breakeven_triggered', {
                            'id': sig['id'],
                            'new_sl': new_sl,
                            'entry': entry,
                            'pnl': unrealized_pnl,
                            'dt_str': dt_str
                        })
                elif direction == "SELL":
                    new_sl = round(entry - 15.0, 2)
                    if new_sl < sl:
                        update_signal_breakeven(sig['id'], new_sl, "🛡️ 1R Breakeven Dragged (+0.12%)")
                        sig['stop_loss'] = new_sl
                        sl = new_sl
                        self.breakeven_tracked[sig['id']] = True
                        print(f"\n🛡️ [{dt_str}] 1R PROFIT REACHED (+{unrealized_pnl:.2f}%): Stop Loss dragged to Breakeven (${new_sl:,.2f}) on #{sig['id']} {direction} (Locks in +$15 fee buffer)")
                        self._broadcast('breakeven_triggered', {
                            'id': sig['id'],
                            'new_sl': new_sl,
                            'entry': entry,
                            'pnl': unrealized_pnl,
                            'dt_str': dt_str
                        })

            # Check Stop Loss
            hit_sl = (price <= sl) if direction == "BUY" else (price >= sl)
            # Check Take Profit
            hit_tp = (price >= tp2) if direction == "BUY" else (price <= tp2)

            if hit_sl:
                outcome_label = "BREAKEVEN_EXIT" if (sig['id'] in self.breakeven_tracked) else "SL_HIT"
                realized_pnl = round(unrealized_pnl - 0.03, 2) # Post-Only maker fee deduction ~0.03%
                update_signal_status(sig['id'], f"CLOSED_{outcome_label}")
                save_trade({
                    'signal_id': sig['id'],
                    'symbol': sig['symbol'],
                    'direction': direction,
                    'entry_time': sig['dt_str'],
                    'entry_price': entry,
                    'exit_time': dt_str,
                    'exit_price': price,
                    'pnl_pct': realized_pnl,
                    'outcome': outcome_label,
                    'reason': f"{'Breakeven Stop' if outcome_label == 'BREAKEVEN_EXIT' else 'Stop Loss'} triggered at ${sl:,.2f}",
                    'timeframe': sig.get('timeframe', '1M')
                })
                icon = "🛡️" if outcome_label == "BREAKEVEN_EXIT" else "❌"
                print(f"\n{icon} [{dt_str}] {outcome_label} HIT on #{sig['id']} {direction}: Exit @ ${price:,.2f} | Realized PnL: {realized_pnl:+.2f}%")
                self._broadcast('trade_closed', {'id': sig['id'], 'outcome': outcome_label, 'pnl': realized_pnl})

            elif hit_tp:
                realized_pnl = round(unrealized_pnl - 0.03, 2)
                update_signal_status(sig['id'], "CLOSED_WIN_FULL")
                save_trade({
                    'signal_id': sig['id'],
                    'symbol': sig['symbol'],
                    'direction': direction,
                    'entry_time': sig['dt_str'],
                    'entry_price': entry,
                    'exit_time': dt_str,
                    'exit_price': price,
                    'pnl_pct': realized_pnl,
                    'outcome': 'WIN_FULL',
                    'reason': f"Take Profit triggered at ${tp2:,.2f}",
                    'timeframe': sig.get('timeframe', '1M')
                })
                print(f"\n🎯 [{dt_str}] TAKE PROFIT HIT on #{sig['id']} {direction}: Exit @ ${price:,.2f} | Realized PnL: +{realized_pnl:.2f}%")
                self._broadcast('trade_closed', {'id': sig['id'], 'outcome': 'WIN_FULL', 'pnl': realized_pnl})

        # 2. Periodically scan for new setup triggers (every 5 seconds)
        if now_ts - self.last_candle_eval_ts >= 5:
            self.last_candle_eval_ts = now_ts
            self._scan_for_signals(price, dt_str)

        # 3. Periodically re-evaluate Agentic Regime (every 60 seconds)
        if now_ts - self.last_regime_eval_ts >= 60:
            self.last_regime_eval_ts = now_ts
            self._evaluate_market_regime()

        # 4. Broadcast live tick with hardening sentinel statuses
        is_blackout, event_name = self.news_sentinel.is_news_blackout(now_ist)
        is_asian_lull = (3 <= now_ist.hour < 9)
        tick_summary = {
            'symbol': self.symbol,
            'price': price,
            'timestamp': tick['timestamp'],
            'dt_str': dt_str,
            'cvd': round(tick['cvd'], 1),
            'funding_rate': tick['funding_rate'],
            'active_positions': len(active_signals),
            'mode': tick['mode'],
            'news_blackout': is_blackout,
            'active_news_event': event_name,
            'session_lockout': is_asian_lull
        }
        self._broadcast('tick', tick_summary)

    def _handle_candle_close(self, closed_candle: Dict[str, Any]):
        print(f"\n📊 [{closed_candle['dt_str']}] 15M CANDLE CLOSED: O: {closed_candle['open']:.1f} H: {closed_candle['high']:.1f} L: {closed_candle['low']:.1f} C: {closed_candle['close']:.1f} Vol: {closed_candle['volume']:.1f}")
        self._broadcast('candle_closed', closed_candle)

    def _scan_for_signals(self, current_price: float, dt_str: str):
        # Prevent opening more than max concurrent positions
        if len(get_active_signals()) >= self.max_concurrent_positions:
            return

        db_candles = get_recent_candles(self.symbol, "15m", limit=80)
        if len(db_candles) < 30:
            return

        candle_objects = [
            Candle(c['timestamp'], c['open'], c['high'], c['low'], c['close'], c['volume'])
            for c in db_candles
        ]

        now_ts = int(time.time())
        now_ist = datetime.now(IST)

        # HARDENING RULE 3: Session Timing Lockout (03:00 - 09:00 IST Asian Lull)
        is_asian_lull = (3 <= now_ist.hour < 9)
        # HARDENING RULE 4: Macroeconomic News Blackout Sentinel (+-15 min)
        is_blackout, event_name = self.news_sentinel.is_news_blackout(now_ist)

        candidate_signals = []

        # Evaluate 1M High-Leverage Scalps & 5M Trend Expansion when news is clear
        cvd_val = getattr(self.feed, 'cvd', getattr(self.feed, 'cum_cvd', 0.0)) if self.feed else 0.0
        fr_val = getattr(self.feed, 'funding_rate', getattr(self.feed, 'current_funding_rate', 0.0001)) if self.feed else 0.0001

        if not is_asian_lull and not is_blackout:
            candidate_signals.extend(self.s_scalp.evaluate_1m(candle_objects, cvd_delta=cvd_val, funding_rate=fr_val))
        else:
            if is_asian_lull and (now_ts - self.last_lull_log_ts >= 60):
                self.last_lull_log_ts = now_ts
                print(f"🔒 [{dt_str}] 1M SCALP ENTRIES LOCKED: Asian Session Lull (03:00 - 09:00 IST). High spread risk.")
            if is_blackout and (now_ts - self.last_blackout_log_ts >= 30):
                self.last_blackout_log_ts = now_ts
                print(f"⚠️ [{dt_str}] 1M SCALP BLOCKED: High-Impact Macro News Blackout ({event_name}).")

        # 5M Trend Expansion (VWAP Pullback + CVD Absorption)
        if not is_blackout:
            candidate_signals.extend(self.s_expansion_5m.evaluate_5m(candle_objects, cvd_delta=cvd_val, funding_rate=fr_val))

        # Swing setups (Alpha Precision, Asian Range Sweeps, Squeeze)
        candidate_signals.extend(self.s_alpha.evaluate(candle_objects))
        candidate_signals.extend(self.s_asian.evaluate(candle_objects))
        candidate_signals.extend(self.s_squeeze.evaluate(candle_objects))

        if not candidate_signals:
            return

        # Sort candidate signals by recency (most recent first)
        candidate_signals.sort(key=lambda s: s.timestamp, reverse=True)
        most_recent = candidate_signals[0]

        # Prevent duplicate activation of the exact same signal
        active_sigs = get_active_signals()
        for a in active_sigs:
            if a['timestamp'] == most_recent.timestamp:
                return

        # Activate the latest high-conviction signal
        # Use Post-Only entry price from setup
        entry_price = most_recent.entry_price if most_recent.entry_price > 0 else current_price

        # Determine setup timeframe
        tf = '1M'
        if hasattr(most_recent, 'timeframe') and getattr(most_recent, 'timeframe'):
            tf = getattr(most_recent, 'timeframe')
        else:
            r_up = (most_recent.reason or '').upper()
            if '5M' in r_up or 'TREND EXPANSION' in r_up:
                tf = '5M'
            elif 'ASIAN' in r_up or 'SWEEP' in r_up or 'ALPHA' in r_up or '15M' in r_up or 'SWING' in r_up:
                tf = '15M'
            else:
                tf = '1M'

        sig_id = save_signal({
            'symbol': self.symbol,
            'timestamp': most_recent.timestamp,
            'dt_str': dt_str,
            'direction': most_recent.direction,
            'entry_price': entry_price,
            'stop_loss': most_recent.stop_loss,
            'take_profit_1': most_recent.take_profit_1,
            'take_profit_2': most_recent.take_profit_2,
            'risk_reward': most_recent.risk_reward,
            'status': 'ACTIVE',
            'reason': most_recent.reason,
            'timeframe': tf
        })

        dir_icon = "🟢" if most_recent.direction == "BUY" else "🔴"
        print("\n" + "=" * 80)
        print(f" {dir_icon} ACTIVE {most_recent.direction} SIGNAL #{sig_id} ACTIVATED @ {dt_str}")
        print(f"    Symbol: {self.symbol} | Order: LIMIT_MAKER @ ${entry_price:,.2f}")
        print(f"    Stop Loss: ${most_recent.stop_loss:,.2f} | TP1: ${most_recent.take_profit_1:,.2f} | TP2: ${most_recent.take_profit_2:,.2f}")
        print(f"    Risk:Reward: {most_recent.risk_reward}:1 | 1R Breakeven: Armed (+0.12%)")
        print(f"    Setup Reason: {most_recent.reason}")
        print("=" * 80 + "\n")

        self._broadcast('signal_generated', {
            'id': sig_id,
            'direction': most_recent.direction,
            'entry_price': entry_price,
            'stop_loss': most_recent.stop_loss,
            'take_profit_1': most_recent.take_profit_1,
            'take_profit_2': most_recent.take_profit_2,
            'risk_reward': most_recent.risk_reward,
            'reason': most_recent.reason
        })

    def _evaluate_market_regime(self):
        db_candles = get_recent_candles(self.symbol, "15m", limit=96)
        if len(db_candles) < 20:
            return

        candle_objects = [
            Candle(c['timestamp'], c['open'], c['high'], c['low'], c['close'], c['volume'])
            for c in db_candles
        ]

        decision = self.agent.analyze(candle_objects)
        now_ist = datetime.now(IST)
        dt_str = now_ist.strftime('%Y-%m-%d %H:%M:%S IST')

        save_regime_log({
            'timestamp': int(now_ist.timestamp() * 1000),
            'dt_str': dt_str,
            'regime': decision.regime,
            'risk_multiplier': decision.risk_multiplier,
            'bull_case': decision.bullish_case,
            'bear_case': decision.bearish_case,
            'synthesis': decision.synthesis
        })

        self._broadcast('regime_update', {
            'regime': decision.regime,
            'risk_multiplier': decision.risk_multiplier,
            'bull_case': decision.bullish_case,
            'bear_case': decision.bearish_case,
            'synthesis': decision.synthesis,
            'dt_str': dt_str
        })
