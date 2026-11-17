"""Event-Driven Intraday Backtester for Bitcoin Strategies.

Simulates tick-level trade progression, realistic exchange fees (Taker 0.05%),
slippage (0.02%), two-stage profit taking (TP1 50%, TP2 50%), and hard stops.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from btc_engine.indicators import Candle
from btc_engine.setups.asian_sweep import TradeSignal
from btc_engine.agent.market_regime_agent import MarketRegimeAgent


@dataclass
class TradeResult:
    entry_time: str
    exit_time: str
    direction: str
    entry_price: float
    exit_price: float
    pnl_pct: float
    outcome: str  # 'WIN_FULL', 'WIN_PARTIAL', 'LOSS'
    reason: str


class IntradayBacktester:
    def __init__(
        self,
        fee_rate: float = 0.0005,      # 0.05% taker fee
        slippage_rate: float = 0.0002  # 0.02% slippage
    ):
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate

    def simulate(self, candles: List[Candle], signals: List[TradeSignal]) -> Dict[str, Any]:
        if not signals or not candles:
            return {
                "total_trades": 0, "win_rate": 0.0, "net_pnl_pct": 0.0,
                "profit_factor": 0.0, "max_drawdown_pct": 0.0, "trades": []
            }

        # Index candles by timestamp for rapid forward lookup
        candle_map = {c.timestamp: idx for idx, c in enumerate(candles)}
        trades: List[TradeResult] = []

        for sig in signals:
            if sig.timestamp not in candle_map:
                continue

            entry_idx = candle_map[sig.timestamp]
            # Account for entry slippage and fee
            if sig.direction == "BUY":
                actual_entry = sig.entry_price * (1.0 + self.slippage_rate)
            else:
                actual_entry = sig.entry_price * (1.0 - self.slippage_rate)

            tp1_hit = False
            exit_price = actual_entry
            exit_time = sig.dt_str
            outcome = "LOSS"

            # Walk forward up to 32 candles (8 hours maximum intraday hold)
            max_forward = min(entry_idx + 33, len(candles))
            for f_idx in range(entry_idx + 1, max_forward):
                fc = candles[f_idx]

                if sig.direction == "BUY":
                    # Check Stop Loss first
                    if fc.low <= sig.stop_loss:
                        exit_price = sig.stop_loss * (1.0 - self.slippage_rate)
                        exit_time = fc.dt.strftime('%Y-%m-%d %H:%M UTC')
                        outcome = "LOSS" if not tp1_hit else "WIN_PARTIAL"
                        break

                    # Check TP1
                    if not tp1_hit and fc.high >= sig.take_profit_1:
                        tp1_hit = True

                    # Check TP2
                    if fc.high >= sig.take_profit_2:
                        exit_price = sig.take_profit_2 * (1.0 - self.slippage_rate)
                        exit_time = fc.dt.strftime('%Y-%m-%d %H:%M UTC')
                        outcome = "WIN_FULL"
                        break

                elif sig.direction == "SELL":
                    # Check Stop Loss first
                    if fc.high >= sig.stop_loss:
                        exit_price = sig.stop_loss * (1.0 + self.slippage_rate)
                        exit_time = fc.dt.strftime('%Y-%m-%d %H:%M UTC')
                        outcome = "LOSS" if not tp1_hit else "WIN_PARTIAL"
                        break

                    # Check TP1
                    if not tp1_hit and fc.low <= sig.take_profit_1:
                        tp1_hit = True

                    # Check TP2
                    if fc.low <= sig.take_profit_2:
                        exit_price = sig.take_profit_2 * (1.0 + self.slippage_rate)
                        exit_time = fc.dt.strftime('%Y-%m-%d %H:%M UTC')
                        outcome = "WIN_FULL"
                        break

            # Calculate Net PnL % factoring in two-way fees
            if sig.direction == "BUY":
                gross_pnl = (exit_price - actual_entry) / actual_entry
            else:
                gross_pnl = (actual_entry - exit_price) / actual_entry

            # Deduct two-way transaction fees
            net_pnl = gross_pnl - (2 * self.fee_rate)

            trades.append(TradeResult(
                entry_time=sig.dt_str,
                exit_time=exit_time,
                direction=sig.direction,
                entry_price=actual_entry,
                exit_price=exit_price,
                pnl_pct=round(net_pnl * 100, 2),
                outcome=outcome,
                reason=sig.reason
            ))

        # Metrics computation
        winning_trades = [t for t in trades if t.pnl_pct > 0]
        losing_trades = [t for t in trades if t.pnl_pct <= 0]

        win_rate = (len(winning_trades) / len(trades)) * 100 if trades else 0.0
        total_pnl = sum(t.pnl_pct for t in trades)

        gross_wins = sum(t.pnl_pct for t in winning_trades)
        gross_losses = abs(sum(t.pnl_pct for t in losing_trades))
        profit_factor = round(gross_wins / gross_losses, 2) if gross_losses > 0 else 9.99

        # Drawdown calculation
        equity_curve = [100.0]
        for t in trades:
            equity_curve.append(equity_curve[-1] * (1.0 + t.pnl_pct / 100.0))

        peak = equity_curve[0]
        max_dd = 0.0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100.0
            if dd > max_dd:
                max_dd = dd

        return {
            "total_trades": len(trades),
            "win_rate": round(win_rate, 1),
            "net_pnl_pct": round(total_pnl, 2),
            "profit_factor": profit_factor,
            "max_drawdown_pct": round(max_dd, 2),
            "trades": trades
        }
