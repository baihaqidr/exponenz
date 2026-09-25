import numpy as np
import pandas as pd
from src.strategies.base import BaseStrategy
from open_source_original.freqtrade.bband_rsi import BbandRsi

class FreqtradePureBbandRsiStrategy(BaseStrategy):
    """
    ⚡ FREQTRADE OFFICIAL PURE BBAND_RSI (100% ORIGINAL UNMODIFIED)
    - File Source: open_source_original/freqtrade/bband_rsi.py
    - Indikator: Rolling SMA RSI (14) & Bollinger Bands (20, 2.0).
    - Entry: Close < BB Lower & RSI < 30 (Oversold Dip).
    - Exit: RSI > 70 atau Minimal ROI (+4% / +2% / +1%).
    - Stop Loss: Bawaan asli Freqtrade (-10.0%).
    """
    def __init__(self):
        super().__init__(name="Freqtrade Pure BbandRsi (Original SL -10%)", is_long_only=True)
        self.freq_strat = BbandRsi()
        self.is_long_only = True

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = self.freq_strat.populate_indicators(df)
        df = self.freq_strat.populate_entry_trend(df)
        df = self.freq_strat.populate_exit_trend(df)
        
        df['signal'] = 0
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan
        df['sl_price'] = np.nan
        df['tp_price'] = np.nan
        
        if 'enter_long' in df.columns:
            df.loc[df['enter_long'] == 1, 'signal'] = 1
        if 'exit_long' in df.columns:
            df.loc[df['exit_long'] == 1, 'signal'] = -1
        
        for i in range(1, len(df)):
            if df['signal'].iloc[i] == 1:
                close_p = df['close'].iloc[i]
                sl_val = close_p * (1.0 + self.freq_strat.stoploss) # -10% Official Freqtrade Stoploss
                tp_val = close_p * 1.04 # +4% Official ROI Target
                df.iloc[i, df.columns.get_loc('stop_loss')] = sl_val
                df.iloc[i, df.columns.get_loc('take_profit')] = tp_val
                df.iloc[i, df.columns.get_loc('sl_price')] = sl_val
                df.iloc[i, df.columns.get_loc('tp_price')] = tp_val

        return df


class FreqtradeAdjustedBbandRsiStrategy(BaseStrategy):
    """
    🛡️ FREQTRADE BBAND_RSI (ADJUSTED FUTURES HARD SL -5% PROTECTION)
    - Indikator: Rolling SMA RSI (14) & Bollinger Bands (20, 2.0).
    - Entry: Close < BB Lower & RSI < 30.
    - Exit: RSI > 70.
    - Stop Loss: Hard Fixed SL -5.0% (Proteksi Ketat Futures).
    - Take Profit: Hard Fixed TP +4.0%.
    """
    def __init__(self):
        super().__init__(name="Freqtrade BbandRsi (Adjusted SL -5%)", is_long_only=True)
        self.freq_strat = BbandRsi()
        self.is_long_only = True

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = self.freq_strat.populate_indicators(df)
        df = self.freq_strat.populate_entry_trend(df)
        df = self.freq_strat.populate_exit_trend(df)
        
        df['signal'] = 0
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan
        df['sl_price'] = np.nan
        df['tp_price'] = np.nan
        
        if 'enter_long' in df.columns:
            df.loc[df['enter_long'] == 1, 'signal'] = 1
        if 'exit_long' in df.columns:
            df.loc[df['exit_long'] == 1, 'signal'] = -1
        
        for i in range(1, len(df)):
            if df['signal'].iloc[i] == 1:
                close_p = df['close'].iloc[i]
                sl_val = close_p * 0.95 # -5% Hard Stop Loss
                tp_val = close_p * 1.04 # +4% Hard Take Profit
                df.iloc[i, df.columns.get_loc('stop_loss')] = sl_val
                df.iloc[i, df.columns.get_loc('take_profit')] = tp_val
                df.iloc[i, df.columns.get_loc('sl_price')] = sl_val
                df.iloc[i, df.columns.get_loc('tp_price')] = tp_val

        return df


# Alias untuk backwards compatibility
FreqtradeBbandRsiStrategy = FreqtradePureBbandRsiStrategy

