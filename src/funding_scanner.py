import requests
import urllib3
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import urllib3.util.connection as urllib_conn

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Real Binance Global Cloudfront IP (Bypass Indonesian ISP DNS block)
REAL_BINANCE_IP = '108.138.141.24'
old_create_connection = urllib_conn.create_connection

def custom_create_connection(address, *args, **kwargs):
    host, port = address
    if 'binance.com' in host:
        return old_create_connection((REAL_BINANCE_IP, port), *args, **kwargs)
    return old_create_connection(address, *args, **kwargs)

urllib_conn.create_connection = custom_create_connection

class FundingRateScanner:
    """
    Scanner Live Official Binance Arbitrage Hub (100% Direct Official Binance Servers).
    Membaca langsung Live Premium Index Futures, Live Spot Ticker, 
    menghitung Basis Spread presisi, dan memisahkan Positive Carry vs Reverse Carry.
    """
    def __init__(self, min_volume_24h_usd: float = 100_000):
        self.min_volume_24h_usd = min_volume_24h_usd

    def get_live_funding_rates(self) -> List[Dict[str, Any]]:
        results = []
        try:
            # 1. Fetch Official Binance Futures Premium Index
            r_fut = requests.get('https://fapi.binance.com/fapi/v1/premiumIndex', verify=False, timeout=8).json()
            if not isinstance(r_fut, list):
                return []

            # 2. Fetch Official Binance Spot Ticker Prices
            r_spot_raw = requests.get('https://api.binance.com/api/v3/ticker/price', verify=False, timeout=8).json()
            r_spot = {x['symbol']: float(x['price']) for x in r_spot_raw if isinstance(x, dict) and 'symbol' in x}

            now_ts = int(time.time() * 1000)

            for f in r_fut:
                if not isinstance(f, dict): continue
                sym = f.get('symbol', '')
                if not sym.endswith('USDT'): continue

                raw_rate = float(f.get('lastFundingRate', 0.0))
                funding_pct = raw_rate * 100.0
                fut_price = float(f.get('markPrice', 0.0))
                next_time_ms = int(f.get('nextFundingTime', 0))

                spot_price = r_spot.get(sym, None)
                has_spot = spot_price is not None

                # Hitung Spread
                if spot_price and fut_price > 0:
                    spread_pct = ((spot_price - fut_price) / fut_price) * 100.0
                else:
                    spread_pct = 0.0

                # Hitung Countdown Waktu Gajian
                seconds_left = max(0, int((next_time_ms - now_ts) / 1000))
                hours = seconds_left // 3600
                minutes = (seconds_left % 3600) // 60
                seconds = seconds_left % 60
                countdown_str = f"{hours:02d}h {minutes:02d}m {seconds:02d}s"

                # Hitung APY Tahunan (Berdasarkan interval: jika countdown < 1h berarti 1h/4h/8h interval)
                # Standar APR tahunan
                apy = abs(funding_pct) * 3 * 365 # 3x sehari dasar
                if abs(funding_pct) > 0.20:
                    # Koin interval 1 jam (24x sehari)
                    apy = abs(funding_pct) * 24 * 365

                # Kategori Carry
                if funding_pct >= 0:
                    carry_type = "POSITIVE CARRY"
                    action_guide = "Beli Spot + Short Futures 1x"
                    action_badge_color = "#3b82f6"
                else:
                    carry_type = "REVERSE CARRY"
                    action_guide = "Beli Futures 1x + Short Spot"
                    action_badge_color = "#10b981"

                # Status Arbitrase
                if has_spot:
                    spot_badge = "SPOT AVAILABLE"
                    spot_color = "#10b981"
                    if abs(funding_pct) >= 0.30:
                        status = "🔥 SUPER ARBITRAGE"
                        status_color = "#10b981"
                        recommendation = f"Peluang Emas: APR {apy:,.0f}%. Spread {abs(spread_pct):.2f}%. {action_guide}."
                    elif abs(funding_pct) >= 0.08:
                        status = "HOT ARBITRAGE"
                        status_color = "#3b82f6"
                        recommendation = f"Valid Arbitrase: {action_guide}. Bebas arah harga."
                    else:
                        status = "NORMAL"
                        status_color = "#64748b"
                        recommendation = f"Funding normal ({funding_pct:.4f}%)."
                else:
                    spot_badge = "FUTURES ONLY"
                    spot_color = "#f43f5e"
                    status = "FUTURES ONLY"
                    status_color = "#f43f5e"
                    recommendation = "Tidak ada di Spot Binance. Tidak bisa arbitrase Spot-Futures."

                # Hitung Estimasi Cuan Modal $1,000
                gross_yield_1k = 1000.0 * (abs(funding_pct) / 100.0)
                roundtrip_fee_1k = 1000.0 * 0.0010
                net_yield_1k = gross_yield_1k - roundtrip_fee_1k

                results.append({
                    "symbol": sym,
                    "funding_rate": funding_pct,
                    "funding_rate_raw": raw_rate,
                    "apy": apy,
                    "carry_type": carry_type,
                    "action_guide": action_guide,
                    "action_badge_color": action_badge_color,
                    "futures_price": fut_price,
                    "spot_price": spot_price if spot_price else fut_price,
                    "spread_pct": spread_pct,
                    "has_spot": has_spot,
                    "spot_badge": spot_badge,
                    "spot_color": spot_color,
                    "countdown": countdown_str,
                    "next_settle_time": datetime.fromtimestamp(next_time_ms/1000, tz=timezone(timedelta(hours=7))).strftime('%H:%M WIB'),
                    "status": status,
                    "status_color": status_color,
                    "recommendation": recommendation,
                    "gross_profit_1k": gross_yield_1k,
                    "net_profit_1k": net_yield_1k,
                    "volume_24h": 1_000_000
                })

            # Urutkan berdasarkan bunga tertinggi mutlak
            results.sort(key=lambda x: (1 if x['has_spot'] else 0, abs(x['funding_rate'])), reverse=True)
            return results

        except Exception as e:
            print(f"Error fetching official Binance funding rates: {e}")
            return []
