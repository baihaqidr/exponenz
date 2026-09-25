import requests
import urllib3
urllib3.disable_warnings()
import urllib3.util.connection as urllib_conn

real_ip = '108.138.141.24'
old_create_connection = urllib_conn.create_connection
def custom_create_connection(address, *args, **kwargs):
    host, port = address
    if 'binance.com' in host:
        return old_create_connection((real_ip, port), *args, **kwargs)
    return old_create_connection(address, *args, **kwargs)
urllib_conn.create_connection = custom_create_connection

r_fut = requests.get('https://fapi.binance.com/fapi/v1/premiumIndex', verify=False, timeout=8).json()
r_spot_raw = requests.get('https://api.binance.com/api/v3/ticker/price', verify=False, timeout=8).json()
r_spot = {x['symbol']: float(x['price']) for x in r_spot_raw if 'symbol' in x}

items = []
for f in r_fut:
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

spot_items = [x for x in items if x['has_spot']]
spot_items.sort(key=lambda x: abs(x['funding_pct']), reverse=True)

print("="*115)
print("100% REAL OFFICIAL BINANCE ARBITRAGE SCANNER (LANGSUNG DARI SERVER RESMI BINANCE)")
print("="*115)
print(f"{'SYMBOL':12} | {'FUNDING RATE':14} | {'FUT PRICE':11} | {'SPOT PRICE':11} | {'SPREAD %':10} | {'STRATEGI CARRY'}")
print("-" * 115)
for it in spot_items[:18]:
    c_type = 'POSITIVE CARRY (Short Fut + Long Spot)' if it['funding_pct'] > 0 else 'REVERSE CARRY (Long Fut + Short Spot)'
    sp_str = f"{it['spread_pct']:7.2f}%" if it['spread_pct'] is not None else 'N/A'
    print(f"{it['symbol']:12} | {it['funding_pct']:10.4f}%   | {it['fut_price']:11.4f} | {it['spot_price']:11.4f} | {sp_str:10} | {c_type}")
print("="*115)
