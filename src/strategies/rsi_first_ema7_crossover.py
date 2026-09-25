import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy
from src.indicators import calculate_rsi, calculate_ema

class RsiFirstEma7CrossoverStrategy(BaseStrategy):
    """
    Strategi Rebound Kuantitatif: First Time RSI Oversold (< 30) State Machine 
    dengan Pemicu Konfirmasi Lilin Pertama Menembus EMA 7 (Breakout Crossover)
    dan Manajemen Risiko Presisi R:R 1:2 (SL di Low Lilin Entry, TP di 2x Jarak Risk).
    """
    def __init__(
        self,
        rsi_period: int = 14,
        rsi_oversold: float = 30.0,
        ema_period: int = 7,
        rr_multiplier: float = 2.0,
        min_risk_pct: float = 0.001,
        name: str = "rsi_first_ema7_crossover"
    ):
        super().__init__(name=name, is_long_only=True)
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.ema_period = ema_period
        self.rr_multiplier = rr_multiplier
        self.min_risk_pct = min_risk_pct

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # 1. Hitung Indikator Resmi
        df['rsi'] = calculate_rsi(df['close'], period=self.rsi_period)
        df['ema_7'] = calculate_ema(df['close'], length=self.ema_period)
        
        enter_long = np.zeros(len(df), dtype=int)
        signal = np.zeros(len(df), dtype=int)
        sl_price = np.full(len(df), np.nan)
        tp_price = np.full(len(df), np.nan)
        
        armed = False
        
        # 2. State Machine:
        # - Status ARMED aktif saat RSI < 30
        # - Status ARMED TETAP AKTIF meskipun lilin berikutnya membuat RSI pulih > 30
        # - Eksekusi pada lilin PERTAMA yang berhasil Close melintasi ke atas EMA 7
        for i in range(1, len(df)):
            rsi_val = df['rsi'].iloc[i]
            close_val = df['close'].iloc[i]
            low_val = df['low'].iloc[i]
            ema7_val = df['ema_7'].iloc[i]
            prev_close = df['close'].iloc[i-1]
            prev_ema7 = df['ema_7'].iloc[i-1]
            
            # Pemicu Siaga (Oversold terjadi)
            if rsi_val < self.rsi_oversold:
                armed = True
                
            # Pemicu Eksekusi: Crossover Pertama ke atas EMA 7
            if armed and (prev_close <= prev_ema7) and (close_val > ema7_val):
                enter_long[i] = 1
                signal[i] = 1
                
                entry_p = close_val
                sl_p = low_val
                risk = entry_p - sl_p
                
                # Buffer pengaman jika lilin tidak memiliki ekor bawah (marubozu)
                min_risk = entry_p * self.min_risk_pct
                if risk < min_risk:
                    risk = min_risk
                    sl_p = entry_p - risk
                    
                tp_p = entry_p + (self.rr_multiplier * risk)
                
                sl_price[i] = sl_p
                tp_price[i] = tp_p
                
                # Matikan status siaga (1x entry per siklus)
                armed = False
                
        df['enter_long'] = enter_long
        df['signal'] = signal
        df['sl_price'] = sl_price
        df['tp_price'] = tp_price
        
        return df
