from src.data_fetcher import fetch_binance_futures_klines
from src.strategy_registry import get_strategy_instance
from src.backtester import BacktestEngine

strat = get_strategy_instance('trend_rider_pure')
pairs = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'DOGEUSDT', '1000PEPEUSDT', 'SUIUSDT', 'NEARUSDT', 'AVAXUSDT', 'XRPUSDT', 'LINKUSDT', 'ADAUSDT']

print(f"{'PAIR':14} | {'AVG WIN':10} | {'AVG LOSS':10} | {'REALIZED R:R':15} | {'WIN RATE':10} | {'PROFIT FACTOR':13}")
print("-" * 80)
tot_win_usd = 0
tot_loss_usd = 0
wins_cnt = 0
losses_cnt = 0

for sym in pairs:
    df = fetch_binance_futures_klines(sym, '4h', 3000, use_cache=True)
    res = BacktestEngine(1000.0, 2.0, 0.02).run(strat.generate_signals(df))
    m = res['metrics']
    tot_win_usd += m['gross_profit']
    tot_loss_usd += m['gross_loss']
    wins_cnt += m['win_count']
    losses_cnt += m['loss_count']
    print(f"{sym:14} | +${m['avg_win']:<8.2f} | -${m['avg_loss']:<8.2f} | 1 : {m['risk_reward_ratio']:<11.2f} | {m['win_rate']:<9.1f}% | {m['profit_factor']:<13.2f}")

avg_win_all = tot_win_usd / wins_cnt if wins_cnt > 0 else 0
avg_loss_all = tot_loss_usd / losses_cnt if losses_cnt > 0 else 0
overall_rrr = avg_win_all / avg_loss_all if avg_loss_all > 0 else 0
overall_pf = tot_win_usd / tot_loss_usd if tot_loss_usd > 0 else 0
print("-" * 80)
print(f"{'TOTAL PORTFOLIO':14} | +${avg_win_all:<8.2f} | -${avg_loss_all:<8.2f} | 1 : {overall_rrr:<11.2f} | {(wins_cnt/(wins_cnt+losses_cnt)*100):<9.1f}% | {overall_pf:<13.2f}")
