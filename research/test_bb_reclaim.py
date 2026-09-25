from src.strategy_registry import get_strategy_instance
from src.data_fetcher import fetch_fast_api_klines
from src.backtester import BacktestEngine

strat = get_strategy_instance('bb_reclaim_sniper')
engine = BacktestEngine(initial_capital=1000.0, leverage=3.0)

symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', '1000PEPEUSDT', 'DOGEUSDT', 'SUIUSDT']
timeframes = ['15m', '1h', '4h']

print("="*95)
print(f"{'SYMBOL':12} | {'TF':4} | {'TRADES':6} | {'WIN RATE':9} | {'NET PROFIT':12} | {'RETURN':9} | {'PF':5} | {'MAX DD':7}")
print("="*95)

for sym in symbols:
    for tf in timeframes:
        df = fetch_fast_api_klines(sym, tf, total_candles=1000)
        df_sig = strat.generate_signals(df)
        res = engine.run(df_sig)
        m = res['metrics']
        print(f"{sym:12} | {tf:4} | {m['total_trades']:6} | {m['win_rate']:8.1f}% | ${m['net_profit']:10.2f} | {m['net_profit_pct']:8.1f}% | {m['profit_factor']:5.2f} | {m['max_drawdown_pct']:6.1f}%")

print("="*95)
