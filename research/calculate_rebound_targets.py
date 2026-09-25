import sys
import pandas as pd
import numpy as np
from test_backtest_eth_15m import fetch_1year_15m_eth
from src.indicators import calculate_rsi, calculate_sma

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def run():
    df = fetch_1year_15m_eth()
    df['bb_mid'] = calculate_sma(df['close'], 20)
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
    df['rsi'] = calculate_rsi(df['close'], 14)
    
    entry_mask = (df['rsi'] < 30) & (df['close'] < df['bb_lower'])
    entry_indices = df[entry_mask].index.tolist()
    
    mfe_gains = []
    mid_bb_gains = []
    
    for idx in entry_indices:
        entry_p = df.loc[idx, 'close']
        sub = df.loc[idx+1:idx+24] # 6 jam ke depan (24 lilin 15m)
        if len(sub) == 0:
            continue
        max_p = sub['high'].max()
        mfe_gains.append((max_p - entry_p) / entry_p * 100)
        
        mid_hits = sub[sub['close'] >= sub['bb_mid']]
        if not mid_hits.empty:
            mid_p = mid_hits.iloc[0]['close']
            mid_bb_gains.append((mid_p - entry_p) / entry_p * 100)
            
    s_mfe = pd.Series(mfe_gains)
    s_mid = pd.Series(mid_bb_gains)
    
    print("\n" + "="*70)
    print("🎯 ANALISIS PANTULAN HARGA SETELAH BUY THE DIP (15M ETHUSDT 1 TAHUN)")
    print("="*70)
    print(f"1. POTENSI PANTULAN HARGA TERTINGGI (Peak / MFE dalam 6 Jam):")
    print(f"   • Rata-rata Kenaikan Maksimal : +{s_mfe.mean():.2f}%")
    print(f"   • Median Kenaikan Maksimal    : +{s_mfe.median():.2f}%")
    print(f"   • Potensi Tertinggi           : +{s_mfe.max():.2f}%")
    print("-" * 70)
    print(f"2. JIKA TAKE PROFIT DI GARIS TENGAH BOLLINGER BAND (Middle Band / SMA 20):")
    print(f"   • Probabilitas Tercapai (Win Rate Touch Mid-BB) : {len(mid_bb_gains)/len(entry_indices)*100:.1f}% ({len(mid_bb_gains)} dari {len(entry_indices)} sinyal)")
    print(f"   • Rata-rata Profit saat kena Middle Band       : +{s_mid.mean():.2f}%")
    print(f"   • Median Profit saat kena Middle Band          : +{s_mid.median():.2f}%")
    print("="*70)

if __name__ == "__main__":
    run()
