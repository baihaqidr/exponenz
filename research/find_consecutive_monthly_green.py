import sys
import requests
import urllib3
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

urllib3.disable_warnings()

def check_monthly_candles(sym):
    try:
        spot_sym = sym
        for prefix in ['1000000', '1000']:
            if sym.startswith(prefix):
                spot_sym = sym[len(prefix):]
                break

        url = f"https://data-api.binance.vision/api/v3/klines?symbol={spot_sym}&interval=1M&limit=14"
        r = requests.get(url, verify=False, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) >= 8:
                # Ambil 12 bulan terakhir (atau lilin yang tersedia)
                candles = data[-12:]
                
                green_months = 0
                max_consecutive_green = 0
                curr_consecutive_green = 0
                current_streak = 0
                monthly_changes = []
                
                for c in candles:
                    o = float(c[1])
                    cl = float(c[4])
                    chg_pct = (cl - o) / o * 100
                    monthly_changes.append(chg_pct)
                    
                    if cl > o:
                        green_months += 1
                        current_streak += 1
                        max_consecutive_green = max(max_consecutive_green, current_streak)
                    else:
                        current_streak = 0
                        
                # Current ongoing streak from the end
                curr_streak_back = 0
                for chg in reversed(monthly_changes):
                    if chg > 0:
                        curr_streak_back += 1
                    else:
                        break
                        
                return {
                    "symbol": sym,
                    "total_months": len(candles),
                    "green_months": green_months,
                    "green_ratio_pct": (green_months / len(candles)) * 100,
                    "max_consecutive_green": max_consecutive_green,
                    "current_green_streak": curr_streak_back,
                    "last_12m_return": ((float(candles[-1][4]) - float(candles[0][1])) / float(candles[0][1])) * 100,
                    "monthly_pattern": "".join(["🟢" if chg > 0 else "🔴" for chg in monthly_changes])
                }
    except Exception:
        pass
    return None

def main():
    print("="*85)
    print("🔍 MEMINDAI CANDLE BULANAN (1M) SELURUH KOIN UNTUK MENEMUKAN CONSECUTIVE GREEN TERBANYAK...")
    print("="*85)
    
    r = requests.get("https://testnet.binancefuture.com/fapi/v1/exchangeInfo", verify=False, timeout=8).json()
    symbols = [s['symbol'] for s in r['symbols'] if s['symbol'].endswith('USDT') and s['status'] == 'TRADING']
    print(f"Total pair yang dipindai: {len(symbols)} koin...")
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(check_monthly_candles, symbols))
        
    valid_results = [r for r in results if r is not None]
    df = pd.DataFrame(valid_results)
    
    # Sort by max_consecutive_green descending, then green_months descending
    df_sorted = df.sort_values(['max_consecutive_green', 'green_months', 'current_green_streak', 'last_12m_return'], ascending=[False, False, False, False]).reset_index(drop=True)
    
    print("\n" + "="*95)
    print("🚀 TOP 10 KOIN DENGAN CANDLE BULANAN HIJAU BERUNTUN (CONSECUTIVE GREEN) TERBANYAK 🚀")
    print("="*95)
    print(f"{'Rank':<5} | {'Symbol':<14} | {'Max Green Streak':<18} | {'Total Bulan Hijau':<18} | {'Streak Terkini':<15} | {'Pola 12 Bulan Terakhir'}")
    print("-" * 95)
    for i, row in df_sorted.head(15).iterrows():
        print(f"{i+1:<5} | {row['symbol']:<14} | {row['max_consecutive_green']:>2} Bulan Beruntun  | {row['green_months']:>2}/{row['total_months']} Bulan ({row['green_ratio_pct']:>4.0f}%) | {row['current_green_streak']:>2} Bulan Aktif   | {row['monthly_pattern']}")
    print("="*95)

if __name__ == "__main__":
    main()
