import os
import pandas as pd
import numpy as np
from src.indicators import calculate_supertrend, calculate_ema, calculate_adx
from src.backtester import BacktestEngine

top_pairs = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'DOGEUSDT', 'SUIUSDT', 'NEARUSDT', '1000PEPEUSDT', 'AVAXUSDT', 'LINKUSDT', 'XRPUSDT', 'ADAUSDT']

def test_optimized_supertrend(tf='4h', period=16, mult=4.0, adx_min=18.0, use_ema200=True):
    monthly_pnl_all = {}
    pair_results = {}
    
    for pair in top_pairs:
        filepath = f'data/{pair}_{tf}_3000.csv'
        if not os.path.exists(filepath):
            continue
        df = pd.read_csv(filepath)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        st, direction = calculate_supertrend(df, period=period, multiplier=mult)
        df['supertrend'] = st
        df['st_dir'] = direction
        adx = calculate_adx(df, 14).values
        ema200 = calculate_ema(df['close'], 200).values
        close_p = df['close'].values
        st_vals = st.values
        dir_vals = direction.values
        
        signals = np.zeros(len(df), dtype=int)
        sl_prices = np.full(len(df), np.nan)
        
        for i in range(1, len(df)):
            p_dir = dir_vals[i-1]
            c_dir = dir_vals[i]
            c = close_p[i]
            e200 = ema200[i]
            a = adx[i]
            s = st_vals[i]
            
            if c_dir == 1 and p_dir == -1 and a >= adx_min:
                if not use_ema200 or c >= e200:
                    signals[i] = 1
                    sl_prices[i] = s
            elif c_dir == -1 and p_dir == 1 and a >= adx_min:
                if not use_ema200 or c <= e200:
                    signals[i] = -1
                    sl_prices[i] = s
                    
        df['signal'] = signals
        df['sl_price'] = sl_prices
        df['tp_price'] = np.nan
        
        engine = BacktestEngine(initial_capital=1000.0, leverage=3.0, risk_per_trade_pct=0.02)
        res = engine.run(df)
        trades = res['trades_df']
        if not trades.empty:
            trades['month'] = pd.to_datetime(trades['exit_time']).dt.strftime('%Y-%m')
            m_pnl = trades.groupby('month')['net_pnl'].sum()
            for m, p in m_pnl.items():
                monthly_pnl_all[m] = monthly_pnl_all.get(m, 0.0) + p
        pair_results[pair] = res['metrics']
        
    tot_net = sum(m['net_profit'] for m in pair_results.values())
    tot_tr = sum(m['total_trades'] for m in pair_results.values())
    pos_m = sum(1 for p in monthly_pnl_all.values() if p > 0)
    tot_m = len(monthly_pnl_all)
    m_rate = (pos_m / tot_m * 100) if tot_m > 0 else 0
    print(f"ADX={adx_min:4.1f} | EMA200={str(use_ema200):5s} -> Net: ${tot_net:+8.2f} | Trades: {tot_tr:4d} | Pos Months: {pos_m}/{tot_m} ({m_rate:5.1f}%)", flush=True)

for adx in [12.0, 15.0, 18.0, 20.0, 25.0]:
    for ema in [True, False]:
        test_optimized_supertrend('4h', period=16, mult=4.0, adx_min=adx, use_ema200=ema)
