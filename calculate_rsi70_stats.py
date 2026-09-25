import sys
import pandas as pd
import numpy as np
from test_backtest_eth_15m import fetch_1year_15m_eth
from test_backtest_eth_5m import fetch_1year_5m_eth
from src.indicators import calculate_rsi, calculate_sma

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def analyze_rsi70_gain(tf_name: str, fetch_fn):
    df = fetch_fn()
    df['bb_mid'] = calculate_sma(df['close'], 20)
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
    df['rsi'] = calculate_rsi(df['close'], 14)
    
    # Kondisi entry RSI < 30 & Close < BB Lower
    entry_mask = (df['rsi'] < 30) & (df['close'] < df['bb_lower'])
    entry_indices = df[entry_mask].index.tolist()
    
    reached_70_gains = []
    max_drawdowns_during_hold = []
    hold_durations = []
    not_reached = 0
    
    i = 0
    while i < len(entry_indices):
        idx = entry_indices[i]
        entry_p = df.loc[idx, 'close']
        entry_t = df.loc[idx, 'timestamp']
        
        # Cari lilin berikutnya yang menyentuh RSI >= 70
        sub = df.loc[idx+1:idx+3000]
        hits = sub[sub['rsi'] >= 70]
        
        if not hits.empty:
            exit_idx = hits.index[0]
            exit_p = df.loc[exit_idx, 'close']
            exit_t = df.loc[exit_idx, 'timestamp']
            
            gain_pct = (exit_p - entry_p) / entry_p * 100
            min_p = df.loc[idx:exit_idx, 'low'].min()
            dd_pct = (min_p - entry_p) / entry_p * 100
            dur_hours = (exit_t - entry_t).total_seconds() / 3600
            
            reached_70_gains.append(gain_pct)
            max_drawdowns_during_hold.append(dd_pct)
            hold_durations.append(dur_hours)
            
            # Skip semua sinyal entry selama posisi ini masih aktif
            next_positions = [x for x in entry_indices if x > exit_idx]
            if next_positions:
                i = entry_indices.index(next_positions[0])
            else:
                break
        else:
            not_reached += 1
            i += 1
            
    sg = pd.Series(reached_70_gains)
    sd = pd.Series(max_drawdowns_during_hold)
    sh = pd.Series(hold_durations)
    
    print(f"\n" + "="*70)
    print(f"📊 HASIL ANALISIS TAKE PROFIT DI RSI 70 - TIMEFRAME {tf_name.upper()}")
    print("="*70)
    print(f"  • Total Sinyal Posisi Berhasil Capai RSI >= 70 : {len(sg)} trade")
    print(f"  • RATA-RATA TAKE PROFIT (Gain %)              : +{sg.mean():.2f}%")
    print(f"  • MEDIAN TAKE PROFIT                          : +{sg.median():.2f}%")
    print(f"  • MINIMUM GAIN (Terkecil saat RSI 70)         : {sg.min():+.2f}%")
    print(f"  • MAKSIMUM GAIN (Terbesar saat RSI 70)        : +{sg.max():.2f}%")
    print(f"  • Rata-rata Waktu Tahan (Durasi Hold)         : {sh.mean():.1f} Jam ({sh.median():.1f} Jam median)")
    print(f"  • Rata-rata Floating Minus sebelum tembus 70  : {sd.mean():.2f}%")
    print(f"  • Floating Minus Terparah sebelum tembus 70   : {sd.min():.2f}%")
    print("-" * 70)
    print("📈 Distribusi Persentase Profit saat RSI Menyentuh 70:")
    bins = [-50, 0, 1.0, 2.0, 3.0, 5.0, 10.0, 100.0]
    labels = ['< 0% (Minus)', '0% s/d 1%', '1% s/d 2%', '2% s/d 3%', '3% s/d 5%', '5% s/d 10%', '> 10%']
    dist = pd.cut(sg, bins=bins, labels=labels).value_counts().sort_index()
    for cat, val in dist.items():
        pct = (val / len(sg)) * 100
        print(f"    • {cat:<18}: {val:>3} trade ({pct:>5.1f}%)")
    print("="*70)

if __name__ == "__main__":
    analyze_rsi70_gain("15-Menit (15m)", fetch_1year_15m_eth)
    analyze_rsi70_gain("5-Menit (5m)", fetch_1year_5m_eth)
