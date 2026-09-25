import numpy as np
import pandas as pd
from src.strategies.base import BaseStrategy

class UltraFast1mScalperPro(BaseStrategy):
    """
    ⚡ ULTRA FAST 1M SCALPER PRO (Institutional Micro-Trend & Confluence Scalper)
    Khusus Timeframe 1 Menit Binance Futures.
    
    Komponen:
    1. Trend Filter: EMA 100 (Hanya Long saat Uptrend, Hanya Short saat Downtrend)
    2. Value Pullback: EMA 9 & EMA 21 Dynamic Pullback Zone
    3. Momentum Trigger: Fast RSI 7 Bounce / Stochastic Momentum
    4. Volume Filter: Volume > 1.1x MA 20 Volume (Menghindari Sideways Sepi / Fee Trap)
    5. Smart Profit Lock: R:R 1:1.8 with Tight Dynamic SL (0.20% - 0.35%)
    """
    def __init__(self, ema_fast: int = 9, ema_mid: int = 21, ema_trend: int = 100, rsi_period: int = 7):
        super().__init__(name="UltraFast 1M Scalper Pro")
        self.ema_fast = ema_fast
        self.ema_mid = ema_mid
        self.ema_trend = ema_trend
        self.rsi_period = rsi_period

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # 1. EMAs
        df['ema_fast'] = df['close'].ewm(span=self.ema_fast, adjust=False).mean()
        df['ema_mid'] = df['close'].ewm(span=self.ema_mid, adjust=False).mean()
        df['ema_trend'] = df['close'].ewm(span=self.ema_trend, adjust=False).mean()
        
        # 2. RSI Fast (7)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / (loss + 1e-9)
        df['rsi_fast'] = 100 - (100 / (1 + rs))
        
        # 3. Volume Moving Average Filter
        df['vol_ma'] = df['volume'].rolling(window=20).mean()
        df['vol_filter'] = df['volume'] > (df['vol_ma'] * 0.9)
        
        # 4. ATR untuk Dynamic SL/TP
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # Inisialisasi kolom output
        df['signal'] = 0
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan
        df['trail_stop_pct'] = 0.0025 # 0.25% Trailing offset
        
        for i in range(self.ema_trend + 2, len(df)):
            close_curr = df['close'].iloc[i]
            close_prev = df['close'].iloc[i-1]
            ema_f_curr = df['ema_fast'].iloc[i]
            ema_f_prev = df['ema_fast'].iloc[i-1]
            ema_m_curr = df['ema_mid'].iloc[i]
            ema_m_prev = df['ema_mid'].iloc[i-1]
            ema_t = df['ema_trend'].iloc[i]
            rsi = df['rsi_fast'].iloc[i]
            rsi_prev = df['rsi_fast'].iloc[i-1]
            vol_ok = df['vol_filter'].iloc[i]
            atr = df['atr'].iloc[i] if not np.isnan(df['atr'].iloc[i]) else close_curr * 0.002
            
            # 🟢 LONG CONDITION:
            # - Trend: Close > EMA 100 & EMA Fast > EMA Mid
            # - Pullback Trigger: Lilin memantul dari EMA 9/21 atau Crossover Fast > Mid dengan RSI keluar dari oversold (< 45 naik ke atas)
            is_uptrend = (close_curr > ema_t) and (ema_f_curr >= ema_m_curr)
            is_pullback_bounce = (close_prev <= ema_f_prev) and (close_curr > ema_f_curr) and (rsi > 40 and rsi < 70)
            is_fast_cross_up = (ema_f_prev <= ema_m_prev) and (ema_f_curr > ema_m_curr) and (rsi > 45)
            
            if is_uptrend and (is_pullback_bounce or is_fast_cross_up) and vol_ok:
                df.iloc[i, df.columns.get_loc('signal')] = 1
                # Stop loss tipis di bawah EMA mid atau 1.2x ATR
                sl = min(df['low'].iloc[i-1], ema_m_curr - atr * 0.5)
                sl = max(sl, close_curr * 0.996) # Max SL 0.4%
                risk = close_curr - sl
                tp = close_curr + (risk * 1.8) # R:R 1:1.8
                df.iloc[i, df.columns.get_loc('stop_loss')] = sl
                df.iloc[i, df.columns.get_loc('take_profit')] = tp
                continue
                
            # 🔴 SHORT CONDITION:
            # - Trend: Close < EMA 100 & EMA Fast < EMA Mid
            # - Pullback Trigger: Lilin reject di bawah EMA 9/21 atau Crossover Fast < Mid dengan RSI keluar dari overbought (> 55 turun ke bawah)
            is_downtrend = (close_curr < ema_t) and (ema_f_curr <= ema_m_curr)
            is_pullback_reject = (close_prev >= ema_f_prev) and (close_curr < ema_f_curr) and (rsi < 60 and rsi > 30)
            is_fast_cross_down = (ema_f_prev >= ema_m_prev) and (ema_f_curr < ema_m_curr) and (rsi < 55)
            
            if is_downtrend and (is_pullback_reject or is_fast_cross_down) and vol_ok:
                df.iloc[i, df.columns.get_loc('signal')] = -1
                # Stop loss tipis di atas EMA mid atau 1.2x ATR
                sl = max(df['high'].iloc[i-1], ema_m_curr + atr * 0.5)
                sl = min(sl, close_curr * 1.004) # Max SL 0.4%
                risk = sl - close_curr
                tp = close_curr - (risk * 1.8) # R:R 1:1.8
                df.iloc[i, df.columns.get_loc('stop_loss')] = sl
                df.iloc[i, df.columns.get_loc('take_profit')] = tp

        return df
