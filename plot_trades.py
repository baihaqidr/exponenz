import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from src.data_fetcher import fetch_binance_futures_klines
from src.strategies.trend_rider import TrendRiderProStrategy
from src.backtester import BacktestEngine

ARTIFACT_DIR = r"C:\Users\Baihaqi\.gemini\antigravity-ide\brain\b7a7b608-4e11-4389-a4c5-3c4973e28a39"

def plot_backtest_chart(symbol="BTCUSDT", interval="4h", total_candles=3000, display_candles=220):
    # 1. Fetch data from cached 3000 candles
    df = fetch_binance_futures_klines(symbol=symbol, interval=interval, total_candles=total_candles)
    # Convert to WIB (UTC+7)
    df['timestamp'] = pd.to_datetime(df['timestamp']) + pd.Timedelta(hours=7)
    
    # 2. Run Strategy & Backtest
    strategy = TrendRiderProStrategy(period=16, multiplier=4.0, adx_min=15.0)
    df_signals = strategy.generate_signals(df)
    
    backtester = BacktestEngine(initial_capital=1000.0, leverage=2.0, fixed_pos_size_pct=0.7)
    results = backtester.run(df_signals)
    metrics = results['metrics']
    df_trades = results['trades_df']
    
    # Filter for display
    df_plot = df_signals.tail(display_candles).copy().reset_index(drop=True)
    min_date = df_plot['timestamp'].min()
    max_date = df_plot['timestamp'].max()
    
    # Filter trades within display range
    if not df_trades.empty:
        df_trades['entry_time_dt'] = pd.to_datetime(df_trades['entry_time']) + pd.Timedelta(hours=7)
        df_trades['exit_time_dt'] = pd.to_datetime(df_trades['exit_time']) + pd.Timedelta(hours=7)
        trades_in_view = df_trades[(df_trades['entry_time_dt'] >= min_date) | (df_trades['exit_time_dt'] >= min_date)]
    else:
        trades_in_view = pd.DataFrame()
    
    # 3. Create High-Quality Plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 10), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
    plt.style.use('dark_background')
    fig.patch.set_facecolor('#0b0f19')
    ax1.set_facecolor('#111827')
    ax2.set_facecolor('#111827')
    
    width = 0.10
    
    up = df_plot[df_plot.close >= df_plot.open]
    down = df_plot[df_plot.close < df_plot.open]
    
    up_dates = mdates.date2num(up['timestamp'])
    down_dates = mdates.date2num(down['timestamp'])
    all_dates = mdates.date2num(df_plot['timestamp'])
    
    # Plot Wicks
    ax1.vlines(up_dates, up.low, up.high, color='#10b981', linewidth=1.2, alpha=0.9)
    ax1.vlines(down_dates, down.low, down.high, color='#ef4444', linewidth=1.2, alpha=0.9)
    
    # Plot Bodies
    ax1.bar(up_dates, up.close - up.open, width, bottom=up.open, color='#10b981', alpha=0.95, label='Bull Candle')
    ax1.bar(down_dates, down.open - down.close, width, bottom=down.close, color='#ef4444', alpha=0.95, label='Bear Candle')
    
    # Plot Supertrend Line
    bull_st = df_plot[df_plot['st_dir'] == 1]
    bear_st = df_plot[df_plot['st_dir'] == -1]
    ax1.scatter(mdates.date2num(bull_st['timestamp']), bull_st['supertrend'], color='#059669', s=6, label='Supertrend (16, 4.0) Bull', zorder=4)
    ax1.scatter(mdates.date2num(bear_st['timestamp']), bear_st['supertrend'], color='#dc2626', s=6, label='Supertrend (16, 4.0) Bear', zorder=4)
    
    # Mark Trades
    for _, t in trades_in_view.iterrows():
        e_time = t['entry_time_dt']
        x_time = t['exit_time_dt']
        entry_price = t['entry_price']
        exit_price = t['exit_price']
        net_pnl = t['net_pnl']
        pnl_pct = t['pnl_pct']
        side = t['type']
        exit_reason = t['exit_reason']
        
        entry_time_num = mdates.date2num(e_time)
        exit_time_num = mdates.date2num(x_time)
        
        pnl_color = '#10b981' if net_pnl > 0 else '#ef4444'
        pnl_text = f"+${net_pnl:.1f} (+{pnl_pct:.1f}%)" if net_pnl > 0 else f"-${abs(net_pnl):.1f} ({pnl_pct:.1f}%)"
        
        if e_time >= min_date:
            if side == 'LONG':
                ax1.scatter(entry_time_num, entry_price, color='#38bdf8', marker='^', s=160, edgecolors='white', linewidths=1.5, zorder=6)
                ax1.annotate(f"BUY LONG\n${entry_price:,.0f}", (entry_time_num, entry_price), textcoords="offset points", xytext=(0, -32), ha='center', fontsize=8, color='#38bdf8', weight='bold')
            else:
                ax1.scatter(entry_time_num, entry_price, color='#fbbf24', marker='v', s=160, edgecolors='white', linewidths=1.5, zorder=6)
                ax1.annotate(f"SELL SHORT\n${entry_price:,.0f}", (entry_time_num, entry_price), textcoords="offset points", xytext=(0, 18), ha='center', fontsize=8, color='#fbbf24', weight='bold')
            
        if x_time >= min_date and x_time <= max_date:
            ax1.scatter(exit_time_num, exit_price, color=pnl_color, marker='X', s=130, edgecolors='white', linewidths=1.2, zorder=6)
            ax1.annotate(f"EXIT: {exit_reason}\n{pnl_text}", (exit_time_num, exit_price), textcoords="offset points", xytext=(0, 15 if net_pnl > 0 else -30), ha='center', fontsize=8, color='white', weight='bold', bbox=dict(boxstyle='round,pad=0.3', facecolor=pnl_color, edgecolor='none', alpha=0.9))
        
        if e_time >= min_date and x_time <= max_date:
            ax1.plot([entry_time_num, exit_time_num], [entry_price, exit_price], color=pnl_color, linestyle='--', linewidth=1.5, alpha=0.7)

    ax1.set_title(f"Binance Futures [{symbol} - {interval}] Strategy: Trend Rider Pro [WIB / UTC+7]\nTotal Net Profit: ${metrics['net_profit']:.2f} (+{metrics['net_profit_pct']:.1f}% ROI) | Win Rate: {metrics['win_rate']:.1f}% | Profit Factor: {metrics['profit_factor']:.2f}", fontsize=14, color='#f8fafc', pad=15, weight='bold')
    ax1.set_ylabel("Price (USDT)", fontsize=11, color='#94a3b8')
    ax1.grid(True, linestyle=':', alpha=0.25, color='#475569')
    ax1.legend(loc='upper left', fontsize=9, facecolor='#1e293b', edgecolor='#334155')
    
    # Subplot 2: ADX Indicator
    ax2.plot(all_dates, df_plot['adx'], color='#a855f7', label='ADX (14)', linewidth=2.0)
    ax2.axhline(15, color='#fbbf24', linestyle='--', linewidth=1.2, label='Filter Threshold (15)')
    ax2.set_ylabel("ADX Strength", fontsize=10, color='#94a3b8')
    ax2.set_ylim(0, 65)
    ax2.grid(True, linestyle=':', alpha=0.25, color='#475569')
    ax2.legend(loc='upper left', fontsize=9, facecolor='#1e293b', edgecolor='#334155')
    
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d %b %Y\n%H:%M WIB'))
    fig.autofmt_xdate()
    plt.tight_layout()
    
    out1 = "results/chart_BTCUSDT_4h.png"
    out2 = os.path.join(ARTIFACT_DIR, "chart_BTCUSDT_4h.png")
    os.makedirs("results", exist_ok=True)
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    
    plt.savefig(out1, dpi=160, bbox_inches='tight')
    plt.savefig(out2, dpi=160, bbox_inches='tight')
    plt.close()
    print(f"[+] Chart gambar tersimpan di: {out1} dan {out2}")

if __name__ == "__main__":
    plot_backtest_chart(symbol="BTCUSDT", interval="4h", total_candles=3000, display_candles=220)
