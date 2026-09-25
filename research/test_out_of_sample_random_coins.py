import sys
import pandas as pd
import numpy as np
from test_unbiased_20_pairs import fetch_1year_klines, calculate_supertrend, calculate_ema
from src.backtester import BacktestEngine

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 30 KOIN BARU (OUT-OF-SAMPLE) - TIDAK ADA DALAM 20 KOIN AWAL SAMA SEKALI
out_of_sample_coins = [
    # Meme Coins
    'PEPEUSDT', 'WIFUSDT', 'SHIBUSDT', 'BONKUSDT', 'FLOKIUSDT', 'MEMEUSDT', 'BOMEUSDT',
    # AI & DePIN
    'RENDERUSDT', 'FETUSDT', 'WLDUSDT', 'TAOUSDT', 'NEARUSDT',
    # New Gen L1 & L2
    'SUIUSDT', 'SEIUSDT', 'TIAUSDT', 'STXUSDT', 'IMXUSDT', 'STRKUSDT', 'TONUSDT',
    # DeFi & Real World Asset (RWA)
    'AAVEUSDT', 'PENDLEUSDT', 'ONDOUSDT', 'JUPUSDT', 'PYTHUSDT', 'CRVUSDT', 'MKRUSDT', 'DYDXUSDT',
    # Gaming & Metaverse
    'GALAUSDT', 'SANDUSDT', 'MANAUSDT', 'AXSUSDT'
]

def test_out_of_sample():
    print("="*95)
    print("🧪 OUT-OF-SAMPLE TEST: MENGUJI 30 KOIN BARU (TIDAK PERNAH DI-CHERRY PICK)")
    print("   Data 1 Tahun Penuh Binance Futures (Timeframe 1-Jam | 1H)")
    print("="*95)
    
    results = []
    
    for sym in out_of_sample_coins:
        try:
            df = fetch_1year_klines(sym, '1h')
            if df is None or len(df) < 500:
                continue
                
            df['supertrend'], df['st_dir'] = calculate_supertrend(df, 10, 3.0)
            df['ema_50'] = calculate_ema(df['close'], 50)
            
            df['enter_long'] = np.where((df['st_dir'] == 1) & (df['st_dir'].shift(1) == -1) & (df['close'] > df['ema_50']), 1, 0)
            df['exit_long'] = np.where(df['st_dir'] == -1, 1, 0)
            df['enter_short'] = np.where((df['st_dir'] == -1) & (df['st_dir'].shift(1) == 1) & (df['close'] < df['ema_50']), 1, 0)
            df['exit_short'] = np.where(df['st_dir'] == 1, 1, 0)
            df['sl_price'] = df['supertrend']
            
            engine = BacktestEngine(initial_capital=5000.0, leverage=2.0, fixed_pos_size_pct=0.20, fee_rate=0.0005, slippage_pct=0.0002)
            m = engine.run(df)['metrics']
            
            results.append({
                'Symbol': sym,
                'Lilin': len(df),
                'Trades': m['total_trades'],
                'Wins': m['win_count'],
                'Losses': m['loss_count'],
                'Win Rate': f"{m['win_rate']:.1f}%",
                'Profit Factor': m['profit_factor'],
                'Max DD': f"-{m['max_drawdown_pct']:.1f}%",
                'Net PnL ($)': m['net_profit'],
                'ROI (%)': m['net_profit_pct']
            })
        except Exception:
            pass
            
    df_res = pd.DataFrame(results)
    if df_res.empty:
        print("Gagal menguji koin.")
        return
        
    print(f"{'Symbol':<12} | {'Trades':<7} | {'Win Rate':<9} | {'Profit Factor':<14} | {'Max DD':<9} | {'Net PnL ($)':<14} | {'Status'}")
    print("-" * 95)
    
    for _, r in df_res.iterrows():
        pnl_str = f"{'+' if r['Net PnL ($)']>=0 else ''}${r['Net PnL ($)']:,.2f}"
        st_icon = "🟢 PROFIT" if r['Net PnL ($)'] > 0 else "🔴 LOSS"
        print(f"{r['Symbol']:<12} | {r['Trades']:<7} | {r['Win Rate']:<9} | {r['Profit Factor']:>12.2f}  | {r['Max DD']:<9} | {pnl_str:>13}  | {st_icon}")
        
    print("="*95)
    total_pnl = df_res['Net PnL ($)'].sum()
    win_coins = (df_res['Net PnL ($)'] > 0).sum()
    total_coins = len(df_res)
    total_trades = df_res['Trades'].sum()
    
    print(f"💰 TOTAL PORTOFOLIO NET PNL (30 KOIN BARU): {'+' if total_pnl>=0 else ''}${total_pnl:,.2f} USDT")
    print(f"📊 PERSENTASE KOIN HIJAU (PROFIT)         : {win_coins} dari {total_coins} koin ({win_coins/total_coins*100:.1f}%)")
    print(f"🔥 TOTAL SAMPEL DATA KOIN BARU            : {total_trades} Trades")
    print("="*95)

if __name__ == "__main__":
    test_out_of_sample()
