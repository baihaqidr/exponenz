import pandas as pd
import numpy as np
from src.data_fetcher import fetch_fast_api_klines
from src.indicators import calculate_bollinger_bands

def backtest_bb_reclaim(df, bb_len=20, bb_std=2.0, rr=2.0, lock_be_at_rr1=True, trail_middle=True):
    upper, middle, lower = calculate_bollinger_bands(df['close'], length=bb_len, std_dev=bb_std)
    
    capital = 1000.0
    initial_capital = 1000.0
    leverage = 3.0
    risk_pct = 0.02 # 2% risk per trade
    fee_rate = 0.0005
    
    position = None
    entry_p = 0.0
    sl_p = 0.0
    tp_p = 0.0
    qty = 0.0
    trades = []
    
    open_p = df['open'].values
    high_p = df['high'].values
    low_p = df['low'].values
    close_p = df['close'].values
    time_p = df['timestamp'].values
    lower_p = lower.values
    upper_p = upper.values
    middle_p = middle.values
    
    for i in range(bb_len, len(df)):
        o, h, l, c = open_p[i], high_p[i], low_p[i], close_p[i]
        prev_o, prev_h, prev_l, prev_c = open_p[i-1], high_p[i-1], low_p[i-1], close_p[i-1]
        
        low_band = lower_p[i]
        up_band = upper_p[i]
        mid_band = middle_p[i]
        prev_low_band = lower_p[i-1]
        prev_up_band = upper_p[i-1]
        
        if np.isnan(low_band) or np.isnan(prev_low_band):
            continue
            
        # 1. Manage Active Position
        if position == 'LONG':
            # Check Trailing Middle Band
            if trail_middle and c > mid_band and mid_band > entry_p:
                sl_p = max(sl_p, mid_band)
            elif lock_be_at_rr1 and h >= entry_p + (entry_p - sl_p):
                sl_p = max(sl_p, entry_p * 1.001)
                
            # Check SL
            if l <= sl_p:
                exit_p = min(o, sl_p)
                pnl = (exit_p - entry_p) * qty - (exit_p * qty * fee_rate)
                capital += pnl
                trades.append({'type': 'LONG', 'pnl': pnl, 'win': pnl > 0, 'reason': 'SL/Trail'})
                position = None
            elif h >= tp_p:
                exit_p = max(o, tp_p)
                pnl = (exit_p - entry_p) * qty - (exit_p * qty * fee_rate)
                capital += pnl
                trades.append({'type': 'LONG', 'pnl': pnl, 'win': True, 'reason': 'TP Full'})
                position = None
                
        elif position == 'SHORT':
            if trail_middle and c < mid_band and mid_band < entry_p:
                sl_p = min(sl_p, mid_band)
            elif lock_be_at_rr1 and l <= entry_p - (sl_p - entry_p):
                sl_p = min(sl_p, entry_p * 0.999)
                
            if h >= sl_p:
                exit_p = max(o, sl_p)
                pnl = (entry_p - exit_p) * qty - (exit_p * qty * fee_rate)
                capital += pnl
                trades.append({'type': 'SHORT', 'pnl': pnl, 'win': pnl > 0, 'reason': 'SL/Trail'})
                position = None
            elif l <= tp_p:
                exit_p = min(o, tp_p)
                pnl = (entry_p - exit_p) * qty - (exit_p * qty * fee_rate)
                capital += pnl
                trades.append({'type': 'SHORT', 'pnl': pnl, 'win': True, 'reason': 'TP Full'})
                position = None
                
        # 2. Open Position if None
        if position is None:
            # Long Reclaim
            # Candle 1: close below lower band
            # Candle 2: close above lower band & green
            if prev_c < prev_low_band and c > low_band and c > o:
                entry_p = c
                sl_p = min(prev_l, l) * 0.999
                sl_dist = entry_p - sl_p
                if sl_dist > 0:
                    tp_p = entry_p + (sl_dist * rr)
                    risk_amt = capital * risk_pct
                    qty = min(risk_amt / sl_dist, (capital * 0.5 * leverage) / entry_p)
                    fee = entry_p * qty * fee_rate
                    capital -= fee
                    position = 'LONG'
                    
            # Short Reclaim
            # Candle 1: close above upper band
            # Candle 2: close below upper band & red
            elif prev_c > prev_up_band and c < up_band and c < o:
                entry_p = c
                sl_p = max(prev_h, h) * 1.001
                sl_dist = sl_p - entry_p
                if sl_dist > 0:
                    tp_p = entry_p - (sl_dist * rr)
                    risk_amt = capital * risk_pct
                    qty = min(risk_amt / sl_dist, (capital * 0.5 * leverage) / entry_p)
                    fee = entry_p * qty * fee_rate
                    capital -= fee
                    position = 'SHORT'
                    
    total_trades = len(trades)
    if total_trades == 0:
        return {'trades': 0, 'wr': 0, 'net_profit': 0, 'return_pct': 0}
    wins = sum(1 for t in trades if t['win'])
    wr = (wins / total_trades) * 100
    net_profit = capital - initial_capital
    return {'trades': total_trades, 'wr': wr, 'net_profit': net_profit, 'return_pct': (net_profit / initial_capital) * 100}

symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'DOGEUSDT', 'SUIUSDT', 'ADAUSDT']
for tf in ['15m', '1h', '4h']:
    print(f"\n--- TIMEFRAME {tf} ---")
    for sym in symbols:
        df = fetch_fast_api_klines(sym, tf, total_candles=1500)
        if df is not None and len(df) > 100:
            res = backtest_bb_reclaim(df, bb_len=20, bb_std=2.0, rr=2.0)
            print(f"{sym:12} | Trades: {res['trades']:3} | WR: {res['wr']:5.1f}% | NetPnL: ${res['net_profit']:7.2f} ({res['return_pct']:5.1f}%)")
