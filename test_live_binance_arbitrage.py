import requests
import urllib3
urllib3.disable_warnings()

r_fut = requests.get('https://fapi.binance.com/fapi/v1/premiumIndex', verify=False, timeout=8).json()
r_spot_raw = requests.get('https://data-api.binance.vision/api/v3/ticker/price', verify=False, timeout=8).json()
r_spot = {x['symbol']: float(x['price']) for x in r_spot_raw if isinstance(x, dict) and 'symbol' in x}

items = []
for f in r_fut:
    if not isinstance(f, dict): continue
    sym = f.get('symbol', '')
    if not sym.endswith('USDT'): continue
    rate = float(f.get('lastFundingRate', 0.0)) * 100.0
    fut_price = float(f.get('markPrice', 0.0))
    idx_price = float(f.get('indexPrice', 0.0))
    next_time = int(f.get('nextFundingTime', 0))
    
    spot_price = r_spot.get(sym, None)
    has_spot = spot_price is not None
    spread_pct = ((spot_price - fut_price) / fut_price * 100.0) if spot_price else None
    
    items.append({
        'symbol': sym,
        'funding_pct': rate,
        'fut_price': fut_price,
        'spot_price': spot_price,
        'spread_pct': spread_pct,
        'has_spot': has_spot,
        'next_time': next_time
    })

items.sort(key=lambda x: abs(x['funding_pct']), reverse=True)

print("="*105)
print(f"{'SYMBOL':12} | {'FUNDING %':11} | {'FUT PRICE':10} | {'SPOT PRICE':10} | {'SPREAD %':10} | {'CARRY TYPE':15} | {'SPOT'}")
print("="*105)
for it in items[:20]:
    c_type = 'POSITIVE CARRY' if it['funding_pct'] > 0 else 'REVERSE CARRY'
    sp_str = f"{it['spread_pct']:7.2f}%" if it['spread_pct'] is not None else 'N/A'
    spot_str = f"{it['spot_price']:9.4f}" if it['spot_price'] is not None else 'No Spot'
    spot_badge = 'AVAILABLE' if it['has_spot'] else 'FUTURES ONLY'
    print(f"{it['symbol']:12} | {it['funding_pct']:9.4f}% | {it['fut_price']:9.4f} | {spot_str} | {sp_str:10} | {c_type:15} | {spot_badge}")
print("="*105)
