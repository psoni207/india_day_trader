"""Main Entrypoint for Bitcoin Intraday Live Trading System.

Boots:
1. SQLite Database Schema (data/intraday.db)
2. Live Market Ingestion & Continuous Strategy Engine (LiveTradingEngine)
3. Multi-Threaded HTTP & Server-Sent Events (SSE) Web Server (port 8080)
"""

import sys
import os
import signal
import time

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.database.db import init_db
from backend.multi_asset_manager import MultiAssetManager
from backend.server import run_server


def main():
    print("\n" + "=" * 80)
    print(" 🚀 MULTI-ASSET INTRADAY TRADING PLATFORM | BTC • NIFTY • XAU/USD")
    print("=" * 80)

    # 1. Initialize SQLite Database
    print("[1/3] Initializing SQLite database at data/intraday.db...")
    init_db()
    print("      ✓ Database ready. Tables: candles, signals, trades, agent_regime_logs.")

    # 2. Boot Multi-Asset Trading Engine (BTC + NSE + Gold)
    print("[2/3] Booting Multi-Asset Trading Engines...")
    manager = MultiAssetManager()
    manager.start()
    print("      ✓ BTC/USD (24/7), NSE Nifty/BankNifty, and XAU/USD Gold engines online.")

    # 3. Boot Web Server
    port = int(os.environ.get("PORT", 8080))
    print(f"[3/3] Launching Web & SSE Server on port {port}...")
    server = run_server(host="0.0.0.0", port=port, engine=manager)
    print("=" * 80)
    print(f" 🌐 DASHBOARD READY: Open in your browser -> http://localhost:{port}")
    print("    Press Ctrl+C to stop the system cleanly.")
    print("=" * 80 + "\n")

    def handle_exit(sig, frame):
        print("\n\nShutting down multi-asset trading platform...")
        manager.stop()
        server.shutdown()
        server.server_close()
        print("✓ All background workers and database connections cleanly closed.")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # Serve requests continuously
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        handle_exit(None, None)


if __name__ == "__main__":
    main()
