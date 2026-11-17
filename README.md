# 🚀 India Day Trader & Multi-Asset Intraday Trading Terminal

An institutional-grade, real-time algorithmic trading terminal and execution engine engineered for high-precision intraday trading across **Indian Equities (NIFTY 50)**, **Cryptocurrency (Bitcoin BTC/USD)**, and **Commodities (Spot Gold XAU/USD)**.

Built with high-frequency micro-structure orderflow analysis, Smart Money Concepts (SMC), dynamic multi-timeframe strategy execution, live currency conversion (USD/INR), and automated risk management.

---

## 📸 Key Features at a Glance

* **Multi-Market Unified Engine**:
  * 🇮🇳 **NIFTY 50 (NSE/BSE)**: Indian market session (09:15 – 15:15 IST), Central Pivot Range (CPR), Options PCR sentiment, and dynamic lot sizing.
  * ₿ **Bitcoin (BTC/USD)**: 24/7 continuous crypto engine, perpetual funding rate monitoring, Cumulative Volume Delta (CVD) absorption, and 100x leverage risk modeling.
  * 🥇 **Spot Gold (XAU/USD)**: 24/5 bullion trading, London/NY peak session tracking, US Dollar Index (DXY) macro correlation, and ounce/lot sizing.
* **Universal 3-Mode Strategy Engine (Available on All Assets)**:
  * ⚡ **1M Scalp**: Micro-structure Fair Value Gap (FVG) equilibrium retests + CVD delta absorption + automated 1R Breakeven trailing stop.
  * 🎯 **5M Trend Expansion**: Dynamic ATR volatility expansion bands + multi-timeframe EMA trend alignment + momentum breakout continuation.
  * 📊 **15M Intraday Swing**: Smart Money Concepts (SMC) + Asian Session High/Low (ASH/ASL) liquidity sweeps + CPR/VWAP institutional reclaim.
* **Real-Time Interactive TradingView Charting**:
  * Seamless live candlestick chart with customizable intervals (`1m`, `3m`, `5m`, `15m`, `1h`).
  * Pre-loaded with Moving Averages (`MASimple`) and Anchored VWAP (`VWAP`).
  * Unrestricted, zero-popup feed routing (`AMEX:INDA` & `NASDAQ:INDY` for India proxy, `BINANCE:BTCUSDT` for Crypto, `OANDA:XAUUSD` for Gold).
* **Live Dynamic Capital & Margin Risk Calculator**:
  * Real-time **Live USD to INR FX conversion**.
  * User-adjustable **Capital (INR)**, **Leverage Ratio (1x – 500x)**, and **Lot Sizing**.
  * Instant recalculation of required margin, position notional, stop-loss risk in INR, and profit targets.
* **Automated Audit Trail & Trades Journal**:
  * Thread-safe **SQLite database** (`data/intraday.db`).
  * Real-time signal feed and closed trades audit trail recording entry, exit, win rate, profit factor, and realized PnL.
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
├── indian_engine/             # Indian Market Core (NIFTY 50 / Sensex)
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
    └── .gitkeep               # Directory placeholder
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
[INFO] Indian Equities Engine active (NIFTY 50 / NSE)
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
   * Click **`₿ BITCOIN (BTC/USD)`**: Loads crypto live stream, CVD delta, and 24/7 perpetual parameters.
   * Click **`🇮🇳 NIFTY 50 (NSE)`**: Switches to Indian equities, displays Central Pivot Range (CPR), Options PCR, and hides USD FX fields.
   * Click **`🥇 GOLD (XAU/USD)`**: Switches to Gold bullion, displays US Dollar (DXY) tailwind, and ounce-based contract sizing.

2. **Universal 3-Strategy Switcher**:
   * **`⚡ 1M SCALP`**: 1-minute chart, 50% FVG maker limit entries, 1R Breakeven trailing stop.
   * **`🎯 5M TREND EXPANSION`**: 5-minute chart, dynamic ATR expansion channels, breakout continuation.
   * **`📊 15M INTRADAY SWING`**: 15-minute chart, Asian Session High/Low sweeps, VWAP reclaims.

3. **Interactive Risk & Sizing Controls**:
   * Change **Amount (INR)** or **Leverage**: The terminal automatically recalculates your required margin, position value in USD, and maximum allowable risk per trade.
   * Change **Lot Size**: Sizing updates instantly across all execution badges and active position cards (e.g., `0.05 BTC`, `1 Lot / 25 Qty NIFTY`, `0.02 Lots / 2 oz GOLD`).

4. **Interactive Charting Toolbar**:
   * Toggle between **`1m`**, **`3m`**, **`5m`**, **`15m`**, and **`1h`** candlestick intervals.
   * On the NIFTY tab, switch between **`INDIA ETF (INDA)`**, **`INDIA 50 (INDY)`**, or click **`↗ NSE NIFTY`** to view the official NSE cash index on TradingView.

---

## 🛡️ Risk Management & Strategy Rules

| Strategy | Timeframe | Entry Trigger | Stop Loss Logic | Take Profit Targets | Risk/Reward |
| :--- | :---: | :--- | :--- | :--- | :---: |
| **Micro Scalp** | `1m` | 50% FVG Retest + CVD Absorption | 1R Breakeven Trailing (+broker spread buffer) | TP1: +0.25%, TP2: +0.40% | 1 : 2.5 |
| **Trend Expansion** | `5m` | Volatility Band Breakout + EMA Trend Align | Trailing ATR Volatility Band (1.5x ATR) | TP1: +0.60%, TP2: +1.20% | 1 : 2.8 |
| **Intraday Swing**| `15m` | Asian Range Sweep (ASH/ASL) + VWAP Reclaim | Key Swing High / Swing Low | TP1: 1R Safe, TP2: Opposite Range | 1 : 3.5+ |

---

## 🗄️ Database Management (`data/intraday.db`)

The SQLite database is managed automatically by `backend/database/db.py`:
* **`candles`**: Stores historical OHLCV and Cumulative Volume Delta data.
* **`signals`**: Real-time signal records with entry prices, SL, TP, timestamps in IST, and status (`ACTIVE`, `HIT TP`, `STOPPED_OUT`).
* **`trades`**: Completed trade journal recording realized PnL, lot sizing, and holding durations.

To query trade logs via terminal:
```bash
sqlite3 data/intraday.db "SELECT dt_str, symbol, type, entry_price, exit_price, pnl_pct FROM trades ORDER BY id DESC LIMIT 10;"
```

---

## 🤝 Contributing

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AdvancedExecution`)
3. Commit your Changes (`git commit -m 'feat: Add multi-exchange execution module'`)
4. Push to the Branch (`git push origin feature/AdvancedExecution`)
5. Open a Pull Request

---

## ⚖️ License & Disclaimer

Distributed under the MIT License. 

**Disclaimer:** *This software is designed for algorithmic research, backtesting, and quantitative trading automation. Intraday trading in derivatives, equities, and cryptocurrencies involves substantial risk of financial loss. Ensure you thoroughly test all strategies with paper trading before deploying capital.*
