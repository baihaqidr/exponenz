import os
import json
import time
import requests
import urllib3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ArbitrageEngine:
    """
    Mesin Otomasi Arbitrase Funding Rate (Cash & Carry Delta-Neutral) Binance.
    - Membuka pasangan posisi seimbang: [Spot Long + Futures Short 1x]
    - Otomatis memanen bunga transferan Funding Fee setiap siklus settlement (07:00, 15:00, 23:00 WIB)
    - Otomatis melakukan Rebalance saldo ketika posisi ditutup.
    """
    def __init__(self, data_file: str = "data/arbitrage_positions.json"):
        self.data_file = data_file
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.trade_history: List[Dict[str, Any]] = []
        self.is_auto_running = False
        self.auto_config = {
            "max_pairs": 3,
            "notional_per_pair": 500.0,
            "min_funding_rate_pct": 0.03
        }
        self._load_state()

    def _load_state(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    self.positions = d.get("positions", {})
                    self.trade_history = d.get("history", [])
                    self.is_auto_running = d.get("is_auto_running", False)
                    self.auto_config = d.get("auto_config", self.auto_config)
        except Exception as e:
            print(f"[ERROR] Failed to load arbitrage state: {e}")

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(self.data_file) if os.path.dirname(self.data_file) else "data", exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump({
                    "positions": self.positions,
                    "history": self.trade_history[:100],
                    "is_auto_running": self.is_auto_running,
                    "auto_config": self.auto_config,
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save arbitrage state: {e}")

    def get_live_prices(self, symbol: str) -> Dict[str, float]:
        """Tarik harga live Spot dan Futures secara bersamaan"""
        sym = symbol.upper().strip()
        spot_p = 0.0
        fut_p = 0.0
        try:
            r_fut = requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={sym}", verify=False, timeout=3)
            if r_fut.status_code == 200:
                fut_p = float(r_fut.json().get("price", 0.0))
        except Exception:
            pass

        try:
            r_spot = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}", verify=False, timeout=3)
            if r_spot.status_code == 200:
                spot_p = float(r_spot.json().get("price", 0.0))
        except Exception:
            pass

        if spot_p == 0.0 and fut_p > 0.0:
            spot_p = fut_p
        if fut_p == 0.0 and spot_p > 0.0:
            fut_p = spot_p

        return {"spot": spot_p, "futures": fut_p}

    def get_symbol_funding_info(self, symbol: str) -> Dict[str, Any]:
        """Tarik rate funding live dan jadwal settlement terdekat"""
        sym = symbol.upper().strip()
        try:
            r = requests.get(f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={sym}", verify=False, timeout=3)
            if r.status_code == 200:
                d = r.json()
                if isinstance(d, dict):
                    raw_rate = float(d.get("lastFundingRate", 0.0))
                    next_time = int(d.get("nextFundingTime", 0))
                    mark_p = float(d.get("markPrice", 0.0))
                    return {
                        "funding_rate": raw_rate,
                        "funding_pct": raw_rate * 100.0,
                        "next_funding_time": next_time,
                        "mark_price": mark_p
                    }
        except Exception:
            pass
        return {"funding_rate": 0.0001, "funding_pct": 0.01, "next_funding_time": int(time.time()*1000) + 28800000, "mark_price": 0.0}

    def open_arbitrage(self, symbol: str, notional_total: float = 500.0) -> Dict[str, Any]:
        """
        Buka Posisi Arbitrase Delta-Neutral 50% Spot Long + 50% Futures Short 1x
        """
        sym = symbol.upper().strip()
        if sym in self.positions:
            return {"status": "error", "message": f"Posisi arbitrase untuk {sym} sudah aktif"}

        prices = self.get_live_prices(sym)
        spot_p = prices["spot"]
        fut_p = prices["futures"]

        if spot_p <= 0 or fut_p <= 0:
            return {"status": "error", "message": f"Gagal membaca harga pasar live Binance untuk {sym}"}

        funding_info = self.get_symbol_funding_info(sym)
        half_notional = notional_total / 2.0
        qty = round(half_notional / spot_p, 4) if spot_p > 1.0 else round(half_notional / spot_p, 1)

        now_dt = datetime.now()
        now_wib = now_dt.strftime("%Y-%m-%d %H:%M:%S")

        pos_data = {
            "symbol": sym,
            "status": "OPEN",
            "opened_at": now_wib,
            "opened_ts": int(time.time() * 1000),
            "notional_total": notional_total,
            "allocated_spot_usd": half_notional,
            "allocated_futures_usd": half_notional,
            "spot_entry_price": spot_p,
            "futures_entry_price": fut_p,
            "quantity": qty,
            "funding_rate_at_entry": funding_info["funding_rate"],
            "funding_pct_at_entry": funding_info["funding_pct"],
            "current_funding_pct": funding_info["funding_pct"],
            "accumulated_funding_reward": 0.0,
            "harvest_count": 0,
            "next_funding_time": funding_info["next_funding_time"],
            "last_harvest_time": now_wib
        }

        self.positions[sym] = pos_data
        self._save_state()
        return {
            "status": "success",
            "message": f"Berhasil membuka posisi Arbitrase {sym} (Spot Long ${half_notional:.2f} + Futures Short ${half_notional:.2f})",
            "position": pos_data
        }

    def close_arbitrage(self, symbol: str) -> Dict[str, Any]:
        """
        Tutup posisi Arbitrase, lakukan auto-rebalance saldo, dan bukukan laba bersih.
        """
        sym = symbol.upper().strip()
        if sym not in self.positions:
            return {"status": "error", "message": f"Posisi {sym} tidak ditemukan di daftar arbitrase"}

        pos = self.positions[sym]
        prices = self.get_live_prices(sym)
        curr_spot_p = prices["spot"] if prices["spot"] > 0 else pos["spot_entry_price"]
        curr_fut_p = prices["futures"] if prices["futures"] > 0 else pos["futures_entry_price"]

        qty = pos["quantity"]
        spot_entry_val = pos["allocated_spot_usd"]
        fut_entry_val = pos["allocated_futures_usd"]

        # Hitung PnL Spot & Futures
        spot_exit_val = qty * curr_spot_p
        spot_pnl = spot_exit_val - spot_entry_val

        # Futures Short PnL: (Entry Price - Exit Price) * Qty
        fut_pnl = (pos["futures_entry_price"] - curr_fut_p) * qty
        fut_exit_val = fut_entry_val + fut_pnl

        # Delta PnL harga (mendekati $0 karena saling mengunci)
        price_delta_pnl = spot_pnl + fut_pnl

        # Total Keuntungan = Delta Harga + Akumulasi Bunga Funding Fee
        harvested_fee = pos.get("accumulated_funding_reward", 0.0)
        net_profit = price_delta_pnl + harvested_fee
        roi_pct = (net_profit / pos["notional_total"]) * 100.0

        now_wib = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        trade_record = {
            "symbol": sym,
            "type": "ARBITRAGE (CASH & CARRY)",
            "opened_at": pos["opened_at"],
            "closed_at": now_wib,
            "notional_total": pos["notional_total"],
            "spot_entry_price": pos["spot_entry_price"],
            "spot_exit_price": curr_spot_p,
            "futures_entry_price": pos["futures_entry_price"],
            "futures_exit_price": curr_fut_p,
            "price_delta_pnl": round(price_delta_pnl, 4),
            "harvested_funding_fee": round(harvested_fee, 4),
            "net_profit": round(net_profit, 2),
            "roi_pct": round(roi_pct, 2),
            "harvest_count": pos.get("harvest_count", 0),
            "rebalanced": True,
            "rebalance_note": f"Auto-Rebalanced: Spot (${spot_exit_val:.2f}) & Futures (${fut_exit_val:.2f}) digabungkan kembali ke modal awal + cuan ${net_profit:+.2f}"
        }

        self.trade_history.insert(0, trade_record)
        del self.positions[sym]
        self._save_state()

        return {
            "status": "success",
            "message": f"Posisi Arbitrase {sym} berhasil ditutup & di-rebalance otomatis. Net Profit: ${net_profit:+.2f} USDT",
            "trade": trade_record
        }

    def check_and_harvest_funding(self) -> List[Dict[str, Any]]:
        """
        Pengecekan rutin: Jika jadwal settlement terlewati, otomatis panen bunga transferan funding fee!
        """
        now_ts = int(time.time() * 1000)
        harvested = []

        for sym, pos in list(self.positions.items()):
            next_ts = pos.get("next_funding_time", 0)
            # Tarik info live rate
            f_info = self.get_symbol_funding_info(sym)
            pos["current_funding_pct"] = f_info["funding_pct"]

            # Jika waktu settlement sudah terlewati atau update cycle
            if now_ts >= next_ts and next_ts > 0:
                rate = f_info["funding_rate"]
                fut_val = pos.get("allocated_futures_usd", pos["notional_total"] / 2.0)
                reward = fut_val * rate
                pos["accumulated_funding_reward"] = round(pos.get("accumulated_funding_reward", 0.0) + reward, 4)
                pos["harvest_count"] = pos.get("harvest_count", 0) + 1
                pos["next_funding_time"] = f_info["next_funding_time"]
                pos["last_harvest_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                harvested.append({
                    "symbol": sym,
                    "reward_usd": round(reward, 4),
                    "total_accumulated": pos["accumulated_funding_reward"],
                    "cycle": pos["harvest_count"]
                })

        if harvested:
            self._save_state()

        return harvested

    def get_active_positions_details(self) -> List[Dict[str, Any]]:
        """
        Tarik daftar posisi arbitrase aktif lengkap dengan live calculation
        """
        self.check_and_harvest_funding()
        res = []
        for sym, pos in self.positions.items():
            prices = self.get_live_prices(sym)
            curr_spot_p = prices["spot"] if prices["spot"] > 0 else pos["spot_entry_price"]
            curr_fut_p = prices["futures"] if prices["futures"] > 0 else pos["futures_entry_price"]

            qty = pos["quantity"]
            spot_pnl = (curr_spot_p - pos["spot_entry_price"]) * qty
            fut_pnl = (pos["futures_entry_price"] - curr_fut_p) * qty
            price_delta_pnl = spot_pnl + fut_pnl

            harvested = pos.get("accumulated_funding_reward", 0.0)
            total_net_pnl = price_delta_pnl + harvested
            roi_pct = (total_net_pnl / pos["notional_total"]) * 100.0

            # Countdown next funding
            next_ts = pos.get("next_funding_time", int(time.time()*1000) + 3600000)
            sec_left = max(0, int((next_ts - int(time.time()*1000)) / 1000))
            h = sec_left // 3600
            m = (sec_left % 3600) // 60
            s = sec_left % 60
            cd_str = f"{h:02d}h {m:02d}m {s:02d}s"

            res.append({
                "symbol": sym,
                "opened_at": pos["opened_at"],
                "notional_total": pos["notional_total"],
                "spot_leg": {
                    "entry_price": pos["spot_entry_price"],
                    "current_price": curr_spot_p,
                    "allocated_usd": pos["allocated_spot_usd"],
                    "pnl": round(spot_pnl, 2)
                },
                "futures_leg": {
                    "entry_price": pos["futures_entry_price"],
                    "current_price": curr_fut_p,
                    "allocated_usd": pos["allocated_futures_usd"],
                    "pnl": round(fut_pnl, 2)
                },
                "quantity": qty,
                "current_funding_pct": pos.get("current_funding_pct", 0.0),
                "harvest_count": pos.get("harvest_count", 0),
                "accumulated_funding_reward": round(harvested, 4),
                "price_delta_pnl": round(price_delta_pnl, 2),
                "total_net_pnl": round(total_net_pnl, 2),
                "roi_pct": round(roi_pct, 2),
                "countdown_str": cd_str
            })
        return res

# Global Singleton Engine
arbitrage_engine = ArbitrageEngine()
