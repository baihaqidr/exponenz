import sys
import time
import requests
import urllib3
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

urllib3.disable_warnings()

def check_symbol(sym):
    try:
        # Check spot/futures market data on Binance Vision
        spot_sym = sym
        for prefix in ['1000', '1000000']:
            if sym.startswith(prefix):
                spot_sym = sym[len(prefix):]
                break

        url = f"https://data-api.binance.vision/api/v3/klines?symbol={spot_sym}&interval=1d&limit=370"
        r = requests.get(url, verify=False, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) >= 250:
                p_start = float(data[0][4]) # Close price 1 year ago
                p_now = float(data[-1][4])   # Current live price
                p_high = max(float(x[2]) for x in data) # 1-year high
                p_low = min(float(x[3]) for x in data)  # 1-year low
                
                ret_1y = ((p_now - p_start) / p_start) * 100
                peak_gain = ((p_high - p_start) / p_start) * 100
                from_low_gain = ((p_now - p_low) / p_low) * 100
                
                return {
                    "symbol": sym,
                    "return_1y": ret_1y,
                    "start_price": p_start,
                    "now_price": p_now,
                    "high_1y": p_high,
                    "peak_gain": peak_gain,
                    "gain_from_low": from_low_gain,
                    "candles_count": len(data)
                }
    except Exception:
        pass
    return None

def main():
    print("="*75)
    print("🔍 MEMINDAI SELURUH PASAR CRYPTO UNTUK MENEMUKAN TOP 10 BULLISH 1 TAHUN...")
    print("="*75)
    
    r = requests.get("https://testnet.binancefuture.com/fapi/v1/exchangeInfo", verify=False, timeout=8).json()
    symbols = [s['symbol'] for s in r['symbols'] if s['symbol'].endswith('USDT') and s['status'] == 'TRADING']
    print(f"Total pair futures yang dipindai: {len(symbols)} koin...")
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(check_symbol, symbols))
        
    valid_results = [r for r in results if r is not None]
    df = pd.DataFrame(valid_results)
    
    df_top = df.sort_values('return_1y', ascending=False).reset_index(drop=True)
    
    print("\n" + "="*85)
    print("🚀 TOP 10 KOIN PALING BULLISH 1 TAHUN TERAKHIR (BINANCE) 🚀")
    print("="*85)
    print(f"{'Rank':<5} | {'Symbol':<14} | {'1Y Return (%)':<15} | {'Harga 1 Thn Lalu':<16} | {'Harga Saat Ini':<15} | {'Peak Kenaikan'}")
    print("-" * 85)
    for i, row in df_top.head(10).iterrows():
        print(f"{i+1:<5} | {row['symbol']:<14} | {row['return_1y']:>+13.2f}% | ${row['start_price']:<15.4f} | ${row['now_price']:<14.4f} | +{row['peak_gain']:.1f}%")
    print("="*85)

if __name__ == "__main__":
    main()
