import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import requests
import pandas as pd
from datetime import datetime
from src.strategy_registry import get_strategy_instance
from src.backtester import BacktestEngine

def fetch_data(symbol='SAGAUSDT', interval='15m', max_batches=35):
    url = "https://data-api.binance.vision/api/v3/klines"
    all_rows = []
    end_time = None
    
    for i in range(max_batches):
        params = {"symbol": symbol, "interval": interval, "limit": 1000}
        if end_time:
            params["endTime"] = end_time - 1
        try:
            r = requests.get(url, params=params, timeout=5)
            data = r.json()
            if not data or not isinstance(data, list) or len(data) == 0:
                break
            all_rows = data + all_rows
            end_time = data[0][0]
            if len(data) < 1000:
                break
        except Exception as e:
            break
            
    cols = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']
    df = pd.DataFrame(all_rows, columns=cols[:len(all_rows[0])])
    df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = df[c].astype(float)
    df.drop_duplicates(subset=['timestamp'], inplace=True)
    df.sort_values('timestamp', inplace=True)
    return df.reset_index(drop=True)

for tf in ['5m (35 Batches)', '15m (Jangka Panjang)', '1h (1 Tahun Penuh)']:
    interval = tf.split()[0]
    df = fetch_data('SAGAUSDT', interval=interval, max_batches=35)
    
    strategy = get_strategy_instance('freqtrade_bband_rsi')
    df_sig = strategy.generate_signals(df)
    
    engine = BacktestEngine(
        initial_capital=1000.0,
        leverage=2.0,
        risk_per_trade_pct=0.02,
        fixed_pos_size_pct=0.5,
        fee_rate=0.0005,
        slippage_pct=0.0002
    )
    res = engine.run(df_sig)
    m = res["metrics"]
    trades_df = res["trades_df"]
    
    print(f"\n=======================================================", flush=True)
    print(f"=== SAGAUSDT [{tf}] | {len(df)} candles ({df['timestamp'].min().strftime('%Y-%m-%d')} s/d {df['timestamp'].max().strftime('%Y-%m-%d')}) ===", flush=True)
    print(f"Total Trades : {m.get('total_trades')}", flush=True)
    print(f"Win Rate     : {m.get('win_rate', 0):.1f}% ({m.get('win_count')} W / {m.get('loss_count')} L)", flush=True)
    print(f"Total Net PnL: ${m.get('net_profit', 0):.2f}", flush=True)
    print(f"Profit Factor: {m.get('profit_factor', 0):.2f}", flush=True)
    print(f"Max Drawdown : {m.get('max_drawdown_pct', 0):.2f}%", flush=True)
    
    if not trades_df.empty:
        trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
        trades_df['month'] = (trades_df['exit_time'] + pd.Timedelta(hours=7)).dt.strftime('%Y-%m')
        monthly = trades_df.groupby('month').agg(
            trades=('net_pnl', 'count'),
            win_rate=('net_pnl', lambda x: round((x > 0).sum() / len(x) * 100, 1)),
            net_pnl=('net_pnl', lambda x: round(x.sum(), 2))
        )
        print("Breakdown Bulanan:", flush=True)
        print(monthly, flush=True)
