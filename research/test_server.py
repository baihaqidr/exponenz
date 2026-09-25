import urllib.request
import json
import time

t0 = time.time()
req = urllib.request.Request('http://localhost:5000/api/matrix', data=b'{}', headers={'Content-Type': 'application/json'})
res = urllib.request.urlopen(req)
m = json.loads(res.read())
t1 = time.time()

print(f"Matrix loaded in {t1 - t0:.2f} seconds!")
print(f"Total Rows: {len(m['matrix_rows'])}")
print(f"Total Months: {len(m['months'])}")
for r in m['matrix_rows']:
    print(f"  • {r['symbol']}: Net PnL +${r['net_profit']} (WR: {r['win_rate']}%, Trades: {r['total_trades']})")
