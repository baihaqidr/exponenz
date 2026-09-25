import sys
import pandas as pd
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from src.data_fetcher import fetch_binance_futures_klines
from src.strategies.pure_price_action_sweep import PurePriceActionLiquiditySweep
from src.backtester import BacktestEngine

print("=" * 85)
print("   🎯 TESTING PURE PRICE ACTION (ZERO INDICATOR) - NET R:R 1:2 FEE-ADJUSTED   ")
print("=" * 85)

pairs = ['ETHUSDT', 'SOLUSDT', 'BTCUSDT', 'DOGEUSDT', 'BNBUSDT', '1000PEPEUSDT', 'SUIUSDT']
timeframes = ['1m', '5m', '15m']

for tf in timeframes:
    print(f"\n--- TIMEFRAME {tf} ---")
    for sym in pairs:
        try:
            df = fetch_binance_futures_klines(sym, tf, total_candles=5000, use_cache=True)
            strat = PurePriceActionLiquiditySweep(swing_lookback=20, min_wick_ratio=1.2, rr_ratio=2.0)
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
            print(f"[{sym:12s} {tf:3s}] Net PnL: ${m['net_profit']:+8.2f} ({m['net_profit_pct']:+6.2f}%) | WR: {m['win_rate']:5.1f}% | PF: {m['profit_factor']:4.2f} | Trades: {m['total_trades']:3d} (W:{m['win_count']} L:{m['loss_count']}) | MaxDD: -{m['max_drawdown_pct']:.2f}%")
        except Exception as e:
            print(f"Error {sym} {tf}: {e}")

print("=" * 85)
