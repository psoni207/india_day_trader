/**
 * Main Application Controller for Bitcoin Intraday Trading Dashboard.
 * Dual-Channel Architecture: Real-time Server-Sent Events (SSE) + 1-Second Polling Engine.
 */

class AppController {
  constructor() {
    this.liveChart = new LiveChart('tradingChart');
    this.cvdChart = new CVDChart('cvdChart');
    this.activeSignal = null;
    this.lastTickTime = Date.now();
    this.init();
  }

  async init() {
    console.log("🚀 Initializing Live Intraday Dashboard Controller...");
    await this.loadInitialData();
    this.startClock();
    this.startActivePolling();
    this.connectSSE();
  }

  startClock() {
    setInterval(() => {
      const now = new Date();
      const utcStr = now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
      const el = document.getElementById('clock-utc');
      if (el) el.innerText = utcStr;
    }, 1000);
  }

  /**
   * 1-Second Active Poller: Guarantees continuous live data updates
   * even if SSE is buffering or reconnecting.
   */
  startActivePolling() {
    // 1. Poll status & live price every 1 second
    setInterval(async () => {
      try {
        const res = await fetch('/api/status');
        if (res.ok) {
          const status = await res.json();
          this.updateFromStatus(status);
          this.markConnected(status.mode || 'LIVE (1s)');
        }
      } catch (e) {
        this.markConnecting();
      }
    }, 1000);

    // 2. Poll candles every 5 seconds to keep the chart synchronized
    setInterval(async () => {
      try {
        const res = await fetch('/api/candles?symbol=BTCUSDT&limit=70');
        if (res.ok) {
          const candles = await res.json();
          if (candles && candles.length > 0) {
            this.liveChart.setCandles(candles);
          }
        }
      } catch (e) {}
    }, 5000);

    // 3. Poll signals and trades every 3 seconds
    setInterval(async () => {
      try {
        const [resSig, resTrade] = await Promise.all([
          fetch('/api/signals'),
          fetch('/api/trades')
        ]);
        if (resSig.ok) {
          const signals = await resSig.json();
          this.renderSignalsTable(signals);
        }
        if (resTrade.ok) {
          const tradeData = await resTrade.json();
          this.renderTradesTable(tradeData.trades || []);
          this.updateMetrics(tradeData.summary || {});
        }
      } catch (e) {}
    }, 3000);
  }

  markConnected(modeLabel) {
    const pill = document.getElementById('connection-status');
    if (pill) {
      pill.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> 🟢 LIVE (1s) • ${modeLabel}`;
      pill.className = 'px-3 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5';
    }
  }

  markConnecting() {
    const pill = document.getElementById('connection-status');
    if (pill) {
      pill.innerHTML = '<span class="w-2 h-2 rounded-full bg-amber-400 animate-ping"></span> 🟡 SYNCING...';
      pill.className = 'px-3 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center gap-1.5';
    }
  }

  async loadInitialData() {
    try {
      const [resCandles, resStatus, resSignals, resTrades, resRegime] = await Promise.all([
        fetch('/api/candles?symbol=BTCUSDT&limit=70'),
        fetch('/api/status'),
        fetch('/api/signals'),
        fetch('/api/trades'),
        fetch('/api/regime')
      ]);

      if (resCandles.ok) {
        const candles = await resCandles.json();
        if (candles && candles.length > 0) {
          this.liveChart.setCandles(candles);
          candles.forEach(c => this.cvdChart.addCVDPoint(c.cvd || 0));
        }
      }

      if (resStatus.ok) {
        const status = await resStatus.json();
        this.updateFromStatus(status);
        this.markConnected('CONNECTED');
      }

      if (resSignals.ok) {
        const signals = await resSignals.json();
        this.renderSignalsTable(signals);
      }

      if (resTrades.ok) {
        const tradeData = await resTrades.json();
        this.renderTradesTable(tradeData.trades || []);
        this.updateMetrics(tradeData.summary || {});
      }

      if (resRegime.ok) {
        const regime = await resRegime.json();
        this.updateRegime(regime);
      }
    } catch (err) {
      console.warn("Initial data load encountered network issue:", err);
    }
  }

  updateFromStatus(status) {
    if (!status) return;

    // 1. Update Live Price
    if (status.current_price) {
      const elPrice = document.getElementById('live-price');
      if (elPrice) {
        elPrice.innerText = `$${status.current_price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
      }
      this.liveChart.updateLiveTick(status.current_price, 1.0);
    }

    // 2. Active signals
    if (status.active_signals && status.active_signals.length > 0) {
      this.activeSignal = status.active_signals[0];
      this.liveChart.setActiveSignal(this.activeSignal);
      this.showActiveBanner(this.activeSignal);

      if (status.current_price) {
        const entry = this.activeSignal.entry_price;
        const isBuy = this.activeSignal.direction === 'BUY';
        const unrealizedPnl = isBuy
          ? ((status.current_price - entry) / entry * 100)
          : ((entry - status.current_price) / entry * 100);

        const elPnl = document.getElementById('active-pos-pnl');
        if (elPnl) {
          elPnl.innerText = `${unrealizedPnl >= 0 ? '+' : ''}${unrealizedPnl.toFixed(2)}%`;
          elPnl.className = `font-mono font-bold ${unrealizedPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`;
        }
      }
    } else {
      this.hideActiveBanner();
      this.liveChart.setActiveSignal(null);
    }

    // 3. Regime
    if (status.regime) {
      this.updateRegime(status.regime);
    }

    // 4. Performance metrics
    if (status.performance) {
      this.updateMetrics(status.performance);
    }
  }

  connectSSE() {
    try {
      const source = new EventSource('/api/stream');
      source.onopen = () => this.markConnected('SSE STREAM');
      source.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          this.handleEvent(payload);
        } catch (e) {}
      };
    } catch (e) {
      console.warn("SSE connection fallback to polling");
    }
  }

  handleEvent(payload) {
    const { type, data } = payload;
    if (type === 'tick') {
      const elPrice = document.getElementById('live-price');
      if (elPrice) elPrice.innerText = `$${data.price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

      const elFunding = document.getElementById('live-funding');
      if (elFunding) elFunding.innerText = `${(data.funding_rate * 100).toFixed(3)}%`;

      const elCvd = document.getElementById('live-cvd');
      if (elCvd) elCvd.innerText = `${data.cvd > 0 ? '+' : ''}${data.cvd.toLocaleString()}`;

      this.liveChart.updateLiveTick(data.price, data.volume || 1.0);
      this.cvdChart.addCVDPoint(data.cvd);
      this.markConnected(data.mode ? 'LIVE' : 'SYNCED');
    } else if (type === 'signal_generated') {
      this.activeSignal = data;
      this.liveChart.setActiveSignal(data);
      this.showActiveBanner(data);
    } else if (type === 'trade_closed') {
      this.activeSignal = null;
      this.liveChart.setActiveSignal(null);
      this.hideActiveBanner();
    } else if (type === 'regime_update') {
      this.updateRegime(data);
    } else if (type === 'candle_closed') {
      this.liveChart.appendCandle(data);
    }
  }

  showActiveBanner(sig) {
    const banner = document.getElementById('active-position-banner');
    if (!banner) return;
    banner.classList.remove('hidden');

    document.getElementById('active-pos-dir').innerText = sig.direction;
    document.getElementById('active-pos-dir').className = `px-2.5 py-0.5 rounded text-xs font-bold ${sig.direction === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`;
    document.getElementById('active-pos-entry').innerText = `$${sig.entry_price.toLocaleString()}`;
    document.getElementById('active-pos-sl').innerText = `$${sig.stop_loss.toLocaleString()}`;
    document.getElementById('active-pos-tp').innerText = `$${sig.take_profit_2.toLocaleString()}`;
    document.getElementById('active-pos-reason').innerText = sig.reason;
  }

  hideActiveBanner() {
    const banner = document.getElementById('active-position-banner');
    if (banner) banner.classList.add('hidden');
  }

  updateMetrics(summary) {
    const pnl = summary.net_pnl_pct || 0.0;
    const elPnl = document.getElementById('metric-pnl');
    if (elPnl) {
      elPnl.innerText = `${pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}%`;
      elPnl.className = `text-2xl font-black ${pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'} mt-1`;
    }

    const elWin = document.getElementById('metric-winrate');
    if (elWin) elWin.innerText = `${summary.win_rate || 0.0}%`;

    const elPf = document.getElementById('metric-pf');
    if (elPf) elPf.innerText = `${summary.profit_factor || 0.0}`;

    const elTrades = document.getElementById('metric-trades');
    if (elTrades) elTrades.innerText = `${summary.total_trades || 0}`;
  }

  updateRegime(regime) {
    if (!regime || !regime.regime) return;
    const elBadge = document.getElementById('regime-badge');
    if (elBadge) {
      elBadge.innerText = regime.regime.replace(/_/g, ' ');
      elBadge.className = `text-xs font-bold px-2 py-0.5 rounded ${regime.regime === 'TRENDING_EXPANSION' ? 'text-emerald-400 bg-emerald-500/20' : 'text-amber-400 bg-amber-500/20'}`;
    }

    const elBull = document.getElementById('regime-bull-case');
    if (elBull) elBull.innerText = regime.bull_case || "Analyzing liquidity pools...";

    const elBear = document.getElementById('regime-bear-case');
    if (elBear) elBear.innerText = regime.bear_case || "Monitoring resistance overhead...";

    const elSynthesis = document.getElementById('regime-synthesis');
    if (elSynthesis) elSynthesis.innerText = regime.synthesis || "Balanced market exposure.";
  }

  renderSignalsTable(signals) {
    const tbody = document.getElementById('signals-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!signals || signals.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="py-4 text-center text-slate-500">Scanning live market ticks for setups...</td></tr>';
      return;
    }

    signals.slice(0, 10).forEach(s => {
      const isBuy = s.direction === 'BUY';
      const tr = document.createElement('tr');
      tr.className = 'hover:bg-slate-800/40 transition border-b border-slate-800/60';
      tr.innerHTML = `
        <td class="py-2 px-2.5 font-mono text-slate-400">${s.dt_str}</td>
        <td class="py-2 px-2.5 font-bold ${isBuy ? 'text-emerald-400' : 'text-rose-400'}">${s.direction}</td>
        <td class="py-2 px-2.5 font-mono text-slate-200">$${s.entry_price.toLocaleString()}</td>
        <td class="py-2 px-2.5 font-mono text-rose-400">$${s.stop_loss.toLocaleString()}</td>
        <td class="py-2 px-2.5 font-mono text-emerald-400">$${s.take_profit_2.toLocaleString()}</td>
        <td class="py-2 px-2.5 font-mono text-blue-400">${s.risk_reward}:1</td>
        <td class="py-2 px-2.5 font-semibold ${s.status === 'ACTIVE' ? 'text-amber-400 animate-pulse' : 'text-slate-400'}">${s.status}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  renderTradesTable(trades) {
    const tbody = document.getElementById('trades-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!trades || trades.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="py-4 text-center text-slate-500">No closed trades recorded in SQLite yet.</td></tr>';
      return;
    }

    trades.slice(0, 10).forEach(t => {
      const isWin = t.pnl_pct > 0;
      const tr = document.createElement('tr');
      tr.className = 'hover:bg-slate-800/40 transition border-b border-slate-800/60';
      tr.innerHTML = `
        <td class="py-2.5 px-3 font-mono text-slate-400">${t.exit_time}</td>
        <td class="py-2.5 px-3 font-bold ${t.direction === 'BUY' ? 'text-emerald-400' : 'text-rose-400'}">${t.direction}</td>
        <td class="py-2.5 px-3 font-mono text-slate-200">$${t.entry_price.toLocaleString()}</td>
        <td class="py-2.5 px-3 font-mono text-slate-200">$${t.exit_price.toLocaleString()}</td>
        <td class="py-2.5 px-3 font-bold ${isWin ? 'text-emerald-400' : 'text-rose-400'}">${isWin ? '+' : ''}${t.pnl_pct}%</td>
        <td class="py-2.5 px-3 text-slate-300 truncate max-w-xs">${t.reason}</td>
      `;
      tbody.appendChild(tr);
    });
  }
}

window.addEventListener('DOMContentLoaded', () => {
  window.app = new AppController();
});
