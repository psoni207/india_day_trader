/**
 * Live Financial Candlestick & Microstructure Chart Engine.
 * Renders real-time 15m candles, Asian Range (ASH / ASL), and Daily Anchored VWAP.
 */

class LiveChart {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.candles = [];
    this.activeSignal = null;

    window.addEventListener('resize', () => this.render());
  }

  setCandles(candles) {
    this.candles = [...candles];
    this.render();
  }

  updateLiveTick(price, volume) {
    if (this.candles.length === 0) return;
    const last = this.candles[this.candles.length - 1];
    last.high = Math.max(last.high, price);
    last.low = Math.min(last.low, price);
    last.close = price;
    last.volume += volume;
    this.render();
  }

  appendCandle(candle) {
    this.candles.push(candle);
    if (this.candles.length > 100) this.candles.shift();
    this.render();
  }

  setActiveSignal(signal) {
    this.activeSignal = signal;
    this.render();
  }

  calculateMicrostructure() {
    if (this.candles.length === 0) return { ash: 0, asl: 0, vwap: 0 };

    // Get current day's candles (or latest 24h)
    const latestCandle = this.candles[this.candles.length - 1];
    const latestDate = new Date(latestCandle.timestamp).getUTCDate();

    // Asian session levels (candles between 00:00 and 08:00 UTC of the active day)
    let asianCandles = this.candles.filter(c => {
      const dt = new Date(c.timestamp);
      return dt.getUTCHours() >= 0 && dt.getUTCHours() < 8;
    });

    let ash = 0;
    let asl = Infinity;

    if (asianCandles.length > 0) {
      // Take the most recent Asian session block
      const recentAsian = asianCandles.slice(-32); // at most 8 hours of 15m candles
      ash = Math.max(...recentAsian.map(c => c.high));
      asl = Math.min(...recentAsian.map(c => c.low));
    } else {
      // Fallback: Tight intraday bounds around latest price (+-0.5%)
      ash = latestCandle.close * 1.005;
      asl = latestCandle.close * 0.995;
    }

    // Daily Anchored VWAP (reset at 00:00 UTC of current day)
    let cumVol = 0;
    let cumTPVol = 0;
    for (let c of this.candles) {
      const tp = (c.high + c.low + c.close) / 3.0;
      cumVol += c.volume;
      cumTPVol += tp * c.volume;
    }

    const vwap = cumVol > 0 ? (cumTPVol / cumVol) : latestCandle.close;

    return { ash, asl, vwap };
  }

  render() {
    if (!this.canvas) return;
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    const ctx = this.ctx;

    // Background
    ctx.fillStyle = '#090d16';
    ctx.fillRect(0, 0, w, h);

    if (this.candles.length < 5) return;

    // Calculate Price Range
    let minPrice = Infinity;
    let maxPrice = -Infinity;
    for (let c of this.candles) {
      if (c.low < minPrice) minPrice = c.low;
      if (c.high > maxPrice) maxPrice = c.high;
    }

    const pricePadding = (maxPrice - minPrice) * 0.1 || 100;
    minPrice -= pricePadding;
    maxPrice += pricePadding;
    const priceRange = maxPrice - minPrice;

    const getY = (price) => h - ((price - minPrice) / priceRange) * h;

    // Draw Grid Lines & Price Labels
    ctx.strokeStyle = '#1a2333';
    ctx.lineWidth = 1;
    ctx.fillStyle = '#64748b';
    ctx.font = '11px monospace';

    const numGridLines = 5;
    for (let i = 0; i <= numGridLines; i++) {
      const p = minPrice + (priceRange / numGridLines) * i;
      const y = getY(p);
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w - 60, y);
      ctx.stroke();

      ctx.fillText(`$${p.toFixed(0)}`, w - 55, y + 4);
    }

    // Microstructure Levels (ASH, ASL, VWAP)
    const { ash, asl, vwap } = this.calculateMicrostructure();

    // Update legend elements in DOM if present
    const elAsh = document.getElementById('chart-ash');
    const elAsl = document.getElementById('chart-asl');
    const elVwap = document.getElementById('chart-vwap');
    if (elAsh) elAsh.innerText = `$${ash.toLocaleString(undefined, {minimumFractionDigits: 1})}`;
    if (elAsl) elAsl.innerText = `$${asl.toLocaleString(undefined, {minimumFractionDigits: 1})}`;
    if (elVwap) elVwap.innerText = `$${vwap.toLocaleString(undefined, {minimumFractionDigits: 1})}`;

    // Draw ASH (Red dashed)
    if (ash > 0) {
      const ashY = getY(ash);
      ctx.strokeStyle = '#f43f5e';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      ctx.moveTo(0, ashY);
      ctx.lineTo(w - 60, ashY);
      ctx.stroke();
    }

    // Draw ASL (Green dashed)
    if (asl > 0 && asl < Infinity) {
      const aslY = getY(asl);
      ctx.strokeStyle = '#10b981';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      ctx.moveTo(0, aslY);
      ctx.lineTo(w - 60, aslY);
      ctx.stroke();
    }

    // Draw VWAP (Blue solid)
    if (vwap > 0) {
      const vwapY = getY(vwap);
      ctx.strokeStyle = '#3b82f6';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.moveTo(0, vwapY);
      ctx.lineTo(w - 60, vwapY);
      ctx.stroke();
    }

    // Draw Candlesticks
    const candleWidth = Math.max(3, (w - 80) / this.candles.length);

    for (let i = 0; i < this.candles.length; i++) {
      const c = this.candles[i];
      const x = i * candleWidth;
      const isBull = c.close >= c.open;

      const openY = getY(c.open);
      const closeY = getY(c.close);
      const highY = getY(c.high);
      const lowY = getY(c.low);

      const color = isBull ? '#10b981' : '#f43f5e';
      ctx.strokeStyle = color;
      ctx.fillStyle = color;

      // Wick
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(x + candleWidth / 2, highY);
      ctx.lineTo(x + candleWidth / 2, lowY);
      ctx.stroke();

      // Body
      const bodyTop = Math.min(openY, closeY);
      const bodyH = Math.max(2, Math.abs(openY - closeY));
      ctx.fillRect(x + 1.5, bodyTop, Math.max(1, candleWidth - 3), bodyH);
    }

    // Draw Active Signal Target / Stop Box
    if (this.activeSignal) {
      const sig = this.activeSignal;
      const entryY = getY(sig.entry_price);
      const slY = getY(sig.stop_loss);
      const tpY = getY(sig.take_profit_2);

      // Entry line
      ctx.strokeStyle = '#f59e0b';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(w - 180, entryY);
      ctx.lineTo(w - 60, entryY);
      ctx.stroke();

      // SL line (Red)
      ctx.strokeStyle = '#f43f5e';
      ctx.beginPath();
      ctx.moveTo(w - 180, slY);
      ctx.lineTo(w - 60, slY);
      ctx.stroke();

      // TP line (Green)
      ctx.strokeStyle = '#10b981';
      ctx.beginPath();
      ctx.moveTo(w - 180, tpY);
      ctx.lineTo(w - 60, tpY);
      ctx.stroke();
    }
  }
}

window.LiveChart = LiveChart;
