import os
import time
import uuid
import json
import sqlite3
import requests
import urllib3
from typing import List, Dict, Any, Optional

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Konfigurasi Turso Default
TURSO_DB_URL = os.getenv("TURSO_DATABASE_URL", "libsql://binance-futures-bot-baihaqidr.aws-ap-northeast-1.turso.io")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTA2NDIxODksImlkIjoiMDFhMGVhOTMtZDQwMS03ZjQ0LWI0YTItODc2YmJmMmM3OTcyIiwia2lkIjoidVVTc3ptdDNaUTNzQ0puZ3FVeWhIMXpRWTVfSEJydmp0cDhDMEdsdXp2TSIsInJpZCI6IjM3YmVkMjg5LTNkN2UtNGVhMi04NjM0LTBiYzU2Zjc1N2Q1YyJ9.xeFklbhjMgeFf1Y_vafFmk7j5gDSGeGUvyCLTuyf5m09gjgmB0PiCqM8zmMas0LrlRL7OFJmi5ZYT3yoQV-xAw")
LOCAL_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "local_database.sqlite")

class TursoDatabaseManager:
    """
    Database Manager untuk Turso Cloud (libSQL) dengan Fallback SQLite Lokal.
    Menangani penyimpanan:
    1. Active Strategy Positions (Posisi Aktif & Floating Net PnL)
    2. Closed Strategy Trades (Riwayat Selesai & Realized Net PnL)
    3. Performance Metrics (Win Rate, Total Profit Bersih)
    """
    def __init__(self, db_url: str = TURSO_DB_URL, auth_token: str = TURSO_TOKEN):
        self.db_url = db_url.strip()
        self.auth_token = auth_token.strip()
        
        # Format HTTP endpoint untuk Turso Pipeline
        clean_host = self.db_url.replace("libsql://", "").replace("https://", "").replace("http://", "")
        self.http_endpoint = f"https://{clean_host}/v2/pipeline"
        
        self.is_cloud_active = False
        self._init_local_db()
        self._init_turso_tables()

    def _init_local_db(self):
        """Inisialisasi SQLite lokal untuk offline fallback"""
        try:
            conn = sqlite3.connect(LOCAL_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_positions (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                current_price REAL NOT NULL,
                position_size REAL NOT NULL,
                notional_usd REAL NOT NULL,
                tp_price REAL DEFAULT 0,
                sl_price REAL DEFAULT 0,
                gross_pnl REAL DEFAULT 0,
                estimated_fees REAL DEFAULT 0,
                net_pnl REAL DEFAULT 0,
                net_pnl_pct REAL DEFAULT 0,
                status TEXT DEFAULT 'OPEN',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS closed_trades (
                id TEXT PRIMARY KEY,
                position_id TEXT,
                symbol TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                position_size REAL NOT NULL,
                notional_usd REAL NOT NULL,
                gross_pnl REAL NOT NULL,
                total_fees REAL NOT NULL,
                net_pnl REAL NOT NULL,
                net_pnl_pct REAL NOT NULL,
                exit_reason TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL,
                status TEXT NOT NULL,
                opened_at INTEGER NOT NULL,
                closed_at INTEGER NOT NULL
            );
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DB] Local SQLite init warning: {e}")

    def execute_turso_query(self, sql: str, args: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Eksekusi query SQL ke Turso Cloud via HTTP Pipeline"""
        stmt: Dict[str, Any] = {"sql": sql}
        if args:
            params = []
            for a in args:
                if a is None:
                    params.append({"type": "null"})
                elif isinstance(a, int):
                    params.append({"type": "integer", "value": str(a)})
                elif isinstance(a, float):
                    params.append({"type": "float", "value": float(a)})
                else:
                    params.append({"type": "text", "value": str(a)})
            stmt["args"] = params

        payload = {
            "requests": [
                {"type": "execute", "stmt": stmt},
                {"type": "close"}
            ]
        }
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }

        try:
            r = requests.post(self.http_endpoint, headers=headers, json=payload, timeout=6)
            if r.status_code == 200:
                data = r.json()
                self.is_cloud_active = True
                results = data.get("results", [])
                if results and results[0].get("type") == "ok":
                    exec_res = results[0].get("response", {}).get("result", {})
                    cols = [c["name"] for c in exec_res.get("cols", [])]
                    raw_rows = exec_res.get("rows", [])
                    
                    rows = []
                    for raw_r in raw_rows:
                        row_dict = {}
                        for idx, col_name in enumerate(cols):
                            val_obj = raw_r[idx]
                            v = val_obj.get("value")
                            v_type = val_obj.get("type")
                            if v_type == "integer" and v is not None:
                                v = int(v)
                            elif v_type == "float" and v is not None:
                                v = float(v)
                            elif v_type == "null":
                                v = None
                            row_dict[col_name] = v
                        rows.append(row_dict)
                    return {"success": True, "rows": rows, "affected_rows": exec_res.get("affected_row_count", 0)}
        except Exception as e:
            self.is_cloud_active = False

        # Fallback ke Local SQLite jika Turso gagal / offline
        return self._execute_local_query(sql, args)

    def _execute_local_query(self, sql: str, args: Optional[List[Any]] = None) -> Dict[str, Any]:
        try:
            conn = sqlite3.connect(LOCAL_DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if args:
                cursor.execute(sql, args)
            else:
                cursor.execute(sql)
            
            rows = []
            if cursor.description:
                for r in cursor.fetchall():
                    rows.append(dict(r))
            affected = cursor.rowcount
            conn.commit()
            conn.close()
            return {"success": True, "rows": rows, "affected_rows": affected, "is_local": True}
        except Exception as e:
            return {"success": False, "error": str(e), "rows": []}

    def _init_turso_tables(self):
        """Membuat skema tabel di Turso Cloud"""
        tables = [
            """
            CREATE TABLE IF NOT EXISTS active_positions (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                current_price REAL NOT NULL,
                position_size REAL NOT NULL,
                notional_usd REAL NOT NULL,
                tp_price REAL DEFAULT 0,
                sl_price REAL DEFAULT 0,
                gross_pnl REAL DEFAULT 0,
                estimated_fees REAL DEFAULT 0,
                net_pnl REAL DEFAULT 0,
                net_pnl_pct REAL DEFAULT 0,
                status TEXT DEFAULT 'OPEN',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS closed_trades (
                id TEXT PRIMARY KEY,
                position_id TEXT,
                symbol TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                position_size REAL NOT NULL,
                notional_usd REAL NOT NULL,
                gross_pnl REAL NOT NULL,
                total_fees REAL NOT NULL,
                net_pnl REAL NOT NULL,
                net_pnl_pct REAL NOT NULL,
                exit_reason TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL,
                status TEXT NOT NULL,
                opened_at INTEGER NOT NULL,
                closed_at INTEGER NOT NULL
            );
            """
        ]
        for q in tables:
            self.execute_turso_query(q)

    # --- CRUD OPERATIONS UNTUK POSISI STRATEGI ---

    def open_position(self, symbol: str, strategy_name: str, timeframe: str, side: str,
                      entry_price: float, position_size: float, notional_usd: float,
                      tp_price: float = 0.0, sl_price: float = 0.0) -> Dict[str, Any]:
        pos_id = str(uuid.uuid4())[:8].upper()
        now = int(time.time())
        fee_est = notional_usd * 0.0008 # Estimasi taker fee roundtrip (0.08%)

        sql = """
        INSERT INTO active_positions 
        (id, symbol, strategy_name, timeframe, side, entry_price, current_price, position_size, notional_usd, tp_price, sl_price, gross_pnl, estimated_fees, net_pnl, net_pnl_pct, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, 0, 'OPEN', ?, ?);
        """
        initial_net_pnl = -fee_est
        initial_net_pct = (-fee_est / notional_usd) * 100.0 if notional_usd > 0 else 0.0

        args = [
            pos_id, symbol.upper(), strategy_name, timeframe, side.upper(),
            entry_price, entry_price, position_size, notional_usd,
            tp_price, sl_price, fee_est, initial_net_pnl, now, now
        ]
        res = self.execute_turso_query(sql, args)
        return {
            "success": res.get("success", False),
            "position_id": pos_id,
            "symbol": symbol.upper(),
            "strategy_name": strategy_name,
            "entry_price": entry_price,
            "notional_usd": notional_usd,
            "side": side.upper(),
            "created_at": now
        }

    def get_active_positions(self) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM active_positions WHERE status = 'OPEN' ORDER BY created_at DESC;"
        res = self.execute_turso_query(sql)
        return res.get("rows", [])

    def update_position_price(self, pos_id: str, current_price: float) -> Optional[Dict[str, Any]]:
        """Update live price dan hitung ulang Net PnL real-time"""
        sql_get = "SELECT * FROM active_positions WHERE id = ? AND status = 'OPEN';"
        res = self.execute_turso_query(sql_get, [pos_id])
        rows = res.get("rows", [])
        if not rows:
            return None
        
        pos = rows[0]
        entry_price = float(pos["entry_price"])
        size = float(pos["position_size"])
        notional = float(pos["notional_usd"])
        side = pos["side"]
        fees = float(pos.get("estimated_fees", notional * 0.0008))

        # Hitung Gross PnL
        if side == "LONG":
            gross_pnl = (current_price - entry_price) * size
        else: # SHORT
            gross_pnl = (entry_price - current_price) * size

        net_pnl = gross_pnl - fees
        net_pnl_pct = (net_pnl / notional) * 100.0 if notional > 0 else 0.0
        now = int(time.time())

        sql_upd = """
        UPDATE active_positions 
        SET current_price = ?, gross_pnl = ?, net_pnl = ?, net_pnl_pct = ?, updated_at = ?
        WHERE id = ?;
        """
        self.execute_turso_query(sql_upd, [current_price, gross_pnl, net_pnl, net_pnl_pct, now, pos_id])
        
        pos["current_price"] = current_price
        pos["gross_pnl"] = round(gross_pnl, 4)
        pos["net_pnl"] = round(net_pnl, 4)
        pos["net_pnl_pct"] = round(net_pnl_pct, 2)
        return pos

    def close_position(self, pos_id: str, exit_price: float, exit_reason: str = "MANUAL_CLOSE") -> Dict[str, Any]:
        sql_get = "SELECT * FROM active_positions WHERE id = ?;"
        res = self.execute_turso_query(sql_get, [pos_id])
        rows = res.get("rows", [])
        if not rows:
            return {"success": False, "error": "Posisi tidak ditemukan"}

        pos = rows[0]
        entry_price = float(pos["entry_price"])
        size = float(pos["position_size"])
        notional = float(pos["notional_usd"])
        side = pos["side"]
        opened_at = int(pos["created_at"])
        now = int(time.time())
        duration_sec = max(1, now - opened_at)

        # Hitung Realized Gross PnL & Fee
        if side == "LONG":
            gross_pnl = (exit_price - entry_price) * size
        else:
            gross_pnl = (entry_price - exit_price) * size

        total_fees = notional * 0.0008
        net_pnl = gross_pnl - total_fees
        net_pnl_pct = (net_pnl / notional) * 100.0 if notional > 0 else 0.0
        status = "WIN" if net_pnl >= 0 else "LOSS"
        trade_id = f"TRD-{uuid.uuid4().hex[:6].upper()}"

        # 1. Simpan ke closed_trades
        sql_insert = """
        INSERT INTO closed_trades 
        (id, position_id, symbol, strategy_name, timeframe, side, entry_price, exit_price, position_size, notional_usd, gross_pnl, total_fees, net_pnl, net_pnl_pct, exit_reason, duration_seconds, status, opened_at, closed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        args_ins = [
            trade_id, pos_id, pos["symbol"], pos["strategy_name"], pos["timeframe"], side,
            entry_price, exit_price, size, notional, gross_pnl, total_fees, net_pnl, net_pnl_pct,
            exit_reason, duration_sec, status, opened_at, now
        ]
        self.execute_turso_query(sql_insert, args_ins)

        # 2. Hapus atau update status di active_positions
        sql_del = "DELETE FROM active_positions WHERE id = ?;"
        self.execute_turso_query(sql_del, [pos_id])

        return {
            "success": True,
            "trade_id": trade_id,
            "symbol": pos["symbol"],
            "net_pnl": round(net_pnl, 4),
            "net_pnl_pct": round(net_pnl_pct, 2),
            "status": status,
            "exit_reason": exit_reason,
            "duration_seconds": duration_sec
        }

    def get_closed_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        sql = f"SELECT * FROM closed_trades ORDER BY closed_at DESC LIMIT {limit};"
        res = self.execute_turso_query(sql)
        return res.get("rows", [])

    def get_performance_stats(self) -> Dict[str, Any]:
        """Menghitung agregasi statistik performa (Win Rate, Total PnL)"""
        sql = """
        SELECT 
            COUNT(*) as total_trades,
            SUM(CASE WHEN status = 'WIN' THEN 1 ELSE 0 END) as win_count,
            SUM(CASE WHEN status = 'LOSS' THEN 1 ELSE 0 END) as loss_count,
            SUM(net_pnl) as total_net_pnl,
            AVG(net_pnl_pct) as avg_pnl_pct,
            MAX(net_pnl) as max_profit,
            MIN(net_pnl) as max_loss
        FROM closed_trades;
        """
        res = self.execute_turso_query(sql)
        rows = res.get("rows", [])
        if rows and rows[0].get("total_trades", 0) > 0:
            r = rows[0]
            total = int(r.get("total_trades") or 0)
            wins = int(r.get("win_count") or 0)
            losses = int(r.get("loss_count") or 0)
            win_rate = (wins / total * 100.0) if total > 0 else 0.0
            return {
                "total_trades": total,
                "win_count": wins,
                "loss_count": losses,
                "win_rate_pct": round(win_rate, 1),
                "total_net_pnl": round(float(r.get("total_net_pnl") or 0.0), 4),
                "avg_pnl_pct": round(float(r.get("avg_pnl_pct") or 0.0), 2),
                "max_profit": round(float(r.get("max_profit") or 0.0), 4),
                "max_loss": round(float(r.get("max_loss") or 0.0), 4),
                "db_status": "Turso Cloud (Connected)" if self.is_cloud_active else "Local SQLite (Offline)"
            }
        return {
            "total_trades": 0,
            "win_count": 0,
            "loss_count": 0,
            "win_rate_pct": 0.0,
            "total_net_pnl": 0.0,
            "avg_pnl_pct": 0.0,
            "max_profit": 0.0,
            "max_loss": 0.0,
            "db_status": "Turso Cloud (Connected)" if self.is_cloud_active else "Local SQLite (Offline)"
        }

# Global Singleton Database Manager
turso_db = TursoDatabaseManager()
