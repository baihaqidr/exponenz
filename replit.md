# Running this project on Replit

This is the imported Python Binance Futures backtester and web dashboard. Keep the existing Python source layout.

- **Web dashboard:** Use the **Run** button (the `Start application` workflow). It runs `PORT=5000 python run_dashboard.py` and serves the dashboard in Replit Preview.
- **Command-line backtest:** Open the Shell and run, for example, `python run_backtest.py --symbol BTCUSDT --interval 4h --candles 120 --strategy supertrend`. Other strategy and timeframe options are described in `README.md` and `PANDUAN_CARA_JALANKAN.md`. Trade logs, when generated, go to `results/`.
- **Dependencies:** Python packages are listed in `requirements.txt`. Install them through Replit's Python package management if the environment is reset.
- **Data:** The app requests public Binance market data over the network; some historical CSV files are included in `data/`. No Binance API key is needed for backtests or the dashboard's public market-data views. Network access and Binance endpoint availability affect live data.
- **Trading bot:** Unlike backtests, the bot calls Binance account and order APIs. It defaults to Binance **testnet** and needs separate `BINANCE_API_KEY` and `BINANCE_API_SECRET` credentials to trade there. No trading credentials are configured by this setup. Do **not** add real-account credentials or set `BINANCE_TESTNET=False` on a publicly accessible dashboard: the trading endpoints currently have no access control.

Backtest results are simulations, not live trading advice.