import os
import hmac
import hashlib
import time
import requests
import urllib3
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BinanceExecutionEngine:
    """
    Eksekutor Order Otomatis Binance Futures (Mendukung Live Demo Testnet & Real Account).
    Menghubungkan langsung ke API Binance untuk:
    - Cek saldo dompet riil
    - Buka posisi MARKET (LONG / SHORT)
    - Pasang STOP LOSS & TAKE PROFIT otomatis di server Binance
    - Pasang Trailing Stop otomatis
    - Tarik data posisi aktif secara real-time
    """
    def __init__(self):
        self.api_key = os.getenv("BINANCE_API_KEY", "")
        self.api_secret = os.getenv("BINANCE_API_SECRET", "")
        self.is_testnet = os.getenv("BINANCE_TESTNET", "True").lower() == "true"
        
        if self.is_testnet:
            self.base_url = "https://testnet.binancefuture.com"
        else:
            self.base_url = "https://fapi.binance.com"
            
        self.headers = {"X-MBX-APIKEY": self.api_key}
        self.precisions = {}
        self._load_symbol_precisions()

    def _load_symbol_precisions(self):
        try:
            r = requests.get(f"{self.base_url}/fapi/v1/exchangeInfo", verify=False, timeout=8)
            if r.status_code == 200:
                data = r.json()
                for s in data.get("symbols", []):
                    self.precisions[s["symbol"]] = {
                        "qty": int(s.get("quantityPrecision", 2)),
                        "price": int(s.get("pricePrecision", 2))
                    }
        except Exception:
            pass

    def format_qty(self, symbol: str, qty: float) -> float:
        prec = self.precisions.get(symbol, {}).get("qty", 2)
        if prec == 0:
            return float(int(qty))
        return round(qty, prec)

    def format_price(self, symbol: str, price: float) -> float:
        prec = self.precisions.get(symbol, {}).get("price", 2)
        return round(price, prec)

    def _sign(self, params: Dict[str, Any]) -> str:
        params['timestamp'] = int(time.time() * 1000)
        query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f"{query_string}&signature={signature}"

    def get_account_balance(self) -> Dict[str, Any]:
        """Tarik saldo dompet USDT dan Margin dari Binance"""
        try:
            q = self._sign({})
            r = requests.get(f"{self.base_url}/fapi/v2/account?{q}", headers=self.headers, verify=False, timeout=8)
            if r.status_code == 200:
                data = r.json()
                return {
                    "status": "connected",
                    "total_wallet_balance": float(data.get("totalWalletBalance", 0.0)),
                    "available_balance": float(data.get("availableBalance", 0.0)),
                    "total_unrealized_pnl": float(data.get("totalUnrealizedProfit", 0.0)),
                    "total_margin": float(data.get("totalInitialMargin", 0.0)),
                    "can_trade": data.get("canTrade", False),
                    "environment": "BINANCE FUTURES DEMO (TESTNET)" if self.is_testnet else "BINANCE FUTURES LIVE REAL"
                }
            return {"status": "error", "message": r.text}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Tarik posisi yang sedang aktif berjalan di akun Binance"""
        try:
            q = self._sign({})
            r = requests.get(f"{self.base_url}/fapi/v2/positionRisk?{q}", headers=self.headers, verify=False, timeout=8)
            if r.status_code == 200:
                positions = r.json()
                active = []
                for p in positions:
                    amt = float(p.get("positionAmt", 0.0))
                    if amt != 0:
                        active.append({
                            "symbol": p.get("symbol"),
                            "position_amt": amt,
                            "side": "LONG" if amt > 0 else "SHORT",
                            "entry_price": float(p.get("entryPrice", 0.0)),
                            "mark_price": float(p.get("markPrice", 0.0)),
                            "unrealized_pnl": float(p.get("unRealizedProfit", 0.0)),
                            "liquidation_price": float(p.get("liquidationPrice", 0.0)),
                            "leverage": int(p.get("leverage", 1)),
                            "margin_type": p.get("marginType", "cross")
                        })
                return active
            return []
        except Exception:
            return []

    def set_leverage(self, symbol: str, leverage: int = 3) -> bool:
        """Atur besaran leverage di akun Binance"""
        try:
            q = self._sign({"symbol": symbol, "leverage": leverage})
            r = requests.post(f"{self.base_url}/fapi/v1/leverage?{q}", headers=self.headers, verify=False, timeout=8)
            return r.status_code == 200
        except Exception:
            return False

    def place_order(
        self,
        symbol: str,
        side: str, # 'BUY' or 'SELL'
        quantity: float,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Buka posisi MARKET dan otomatis pasang Stop Loss & Take Profit di Binance
        """
        try:
            formatted_qty = self.format_qty(symbol, quantity)
            if formatted_qty <= 0:
                return {"status": "error", "message": f"Kuantitas order {formatted_qty} tidak valid untuk {symbol}"}

            # 1. Market Entry Order
            params = {
                "symbol": symbol,
                "side": side.upper(),
                "type": "MARKET",
                "quantity": int(formatted_qty) if self.precisions.get(symbol, {}).get("qty") == 0 else formatted_qty
            }
            q = self._sign(params)
            r = requests.post(f"{self.base_url}/fapi/v1/order?{q}", headers=self.headers, verify=False, timeout=8)
            res_entry = r.json()
            
            if r.status_code != 200:
                return {"status": "error", "step": "entry", "message": res_entry.get("msg", r.text)}

            order_id = res_entry.get("orderId")
            avg_price = float(res_entry.get("avgPrice", 0.0))
            if avg_price == 0.0 and "cumQuote" in res_entry and "executedQty" in res_entry:
                cq = float(res_entry.get("cumQuote", 0.0))
                eq = float(res_entry.get("executedQty", 1.0))
                avg_price = cq / eq if eq > 0 else 0.0

            opposite_side = "SELL" if side.upper() == "BUY" else "BUY"

            # 2. Pasang Stop Loss Order jika ada
            sl_res = None
            if stop_loss_price:
                formatted_sl = self.format_price(symbol, stop_loss_price)
                sl_params = {
                    "symbol": symbol,
                    "side": opposite_side,
                    "type": "STOP_MARKET",
                    "stopPrice": formatted_sl,
                    "closePosition": "true"
                }
                q_sl = self._sign(sl_params)
                r_sl = requests.post(f"{self.base_url}/fapi/v1/order?{q_sl}", headers=self.headers, verify=False, timeout=8)
                sl_res = r_sl.json()

            # 3. Pasang Take Profit Order jika ada
            tp_res = None
            if take_profit_price:
                formatted_tp = self.format_price(symbol, take_profit_price)
                tp_params = {
                    "symbol": symbol,
                    "side": opposite_side,
                    "type": "TAKE_PROFIT_MARKET",
                    "stopPrice": formatted_tp,
                    "closePosition": "true"
                }
                q_tp = self._sign(tp_params)
                r_tp = requests.post(f"{self.base_url}/fapi/v1/order?{q_tp}", headers=self.headers, verify=False, timeout=8)
                tp_res = r_tp.json()

            return {
                "status": "success",
                "symbol": symbol,
                "side": side,
                "quantity": formatted_qty,
                "entry_price": avg_price,
                "order_id": order_id,
                "sl_price": stop_loss_price,
                "tp_price": take_profit_price,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB")
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def close_position(self, symbol: str) -> Dict[str, Any]:
        """Tutup paksa posisi aktif di Binance"""
        try:
            positions = self.get_open_positions()
            target_pos = next((p for p in positions if p["symbol"] == symbol), None)
            if not target_pos:
                return {"status": "error", "message": f"Tidak ada posisi aktif untuk {symbol}"}

            amt = target_pos["position_amt"]
            side = "SELL" if amt > 0 else "BUY"
            qty = abs(amt)

            # Batalkan order pending dulu
            q_cancel = self._sign({"symbol": symbol})
            requests.delete(f"{self.base_url}/fapi/v1/allOpenOrders?{q_cancel}", headers=self.headers, verify=False, timeout=8)

            # Market Close
            params = {
                "symbol": symbol,
                "side": side,
                "type": "MARKET",
                "quantity": qty
            }
            q = self._sign(params)
            r = requests.post(f"{self.base_url}/fapi/v1/order?{q}", headers=self.headers, verify=False, timeout=8)
            return {"status": "success", "result": r.json()}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def close_partial_position(self, symbol: str, quantity: float) -> Dict[str, Any]:
        """Tutup sebagian posisi (Partial TP) di Binance"""
        try:
            positions = self.get_open_positions()
            target_pos = next((p for p in positions if p["symbol"] == symbol), None)
            if not target_pos:
                return {"status": "error", "message": f"Tidak ada posisi aktif untuk {symbol}"}

            amt = target_pos["position_amt"]
            side = "SELL" if amt > 0 else "BUY"
            formatted_qty = self.format_qty(symbol, quantity)
            if formatted_qty <= 0:
                return {"status": "error", "message": "Kuantitas partial tidak valid"}

            params = {
                "symbol": symbol,
                "side": side,
                "type": "MARKET",
                "quantity": int(formatted_qty) if self.precisions.get(symbol, {}).get("qty") == 0 else formatted_qty,
                "reduceOnly": "true"
            }
            q = self._sign(params)
            r = requests.post(f"{self.base_url}/fapi/v1/order?{q}", headers=self.headers, verify=False, timeout=8)
            return {"status": "success", "result": r.json()}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_account_trades(self, symbols: List[str] = None, limit_per_sym: int = 50, start_time_ms: Optional[int] = None) -> List[Dict[str, Any]]:
        """Tarik histori transaksi & eksekusi riil dari Binance API"""
        if not symbols:
            symbols = ["ETHUSDT"]
        
        all_trades = []
        if not start_time_ms:
            start_time_ms = int((time.time() - 3600 * 24) * 1000) # 24 jam terakhir

        for sym in symbols:
            try:
                q = self._sign({"symbol": sym, "startTime": start_time_ms, "limit": 1000})
                r = requests.get(f"{self.base_url}/fapi/v1/userTrades?{q}", headers=self.headers, verify=False, timeout=4)
                if r.status_code == 200:
                    trades = r.json()
                    if isinstance(trades, list) and trades:
                        for t in trades:
                            t_time = t.get("time", 0)
                            if t_time >= start_time_ms:
                                all_trades.append({
                                    "id": t.get("id"),
                                    "order_id": t.get("orderId"),
                                    "symbol": t.get("symbol"),
                                    "side": t.get("side"),
                                    "price": float(t.get("price", 0.0)),
                                    "qty": float(t.get("qty", 0.0)),
                                    "quote_qty": float(t.get("quoteQty", 0.0)),
                                    "realized_pnl": float(t.get("realizedPnl", 0.0)),
                                    "commission": float(t.get("commission", 0.0)),
                                    "time": datetime.fromtimestamp(t_time / 1000).strftime("%Y-%m-%d %H:%M:%S WIB") if t_time else "-",
                                    "timestamp_ms": t_time
                                })
            except Exception:
                pass

        # Sort newest first across all symbols
        all_trades.sort(key=lambda x: x.get("timestamp_ms", 0), reverse=True)
        return all_trades[:60]

