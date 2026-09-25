from src.funding_scanner import FundingRateScanner
scanner = FundingRateScanner()
data = scanner.get_live_funding_rates()
print(f"Total Live Pairs from Official Binance: {len(data)}")
print("="*110)
print(f"{'SYMBOL':12} | {'FUNDING RATE':14} | {'APR TAHUNAN':12} | {'SPREAD %':10} | {'STRATEGI AKSI'}")
print("="*110)
for d in data[:12]:
    print(f"{d['symbol']:12} | {d['funding_rate']:10.4f}%   | {d['apy']:10.1f}% | {d['spread_pct']:7.2f}%   | {d['action_guide']}")
print("="*110)
