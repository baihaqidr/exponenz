import numpy as np
import pandas as pd
from src.strategies.base import BaseStrategy

class PurePriceActionLiquiditySweep(BaseStrategy):
    """
    🎯 PURE PRICE ACTION: LIQUIDITY SWEEP & PINBAR REVERSAL (ZERO INDICATOR)
    
    100% Murni Price Action Candlestick & Market Structure (Tanpa Indikator Apapun).
    
    Logika Kuantitatif:
    1. Swing High / Swing Low Detection (Lookback N Candle).
    2. Bullish Liquidity Sweep (Spring):
       - Harga Low menusuk ke bawah Swing Low terdekat (menyapu stop loss retail).
       - Closing lilin gagal tembus dan BERHASIL DITUTUP KEMBALI di atas level Swing Low.
       - Membentuk Lower Wick panjang (Rejection Hammer / Pinbar).
    3. Bearish Liquidity Sweep (Upthrust):
       - Harga High menusuk ke atas Swing High terdekat (menyapu stop loss short seller).
       - Closing lilin gagal tembus dan BERHASIL DITUTUP KEMBALI di bawah level Swing High.
       - Membentuk Upper Wick panjang (Shooting Star / Inverted Pinbar).
    4. Auto Fee-Adjusted Net 2R Take Profit:
       - TP = (2.0 x Jarak SL) + 0.10% Roundtrip Binance Fee.
       - SL = Tepat di ujung ekor jarum (0.15% - 0.35%).
    """
    def __init__(self, swing_lookback: int = 20, min_wick_ratio: float = 1.2, max_sl_pct: float = 0.0045, rr_ratio: float = 2.0, fee_pct: float = 0.0010):
        super().__init__(name="Pure Price Action Liquidity Sweep")
        self.swing_lookback = swing_lookback
        self.min_wick_ratio = min_wick_ratio
        self.max_sl_pct = max_sl_pct
        self.rr_ratio = rr_ratio
        self.fee_pct = fee_pct

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Cari Swing High dan Swing Low historis secara rolling
        df['swing_high'] = df['high'].shift(1).rolling(window=self.swing_lookback).max()
        df['swing_low'] = df['low'].shift(1).rolling(window=self.swing_lookback).min()
        
        df['signal'] = 0
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan
        
        for i in range(self.swing_lookback + 2, len(df)):
            open_p = df['open'].iloc[i]
            close_p = df['close'].iloc[i]
            high_p = df['high'].iloc[i]
            low_p = df['low'].iloc[i]
            
            sw_high = df['swing_high'].iloc[i]
            sw_low = df['swing_low'].iloc[i]
            
            body = abs(close_p - open_p)
            body_safe = max(body, close_p * 0.0002)
            upper_wick = high_p - max(open_p, close_p)
            lower_wick = min(open_p, close_p) - low_p
            
            # 🟢 BUY SETUP: Bullish Liquidity Sweep (Spring)
            # 1. Jarum Low menusuk tembus ke bawah Swing Low
            # 2. Harga Close ditutup kembali di atas Swing Low (Rejection Reclaim)
            # 3. Lower wick panjang (ekor bawah >= min_wick_ratio * body)
            is_low_sweep = (low_p < sw_low) and (close_p >= sw_low) and (close_p >= open_p or lower_wick > body * 1.5)
            is_bull_pinbar = lower_wick >= (body_safe * self.min_wick_ratio)
            
            if is_low_sweep and is_bull_pinbar:
                sl = low_p * 0.999 # 0.1% di luar ujung jarum
                risk = close_p - sl
                risk_pct = risk / close_p
                
                # Filter SL jika terlalu lebar (max_sl_pct)
                if 0.0010 <= risk_pct <= self.max_sl_pct:
                    # Fee-Adjusted Net 2R: (2 * risk) + (entry * fee_pct)
                    tp = close_p + (risk * self.rr_ratio) + (close_p * self.fee_pct)
                    df.iloc[i, df.columns.get_loc('signal')] = 1
                    df.iloc[i, df.columns.get_loc('stop_loss')] = sl
                    df.iloc[i, df.columns.get_loc('take_profit')] = tp
                    continue
                    
            # 🔴 SELL SETUP: Bearish Liquidity Sweep (Upthrust)
            # 1. Jarum High menusuk tembus ke atas Swing High
            # 2. Harga Close ditutup kembali di bawah Swing High (Rejection Reclaim)
            # 3. Upper wick panjang (ekor atas >= min_wick_ratio * body)
            is_high_sweep = (high_p > sw_high) and (close_p <= sw_high) and (close_p <= open_p or upper_wick > body * 1.5)
            is_bear_pinbar = upper_wick >= (body_safe * self.min_wick_ratio)
            
            if is_high_sweep and is_bear_pinbar:
                sl = high_p * 1.001 # 0.1% di luar ujung jarum
                risk = sl - close_p
                risk_pct = risk / close_p
                
                if 0.0010 <= risk_pct <= self.max_sl_pct:
                    # Fee-Adjusted Net 2R: (2 * risk) + (entry * fee_pct)
                    tp = close_p - (risk * self.rr_ratio) - (close_p * self.fee_pct)
                    df.iloc[i, df.columns.get_loc('signal')] = -1
                    df.iloc[i, df.columns.get_loc('stop_loss')] = sl
                    df.iloc[i, df.columns.get_loc('take_profit')] = tp

        return df
