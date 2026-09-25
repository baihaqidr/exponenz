import os
import sys
import argparse
import pandas as pd
from tabulate import tabulate
from colorama import init, Fore, Style

# Set UTF-8 encoding untuk Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Inisialisasi colorama untuk Windows
init(autoreset=True)

# Tambahkan path root agar import src berfungsi
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data_fetcher import fetch_binance_futures_klines
from src.strategies.supertrend_rsi import SupertrendRSIStrategy
from src.strategies.ema_crossover import EMACrossoverStrategy
from src.strategies.breakout_atr import BreakoutATRStrategy
from src.strategies.bollinger_rsi import BollingerRSIScalperStrategy
from src.strategies.alpha_pullback import AlphaTrendPullbackStrategy
from src.strategies.liquidation_scalper import LiquidationBounceScalper
from src.strategies.mtf_pullback import MTFTrendPullbackStrategy
from src.strategies.alpha_sniper import AlphaSniperDivergenceStrategy
from src.strategies.trend_rider import TrendRiderProStrategy
from src.strategies.trend_rider_pure import TrendRiderPureStrategy
from src.strategies.price_ema_crossover import PriceEMACrossoverStrategy
from src.strategies.bb_reclaim_sniper import BBReclaimSniperStrategy
from src.strategies.bb_middle_sniper import BBMiddleSniperStrategy
from src.strategies.engulfing_sniper import EngulfingSniperStrategy
from src.strategies.pure_price_action_sweep import PurePriceActionLiquiditySweep
from src.strategies.pure_market_structure import PureMarketStructurePro
from src.strategies.trend_reclaim_sniper_1m import TrendReclaimSniperPro1M
from src.backtester import BacktestEngine
from src.strategy_registry import get_strategy_instance

def print_banner():
    banner = f"""
{Fore.CYAN}========================================================================
   [+] BINANCE FUTURES STRATEGY BACKTESTER ENGINE
   Mode: Historical OHLCV Simulation | Leverage & SL/TP Enabled
========================================================================{Style.RESET_ALL}
"""
    print(banner)

def get_strategy(strategy_name: str):
    name = strategy_name.lower().strip()
    if "bband" in name or "bband_rsi" in name:
        from src.strategies.freqtrade_bband_rsi import FreqtradeBbandRsiStrategy
        return FreqtradeBbandRsiStrategy()
    elif "freqtrade" in name:
        from src.strategies.freqtrade_sample import FreqtradeOriginalSampleStrategy
        return FreqtradeOriginalSampleStrategy()
    elif "pure_market" in name or "structure" in name:
        return PureMarketStructurePro()
    elif "pure_price" in name or "sweep" in name:
        return PurePriceActionLiquiditySweep()
    elif "reclaim_1m" in name or "1m" in name:
        return TrendReclaimSniperPro1M()
    elif "bb_reclaim" in name or "reclaim" in name:
        return BBReclaimSniperStrategy()
    elif "bb_middle" in name or "middle" in name:
        return BBMiddleSniperStrategy()
    elif "engulfing" in name:
        return EngulfingSniperStrategy()
    elif "pure" in name:
        return TrendRiderPureStrategy()
    elif "rider" in name or "trend_rider" in name:
        return TrendRiderProStrategy()
    elif "price_ema_7" in name or name == "ema_7":
        return PriceEMACrossoverStrategy(ema_period=7)
    elif "price_ema_25" in name or name == "ema_25":
        return PriceEMACrossoverStrategy(ema_period=25)
    elif "price_ema_99" in name or name == "ema_99":
        return PriceEMACrossoverStrategy(ema_period=99)
    elif "price_ema" in name:
        return PriceEMACrossoverStrategy()
    elif "sniper" in name:
        return AlphaSniperDivergenceStrategy()
    elif "mtf" in name:
        return MTFTrendPullbackStrategy()
    elif "liquidation" in name or "bounce" in name:
        return LiquidationBounceScalper()
    elif "alpha" in name or "pullback" in name:
        return AlphaTrendPullbackStrategy()
    elif "supertrend" in name:
        return SupertrendRSIStrategy()
    elif "ema" in name:
        return EMACrossoverStrategy()
    elif "breakout" in name:
        return BreakoutATRStrategy()
    elif "bollinger" in name or "bb" in name:
        return BollingerRSIScalperStrategy()
    else:
        return get_strategy_instance(strategy_name)

def main():
    parser = argparse.ArgumentParser(description="Binance Futures Strategy Backtester")
    parser.add_argument("--symbol", type=str, default="BTCUSDT", help="Pair trading Binance Futures (e.g. BTCUSDT, CVCUSDT, ETHUSDT)")
    parser.add_argument("--interval", type=str, default="15m", help="Timeframe candle (e.g. 5m, 15m, 1h, 4h)")
    parser.add_argument("--candles", type=int, default=3000, help="Jumlah total candle historis")
    parser.add_argument("--strategy", type=str, default="supertrend", help="Nama strategi: 'supertrend', 'ema', 'breakout'")
    parser.add_argument("--capital", type=float, default=1000.0, help="Modal awal USDT (default: 1000)")
    parser.add_argument("--leverage", type=float, default=3.0, help="Leverage Futures (default: 3x)")
    parser.add_argument("--pos_size", type=float, default=0.7, help="Proporsi max margin modal (default: 0.7 atau 70%%)")
    parser.add_argument("--risk_pct", type=float, default=0.02, help="Risiko modal tetap per trade jika kena SL (default: 0.02 atau 2%%)")
    parser.add_argument("--tz", type=str, default="WIB", help="Timezone tampilan (WIB atau UTC, default: WIB)")
    parser.add_argument("--no_cache", action="store_true", help="Paksa download ulang data tanpa cache")

    args = parser.parse_args()
    print_banner()

    symbol = args.symbol.upper()
    interval = args.interval
    candles = args.candles
    strategy_name = args.strategy
    tz_offset = pd.Timedelta(hours=7) if args.tz.upper() == "WIB" else pd.Timedelta(hours=0)
    tz_label = "WIB" if args.tz.upper() == "WIB" else "UTC"

    # 1. Fetch Data
    try:
        df = fetch_binance_futures_klines(
            symbol=symbol,
            interval=interval,
            total_candles=candles,
            use_cache=not args.no_cache
        )
    except Exception as e:
        print(f"{Fore.RED}[!] Gagal mengambil data market: {e}{Style.RESET_ALL}")
        return

    # 2. Inisialisasi & Generate Sinyal Strategi
    strategy = get_strategy(strategy_name)
    print(f"[*] Menjalankan Strategi: {Fore.YELLOW}{strategy.name}{Style.RESET_ALL} pada {symbol} ({interval}) [Timezone: {tz_label}]...")
    df_signals = strategy.generate_signals(df)

    # 3. Jalankan Simulasi Backtest
    engine = BacktestEngine(
        initial_capital=args.capital,
        leverage=args.leverage,
        risk_per_trade_pct=args.risk_pct,
        fixed_pos_size_pct=args.pos_size,
        fee_rate=0.0005,     # 0.05% Taker fee
        slippage_pct=0.0002  # 0.02% Slippage
    )
    result = engine.run(df_signals)
    metrics = result["metrics"]
    df_trades = result["trades_df"]

    # 4. Tampilkan Laporan Hasil
    print("\n" + "=" * 70)
    print(f"{Fore.GREEN}[*] LAPORAN PERFORMA HASIL BACKTEST [{tz_label}] [*]{Style.RESET_ALL}")
    print("=" * 70)

    pnl_color = Fore.GREEN if metrics['net_profit'] >= 0 else Fore.RED
    win_color = Fore.GREEN if metrics['win_rate'] >= 50 else Fore.YELLOW

    start_date = pd.to_datetime(df['timestamp'].iloc[0]) + tz_offset
    end_date = pd.to_datetime(df['timestamp'].iloc[-1]) + tz_offset

    summary_table = [
        ["Pair & Timeframe", f"{symbol} ({interval})"],
        ["Timezone Tampilan", f"{tz_label} (UTC+7)" if tz_label == "WIB" else "UTC"],
        ["Rentang Data", f"{start_date.strftime('%Y-%m-%d %H:%M:%S')} s/d {end_date.strftime('%Y-%m-%d %H:%M:%S')}"],
        ["Total Candle Diuji", f"{len(df)} candle"],
        ["Strategi", strategy.name],
        ["Leverage Digunakan", f"{args.leverage}x"],
        ["Modal Awal", f"${metrics['initial_capital']:,.2f} USDT"],
        ["Modal Akhir", f"${metrics['final_capital']:,.2f} USDT"],
        ["Net Profit / PnL", f"{pnl_color}${metrics['net_profit']:+,.2f} USDT ({metrics['net_profit_pct']:+.2f}%){Style.RESET_ALL}"],
        ["Total Trades", f"{metrics['total_trades']} (Win: {metrics['win_count']}, Loss: {metrics['loss_count']})"],
        ["Win Rate", f"{win_color}{metrics['win_rate']:.2f}%{Style.RESET_ALL}"],
        ["Profit Factor", f"{metrics['profit_factor']:.2f}"],
        ["Avg Win vs Avg Loss", f"+${metrics['avg_win']:.2f} / -${abs(metrics['avg_loss']):.2f}"],
        ["Risk-to-Reward Ratio", f"1 : {metrics['risk_reward_ratio']:.2f}"],
        ["Max Drawdown", f"{Fore.RED}-{metrics['max_drawdown_pct']:.2f}% (-${metrics['max_drawdown_usd']:.2f}){Style.RESET_ALL}"],
    ]

    print(tabulate(summary_table, headers=["Metrik", "Nilai"], tablefmt="fancy_grid"))

    # 5. Tampilkan 10 Trade Terakhir
    if not df_trades.empty:
        print(f"\n{Fore.CYAN}[*] 10 Riwayat Trade Terakhir (Waktu {tz_label} - Sama Persis Chart Binance Anda):{Style.RESET_ALL}")
        recent_trades = df_trades.tail(10).copy()
        display_trades = []
        for _, t in recent_trades.iterrows():
            trade_pnl_col = Fore.GREEN if t['net_pnl'] > 0 else Fore.RED
            e_wib = (pd.to_datetime(t['entry_time']) + tz_offset).strftime('%Y-%m-%d %H:%M:%S')
            x_wib = (pd.to_datetime(t['exit_time']) + tz_offset).strftime('%Y-%m-%d %H:%M:%S')
            display_trades.append([
                t['type'],
                f"{e_wib} {tz_label}",
                f"${t['entry_price']:.2f}",
                f"{x_wib} {tz_label}",
                f"${t['exit_price']:.2f}",
                t.get('duration', '-'),
                f"{trade_pnl_col}${t['net_pnl']:+,.2f} ({t['pnl_pct']:+.2f}%){Style.RESET_ALL}",
                t['exit_reason']
            ])
        print(tabulate(
            display_trades,
            headers=["Tipe", f"Waktu Entry ({tz_label})", "Harga In", f"Waktu Exit ({tz_label})", "Harga Out", "Durasi Hold", "Net PnL", "Alasan Exit"],
            tablefmt="grid"
        ))

        # Simpan trade log ke CSV dengan kolom WIB
        os.makedirs("results", exist_ok=True)
        log_path = f"results/backtest_{symbol}_{strategy.name}_{interval}.csv"
        df_trades_save = df_trades.copy()
        df_trades_save['entry_time_wib'] = pd.to_datetime(df_trades_save['entry_time']) + pd.Timedelta(hours=7)
        df_trades_save['exit_time_wib'] = pd.to_datetime(df_trades_save['exit_time']) + pd.Timedelta(hours=7)
        df_trades_save.to_csv(log_path, index=False)
        print(f"\n[+] Log lengkap semua trade tersimpan di: {Fore.YELLOW}{log_path}{Style.RESET_ALL}")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
