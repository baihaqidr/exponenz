import os
import json
import time
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
import requests
import urllib3
import pandas as pd
import numpy as np

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from src.data_fetcher import fetch_binance_futures_klines, fetch_fast_api_klines
from src.strategy_registry import get_all_strategies, get_strategy_instance, STRATEGY_METADATA
from src.backtester import BacktestEngine
from src.funding_scanner import FundingRateScanner
from src.trading_bot import LiveTradingBot

funding_scanner = FundingRateScanner()
trading_bot = LiveTradingBot.get_instance()

TOP_12_PAIRS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "SUIUSDT", "DOGEUSDT",
    "1000PEPEUSDT", "NEARUSDT", "AVAXUSDT", "XRPUSDT", "LINKUSDT", "ADAUSDT"
]

TOP_25_PAIRS = TOP_12_PAIRS + [
    "APTUSDT", "ARBUSDT", "OPUSDT", "INJUSDT", "TIAUSDT", "RENDERUSDT",
    "FETUSDT", "TAOUSDT", "SEIUSDT", "WIFUSDT", "SHIBUSDT", "DOTUSDT", "LTCUSDT"
]

TOP_50_PAIRS = TOP_25_PAIRS + [
    "FILUSDT", "JUPUSDT", "ATOMUSDT", "POLUSDT", "ETCUSDT", "BCHUSDT",
    "UNIUSDT", "AAVEUSDT", "TRXUSDT", "ICPUSDT", "KASUSDT", "ENAUSDT",
    "PENDLEUSDT", "ORDIUSDT", "STXUSDT", "RUNEUSDT", "GALAUSDT", "CRVUSDT",
    "DYDXUSDT", "SANDUSDT", "MANAUSDT", "AXSUSDT", "THETAUSDT", "ALGOUSDT", "FLOKIUSDT"
]

DEFAULT_MATRIX_PAIRS = TOP_12_PAIRS

DASHBOARD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard")

# CACHED BINANCE FUTURES & LIVE SYMBOLS
CACHED_FUTURES_SYMBOLS = []
LAST_SYMBOLS_FETCH = 0

def get_all_futures_symbols() -> List[Dict[str, Any]]:
    global CACHED_FUTURES_SYMBOLS, LAST_SYMBOLS_FETCH
    now = time.time()
    if CACHED_FUTURES_SYMBOLS and (now - LAST_SYMBOLS_FETCH < 1800):
        return CACHED_FUTURES_SYMBOLS

    try:
        # 1. Fetch real 24hr volumes from Binance Vision
        vis_vol = {}
        r_vis = requests.get("https://data-api.binance.vision/api/v3/ticker/24hr", verify=False, timeout=6)
        if r_vis.status_code == 200:
            for t in r_vis.json():
                if t['symbol'].endswith('USDT'):
                    vis_vol[t['symbol']] = float(t.get('quoteVolume', 0))

        # 2. Fetch active TRADING Perpetual USDT contracts
        r_fut = requests.get("https://testnet.binancefuture.com/fapi/v1/exchangeInfo", verify=False, timeout=6)
        fut_map = {}
        if r_fut.status_code == 200:
            for s in r_fut.json().get("symbols", []):
                if s.get("status") == "TRADING" and s.get("contractType") == "PERPETUAL" and s.get("quoteAsset") == "USDT":
                    sym = s["symbol"]
                    base = s.get("baseAsset", sym.replace("USDT", ""))
                    fut_map[sym] = {
                        "symbol": sym,
                        "baseAsset": base,
                        "pricePrecision": s.get("pricePrecision", 2),
                        "quantityPrecision": s.get("quantityPrecision", 2)
                    }

        stables = {'USDCUSDT', 'FDUSDUSDT', 'TUSDUSDT', 'EURUSDT', 'USD1USDT', 'RLUSDUSDT', 'UUSDT', 'USDPUSDT', 'AEURUSDT', 'BUSDUSDT'}
        
        clean_symbols = []
        for sym, item in fut_map.items():
            if sym in stables:
                continue
            base_sym = sym.replace("1000", "")
            vol = vis_vol.get(sym, vis_vol.get(base_sym, 0))
            if vol > 50000 or sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "SUIUSDT", "NEARUSDT", "1000PEPEUSDT"]:
                item["volume_24h"] = vol
                clean_symbols.append(item)

        clean_symbols.sort(key=lambda x: x.get("volume_24h", 0), reverse=True)
        if clean_symbols:
            CACHED_FUTURES_SYMBOLS = clean_symbols
            LAST_SYMBOLS_FETCH = now
            return CACHED_FUTURES_SYMBOLS
    except Exception as e:
        print(f"Error fetching active Binance Futures symbols: {e}")

    # Fallback to verified active list
    if not CACHED_FUTURES_SYMBOLS:
        fallback = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "SUIUSDT", "DOGEUSDT", "1000PEPEUSDT", "NEARUSDT", "AVAXUSDT", "XRPUSDT", "LINKUSDT", "ADAUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "INJUSDT", "TIAUSDT", "RENDERUSDT", "FETUSDT", "TAOUSDT", "SEIUSDT", "WIFUSDT", "SHIBUSDT", "DOTUSDT", "LTCUSDT", "FILUSDT", "JUPUSDT", "ATOMUSDT", "POLUSDT", "ETCUSDT", "BCHUSDT", "UNIUSDT", "AAVEUSDT", "TRXUSDT", "ICPUSDT", "KASUSDT", "ENAUSDT", "PENDLEUSDT", "ORDIUSDT", "STXUSDT", "RUNEUSDT", "GALAUSDT", "CRVUSDT", "DYDXUSDT", "SANDUSDT", "MANAUSDT", "AXSUSDT", "THETAUSDT", "ALGOUSDT", "FLOKIUSDT"]
        CACHED_FUTURES_SYMBOLS = [{"symbol": s, "baseAsset": s.replace("USDT", ""), "pricePrecision": 2, "quantityPrecision": 2} for s in fallback]
    return CACHED_FUTURES_SYMBOLS

class DashboardAPIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DASHBOARD_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/symbols" or parsed.path == "/api/bot/symbols" or parsed.path == "/api/futures-symbols":
            syms = get_all_futures_symbols()
            self.send_json({"success": True, "total": len(syms), "symbols": syms})
        elif parsed.path == "/api/strategies":
            import importlib
            import src.strategy_registry
            importlib.reload(src.strategy_registry)
            self.send_json(src.strategy_registry.get_all_strategies())
        elif parsed.path == "/api/pairs":
            all_syms = [s["symbol"] for s in get_all_futures_symbols() if s["symbol"].endswith("USDT")]
            top_12 = all_syms[:12] if len(all_syms) >= 12 else TOP_12_PAIRS
            top_25 = all_syms[:25] if len(all_syms) >= 25 else TOP_25_PAIRS
            top_50 = all_syms[:50] if len(all_syms) >= 50 else TOP_50_PAIRS
            top_100 = all_syms[:100] if len(all_syms) >= 100 else all_syms
            self.send_json({
                "top_12": top_12,
                "top_25": top_25,
                "top_50": top_50,
                "top_100": top_100,
                "all_coins": all_syms,
                "default": top_12
            })
        elif parsed.path == "/api/tickers":
            try:
                r = requests.get("https://data-api.binance.vision/api/v3/ticker/price", verify=False, timeout=3)
                if r.status_code == 200:
                    prices = {item['symbol']: float(item['price']) for item in r.json()}
                    # Map 1000x multiplier futures pairs
                    for base in ['PEPE', 'SHIB', 'FLOKI', 'BONK', 'LUNC', 'RATS', 'SATS']:
                        spot_sym = f"{base}USDT"
                        fut_sym = f"1000{base}USDT"
                        if spot_sym in prices:
                            prices[fut_sym] = prices[spot_sym] * 1000.0
                    self.send_json({"success": True, "prices": prices})
                else:
                    self.send_json({"success": False, "prices": {}})
            except Exception as e:
                self.send_json({"success": False, "error": str(e), "prices": {}})
        elif parsed.path == "/api/funding/live":
            rates = funding_scanner.get_live_funding_rates()
            self.send_json({
                "success": True,
                "total_pairs": len(rates),
                "pairs": rates
            })
        elif parsed.path == "/api/arbitrage/positions":
            from src.arbitrage_engine import arbitrage_engine
            positions = arbitrage_engine.get_active_positions_details()
            self.send_json({
                "success": True,
                "count": len(positions),
                "positions": positions,
                "history": arbitrage_engine.trade_history[:50],
                "is_auto_running": arbitrage_engine.is_auto_running
            })
        elif parsed.path == "/api/chart/klines":
            qs = urllib.parse.parse_qs(parsed.query)
            sym = qs.get("symbol", ["ETHUSDT"])[0].upper().strip()
            tf = qs.get("timeframe", ["1m"])[0]
            limit = int(qs.get("limit", ["1000"])[0])
            strat_id = qs.get("strategy", [trading_bot.active_strategy_id])[0]
            
            try:
                # Fetch candles for indicator convergence warmup
                warmup_limit = max(limit + 500, 1500)
                df = fetch_fast_api_klines(sym, tf, total_candles=warmup_limit)
                if df is not None and len(df) > 10:
                    import importlib
                    import src.strategy_registry
                    import src.backtester
                    importlib.reload(src.strategy_registry)
                    importlib.reload(src.backtester)
                    strategy = src.strategy_registry.get_strategy_instance(strat_id)
                    df_sig = strategy.generate_signals(df)
                    
                    # Slice to requested limit after accurate calculation
                    df_plot = df_sig.tail(limit).reset_index(drop=True)
                    
                    latest_close = float(df_plot.iloc[-1]['close'])
                    if latest_close < 0.0001:
                        prec = 8
                        min_m = 0.00000001
                    elif latest_close < 0.01:
                        prec = 6
                        min_m = 0.000001
                    elif latest_close < 1.0:
                        prec = 5
                        min_m = 0.00001
                    elif latest_close < 50.0:
                        prec = 4
                        min_m = 0.0001
                    elif latest_close < 1000.0:
                        prec = 2
                        min_m = 0.01
                    else:
                        prec = 2
                        min_m = 0.01

                    # Ensure RSI 14 is present
                    if 'rsi' not in df_plot.columns or df_plot['rsi'].isnull().all():
                        delta = df_sig['close'].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / (loss + 1e-9)
                        df_sig['rsi'] = 100 - (100 / (1 + rs))
                        df_plot = df_sig.tail(limit).reset_index(drop=True)

                    candles = []
                    ema_data = []
                    upper_data = []
                    lower_data = []
                    rsi_data = []
                    markers = []
                    volume_data = []
                    
                    for i in range(len(df_plot)):
                        row = df_plot.iloc[i]
                        t_sec = int(row['open_time'] / 1000) if 'open_time' in row and pd.notnull(row['open_time']) else int(row['timestamp'].timestamp())
                        c_open = float(row['open'])
                        c_close = float(row['close'])
                        c_vol = float(row.get('volume', 0.0))
                        
                        candles.append({
                            "time": t_sec,
                            "open": c_open,
                            "high": float(row['high']),
                            "low": float(row['low']),
                            "close": c_close,
                            "volume": c_vol
                        })

                        vol_color = "rgba(14, 203, 129, 0.45)" if c_close >= c_open else "rgba(246, 70, 93, 0.45)"
                        volume_data.append({
                            "time": t_sec,
                            "value": c_vol,
                            "color": vol_color
                        })
                        
                        # Dynamic Main Line (EMA, Supertrend, or Middle Band)
                        main_val = row.get('ema_7', row.get('ema_main', row.get('supertrend', row.get('sma_mid', row.get('bb_middleband')))))
                        if pd.notnull(main_val):
                            ema_data.append({
                                "time": t_sec,
                                "value": float(main_val)
                            })
                            
                        # Upper Band / Swing High
                        up_val = row.get('bb_upper', row.get('bb_upperband', row.get('swing_high', row.get('sw_high'))))
                        if pd.notnull(up_val):
                            upper_data.append({
                                "time": t_sec,
                                "value": float(up_val)
                            })
                            
                        # Lower Band / Swing Low
                        low_val = row.get('bb_lower', row.get('bb_lowerband', row.get('swing_low', row.get('sw_low'))))
                        if pd.notnull(low_val):
                            lower_data.append({
                                "time": t_sec,
                                "value": float(low_val)
                            })

                        # RSI (14)
                        rsi_val = row.get('rsi', None)
                        if pd.notnull(rsi_val):
                            rsi_data.append({
                                "time": t_sec,
                                "value": round(float(rsi_val), 2)
                            })
                            
                    # Generate 100% accurate, stateful trade markers matching the Data Table
                    engine = BacktestEngine(initial_capital=1000.0, leverage=2.0, risk_per_trade_pct=0.02)
                    res_bt = engine.run(df_sig)
                    df_trades = res_bt.get("trades_df", pd.DataFrame())
                    open_pos = res_bt.get("open_position", None)
                    
                    min_plot_sec = int(df_plot.iloc[0]['timestamp'].timestamp())
                    max_plot_sec = int(df_plot.iloc[-1]['timestamp'].timestamp())
                    markers_map = {}

                    if not df_trades.empty:
                        for _, tr in df_trades.iterrows():
                            e_sec = int(pd.to_datetime(tr['entry_time']).timestamp())
                            x_sec = int(pd.to_datetime(tr['exit_time']).timestamp())
                            is_long = tr['type'] == 'LONG'

                            if min_plot_sec <= e_sec <= max_plot_sec:
                                markers_map[e_sec] = {
                                    "time": e_sec,
                                    "position": "belowBar" if is_long else "aboveBar",
                                    "color": "#10b981" if is_long else "#ef4444",
                                    "shape": "arrowUp" if is_long else "arrowDown",
                                    "text": "BUY" if is_long else "SHORT"
                                }

                            if min_plot_sec <= x_sec <= max_plot_sec:
                                markers_map[x_sec] = {
                                    "time": x_sec,
                                    "position": "aboveBar" if is_long else "belowBar",
                                    "color": "#ef4444" if is_long else "#10b981",
                                    "shape": "arrowDown" if is_long else "arrowUp",
                                    "text": "CLOSE" if is_long else "COVER"
                                }

                    if open_pos is not None:
                        e_sec = int(pd.to_datetime(open_pos['entry_time']).timestamp())
                        is_long = open_pos['type'] == 'LONG'
                        if min_plot_sec <= e_sec <= max_plot_sec:
                            markers_map[e_sec] = {
                                "time": e_sec,
                                "position": "belowBar" if is_long else "aboveBar",
                                "color": "#10b981" if is_long else "#ef4444",
                                "shape": "arrowUp" if is_long else "arrowDown",
                                "text": "BUY" if is_long else "SHORT"
                            }

                    markers = [markers_map[t] for t in sorted(markers_map.keys())]
                            
                    self.send_json({
                        "success": True,
                        "symbol": sym,
                        "timeframe": tf,
                        "strategy_id": strat_id,
                        "strategy_name": strategy.name,
                        "precision": prec,
                        "min_move": min_m,
                        "candles": candles,
                        "ema": ema_data,
                        "upper_band": upper_data,
                        "lower_band": lower_data,
                        "volume": volume_data,
                        "rsi": rsi_data,
                        "markers": markers,
                        "current_price": latest_close
                    })

                else:
                    self.send_json({"success": False, "error": "Gagal mengambil data candle Binance"})
            except Exception as e:
                self.send_json({"success": False, "error": str(e)})
        elif parsed.path == "/api/screener/bollinger":
            try:
                from src.screener_engine import bollinger_screener
                tf = query_params.get("timeframe", ["15m"])[0]
                limit = int(query_params.get("limit", [50])[0])
                data = bollinger_screener.scan_all(timeframe=tf, limit=limit)
                self.send_json({
                    "success": True,
                    "timeframe": tf,
                    "count": len(data),
                    "pairs": data
                })
            except Exception as e:
                self.send_json({"success": False, "error": str(e), "pairs": []})
        elif parsed.path == "/api/bot/status":
            status = trading_bot.get_status()
            self.send_json(status)
        elif parsed.path == "/api/health":
            self.send_json({"status": "healthy", "service": "Binance Futures Bot Dashboard"})
        else:
            super().do_GET()

    def end_headers(self):
        try:
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            super().end_headers()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
            pass

    def send_json(self, data: Any, status_code: int = 200):
        try:
            response_bytes = json.dumps(data, default=self._json_serializer).encode('utf-8')
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(response_bytes)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            self.wfile.write(response_bytes)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
            pass

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        try:
            body = json.loads(post_data) if post_data else {}
        except Exception:
            body = {}

        if parsed.path == "/api/matrix":
            self.handle_matrix(body)
        elif parsed.path == "/api/bot/start":
            strat = body.get("strategy_id", "bb_reclaim_sniper")
            tf = body.get("timeframe", "1h")
            raw_wl = body.get("watchlist", ["ETHUSDT"])
            valid_set = {s["symbol"] for s in get_all_futures_symbols()}
            wl = [s.upper().strip() for s in raw_wl if s.upper().strip() in valid_set]
            if not wl:
                wl = ["ETHUSDT"]
            lev = int(body.get("leverage", 3))
            raw_risk = body.get("risk_pct", 0.20)
            if isinstance(raw_risk, str) and raw_risk.startswith("fixed_"):
                risk = raw_risk
            else:
                try:
                    risk = float(raw_risk)
                except Exception:
                    risk = 0.20
            res = trading_bot.start(strat, tf, wl, lev, risk)
            self.send_json(res)
        elif parsed.path == "/api/bot/stop":
            res = trading_bot.stop()
            self.send_json(res)
        elif parsed.path == "/api/bot/reset":
            res = trading_bot.reset_session()
            self.send_json(res)
        elif parsed.path == "/api/bot/update_watchlist":
            raw_wl = body.get("watchlist", ["ETHUSDT"])
            valid_set = {s["symbol"] for s in get_all_futures_symbols()}
            wl = [s.upper().strip() for s in raw_wl if s.upper().strip() in valid_set]
            if not wl:
                self.send_json({"status": "error", "message": "Tidak ada simbol koin valid yang terdaftar di Binance"}, status_code=400)
                return
            if trading_bot and wl:
                trading_bot.watchlist = wl
                wl_desc = f"{len(trading_bot.watchlist)} pair (Auto-Hunt)" if len(trading_bot.watchlist) > 12 else ', '.join(trading_bot.watchlist)
                trading_bot._log("CONFIG", f"📋 Watchlist diperbarui ({len(trading_bot.watchlist)} pair terverifikasi): {wl_desc}")
            self.send_json({"status": "success", "watchlist": trading_bot.watchlist})
        elif parsed.path == "/api/bot/close_position":
            sym = body.get("symbol")
            res = trading_bot.engine.close_position(sym)
            self.send_json(res)
        elif parsed.path == "/api/arbitrage/open":
            from src.arbitrage_engine import arbitrage_engine
            sym = body.get("symbol", "BTCUSDT")
            notional = float(body.get("notional_usd", 500.0))
            res = arbitrage_engine.open_arbitrage(sym, notional)
            self.send_json(res)
        elif parsed.path == "/api/arbitrage/close":
            from src.arbitrage_engine import arbitrage_engine
            sym = body.get("symbol", "")
            res = arbitrage_engine.close_arbitrage(sym)
            self.send_json(res)
        elif parsed.path == "/api/arbitrage/rebalance":
            from src.arbitrage_engine import arbitrage_engine
            sym = body.get("symbol", "")
            res = arbitrage_engine.rebalance_position(sym)
            self.send_json(res)
        elif parsed.path == "/api/arbitrage/harvest":
            from src.arbitrage_engine import arbitrage_engine
            res = arbitrage_engine.check_and_harvest_funding()
            self.send_json({"status": "success", "harvested": res})
        elif parsed.path == "/api/backtest":
            self.handle_backtest(body)
        elif parsed.path == "/api/funding/simulate":
            self.handle_funding_simulate(body)
        else:
            self.send_error(404, "Endpoint not found")

    def do_OPTIONS(self):
        try:
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
            pass

    def _json_serializer(self, obj):
        if isinstance(obj, (pd.Timestamp, np.datetime64)):
            return str(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return str(obj)

    def _backtest_single_symbol(self, symbol: str, interval: str, strategy_id: str, leverage: float, risk_pct: float, candles: int) -> Dict[str, Any]:
        try:
            import importlib
            import src.data_fetcher
            importlib.reload(src.data_fetcher)
            df = src.data_fetcher.fetch_binance_futures_klines(symbol=symbol, interval=interval, total_candles=candles, use_cache=False)
            if df is None or len(df) < 30:
                return {
                    "symbol": symbol,
                    "success": False,
                    "error": "Insufficient candle data",
                    "net_profit": 0.0,
                    "roi_pct": 0.0,
                    "win_rate": 0.0,
                    "profit_factor": 0.0,
                    "max_drawdown": 0.0,
                    "total_trades": 0,
                    "win_count": 0,
                    "loss_count": 0,
                    "avg_win": 0.0,
                    "avg_loss": 0.0,
                    "risk_reward": 0.0,
                    "monthly_pnl": {},
                    "trades": []
                }

            # Check if pair is delisted/frozen (latest candle older than 45 days)
            latest_time = pd.to_datetime(df['timestamp'].iloc[-1])
            if hasattr(latest_time, 'tzinfo') and latest_time.tzinfo is not None:
                latest_time = latest_time.tz_localize(None)
            if latest_time < (pd.Timestamp.now() - pd.Timedelta(days=45)):
                return {
                    "symbol": symbol,
                    "success": False,
                    "error": "Delisted / Inactive Binance Pair",
                    "net_profit": 0.0,
                    "roi_pct": 0.0,
                    "win_rate": 0.0,
                    "profit_factor": 0.0,
                    "max_drawdown": 0.0,
                    "total_trades": 0,
                    "win_count": 0,
                    "loss_count": 0,
                    "avg_win": 0.0,
                    "avg_loss": 0.0,
                    "risk_reward": 0.0,
                    "monthly_pnl": {},
                    "trades": []
                }

            import importlib
            import src.strategy_registry
            import src.backtester
            importlib.reload(src.strategy_registry)
            importlib.reload(src.backtester)
            strat = src.strategy_registry.get_strategy_instance(strategy_id)
            df_signals = strat.generate_signals(df)

            engine = src.backtester.BacktestEngine(
                initial_capital=1000.0,
                leverage=leverage,
                risk_per_trade_pct=risk_pct,
                fixed_pos_size_pct=0.7,
                fee_rate=0.0005,
                slippage_pct=0.0002
            )
            res = engine.run(df_signals)
            m = res["metrics"]
            df_trades = res["trades_df"]

            tz_offset = pd.Timedelta(hours=7)
            monthly_pnl_map = {}
            trades_formatted = []

            if not df_trades.empty:
                for idx, t in df_trades.iterrows():
                    e_wib = pd.to_datetime(t['entry_time']) + tz_offset
                    x_wib = pd.to_datetime(t['exit_time']) + tz_offset
                    net_pnl = round(float(t['net_pnl']), 2)

                    # Group by Month YYYY-MM
                    m_key = x_wib.strftime('%Y-%m')
                    monthly_pnl_map[m_key] = round(monthly_pnl_map.get(m_key, 0.0) + net_pnl, 2)

                    qty_val = float(t.get('quantity', 0.0))
                    notional_val = round(qty_val * float(t['entry_price']), 2)
                    margin_val = round(notional_val / leverage, 2)

                    trades_formatted.append({
                        "id": idx + 1,
                        "type": t['type'],
                        "entry_time": e_wib.strftime('%Y-%m-%d %H:%M'),
                        "entry_price": float(t['entry_price']),
                        "quantity": qty_val,
                        "notional_size": notional_val,
                        "margin_used": margin_val,
                        "exit_time": x_wib.strftime('%Y-%m-%d %H:%M'),
                        "exit_price": float(t['exit_price']),
                        "duration": t.get('duration', '-'),
                        "net_pnl": net_pnl,
                        "pnl_pct": round(float(t['pnl_pct']), 2),
                        "exit_reason": t.get('exit_reason', 'Manual Exit'),
                        "capital_after": round(float(t['capital_after']), 2)
                    })

            # Ambil real price dan nilai indikator terbaru dari bar terakhir
            last_row = df_signals.iloc[-1]
            last_price = float(last_row['close'])
            
            # Format indikator realtime dinamis berdasarkan kolom yang tersedia di DataFrame strategi
            ind_info = {}
            for col in ['ema_fast', 'ema_slow', 'ema_trend', 'ema7', 'ema25', 'ema99', 'ema200', 'supertrend', 'rsi', 'upper_bb', 'mid_bb', 'lower_bb', 'adx']:
                if col in last_row and not pd.isna(last_row[col]):
                    val = float(last_row[col])
                    # Format desimal presisi
                    val_str = f"{val:.5f}" if val < 1.0 else (f"{val:.3f}" if val < 100.0 else f"{val:.2f}")
                    ind_info[col] = val_str

            return {
                "symbol": symbol,
                "success": True,
                "last_price": last_price,
                "latest_indicators": ind_info,
                "net_profit": round(m['net_profit'], 2),
                "roi_pct": round(m['net_profit_pct'], 2),
                "win_rate": round(m['win_rate'], 1),
                "profit_factor": round(m['profit_factor'], 2),
                "max_drawdown": round(m['max_drawdown_pct'], 2),
                "total_trades": m['total_trades'],
                "win_count": m['win_count'],
                "loss_count": m['loss_count'],
                "avg_win": round(m['avg_win'], 2),
                "avg_loss": round(m['avg_loss'], 2),
                "risk_reward": round(m['risk_reward_ratio'], 2),
                "monthly_pnl": monthly_pnl_map,
                "trades": trades_formatted
            }
        except Exception as e:
            return {
                "symbol": symbol,
                "success": False,
                "error": str(e),
                "net_profit": 0.0,
                "roi_pct": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "max_drawdown": 0.0,
                "total_trades": 0,
                "win_count": 0,
                "loss_count": 0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "risk_reward": 0.0,
                "monthly_pnl": {},
                "trades": []
            }

    def handle_matrix(self, req: Dict[str, Any]):
        try:
            import importlib
            import src.data_fetcher
            importlib.reload(src.data_fetcher)
            raw_symbols = req.get("symbols") or req.get("pairs") or DEFAULT_MATRIX_PAIRS
            # Clean & preserve unique order
            symbols = list(dict.fromkeys([str(s).upper().strip() for s in raw_symbols if s]))
            if not symbols:
                symbols = DEFAULT_MATRIX_PAIRS

            interval = req.get("timeframe") or req.get("interval") or "4h"
            strategy_id = req.get("strategy") or req.get("strategy_id") or "trend_rider_supertrend"
            raw_candles = int(req.get("candles", 3000))
            candles = min(raw_candles, 1000) if len(symbols) > 50 else raw_candles
            leverage = float(req.get("leverage", 2.0))
            raw_risk = req.get("risk_pct", "fixed_250")
            if isinstance(raw_risk, str) and raw_risk.startswith("fixed_"):
                risk_pct = raw_risk
            else:
                try:
                    risk_pct = float(raw_risk)
                except Exception:
                    risk_pct = 0.20

            # Parallel execution across all pairs (High Concurrency 25 Workers)
            max_workers = min(len(symbols), 25) if len(symbols) > 0 else 6
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(self._backtest_single_symbol, sym, interval, strategy_id, leverage, risk_pct, candles)
                    for sym in symbols
                ]
                all_results = [f.result() for f in futures]

            # Filter out failed/delisted pairs
            results = [r for r in all_results if r.get("success") and r.get("last_price", 0) > 0]
            if not results:
                results = all_results

            # Gather all distinct months sorted chronologically
            all_months_set = set()
            for r in results:
                for m in r["monthly_pnl"].keys():
                    all_months_set.add(m)
            all_months_sorted = sorted(list(all_months_set))

            # Build Month Metadata (Labels like "May '25", "Jun '26", etc.)
            months_meta = []
            for m in all_months_sorted:
                dt = pd.to_datetime(m + "-01")
                months_meta.append({
                    "key": m,
                    "label": dt.strftime("%b '%y"),
                    "year": dt.strftime("%Y"),
                    "month_num": dt.strftime("%m")
                })

            # Calculate Portfolio Monthly Totals
            portfolio_monthly = {}
            for m in all_months_sorted:
                tot = sum(r["monthly_pnl"].get(m, 0.0) for r in results)
                portfolio_monthly[m] = round(tot, 2)

            # Portfolio Global Metrics
            total_pnl = sum(r["net_profit"] for r in results)
            total_trades = sum(r["total_trades"] for r in results)
            total_wins = sum(r["win_count"] for r in results)
            portfolio_win_rate = round((total_wins / total_trades) * 100, 1) if total_trades > 0 else 0.0

            # Sort matrix rows by ROI % (Persentase Profit Bersih Strategi) & Win Rate descending
            results.sort(key=lambda x: (x.get("roi_pct", 0), x.get("win_rate", 0), x.get("net_profit", 0)), reverse=True)

            meta = STRATEGY_METADATA.get(strategy_id, {})

            response_data = {
                "success": True,
                "strategy": strategy_id,
                "strategy_meta": meta,
                "interval": interval,
                "leverage": leverage,
                "risk_pct": risk_pct,
                "months": months_meta,
                "portfolio_summary": {
                    "total_net_pnl": round(total_pnl, 2),
                    "total_trades": total_trades,
                    "win_rate": portfolio_win_rate,
                    "monthly_totals": portfolio_monthly
                },
                "matrix_rows": results
            }
            self.send_json(response_data)
        except Exception as e:
            self.send_json({"success": False, "error": str(e)})

    def handle_backtest(self, req: Dict[str, Any]):
        symbol = req.get("symbol", "BTCUSDT").upper()
        interval = req.get("interval", "4h")
        strategy_id = req.get("strategy", "trend_rider")
        candles = int(req.get("candles", 3000))
        leverage = float(req.get("leverage", 2.0))
        risk_pct = float(req.get("risk_pct", 0.02))
        res = self._backtest_single_symbol(symbol, interval, strategy_id, leverage, risk_pct, candles)
        self.send_json({"success": True, **res})

    def handle_funding_simulate(self, req: Dict[str, Any]):
        symbol = req.get("symbol", "BTCUSDT").upper()
        capital = float(req.get("capital", 1000.0))
        funding_rate_pct = float(req.get("funding_rate_pct", 0.15))
        holding_intervals = int(req.get("intervals", 1)) # default 1 interval = 8h hit and run
        
        # Gross funding payout
        # Payout per interval = capital * (funding_rate_pct / 100)
        payout_per_interval = capital * (funding_rate_pct / 100.0)
        total_gross_payout = payout_per_interval * holding_intervals
        
        # Roundtrip taker fee: 0.05% spot buy + 0.05% spot sell + 0.05% futures short + 0.05% futures close
        # Total taker fee = capital * 0.0010 (0.10%)
        taker_fee = capital * 0.0010
        net_profit = total_gross_payout - taker_fee
        roi_pct = (net_profit / capital) * 100.0
        apy = (funding_rate_pct * 3 * 365)
        
        self.send_json({
            "success": True,
            "symbol": symbol,
            "capital": capital,
            "funding_rate_pct": funding_rate_pct,
            "holding_intervals": holding_intervals,
            "holding_duration_hours": holding_intervals * 8,
            "gross_payout_usd": round(total_gross_payout, 4),
            "roundtrip_fee_usd": round(taker_fee, 4),
            "net_profit_usd": round(net_profit, 4),
            "roi_pct": round(roi_pct, 4),
            "annualized_apy_pct": round(apy, 2),
            "break_even_rate_pct": 0.10,
            "is_profitable": net_profit > 0
        })

def run_server(port: int = 5000):
    server_address = ('', port)
    httpd = ThreadingHTTPServer(server_address, DashboardAPIHandler)
    httpd.daemon_threads = True
    print("========================================================================")
    print("  BINANCE FUTURES DASHBOARD SERVER IS RUNNING!")
    print(f"  URL: http://localhost:{port}")
    print("========================================================================")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server(5000)
