import requests, urllib3
urllib3.disable_warnings()

r = requests.get('https://api.coingecko.com/api/v3/derivatives', verify=False, timeout=8).json()
bf = [x for x in r if x.get('market') == 'Binance (Futures)']

# Also fetch Spot prices from data-api.binance.vision
spot_data = requests.get('https://data-api.binance.vision/api/v3/ticker/price', verify=False, timeout=8).json()
spot_dict = {x['symbol']: float(x['price']) for x in spot_data if isinstance(x, dict)}

targets = ['LSK', 'MTL', 'STEEM', 'CVC', 'PUNDIX', 'IOST', 'ARK', 'TUSDT', 'VTHO', 'GLM', 'ONG', 'HIFI', 'TRU', 'RVN']

print("="*105)
print(f"{'SYMBOL':12} | {'FUT PRICE':10} | {'SPOT PRICE':10} | {'SPREAD %':10} | {'FUNDING %':10} | {'SPOT AVAILABLE'}")
print("="*105)
for x in bf:
    sym = x.get('symbol', '')
    if any(t in sym for t in targets):
        fut_p = float(x.get('price', 0))
        fund_r = float(x.get('funding_rate', 0)) * 100.0
        
        # Check spot
        spot_p = spot_dict.get(sym, None)
        has_spot = spot_p is not None
        spread_str = f"{((spot_p - fut_p)/fut_p)*100.0:7.2f}%" if spot_p else "N/A"
        spot_str = f"{spot_p:9.4f}" if spot_p else "No Spot"
        
        print(f"{sym:12} | {fut_p:9.4f} | {spot_str} | {spread_str:10} | {fund_r:9.4f}% | {'YES' if has_spot else 'NO'}")
print("="*105)
