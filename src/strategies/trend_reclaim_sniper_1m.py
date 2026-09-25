import numpy as np
import pandas as pd
from src.strategies.base import BaseStrategy

class TrendReclaimSniperPro1M(BaseStrategy):
    """
    🎯 1M TREND RECLAIM SNIPER PRO (Institutional 1-Minute Confluence Engine)
    
    Dirancang khusus untuk memecahkan masalah trading 1-Menit di Binance Futures:
    1. Trend Anchor Filter (EMA 200):
       - LONG HANYA saat harga > EMA 200 (Menghindari kena pisau jatuh saat dump besar).
       - SHORT HANYA saat harga < EMA 200 (Menghindari terseret roket pump).
    2. Bollinger Band (20, 2.0) + Fast RSI (7) + Pullback Reclaim:
       - Membeli saat pullback ekstrem di dalam tren naik (Dip Buying).
       - Menjual saat retest ekstrem di dalam tren turun (Rip Selling).
    3. Trailing Stop & Fixed Profit Lock:
       - R:R Asimetris 1:1.8 - 1:2.0
       - Stop Loss terpasang ketat (0.25% - 0.35%)
    """
    def __init__(self, bb_period: int = 20, bb_std: float = 2.0, rsi_period: int = 7, ema_trend: int = 200):
        super().__init__(name="1M Trend Reclaim Sniper Pro")
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_period = rsi_period
        self.ema_trend = ema_trend

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # 1. Bollinger Bands
        df['sma_mid'] = df['close'].rolling(window=self.bb_period).mean()
        df['bb_std'] = df['close'].rolling(window=self.bb_period).std()
        df['bb_upper'] = df['sma_mid'] + (df['bb_std'] * self.bb_std)
        df['bb_lower'] = df['sma_mid'] - (df['bb_std'] * self.bb_std)
        df['bandwidth'] = (df['bb_upper'] - df['bb_lower']) / df['sma_mid']
        
        # 2. EMA Trend Filter (200 & 50)
        df['ema_trend'] = df['close'].ewm(span=self.ema_trend, adjust=False).mean()
        df['ema_fast'] = df['close'].ewm(span=9, adjust=False).mean()
        
        # 3. Fast RSI (7)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / (loss + 1e-9)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 4. Volume Moving Average
        df['vol_ma'] = df['volume'].rolling(window=20).mean()
        df['vol_ok'] = df['volume'] > (df['vol_ma'] * 0.75)

        df['signal'] = 0
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan

        for i in range(self.ema_trend + 2, len(df)):
            close_curr = df['close'].iloc[i]
            close_prev = df['close'].iloc[i-1]
            low_prev = df['low'].iloc[i-1]
            high_prev = df['high'].iloc[i-1]
            
            bb_l_curr = df['bb_lower'].iloc[i]
            bb_l_prev = df['bb_lower'].iloc[i-1]
            bb_u_curr = df['bb_upper'].iloc[i]
            bb_u_prev = df['bb_upper'].iloc[i-1]
            bb_m = df['sma_mid'].iloc[i]
            bw = df['bandwidth'].iloc[i]
            
            ema_t = df['ema_trend'].iloc[i]
            rsi = df['rsi'].iloc[i]
            rsi_prev = df['rsi'].iloc[i-1]
            vol_active = df['vol_ok'].iloc[i]
            
            # Filter pasar mati / flat total (Bandwidth minimal 0.18%)
            if bw < 0.0018 or not vol_active:
                continue

            # 🟢 BUY DIP IN UPTREND:
            # - Syarat 1: Harga di atas EMA 200 (Trend Bullish)
            # - Syarat 2: Terjadi pullback ke Lower Band (Oversold Dip)
            # - Syarat 3: Lilin Reclaim naik kembali ke dalam band dengan RSI memantul dari < 35
            is_uptrend = close_curr > ema_t
            lower_dip = (low_prev <= bb_l_prev) or (close_prev < bb_l_prev)
            reclaim_up = (close_curr > bb_l_curr) and (close_curr > close_prev)
            rsi_dip_bounce = (rsi_prev <= 35) and (rsi > rsi_prev)

            if is_uptrend and lower_dip and reclaim_up and rsi_dip_bounce:
                df.iloc[i, df.columns.get_loc('signal')] = 1
                sl = min(low_prev, df['low'].iloc[i]) * 0.9985
                sl = max(sl, close_curr * 0.9965) # Max SL 0.35%
                risk = close_curr - sl
                tp = close_curr + max(risk * 1.8, close_curr * 0.005) # Min TP 0.5% (R:R 1:1.8)
                df.iloc[i, df.columns.get_loc('stop_loss')] = sl
                df.iloc[i, df.columns.get_loc('take_profit')] = tp
                continue

            # 🔴 SELL RIP IN DOWNTREND:
            # - Syarat 1: Harga di bawah EMA 200 (Trend Bearish)
            # - Syarat 2: Terjadi retest ke Upper Band (Overbought Rip)
            # - Syarat 3: Lilin Reclaim turun kembali ke bawah band dengan RSI reject dari > 65
            is_downtrend = close_curr < ema_t
            upper_rip = (high_prev >= bb_u_prev) or (close_prev > bb_u_prev)
            reclaim_down = (close_curr < bb_u_curr) and (close_curr < close_prev)
            rsi_rip_reject = (rsi_prev >= 65) and (rsi < rsi_prev)

            if is_downtrend and upper_rip and reclaim_down and rsi_rip_reject:
                df.iloc[i, df.columns.get_loc('signal')] = -1
                sl = max(high_prev, df['high'].iloc[i]) * 1.0015
                sl = min(sl, close_curr * 1.0035) # Max SL 0.35%
                risk = sl - close_curr
                tp = close_curr - max(risk * 1.8, close_curr * 0.005) # Min TP 0.5% (R:R 1:1.8)
                df.iloc[i, df.columns.get_loc('stop_loss')] = sl
                df.iloc[i, df.columns.get_loc('take_profit')] = tp

        return df
