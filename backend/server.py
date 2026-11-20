"""High-Performance Multi-Threaded HTTP & SSE Live Stream Server.

Zero external dependencies (uses standard library http.server + socketserver).
Provides:
- REST API for database queries (candles, signals, trades, metrics)
- Server-Sent Events (SSE) live push stream for real-time browser synchronization
- Static file serving for the frontend
"""

import http.server
import socketserver
import json
import os
import time
import queue
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs

from backend.database.db import (
    get_recent_candles, get_recent_signals, get_active_signals,
    get_recent_trades, get_performance_summary, get_latest_regime
)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        # Suppress harmless browser disconnects / ConnectionResetError on refresh/close
        pass


class AppRequestHandler(http.server.SimpleHTTPRequestHandler):
    trading_engine = None  # Injected on server startup

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (ConnectionResetError, BrokenPipeError):
            pass

    def log_message(self, format, *args):
        # Keep server console clean (only log errors, not every static asset tick)
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path.startswith("/api/"):
            self._handle_api(path, query)
        else:
            # Default root to index.html
            if path == "/" or path == "":
                self.path = "/index.html"
            super().do_GET()

    def _handle_api(self, path: str, query: Dict[str, Any]):
        if path == "/api/status":
            engine = AppRequestHandler.trading_engine
            current_price = engine.feed.current_price if (engine and hasattr(engine, 'feed') and engine.feed) else 0.0
            sentinel_status = engine.news_sentinel.get_sentinel_status() if (engine and hasattr(engine, 'news_sentinel')) else {}
            data = {
                'status': 'RUNNING' if (engine and getattr(engine, 'running', False)) else 'STOPPED',
                'symbol': getattr(engine, 'symbol', 'BTCUSDT'),
                'current_price': current_price,
                'active_signals': get_active_signals(),
                'performance': get_performance_summary(),
                'regime': get_latest_regime(),
                'macro_sentinel': sentinel_status
            }
            self._send_json(data)

        elif path == "/api/multi_status":
            engine = AppRequestHandler.trading_engine
            if engine and hasattr(engine, 'get_multi_status'):
                self._send_json(engine.get_multi_status())
            else:
                from backend.multi_asset_manager import MultiAssetManager
                # Return standard schema fallback
                mgr = MultiAssetManager()
                self._send_json(mgr.get_multi_status())

        elif path == "/api/candles":
            limit = int(query.get('limit', [100])[0])
            timeframe = query.get('timeframe', ['15m'])[0]
            symbol = query.get('symbol', ['BTCUSDT'])[0]
            candles = get_recent_candles(symbol, timeframe, limit)
            self._send_json(candles)

        elif path == "/api/signals":
            symbol = query.get('symbol', [None])[0]
            status = query.get('status', [None])[0]
            timeframe = query.get('timeframe', [None])[0]
            limit = int(query.get('limit', [40])[0])
            if status and status.upper() == 'ACTIVE':
                signals = get_active_signals()
            else:
                signals = get_recent_signals(limit=limit)
            if symbol:
                signals = [s for s in signals if s.get('symbol') == symbol or symbol in s.get('symbol', '')]
            if timeframe:
                signals = [s for s in signals if (s.get('timeframe') or '').upper() == timeframe.upper()]
            self._send_json(signals)

        elif path == "/api/trades":
            symbol = query.get('symbol', [None])[0]
            timeframe = query.get('timeframe', [None])[0]
            limit = int(query.get('limit', [50])[0])
            trades = get_recent_trades(limit=limit)
            if symbol:
                trades = [t for t in trades if t.get('symbol') == symbol or symbol in t.get('symbol', '')]
            if timeframe:
                trades = [t for t in trades if (t.get('timeframe') or '').upper() == timeframe.upper()]
            summary = get_performance_summary()
            self._send_json({'trades': trades, 'summary': summary})

        elif path == "/api/regime":
            regime = get_latest_regime()
            self._send_json(regime or {})

        elif path == "/api/stream":
            self._handle_sse_stream()

        else:
            self.send_error(404, "Endpoint not found")

    def _send_json(self, data: Any):
        body = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_sse_stream(self):
        """Server-Sent Events (SSE) streaming endpoint."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.flush()

        event_queue = queue.Queue(maxsize=100)

        def on_event(payload):
            try:
                event_queue.put_nowait(payload)
            except queue.Full:
                pass

        engine = AppRequestHandler.trading_engine
        if engine:
            engine.subscribe(on_event)

        try:
            # Send immediate connection handshake and retry directive
            handshake = b"retry: 1000\n" + f"data: {json.dumps({'type': 'connected', 'timestamp': int(time.time()*1000)})}\n\n".encode('utf-8')
            self.wfile.write(handshake)
            self.wfile.flush()

            while True:
                try:
                    payload = event_queue.get(timeout=1.0)
                    msg = f"data: {json.dumps(payload)}\n\n".encode('utf-8')
                    self.wfile.write(msg)
                    self.wfile.flush()
                except queue.Empty:
                    # Keep-alive heartbeat comment every second
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            if engine:
                engine.unsubscribe(on_event)


def run_server(host: str = "0.0.0.0", port: int = 8080, engine=None) -> ThreadedHTTPServer:
    AppRequestHandler.trading_engine = engine
    server = ThreadedHTTPServer((host, port), AppRequestHandler)
    print(f" 🌐 WEB SERVER LISTENING ON: http://localhost:{port}")
    return server
