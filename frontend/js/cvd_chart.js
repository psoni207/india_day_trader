/**
 * Live Cumulative Volume Delta (CVD) Area Chart.
 */

class CVDChart {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.history = [];

    window.addEventListener('resize', () => this.render());
  }

  addCVDPoint(cvd) {
    this.history.push(cvd);
    if (this.history.length > 80) this.history.shift();
    this.render();
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

    ctx.fillStyle = '#090d16';
    ctx.fillRect(0, 0, w, h);

    if (this.history.length < 2) return;

    let min = Math.min(...this.history);
    let max = Math.max(...this.history);
    if (min === max) { min -= 10; max += 10; }
    const range = max - min;

    const getY = (val) => h - ((val - min) / range) * (h - 16) - 8;
    const stepX = w / (this.history.length - 1);

    // Gradient fill
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, 'rgba(56, 189, 248, 0.25)');
    grad.addColorStop(1, 'rgba(56, 189, 248, 0.0)');

    ctx.beginPath();
    ctx.moveTo(0, getY(this.history[0]));
    for (let i = 1; i < this.history.length; i++) {
      ctx.lineTo(i * stepX, getY(this.history[i]));
    }
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.fillStyle = grad;
    ctx.fill();

    // Line
    ctx.strokeStyle = '#38bdf8';
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    ctx.moveTo(0, getY(this.history[0]));
    for (let i = 1; i < this.history.length; i++) {
      ctx.lineTo(i * stepX, getY(this.history[i]));
    }
    ctx.stroke();
  }
}

window.CVDChart = CVDChart;
