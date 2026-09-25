import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Any

class BacktestEngine:
    """
    Mesin Backtest Binance Futures dengan simulasi realistis:
    - Posisi Long & Short
    - Dynamic Stop Loss (SL) & Take Profit (TP) per bar (menguji High & Low)
    - Trading Fee (Maker/Taker Binance Futures) & Slippage
    - Margin & Leverage simulation
    """
    def __init__(
        self,
        initial_capital: float = 1000.0,
        leverage: float = 3.0,
        risk_per_trade_pct: float = 0.02, # 2% risiko modal per trade jika SL ada
        fixed_pos_size_pct: float = 0.50, # Alternatif: alokasi 50% margin modal
        fee_rate: float = 0.0005,         # 0.05% Taker fee
        slippage_pct: float = 0.0002,     # 0.02% Slippage
        enable_partial_tp: bool = False   # False = Full Position TP/Exit (Standard), True = 50% Partial TP1
    ):
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.risk_per_trade_pct = risk_per_trade_pct
        self.fixed_pos_size_pct = fixed_pos_size_pct
        self.fee_rate = fee_rate
        self.slippage_pct = slippage_pct
        self.enable_partial_tp = enable_partial_tp

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        capital = self.initial_capital
        trades: List[Dict[str, Any]] = []
        equity_curve = []

        position = None  # None, 'LONG', 'SHORT'
        entry_price = 0.0
        entry_time = None
        quantity = 0.0
        sl_price = None
        tp_price = None
        tp1_price = None
        partial_taken = False
        notional_value = 0.0

        for i in range(len(df)):
            row = df.iloc[i]
            timestamp = row['timestamp']
            open_p = row['open']
            high_p = row['high']
            low_p = row['low']
            close_p = row['close']
            signal = row.get('signal', 0)
            sig_sl = row.get('sl_price', row.get('stop_loss', np.nan))
            sig_tp = row.get('tp_price', row.get('take_profit', np.nan))

            # 1. Cek Posisi Aktif Terhadap SL / TP pada Bar Ini
            if position == 'LONG':
                exit_price = None
                exit_reason = None

                # Update Trailing Stop mengikuti Supertrend (hanya boleh naik ke atas)
                if 'supertrend' in row and row.get('st_dir', 1) == 1:
                    st_val = row['supertrend']
                    if sl_price is None:
                        sl_price = st_val
                    else:
                        sl_price = max(sl_price, st_val)

                # Cek Partial TP1 (Kunci 50% profit saat capai target 1 dan kunci Break-Even)
                if not partial_taken and tp1_price is not None and high_p >= tp1_price:
                    tp1_exit = max(open_p, tp1_price) * (1 - self.slippage_pct)
                    close_qty = quantity * 0.50
                    fee = (tp1_exit * close_qty) * self.fee_rate
                    pnl = (tp1_exit - entry_price) * close_qty - fee
                    capital += pnl
                    quantity -= close_qty
                    partial_taken = True
                    sl_price = max(sl_price, entry_price * 1.001) # Kunci Break-Even aman fee!

                # Cek Stop Loss / Trailing Stop / Break Even
                if sl_price is not None and low_p <= sl_price:
                    exit_price = min(open_p, sl_price) * (1 - self.slippage_pct)
                    if sl_price > entry_price * 1.002:
                        exit_reason = "Trailing Stop (Profit Lock)"
                    elif sl_price >= entry_price:
                        exit_reason = "Break Even (Capital Safe)"
                    else:
                        exit_reason = "Stop Loss"
                # Cek Full Take Profit TP2
                elif tp_price is not None and high_p >= tp_price:
                    exit_price = max(open_p, tp_price) * (1 - self.slippage_pct)
                    exit_reason = "Take Profit (Full)"
                # Sinyal Exit / Reversal
                elif row.get('exit_long', 0) == 1 or ('exit_long' not in row and signal == -1):
                    exit_price = close_p * (1 - self.slippage_pct)
                    exit_reason = "Signal Exit (Formula / Reversal)"

                if exit_price is not None:
                    # Tutup Long
                    entry_fee = (entry_price * quantity) * self.fee_rate
                    exit_fee = (exit_price * quantity) * self.fee_rate
                    total_fee = entry_fee + exit_fee
                    gross_pnl = (exit_price - entry_price) * quantity
                    net_pnl = gross_pnl - total_fee
                    capital += (gross_pnl - exit_fee) # capital already had entry_fee deducted at entry
                    pnl_pct = (net_pnl / (notional_value / self.leverage)) * 100

                    # Hitung durasi hold
                    duration = timestamp - entry_time
                    days = duration.days
                    hours = int(duration.seconds // 3600)
                    duration_str = f"{days}h {hours}j" if days > 0 else f"{hours} jam"

                    trades.append({
                        "type": "LONG",
                        "entry_time": entry_time,
                        "entry_price": entry_price,
                        "exit_time": timestamp,
                        "exit_price": exit_price,
                        "duration": duration_str,
                        "quantity": quantity,
                        "net_pnl": net_pnl,
                        "pnl_pct": pnl_pct,
                        "exit_reason": exit_reason,
                        "capital_after": capital
                    })
                    position = None

            elif position == 'SHORT':
                exit_price = None
                exit_reason = None

                # Update Trailing Stop mengikuti Supertrend (hanya boleh turun ke bawah)
                if 'supertrend' in row and row.get('st_dir', -1) == -1:
                    st_val = row['supertrend']
                    if sl_price is None:
                        sl_price = st_val
                    else:
                        sl_price = min(sl_price, st_val)

                # Cek Partial TP1 (Kunci 50% profit saat capai target 1 dan kunci Break-Even)
                if not partial_taken and tp1_price is not None and low_p <= tp1_price:
                    tp1_exit = min(open_p, tp1_price) * (1 + self.slippage_pct)
                    close_qty = quantity * 0.50
                    fee = (tp1_exit * close_qty) * self.fee_rate
                    pnl = (entry_price - tp1_exit) * close_qty - fee
                    capital += pnl
                    quantity -= close_qty
                    partial_taken = True
                    sl_price = min(sl_price, entry_price * 0.999) # Kunci Break-Even aman fee!

                # Cek Stop Loss / Trailing Stop / Break Even
                if sl_price is not None and high_p >= sl_price:
                    exit_price = max(open_p, sl_price) * (1 + self.slippage_pct)
                    if sl_price < entry_price * 0.998:
                        exit_reason = "Trailing Stop (Profit Lock)"
                    elif sl_price <= entry_price:
                        exit_reason = "Break Even (Capital Safe)"
                    else:
                        exit_reason = "Stop Loss"
                # Cek Full Take Profit TP2
                elif tp_price is not None and low_p <= tp_price:
                    exit_price = min(open_p, tp_price) * (1 + self.slippage_pct)
                    exit_reason = "Take Profit (Full)"
                # Sinyal Exit / Reversal
                elif row.get('exit_short', 0) == 1 or ('exit_short' not in row and signal == 1):
                    exit_price = close_p * (1 + self.slippage_pct)
                    exit_reason = "Signal Exit (Formula / Reversal)"

                if exit_price is not None:
                    # Tutup Short
                    entry_fee = (entry_price * quantity) * self.fee_rate
                    exit_fee = (exit_price * quantity) * self.fee_rate
                    total_fee = entry_fee + exit_fee
                    gross_pnl = (entry_price - exit_price) * quantity
                    net_pnl = gross_pnl - total_fee
                    capital += (gross_pnl - exit_fee) # capital already had entry_fee deducted at entry
                    pnl_pct = (net_pnl / (notional_value / self.leverage)) * 100

                    # Hitung durasi hold
                    duration = timestamp - entry_time
                    days = duration.days
                    hours = int(duration.seconds // 3600)
                    duration_str = f"{days}h {hours}j" if days > 0 else f"{hours} jam"

                    trades.append({
                        "type": "SHORT",
                        "entry_time": entry_time,
                        "entry_price": entry_price,
                        "exit_time": timestamp,
                        "exit_price": exit_price,
                        "duration": duration_str,
                        "quantity": quantity,
                        "net_pnl": net_pnl,
                        "pnl_pct": pnl_pct,
                        "exit_reason": exit_reason,
                        "capital_after": capital
                    })
                    position = None

            # 2. Buka Posisi Baru Jika Tidak Ada Posisi Aktif
            if position is None and capital > 10:
                is_long = (row.get('enter_long', 0) == 1) or ('enter_long' not in row and signal == 1)
                is_short = (row.get('enter_short', 0) == 1) or ('enter_short' not in row and 'enter_long' not in row and signal == -1)

                if is_long:
                    position = 'LONG'
                    entry_price = close_p * (1 + self.slippage_pct)
                elif is_short:
                    position = 'SHORT'
                    entry_price = close_p * (1 - self.slippage_pct)

                if position is not None:
                    entry_time = timestamp
                    sl_price = sig_sl if not np.isnan(sig_sl) else None
                    tp_price = sig_tp if not np.isnan(sig_tp) else None
                    partial_taken = False

                    # Hitung ukuran posisi berdasarkan Risk Management
                    if isinstance(self.risk_per_trade_pct, str) and self.risk_per_trade_pct.startswith("fixed_"):
                        try:
                            fixed_notional = float(self.risk_per_trade_pct.replace("fixed_", ""))
                        except Exception:
                            fixed_notional = 250.0
                        quantity = fixed_notional / entry_price
                        notional_value = fixed_notional
                        margin_used = notional_value / self.leverage
                    elif isinstance(self.risk_per_trade_pct, (int, float)) and self.risk_per_trade_pct > 0 and sl_price is not None:
                        risk_amount = capital * self.risk_per_trade_pct # Risiko nominal (misal 2% modal = $20)
                        sl_dist = abs(entry_price - sl_price)
                        if sl_dist > 0:
                            desired_qty = risk_amount / sl_dist
                            max_qty = (capital * self.fixed_pos_size_pct * self.leverage) / entry_price
                            quantity = min(desired_qty, max_qty)
                        else:
                            quantity = (capital * self.fixed_pos_size_pct * self.leverage) / entry_price
                        notional_value = quantity * entry_price
                        margin_used = notional_value / self.leverage
                    else:
                        margin_pct = float(self.fixed_pos_size_pct) if isinstance(self.fixed_pos_size_pct, (int, float)) else 0.20
                        margin_used = capital * margin_pct
                        notional_value = margin_used * self.leverage
                        quantity = notional_value / entry_price
                        notional_value = quantity * entry_price
                        margin_used = notional_value / self.leverage

                    # Hitung TP1 level hanya jika partial TP diaktifkan secara eksplisit
                    if self.enable_partial_tp and tp_price is not None:
                        tp1_price = entry_price + (tp_price - entry_price) * 0.50
                    else:
                        tp1_price = None

                    # Biaya entry
                    entry_fee = notional_value * self.fee_rate
                    capital -= entry_fee

            equity_curve.append({
                "timestamp": timestamp,
                "capital": capital,
                "close": close_p
            })

        # Hitung Ringkasan Metrik
        metrics = self._calculate_metrics(trades, equity_curve)
        open_pos_info = None
        if position is not None:
            open_pos_info = {
                "type": position,
                "entry_time": entry_time,
                "entry_price": entry_price,
                "quantity": quantity
            }

        return {
            "metrics": metrics,
            "trades_df": pd.DataFrame(trades),
            "equity_df": pd.DataFrame(equity_curve),
            "open_position": open_pos_info
        }

    def _calculate_metrics(self, trades: List[Dict[str, Any]], equity_curve: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not trades:
            return {
                "initial_capital": self.initial_capital,
                "final_capital": self.initial_capital,
                "net_profit": 0.0,
                "net_profit_pct": 0.0,
                "total_trades": 0,
                "win_count": 0,
                "loss_count": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "gross_profit": 0.0,
                "gross_loss": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "risk_reward_ratio": 0.0,
                "max_drawdown_pct": 0.0,
                "max_drawdown_usd": 0.0
            }

        df_trades = pd.DataFrame(trades)
        df_equity = pd.DataFrame(equity_curve)

        final_capital = df_equity['capital'].iloc[-1]
        net_profit = final_capital - self.initial_capital
        net_profit_pct = (net_profit / self.initial_capital) * 100

        total_trades = len(df_trades)
        winning_trades = df_trades[df_trades['net_pnl'] > 0]
        losing_trades = df_trades[df_trades['net_pnl'] <= 0]

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0.0

        gross_profit = winning_trades['net_pnl'].sum() if win_count > 0 else 0.0
        gross_loss = abs(losing_trades['net_pnl'].sum()) if loss_count > 0 else 0.0

        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)

        avg_win = winning_trades['net_pnl'].mean() if win_count > 0 else 0.0
        avg_loss = losing_trades['net_pnl'].mean() if loss_count > 0 else 0.0
        risk_reward_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0

        # Maximum Drawdown (MDD)
        df_equity['peak'] = df_equity['capital'].cummax()
        df_equity['drawdown'] = (df_equity['capital'] - df_equity['peak']) / df_equity['peak'] * 100
        max_drawdown_pct = abs(df_equity['drawdown'].min())
        max_drawdown_usd = (df_equity['peak'] - df_equity['capital']).max()

        return {
            "initial_capital": self.initial_capital,
            "final_capital": final_capital,
            "net_profit": net_profit,
            "net_profit_pct": net_profit_pct,
            "total_trades": total_trades,
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "risk_reward_ratio": risk_reward_ratio,
            "max_drawdown_pct": max_drawdown_pct,
            "max_drawdown_usd": max_drawdown_usd
        }
