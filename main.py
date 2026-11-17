"""Bitcoin Intraday Engine Runner & Performance Evaluation.

Compares individual setups vs. the Agentic Regime-Filtered Portfolio.
"""

from btc_engine.synthetic_data import generate_btc_intraday_data
from btc_engine.setups.asian_sweep import AsianRangeSweepStrategy
from btc_engine.setups.vwap_bands import VWAPMeanReversionStrategy
from btc_engine.setups.volatility_squeeze import VolatilitySqueezeStrategy
from btc_engine.setups.htf_trend_sweep import TrendAlignedAsianSweepStrategy
from btc_engine.setups.alpha_precision_strategy import AlphaPrecisionStrategy
from btc_engine.agent.market_regime_agent import MarketRegimeAgent
from btc_engine.backtester import IntradayBacktester


def run_benchmark():
    print("=" * 82)
    print(" 🚀 BITCOIN (BTC/USD) INTRADAY BENCHMARK & ALPHA PRECISION EVALUATION")
    print("=" * 82)

    # 1. Generate 30 days of authentic 15m BTC market data (2,880 candles)
    print("\n[1/4] Generating 30 days of 15-minute Bitcoin intraday market data...")
    candles = generate_btc_intraday_data(days=30, start_price=92500.0, seed=101)
    print(f"      Loaded {len(candles):,} candles from {candles[0].dt.strftime('%Y-%m-%d')} to {candles[-1].dt.strftime('%Y-%m-%d')}.")

    # 2. Instantiate strategies & backtester
    backtester = IntradayBacktester(fee_rate=0.0005, slippage_rate=0.0002)
    s_asian = AsianRangeSweepStrategy(min_rr=2.0)
    s_htf_sweep = TrendAlignedAsianSweepStrategy(htf_ema_period=40, min_rr=2.5, volume_threshold=1.1)
    s_alpha = AlphaPrecisionStrategy(htf_ema_period=40, min_rr=2.5)
    s_vwap = VWAPMeanReversionStrategy(min_rr=1.8)
    s_squeeze = VolatilitySqueezeStrategy(min_rr=2.0)
    agent = MarketRegimeAgent()

    # 3. Evaluate Individual Setups
    print("\n[2/4] Evaluating individual setups...")

    res_asian = backtester.simulate(candles, s_asian.evaluate(candles))
    res_htf = backtester.simulate(candles, s_htf_sweep.evaluate(candles))
    res_alpha = backtester.simulate(candles, s_alpha.evaluate(candles))
    res_vwap = backtester.simulate(candles, s_vwap.evaluate(candles))
    res_squeeze = backtester.simulate(candles, s_squeeze.evaluate(candles))

    # 4. Evaluate Agentic Regime-Orchestrated System
    print("\n[3/4] Running Agentic Meta-Orchestrator with Alpha Precision Filters...")
    agentic_signals = []

    candles_by_day = {}
    for c in candles:
        d = c.dt.strftime('%Y-%m-%d')
        if d not in candles_by_day:
            candles_by_day[d] = []
        candles_by_day[d].append(c)

    cumulative_candles = []
    for d, day_candles in candles_by_day.items():
        cumulative_candles.extend(day_candles)
        if len(cumulative_candles) < 30:
            continue

        decision = agent.analyze(cumulative_candles[-96:])

        candidate_signals = []
        if decision.regime == "TRENDING_EXPANSION":
            candidate_signals.extend(s_alpha.evaluate(day_candles))
            candidate_signals.extend(s_squeeze.evaluate(day_candles))
        elif decision.regime == "RANGE_CONSOLIDATION":
            candidate_signals.extend(s_alpha.evaluate(day_candles))
            candidate_signals.extend(s_asian.evaluate(day_candles))

        agentic_signals.extend(candidate_signals)

    res_agentic = backtester.simulate(candles, agentic_signals)

    # 5. Display Performance Comparison Table
    print("\n[4/4] PERFORMANCE COMPARISON RESULTS")
    print("-" * 82)
    headers = f"{'Strategy / System':<35} | {'Trades':<7} | {'Win %':<7} | {'Profit Factor':<13} | {'Net PnL %':<10} | {'Max DD %':<8}"
    print(headers)
    print("-" * 82)

    def print_row(name, res):
        print(f"{name:<35} | {res['total_trades']:<7} | {res['win_rate']:<6}% | {res['profit_factor']:<13} | {res['net_pnl_pct']:>+8.2f}% | {res['max_drawdown_pct']:<7.2f}%")

    print_row("1. Raw Asian Range Sweep", res_asian)
    print_row("2. HTF Trend-Aligned Sweep", res_htf)
    print_row("3. Alpha Precision (CVD + Funding)", res_alpha)
    print_row("4. Raw VWAP Mean Reversion", res_vwap)
    print_row("5. Volatility Squeeze (TTM)", res_squeeze)
    print("-" * 82)
    print_row("🌟 AGENTIC HTF + CVD ORCHESTRATED", res_agentic)
    print("=" * 82)

    # Print Sample Trades from Agentic HTF System
    print("\n📋 SAMPLE RECENT HIGH-PRECISION TRADES:")
    sample_trades = res_agentic['trades'][-5:] if res_agentic['trades'] else []
    for idx, t in enumerate(sample_trades, 1):
        status_icon = "✅" if t.outcome != "LOSS" else "❌"
        print(f" {idx}. {status_icon} [{t.entry_time}] {t.direction} @ ${t.entry_price:,.1f} -> Exit @ ${t.exit_price:,.1f}")
        print(f"    Outcome: {t.outcome} ({t.pnl_pct:+.2f}%) | Setup: {t.reason}")

    print("\n" + "=" * 82)


if __name__ == "__main__":
    run_benchmark()
