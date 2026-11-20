"""SQLite Database Management for Intraday Trading System.

Maintains historical candles, real-time generated signals, active/closed trades,
and Agentic Market Regime logs.
"""

import sqlite3
import os
import threading
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "intraday.db")
_lock = threading.Lock()


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS candles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            dt_str TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            cvd REAL DEFAULT 0.0,
            UNIQUE(symbol, timeframe, timestamp)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            dt_str TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL NOT NULL,
            stop_loss REAL NOT NULL,
            take_profit_1 REAL NOT NULL,
            take_profit_2 REAL NOT NULL,
            risk_reward REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            reason TEXT NOT NULL,
            timeframe TEXT DEFAULT '1M',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_time TEXT NOT NULL,
            entry_price REAL NOT NULL,
            exit_time TEXT NOT NULL,
            exit_price REAL NOT NULL,
            pnl_pct REAL NOT NULL,
            outcome TEXT NOT NULL,
            reason TEXT NOT NULL,
            timeframe TEXT DEFAULT '1M',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        try:
            cursor.execute("ALTER TABLE signals ADD COLUMN timeframe TEXT DEFAULT '1M';")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE trades ADD COLUMN timeframe TEXT DEFAULT '1M';")
        except Exception:
            pass

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_regime_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            dt_str TEXT NOT NULL,
            regime TEXT NOT NULL,
            risk_multiplier REAL NOT NULL,
            bull_case TEXT NOT NULL,
            bear_case TEXT NOT NULL,
            synthesis TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        conn.commit()
        conn.close()


def save_candle(c: Dict[str, Any]):
    with _lock:
        conn = get_connection()
        try:
            conn.execute("""
            INSERT INTO candles (symbol, timeframe, timestamp, dt_str, open, high, low, close, volume, cvd)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, timeframe, timestamp) DO UPDATE SET
                high = max(candles.high, excluded.high),
                low = min(candles.low, excluded.low),
                close = excluded.close,
                volume = excluded.volume,
                cvd = excluded.cvd;
            """, (
                c['symbol'], c['timeframe'], c['timestamp'], c['dt_str'],
                c['open'], c['high'], c['low'], c['close'], c['volume'], c.get('cvd', 0.0)
            ))
            conn.commit()
        finally:
            conn.close()


def get_recent_candles(symbol: str = "BTCUSDT", timeframe: str = "15m", limit: int = 100) -> List[Dict[str, Any]]:
    with _lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT symbol, timeframe, timestamp, dt_str, open, high, low, close, volume, cvd
            FROM candles
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?;
            """, (symbol, timeframe, limit))
            rows = cursor.fetchall()
            results = [dict(r) for r in reversed(rows)]
            return results
        finally:
            conn.close()


def save_signal(sig: Dict[str, Any]) -> int:
    timeframe = sig.get('timeframe')
    if not timeframe:
        reason_upper = (sig.get('reason') or '').upper()
        if '5M' in reason_upper or 'TREND EXPANSION' in reason_upper:
            timeframe = '5M'
        elif 'ASIAN' in reason_upper or 'SWEEP' in reason_upper or 'ALPHA' in reason_upper or '15M' in reason_upper or 'SWING' in reason_upper:
            timeframe = '15M'
        else:
            timeframe = '1M'

    with _lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO signals (symbol, timestamp, dt_str, direction, entry_price, stop_loss, take_profit_1, take_profit_2, risk_reward, status, reason, timeframe)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                sig['symbol'], sig['timestamp'], sig['dt_str'], sig['direction'],
                sig['entry_price'], sig['stop_loss'], sig['take_profit_1'], sig['take_profit_2'],
                sig['risk_reward'], sig.get('status', 'ACTIVE'), sig['reason'], timeframe
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()


def update_signal_status(signal_id: int, status: str):
    with _lock:
        conn = get_connection()
        try:
            conn.execute("UPDATE signals SET status = ? WHERE id = ?;", (status, signal_id))
            conn.commit()
        finally:
            conn.close()


def update_signal_breakeven(signal_id: int, new_sl: float, note: str = ""):
    """Updates the Stop Loss to Breakeven (1R Rule) in SQLite."""
    with _lock:
        conn = get_connection()
        try:
            if note:
                conn.execute(
                    "UPDATE signals SET stop_loss = ?, reason = reason || ' | ' || ? WHERE id = ?;",
                    (new_sl, note, signal_id)
                )
            else:
                conn.execute("UPDATE signals SET stop_loss = ? WHERE id = ?;", (new_sl, signal_id))
            conn.commit()
        finally:
            conn.close()


def get_active_signals() -> List[Dict[str, Any]]:
    with _lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT *, coalesce(timeframe, '1M') as timeframe FROM signals WHERE status = 'ACTIVE' ORDER BY timestamp DESC;")
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()


def get_recent_signals(limit: int = 30) -> List[Dict[str, Any]]:
    with _lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT *, coalesce(timeframe, '1M') as timeframe FROM signals ORDER BY timestamp DESC LIMIT ?;", (limit,))
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()


def save_trade(t: Dict[str, Any]):
    timeframe = t.get('timeframe')
    if not timeframe:
        reason_upper = (t.get('reason') or '').upper()
        if '5M' in reason_upper or 'TREND EXPANSION' in reason_upper:
            timeframe = '5M'
        elif 'ASIAN' in reason_upper or 'SWEEP' in reason_upper or 'ALPHA' in reason_upper or '15M' in reason_upper or 'SWING' in reason_upper:
            timeframe = '15M'
        else:
            timeframe = '1M'

    with _lock:
        conn = get_connection()
        try:
            conn.execute("""
            INSERT INTO trades (signal_id, symbol, direction, entry_time, entry_price, exit_time, exit_price, pnl_pct, outcome, reason, timeframe)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                t.get('signal_id'), t['symbol'], t['direction'], t['entry_time'],
                t['entry_price'], t['exit_time'], t['exit_price'], t['pnl_pct'],
                t['outcome'], t['reason'], timeframe
            ))
            conn.commit()
        finally:
            conn.close()


def get_recent_trades(limit: int = 50) -> List[Dict[str, Any]]:
    with _lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT t.*, coalesce(t.timeframe, s.timeframe, '1M') as timeframe, coalesce(s.reason, t.reason) as signal_reason 
            FROM trades t 
            LEFT JOIN signals s ON t.signal_id = s.id 
            ORDER BY t.id DESC LIMIT ?;
            """, (limit,))
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()


def save_regime_log(r: Dict[str, Any]):
    with _lock:
        conn = get_connection()
        try:
            conn.execute("""
            INSERT INTO agent_regime_logs (timestamp, dt_str, regime, risk_multiplier, bull_case, bear_case, synthesis)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (
                r['timestamp'], r['dt_str'], r['regime'], r['risk_multiplier'],
                r['bull_case'], r['bear_case'], r['synthesis']
            ))
            conn.commit()
        finally:
            conn.close()


def get_latest_regime() -> Optional[Dict[str, Any]]:
    with _lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agent_regime_logs ORDER BY id DESC LIMIT 1;")
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def get_performance_summary() -> Dict[str, Any]:
    with _lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT pnl_pct, outcome FROM trades;")
            trades = cursor.fetchall()

            if not trades:
                return {
                    "total_trades": 0, "win_rate": 0.0, "net_pnl_pct": 0.0,
                    "profit_factor": 0.0, "active_positions": len(get_active_signals())
                }

            winning = [t['pnl_pct'] for t in trades if t['pnl_pct'] > 0]
            losing = [abs(t['pnl_pct']) for t in trades if t['pnl_pct'] <= 0]

            win_rate = (len(winning) / len(trades)) * 100.0
            net_pnl = sum(t['pnl_pct'] for t in trades)
            gross_win = sum(winning)
            gross_loss = sum(losing)
            pf = round(gross_win / gross_loss, 2) if gross_loss > 0 else (9.99 if gross_win > 0 else 0.0)

            return {
                "total_trades": len(trades),
                "win_rate": round(win_rate, 1),
                "net_pnl_pct": round(net_pnl, 2),
                "profit_factor": pf,
                "active_positions": len(get_active_signals())
            }
        finally:
            conn.close()
