# 🚀 India Day Trader & Multi-Asset Intraday Trading Terminal

An institutional-grade, real-time algorithmic trading terminal and execution engine engineered for high-precision intraday trading across **Indian Derivatives (NIFTY 50 Options)**, **Cryptocurrency (Bitcoin BTC/USD)**, and **Commodities (Spot Gold XAU/USD)**.

Built with high-frequency micro-structure orderflow analysis, Smart Money Concepts (SMC), dynamic multi-timeframe strategy execution, Sensibull-style Option Greeks optimization, live currency conversion (USD/INR), and automated risk management.

---

## 📸 Key Features at a Glance

* **Multi-Market Unified Engine**:
  * 🇮🇳 **NIFTY 50 (NSE F&O Derivatives)**: Real-time option contract selector with weekly expiry, Central Pivot Range (CPR), Options PCR (Put-Call Ratio), Call/Put Institutional Strike Walls, and strict 03:15 PM IST auto-square-off sentinel.
  * ₿ **Bitcoin (BTC/USD)**: 24/7 continuous crypto engine, perpetual funding rate monitoring, Cumulative Volume Delta (CVD) absorption, and 100x leverage risk modeling.
  * 🥇 **Spot Gold (XAU/USD)**: 24/5 bullion trading, London/NY peak session tracking, US Dollar Index (DXY) macro correlation, and ounce/lot sizing.

* **🎯 Dedicated NIFTY 50 Intraday Options Intelligence Terminal (Replaces TradingView)**:
  * **AI-Recommended Option Contract to Buy**: Directly identifies whether to buy Call (CE) or Put (PE) options based on live signal confluence, complete with active Weekly Expiry (e.g. `NIFTY 26-NOV-2026 24,100 CE`).
  * **Option Greeks & Sensibull-Style Strike Ladder**: Compares **ITM (In-The-Money, Delta ~0.68)**, **ATM (At-The-Money, Delta ~0.51)**, and **OTM (Out-of-The-Money, Delta ~0.31)**. Emphasizes ITM options to overcome Theta time decay and maximize delta capture.
  * **Exact Premium Execution Levels**: Real-time Option Entry LTP (ticks live with Nifty spot moves via Delta), protective Stop Loss (SL), 1R Breakeven lock, and Take Profit (TP2) in option points and rupees.
  * **Institutional Open Interest (OI) Heatmap**: Live 5-strike ladder around ATM displaying Call OI (Resistance Ceiling), Put OI (Demand Floor), Put-Call Ratio (PCR 1.14), and Max Pain Strike.

* **Universal 3-Mode Strategy Engine (Independent per Timeframe)**:
  * ⚡ **1M Scalp**: Micro-structure Fair Value Gap (FVG) equilibrium retests + CVD delta absorption + automated 1R Breakeven trailing stop.
  * 🎯 **5M Trend Expansion**: Dynamic ATR volatility expansion bands + 20/50 EMA ribbon alignment + momentum breakout continuation.
  * 📊 **15M Intraday Swing**: Smart Money Concepts (SMC) + Asian Session High/Low (ASH/ASL) liquidity sweeps + CPR/VWAP institutional reclaim.
  * *Completely isolated signals and audit logs per timeframe*: Switching between 1M, 5M, and 15M displays timeframe-specific trades, entry times, and execution parameters.

* **Real-Time Interactive TradingView Charting (BTC & GOLD)**:
  * Seamless live candlestick chart with customizable intervals (`1m`, `3m`, `5m`, `15m`, `1h`).
  * Pre-loaded with Moving Averages (`MASimple`) and Anchored VWAP (`VWAP`).
  * Real-time tick streams (`BINANCE:BTCUSDT` for Crypto, `OANDA:XAUUSD` for Gold).

* **Live Dynamic Capital & Margin Risk Calculator**:
  * Real-time **Live USD to INR FX conversion**.
  * User-adjustable **Capital (INR)**, **Leverage Ratio (1x – 1000x)**, and **Lot Sizing**.
  * Instant recalculation of required margin, position notional, stop-loss risk in INR, and profit targets.
  * Transparent **Return on Margin (RoM % @ Leverage)**: Dynamic recalculation of leveraged returns (`Price Change % × Leverage`) across both the active banner and closed trades audit trail.

* **Automated Audit Trail & Trades Journal**:
  * Thread-safe **SQLite database** (`data/intraday.db`).
  * Live signals feed and closed trades audit trail recording entry, exit, win rate, profit factor, and realized PnL.
  * Clear trade outcome badges: `🎯 HIT TP` (Target Reached), `🛡️ 1R BE EXIT` (1R Trailed Breakeven Safe Exit), and `❌ SL HIT` (Protective Stop Loss Hit).
  * High-precision IST timestamps: Signals display their exact generation time in Indian Standard Time (`HH:MM:SS IST`).

* **Zero External Dependencies**:
  * Runs entirely on **Python 3.8+ Standard Library** (`http.server`, `socketserver`, `sqlite3`, `threading`, `urllib`). No bloated packages required!

---

## 🏛️ System Architecture

```
IntradayTrade/
├── run.py                     # Single-command terminal launcher (DB + Engines + Web Server)
├── backend/
│   ├── server.py              # Multi-threaded HTTP & Server-Sent Events (SSE) streaming server
│   ├── multi_asset_manager.py # Unified orchestrator coordinating BTC, Gold, and Nifty engines
│   ├── live_engine.py         # Background event loop & trade lifecycle management
│   ├── live_feed.py           # Real-time WebSocket/REST exchange price feeds
│   └── database/
│       └── db.py              # SQLite schema, tables (candles, signals, trades), and thread-safe locking
├── btc_engine/                # Bitcoin Strategy Core
│   ├── indicators.py          # Anchored VWAP, ATR, EMA bands, FVG detection
│   ├── orderflow.py           # CVD Delta & Perpetual Funding Rate sentiment
│   ├── setups/
│   │   ├── alpha_precision_strategy.py  # 15M Swing Asian Sweep + CVD Absorption
│   │   ├── trend_expansion_5m.py        # 5M Volatility Breakout & ATR Expansion
│   │   ├── asian_sweep.py               # SMC Liquidity Sweeps
│   │   └── volatility_squeeze.py        # TTM Squeeze Breakouts
│   └── agent/
│       └── market_regime_agent.py       # Market regime classification (Bull/Bear/Chop)
├── indian_engine/             # Indian Market Core (NIFTY 50 Options & Derivatives)
│   ├── cpr.py                 # Central Pivot Range (CPR TC/BC/Pivot) indicator
│   ├── options_data.py        # Real-time PCR, Call Wall, Put Wall, Max Pain engine
│   └── setups/
│       ├── nifty_trend_expansion_5m.py  # 5M Nifty ATR Trend Expansion
│       └── orb_cpr_strategy.py          # 15M Opening Range Breakout (ORB) + CPR Pivots
├── gold_engine/               # Spot Gold Core (XAU/USD)
│   └── setups/
│       └── gold_trend_expansion_5m.py   # 5M Gold Bullion Expansion Strategy
├── frontend/                  # Dashboard & User Interface
│   ├── index.html             # Full real-time responsive dashboard UI
│   ├── css/styles.css         # Dark institutional finance theme
│   └── js/
│       ├── app.js             # SSE state management & frontend controller
│       ├── live_chart.js      # High-performance HTML5 Canvas chart
│       └── cvd_chart.js       # Live CVD orderflow area visualizer
├── ui/                        # Synchronized UI mirror
│   └── dashboard.html         # Standalone distribution dashboard
└── data/                      # Local database directory (SQLite)
    └── intraday.db            # Persistent database holding signals and trade logs
```

---

## ⚡ Quick Start: Running on Local Machine

### 1. Prerequisites
Ensure you have **Python 3.8** or newer installed:
```bash
python3 --version
```

### 2. Clone the Repository
```bash
git clone https://github.com/psoni207/india_day_trader.git
cd india_day_trader
```

### 3. Launch the System
No virtual environment or third-party pip packages are required. Simply launch using:
```bash
python3 run.py
```

You will see the startup sequence in your terminal:
```
======================================================================
🚀 MULTI-ASSET INTRADAY TRADING ENGINE STARTING
======================================================================
[INFO] SQLite Database initialized at data/intraday.db
[INFO] Bitcoin Engine active (24/7 Perpetual)
[INFO] Indian Equities & Options Engine active (NIFTY 50 / NSE F&O)
[INFO] Gold Bullion Engine active (XAU/USD Spot)
[INFO] Real-Time Web Server listening on http://localhost:8080
======================================================================
```

### 4. Open the Web Dashboard
Open your favorite browser and visit:
👉 **[http://localhost:8080](http://localhost:8080)**

---

## 🕹️ Dashboard Usage Guide

1. **Market Selector Tabs (Top Navigation Bar)**:
   * Click **`₿ BITCOIN (BTC/USD)`**: Displays crypto candlestick chart, CVD delta, funding rates, and 24/7 perpetual execution.
   * Click **`🇮🇳 NIFTY 50 (NSE)`**: Opens the dedicated **Nifty Options Intelligence Terminal**, showing weekly option contracts to buy, Delta strike ladders, and Open Interest heatmaps.
   * Click **`🥇 GOLD (XAU/USD)`**: Displays bullion candlestick chart, US Dollar Index (DXY) tailwind, and ounce-based contract sizing.

2. **Universal 3-Strategy Switcher**:
   * **`⚡ 1M SCALP`**: 1-minute orderflow scalp, Fair Value Gap (FVG) retests, 1R Breakeven trailing stop.
   * **`🎯 5M TREND EXPANSION`**: 5-minute volatility breakout, 20/50 EMA ribbon pullbacks, ATR expansion.
   * **`📊 15M INTRADAY SWING`**: 15-minute multi-hour swing, Asian High/Low sweeps, London/NY session momentum.

3. **NIFTY 50 Options Trade Execution**:
   * **Recommended Contract**: Check the primary recommendation card for whether to buy **Call (CE)** or **Put (PE)** options, the exact strike (e.g. `24,100 CE`), and the current Weekly Expiry date.
   * **Option Strike Ladder**: Click between **`★ ITM (Delta 0.68)`**, **`⚡ ATM (Delta 0.51)`**, and **`⚠️ OTM (Delta 0.31)`** to immediately adjust your strike and execution levels.
   * **Live Premium Simulation**: Option premiums update in real time with Nifty spot movements using Option Delta ($\Delta$).

4. **Dynamic Risk, Leverage & Lot Sizing**:
   * Change **Lot Size**: Sizing updates instantly across execution tickets, required capital, and closed trade audit trails (e.g. `0.05 BTC`, `1 Lot / 25 Qty NIFTY`, `0.02 Lots / 2 oz GOLD`).
   * Change **Leverage (1x – 1000x)**: The terminal instantly recalculates the Required Margin, Buying Power, and Return on Margin (`RoM % @ Leverage`).

---

## 🛡️ Risk Management & Strategy Rules

| Strategy | Timeframe | Asset Setup | Stop Loss Logic | Take Profit Targets | Risk/Reward |
| :--- | :---: | :--- | :--- | :--- | :---: |
| **Micro Scalp** | `1m` | 50% FVG Retest + CVD Absorption | 1R Breakeven Trailing (+spread buffer) | TP1: +0.25%, TP2: +0.40% | 1 : 2.5 |
| **Trend Expansion** | `5m` | Volatility Band Breakout + 20/50 EMA | Trailing ATR Volatility Band (1.5x ATR) | TP1: +0.60%, TP2: +1.20% | 1 : 2.8 |
| **Intraday Swing**| `15m` | Asian Range Sweep (ASH/ASL) + VWAP | Key Swing High / Swing Low | TP1: 1R Safe, TP2: Opposite Range | 1 : 3.5+ |
| **Nifty Option Buyer**| `1m/5m/15m` | In-The-Money (Delta 0.65-0.75) CE/PE | Dynamic -18 to -32 pts in Option Premium | TP1: +1R BE Lock, TP2: +45 to +85 pts | 1 : 2.2+ |

---

## 🗄️ Database Management (`data/intraday.db`)

The thread-safe SQLite database is managed automatically by `backend/database/db.py`:
* **`candles`**: Stores historical OHLCV and Cumulative Volume Delta data.
* **`signals`**: Real-time signal records with entry prices, SL, TP, timeframe (`1M`, `5M`, `15M`), timestamps in IST, and status (`ACTIVE`, `HIT TP`, `STOPPED_OUT`).
* **`trades`**: Completed trade journal recording realized PnL, lot sizing, timeframe, and holding durations.

To query trade logs via terminal:
```bash
sqlite3 data/intraday.db "SELECT id, symbol, timeframe, direction, entry_price, exit_price, pnl_pct, outcome FROM trades ORDER BY id DESC LIMIT 10;"
```

To query active signals:
```bash
sqlite3 data/intraday.db "SELECT id, symbol, timeframe, direction, entry_price, status, dt_str FROM signals WHERE status = 'ACTIVE';"
```

---

## 🤝 Contributing

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/OptionsExecution`)
3. Commit your Changes (`git commit -m 'feat: Add Nifty options intelligence module'`)
4. Push to the Branch (`git push origin feature/OptionsExecution`)
5. Open a Pull Request

---

## ⚖️ License & Disclaimer

Distributed under the MIT License. 

**Disclaimer:** *This software is designed for algorithmic research, backtesting, and quantitative trading automation. Intraday trading in options, equities, and cryptocurrencies involves substantial risk of financial loss. Ensure you thoroughly test all strategies with paper trading before deploying live capital.*
