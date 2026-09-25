import requests
import urllib3

urllib3.disable_warnings()

# 1. Spot symbols from Binance Public API
r_spot = requests.get('https://data-api.binance.vision/api/v3/exchangeInfo', verify=False, timeout=6)
spot_symbols = {s['symbol'] for s in r_spot.json().get('symbols', []) if s.get('status') == 'TRADING' and s.get('quoteAsset') == 'USDT'}

# 2. Binance Futures data
r_fut = requests.get('https://api.coingecko.com/api/v3/derivatives', verify=False, timeout=6)
binance_futures = [d for d in r_fut.json() if d.get('market') == 'Binance (Futures)' and d.get('symbol', '').endswith('USDT')]

matched = []
unmatched = []
for f in binance_futures:
    sym = f['symbol']
    rate = float(f.get('funding_rate', 0.0)) * 100
    basis = float(f.get('basis', 0.0))
    has_spot = sym in spot_symbols
    item = {
        'symbol': sym,
        'funding_pct': rate,
        'basis_pct': basis,
        'price': float(f.get('price', 0.0)),
        'index': float(f.get('index', 0.0)),
        'has_spot': has_spot,
        'vol': float(f.get('volume_24h', 0.0))
    }
    if has_spot:
        matched.append(item)
    else:
        unmatched.append(item)

matched.sort(key=lambda x: x['funding_pct'], reverse=True)
unmatched.sort(key=lambda x: x['funding_pct'], reverse=True)

print(f"Total Binance Futures: {len(binance_futures)} | Available on Spot: {len(matched)} | Futures-Only: {len(unmatched)}")
print("\n--- TOP 10 ARBITRAGE READY (EXISTS ON BOTH SPOT & FUTURES) ---")
for m in matched[:10]:
    print(f"{m['symbol']:14s} | Rate: {m['funding_pct']:+.4f}% | Basis: {m['basis_pct']:+.3f}% | Futures Price: {m['price']} | Spot Index: {m['index']} | Vol: ${m['vol']/1e6:.1f}M")

print("\n--- TOP 5 FUTURES-ONLY (CANNOT ARBITRAGE SPOT - DIRECTIONAL ONLY) ---")
for u in unmatched[:5]:
    print(f"{u['symbol']:14s} | Rate: {u['funding_pct']:+.4f}% | Basis: {u['basis_pct']:+.3f}% | Futures Price: {u['price']}")
