import sys
import pandas as pd
import numpy as np
from test_1year_1m_strategy_pnl import fetch_1year_1m_data
from src.indicators import calculate_rsi, calculate_ema, calculate_atr

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def fast_simulate(closes, highs, lows, enter_signals, sl_arr, tp_arr, fee_rate=0.0005, slippage=0.0002, init_cap=5000.0, lev=3.0, pos_pct=0.25):
    capital = init_cap
    n = len(closes)
    in_pos = False
    entry_p = 0.0
    curr_sl = 0.0
    curr_tp = 0.0
    qty = 0.0
    trades = 0
    wins = 0
    peak = capital
    max_dd = 0.0

    for i in range(n):
        c = closes[i]
        h = highs[i]
        l = lows[i]
        
        if in_pos:
            exit_p = 0.0
            # Cek SL
            if l <= curr_sl:
                exit_p = curr_sl * (1.0 - slippage)
            elif h >= curr_tp:
                exit_p = curr_tp * (1.0 - slippage)
                
            if exit_p > 0:
                fee = (exit_p * qty) * fee_rate
                net = (exit_p - entry_p) * qty - fee
                capital += net
                trades += 1
                if net > 0:
                    wins += 1
                in_pos = False
                if capital > peak:
                    peak = capital
                dd = (peak - capital) / peak * 100.0
                if dd > max_dd:
                    max_dd = dd
                if capital <= 10:
                    break
                    
        if not in_pos and capital > 10 and enter_signals[i] == 1:
            entry_p = c * (1.0 + slippage)
            curr_sl = sl_arr[i]
            curr_tp = tp_arr[i]
            if curr_sl < entry_p:
                notional = capital * pos_pct * lev
                qty = notional / entry_p
                entry_fee = notional * fee_rate
                capital -= entry_fee
                in_pos = True

    wr = (wins / trades * 100.0) if trades > 0 else 0.0
    net_pnl = capital - init_cap
    return trades, wins, wr, net_pnl, max_dd

def test_1m_quant_models(symbol='SOLUSDT'):
    df = fetch_1year_1m_data(symbol)
    if df is None:
        return

    # 1. Higher-Timeframe (1H) Trend Anchor
    df_1h = df.set_index('timestamp').resample('1h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()
    df_1h['ema_200_1h'] = calculate_ema(df_1h['close'], 200)
    df_1h['ema_50_1h'] = calculate_ema(df_1h['close'], 50)
    
    df = pd.merge_asof(df, df_1h[['timestamp', 'ema_200_1h', 'ema_50_1h']], on='timestamp', direction='backward')
    
    df['ema_7'] = calculate_ema(df['close'], 7)
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['atr_14'] = calculate_atr(df, 14)
    df['atr_ma'] = df['atr_14'].rolling(100).mean()

    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    rsis = df['rsi'].values
    ema7s = df['ema_7'].values
    ema200_1h = df['ema_200_1h'].values
    ema50_1h = df['ema_50_1h'].values
    atrs = df['atr_14'].values
    atr_mas = df['atr_ma'].values
    n = len(df)

    models = {
        "1. Raw Single-Candle SL (Tanpa Filter)": {"macro": False, "sl_type": "candle_low", "rr": 2.0},
        "2. Multi-Timeframe (1H Trend + Candle Low SL)": {"macro": True, "sl_type": "candle_low", "rr": 2.0},
        "3. Multi-Timeframe + ATR Buffer (SL 1.5x, TP 3.0x ATR)": {"macro": True, "sl_type": "atr", "atr_sl": 1.5, "atr_tp": 3.0},
        "4. Volatility Expansion Scalper (ATR>MA + 1H Trend + 1:2.5 RR)": {"macro": True, "vol_filter": True, "sl_type": "atr", "atr_sl": 1.2, "atr_tp": 3.0},
        "5. High R:R Momentum Ride (1H Trend + SL 1.5x ATR, TP 4.5x ATR)": {"macro": True, "sl_type": "atr", "atr_sl": 1.5, "atr_tp": 4.5}
    }
    
    print("="*100)
    print(f"📊 PERBANDINGAN RESOURCE & ARSITEKTUR STRATEGI 1-MENIT (1m) 1 TAHUN PENUH : {symbol}")
    print("="*100)
    print(f"{'Arsitektur / Model 1m':<48} | {'Trades':<7} | {'Win Rate':<9} | {'Net PnL ($)':<14} | {'Max DD'}")
    print("-" * 100)
    
    for name, cfg in models.items():
        armed = False
        enter_long = np.zeros(n, dtype=int)
        tp = np.zeros(n, dtype=float)
        sl = np.zeros(n, dtype=float)
        
        for i in range(1, n):
            rsi = rsis[i]
            c = closes[i]
            low_c = lows[i]
            ema7 = ema7s[i]
            prev_c = closes[i-1]
            prev_ema7 = ema7s[i-1]
            macro_ema = ema200_1h[i]
            macro_50 = ema50_1h[i]
            atr_val = atrs[i]
            atr_ma_val = atr_mas[i]
            
            if np.isnan(rsi) or np.isnan(ema7) or np.isnan(atr_val):
                continue
                
            if rsi < 30.0:
                armed = True
                
            if armed and prev_c <= prev_ema7 and c > ema7:
                valid = True
                if cfg.get("macro"):
                    if np.isnan(macro_ema) or np.isnan(macro_50) or c < macro_ema or macro_50 < macro_ema:
                        valid = False
                if cfg.get("vol_filter"):
                    if np.isnan(atr_ma_val) or atr_val < 1.1 * atr_ma_val:
                        valid = False
                        
                if valid:
                    enter_long[i] = 1
                    if cfg["sl_type"] == "candle_low":
                        risk = c - low_c
                        sl[i] = low_c
                        tp[i] = c + (risk * cfg["rr"])
                    elif cfg["sl_type"] == "atr":
                        sl[i] = c - (cfg["atr_sl"] * atr_val)
                        tp[i] = c + (cfg["atr_tp"] * atr_val)
                armed = False
                
        trades, wins, wr, net_pnl, max_dd = fast_simulate(closes, highs, lows, enter_long, sl, tp)
        pnl_str = f"{'+' if net_pnl>=0 else ''}${net_pnl:,.2f}"
        st = "🟢 PROFIT" if net_pnl > 0 else "🔴 LOSS"
        print(f"{name:<48} | {trades:<7} | {wr:>6.1f}%  | {pnl_str:>13} | -{max_dd:.1f}% [{st}]")

if __name__ == "__main__":
    for s in ['SOLUSDT', 'BTCUSDT', 'ETHUSDT']:
        test_1m_quant_models(s)
