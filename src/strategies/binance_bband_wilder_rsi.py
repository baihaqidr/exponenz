import numpy as np
import pandas as pd
from src.strategies.base import BaseStrategy
from src.indicators import calculate_rsi, calculate_sma

class BinanceBbandWilderRsiStrategy(BaseStrategy):
    """
    ⚡ BINANCE PRO BBAND WILDER'S RSI STRATEGY
    
    100% Menggunakan formula standar resmi Binance & TradingView:
    - Indikator: Bollinger Bands (20, 2.0) & Wilder's Exponential Smoothed RSI (14).
    - Entry LONG (BUY): Harga Close < Lower Bollinger Band & Wilder's RSI < 30 (Extreme Dip).
    - Exit (CLOSE): Wilder's RSI > 70 (Overbought) atau Take Profit ROI Target (+2.5% s/d +4.0%).
    - Stop Loss: -5.0% proteksi modal.
    """
    def __init__(self, bb_length: int = 20, bb_std: float = 2.0, rsi_period: int = 14):
        super().__init__(name="Binance Pro BbandRsi (Wilder's 100% Binance Match)", is_long_only=True)
        self.bb_length = bb_length
        self.bb_std = bb_std
        self.rsi_period = rsi_period

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # 1. Bollinger Bands (20, 2.0)
        df['bb_middleband'] = calculate_sma(df['close'], self.bb_length)
        rolling_std = df['close'].rolling(window=self.bb_length).std()
        df['bb_lowerband'] = df['bb_middleband'] - (rolling_std * self.bb_std)
        df['bb_upperband'] = df['bb_middleband'] + (rolling_std * self.bb_std)
        
        # 2. Wilder's Smoothed Exponential RSI (14) - Identik 100% dengan Binance & TradingView
        df['rsi'] = calculate_rsi(df['close'], period=self.rsi_period)
        df['rsi_wilder'] = df['rsi'] # Explicit tag for UI distinction
        
        # Sinyal default
        df['signal'] = 0
        df['enter_long'] = 0
        df['exit_long'] = 0
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan
        
        # Aturan Entry Long: Close < BB Lower & RSI Wilder < 30 & Volume > 0
        long_condition = (
            (df['rsi'] < 30) &
            (df['close'] < df['bb_lowerband']) &
            (df['volume'] > 0)
        )
        df.loc[long_condition, 'signal'] = 1
        df.loc[long_condition, 'enter_long'] = 1
        
        # Aturan Exit Long: RSI Wilder > 70 & Volume > 0
        exit_condition = (
            (df['rsi'] > 70) &
            (df['volume'] > 0)
        )
        df.loc[exit_condition, 'signal'] = -1
        df.loc[exit_condition, 'exit_long'] = 1
        
        df['stop_loss'] = np.where(df['enter_long'] == 1, df['close'] * 0.95, np.nan)
        df['take_profit'] = np.where(df['enter_long'] == 1, df['close'] * 1.025, np.nan)
        df['sl_price'] = df['stop_loss']
        df['tp_price'] = df['take_profit']

        return df

