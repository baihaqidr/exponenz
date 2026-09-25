import sys
import time
import requests
import urllib3
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

urllib3.disable_warnings()

def check_recent_rally(sym):
    try:
        spot_sym = sym
        for prefix in ['1000000', '1000']:
            if sym.startswith(prefix):
                spot_sym = sym[len(prefix):]
                break

        # Ambil 35 lilin harian terakhir
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={spot_sym}&interval=1d&limit=35"
        r = requests.get(url, verify=False, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) >= 30:
                p_now = float(data[-1][4])       # Harga hari ini
                p_1d = float(data[-2][4])        # 1 hari lalu
                p_3d = float(data[-4][4])        # 3 hari lalu
                p_7d = float(data[-8][4])        # 7 hari lalu
                p_30d = float(data[-31][4])      # 30 hari lalu
                
                vol_24h = float(data[-1][5]) * p_now # Estimasi Volume 24h USD
                
                chg_24h = ((p_now - p_1d) / p_1d) * 100
                chg_3d = ((p_now - p_3d) / p_3d) * 100
                chg_7d = ((p_now - p_7d) / p_7d) * 100
                chg_30d = ((p_now - p_30d) / p_30d) * 100
                
                # Momentum Score: Pembobotan momentum recent
                momentum_score = (chg_24h * 0.4) + (chg_3d * 0.3) + (chg_7d * 0.2) + (chg_30d * 0.1)
                
                return {
                    "symbol": sym,
                    "price_now": p_now,
                    "chg_24h": chg_24h,
                    "chg_3d": chg_3d,
                    "chg_7d": chg_7d,
                    "chg_30d": chg_30d,
                    "vol_24h_usd": vol_24h,
                    "momentum_score": momentum_score
                }
    except Exception:
        pass
    return None

def main():
    print("="*85)
    print("🚀 MEMINDAI 500+ PAIR BINANCE UNTUK MENEMUKAN KOIN YANG BARU-BARU INI RALLY...")
    print("="*85)
    
    r = requests.get("https://testnet.binancefuture.com/fapi/v1/exchangeInfo", verify=False, timeout=8).json()
    symbols = [s['symbol'] for s in r['symbols'] if s['symbol'].endswith('USDT') and s['status'] == 'TRADING']
    print(f"Total pair futures yang dipindai: {len(symbols)} koin...")
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(check_recent_rally, symbols))
        
    valid_results = [r for r in results if r is not None]
    df = pd.DataFrame(valid_results)
    
    # 1. Top 10 Rally 7 Hari Terakhir (Hot This Week)
    df_7d = df.sort_values('chg_7d', ascending=False).reset_index(drop=True)
    
    print("\n" + "="*95)
    print("🔥 TOP 10 KOIN RALLY TERKUAT 7 HARI TERAKHIR (HOT THIS WEEK) 🔥")
    print("="*95)
    print(f"{'Rank':<5} | {'Symbol':<14} | {'Harga':<12} | {'7D Gain (%)':<14} | {'3D Gain (%)':<14} | {'24H Gain (%)':<14} | {'30D Gain (%)'}")
    print("-" * 95)
    for i, row in df_7d.head(10).iterrows():
        print(f"{i+1:<5} | {row['symbol']:<14} | ${row['price_now']:<11.4f} | {row['chg_7d']:>+12.2f}% | {row['chg_3d']:>+12.2f}% | {row['chg_24h']:>+12.2f}% | {row['chg_30d']:>+12.2f}%")
    print("="*95)

    # 2. Top 10 Rally 30 Hari Terakhir (Sustained Momentum This Month)
    df_30d = df.sort_values('chg_30d', ascending=False).reset_index(drop=True)
    print("\n" + "="*95)
    print("💎 TOP 10 KOIN RALLY TERKUAT 30 HARI TERAKHIR (MONTHLY LEADERS) 💎")
    print("="*95)
    print(f"{'Rank':<5} | {'Symbol':<14} | {'Harga':<12} | {'30D Gain (%)':<14} | {'7D Gain (%)':<14} | {'24H Gain (%)':<14} | {'Status'}")
    print("-" * 95)
    for i, row in df_30d.head(10).iterrows():
        print(f"{i+1:<5} | {row['symbol']:<14} | ${row['price_now']:<11.4f} | {row['chg_30d']:>+12.2f}% | {row['chg_7d']:>+12.2f}% | {row['chg_24h']:>+12.2f}% | 🔥 RALLY AKTIF")
    print("="*95)

if __name__ == "__main__":
    main()
