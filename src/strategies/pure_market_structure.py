import numpy as np
import pandas as pd
from src.strategies.base import BaseStrategy

class PureMarketStructurePro(BaseStrategy):
    """
    👑 PURE MARKET STRUCTURE & LIQUIDITY SWEEP PRO (100% PURE PRICE ACTION - ZERO INDICATOR)
    
    100% Murni Price Action, Candlestick Geometry & Market Structure.
    
    Aturan:
    1. Pure Price Action Structure (Higher Highs / Lower Lows):
       - Bullish Structure: Low saat ini lebih tinggi dari Low sebelumnya (Higher Low). LONG ONLY.
       - Bearish Structure: High saat ini lebih rendah dari High sebelumnya (Lower High). SHORT ONLY.
    2. Liquidity Sweep Rejection (Smart Money Sweep):
       - Jarum menusuk melewati key swing level lalu closing berbalik arah.
       - Wick ratio >= 1.2x Body (Pinbar / Hammer / Shooting Star).
    3. Konfirmasi Candle Trigger (No False Wick):
       - Close candle searah dengan arah rejection (Bullish Close untuk Long, Bearish Close untuk Short).
    4. Auto Fee-Adjusted Net 2R Take Profit:
       - TP = (2.0 x Jarak SL) + 0.10% Binance Roundtrip Fee.
       - SL = Ujung ekor jarum terluar.
    """
    def __init__(self, lookback: int = 15, min_wick_ratio: float = 1.0, rr_ratio: float = 2.0, fee_pct: float = 0.0010):
        super().__init__(name="Pure Market Structure Pro")
        self.lookback = lookback
        self.min_wick_ratio = min_wick_ratio
        self.rr_ratio = rr_ratio
        self.fee_pct = fee_pct

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # 1. Swing High & Swing Low Murni Price Action
        df['sw_high'] = df['high'].shift(1).rolling(window=self.lookback).max()
        df['sw_low'] = df['low'].shift(1).rolling(window=self.lookback).min()
        
        # 2. Macro Swing Structure (Lookback x 3)
        df['macro_high'] = df['high'].shift(self.lookback).rolling(window=self.lookback).max()
        df['macro_low'] = df['low'].shift(self.lookback).rolling(window=self.lookback).min()
        
        df['signal'] = 0
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan
        
        for i in range(self.lookback * 2 + 2, len(df)):
            open_c = df['open'].iloc[i]
            close_c = df['close'].iloc[i]
            high_c = df['high'].iloc[i]
            low_c = df['low'].iloc[i]
            
            sw_h = df['sw_high'].iloc[i]
            sw_l = df['sw_low'].iloc[i]
            macro_l = df['macro_low'].iloc[i]
            macro_h = df['macro_high'].iloc[i]
            
            body = abs(close_c - open_c)
            body_safe = max(body, close_c * 0.0002)
            upper_wick = high_c - max(open_c, close_c)
            lower_wick = min(open_c, close_c) - low_c
            
            # Pure PA Market Structure:
            # Bullish Structure = Swing Low sekarang >= Macro Swing Low (Higher Lows)
            is_higher_lows = sw_l >= macro_l
            # Bearish Structure = Swing High sekarang <= Macro Swing High (Lower Highs)
            is_lower_highs = sw_h <= macro_h
            
            # 🟢 BUY SETUP (Pure PA Bullish Sweep in Uptrend Structure):
            # 1. Struktur Market Bullish (Higher Lows)
            # 2. Jarum menusuk di bawah Swing Low lokal tapi Close di atasnya (Rejection)
            # 3. Candle ditutup hijau (Close > Open) dengan Lower Wick panjang
            is_bull_sweep = (low_c < sw_l) and (close_c >= sw_l) and (close_c > open_c)
            is_bull_hammer = lower_wick >= (body_safe * self.min_wick_ratio)
            
            if is_higher_lows and is_bull_sweep and is_bull_hammer:
                sl = low_c * 0.999
                risk = close_c - sl
                risk_pct = risk / close_c
                if 0.0010 <= risk_pct <= 0.0060:
                    tp = close_c + (risk * self.rr_ratio) + (close_c * self.fee_pct)
                    df.iloc[i, df.columns.get_loc('signal')] = 1
                    df.iloc[i, df.columns.get_loc('stop_loss')] = sl
                    df.iloc[i, df.columns.get_loc('take_profit')] = tp
                    continue

            # 🔴 SELL SETUP (Pure PA Bearish Sweep in Downtrend Structure):
            # 1. Struktur Market Bearish (Lower Highs)
            # 2. Jarum menusuk di atas Swing High lokal tapi Close di bawahnya (Rejection)
            # 3. Candle ditutup merah (Close < Open) dengan Upper Wick panjang
            is_bear_sweep = (high_c > sw_h) and (close_c <= sw_h) and (close_c < open_c)
            is_bear_star = upper_wick >= (body_safe * self.min_wick_ratio)
            
            if is_lower_highs and is_bear_sweep and is_bear_star:
                sl = high_c * 1.001
                risk = sl - close_c
                risk_pct = risk / close_c
                if 0.0010 <= risk_pct <= 0.0060:
                    tp = close_c - (risk * self.rr_ratio) - (close_c * self.fee_pct)
                    df.iloc[i, df.columns.get_loc('signal')] = -1
                    df.iloc[i, df.columns.get_loc('stop_loss')] = sl
                    df.iloc[i, df.columns.get_loc('take_profit')] = tp

        return df
