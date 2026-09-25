import sys
import pandas as pd
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from src.data_fetcher import fetch_binance_futures_klines
from src.strategies.pure_market_structure import PureMarketStructurePro
from src.backtester import BacktestEngine

print("=" * 85)
print("   👑 PURE MARKET STRUCTURE PRO (SWEEP + HIGHER LOWS) - NET R:R 1:2   ")
print("=" * 85)

for tf in ['1m', '5m', '15m']:
    print(f"\n--- TIMEFRAME {tf} ---")
    for sym in ['SUIUSDT', 'ETHUSDT', 'SOLUSDT', 'DOGEUSDT', 'BTCUSDT']:
        try:
            df = fetch_binance_futures_klines(sym, tf, total_candles=5000, use_cache=True)
            strat = PureMarketStructurePro(lookback=15, min_wick_ratio=1.0, rr_ratio=2.0)
            df_sig = strat.generate_signals(df)
            
            engine = BacktestEngine(
                initial_capital=1000.0,
                leverage=3.0,
                risk_per_trade_pct=0.02,
                fixed_pos_size_pct=0.5,
                fee_rate=0.0005,
                slippage_pct=0.0002
            )
            res = engine.run(df_sig)
            m = res['metrics']
            print(f"[{sym:10s} {tf:3s}] Net PnL: ${m['net_profit']:+8.2f} ({m['net_profit_pct']:+6.2f}%) | WR: {m['win_rate']:5.1f}% | PF: {m['profit_factor']:4.2f} | Trades: {m['total_trades']:2d} (W:{m['win_count']:2d} L:{m['loss_count']:2d}) | MaxDD: -{m['max_drawdown_pct']:.2f}%")
        except Exception as e:
            print(f"Err {sym} {tf}: {e}")

print("=" * 85)
