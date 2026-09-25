import sys
import pandas as pd
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
from src.data_fetcher import fetch_binance_futures_klines
from src.strategies.trend_reclaim_sniper_1m import TrendReclaimSniperPro1M
from src.backtester import BacktestEngine

print("=" * 80)
print("   🎯 BENCHMARK TEST: 1M TREND RECLAIM SNIPER PRO (BINANCE FUTURES)   ")
print("=" * 80)

pairs = ['ETHUSDT', 'SOLUSDT', 'BTCUSDT', 'SYNUSDT', 'BNBUSDT', 'DOGEUSDT']

for sym in pairs:
    try:
        df = fetch_binance_futures_klines(sym, '1m', total_candles=3000, use_cache=True)
        strat = TrendReclaimSniperPro1M()
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
        print(f"[{sym:8s} 1m] Net Profit: ${m['net_profit']:+8.2f} ({m['net_profit_pct']:+6.2f}%) | WinRate: {m['win_rate']:5.1f}% | PF: {m['profit_factor']:4.2f} | Trades: {m['total_trades']:3d} (W:{m['win_count']} L:{m['loss_count']}) | MaxDD: -{m['max_drawdown_pct']:.2f}%")
    except Exception as e:
        print(f"Error {sym}: {e}")

print("=" * 75)
