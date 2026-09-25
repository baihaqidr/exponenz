import numpy as np
import pandas as pd
from src.strategies.base import BaseStrategy
from open_source_original.freqtrade.sample_strategy import SampleStrategy

class FreqtradeOriginalSampleStrategy(BaseStrategy):
    """
    ⚡ FREQTRADE ORIGINAL SAMPLE STRATEGY (ADAPTER FOR BACKTEST & LIVE)
    
    100% Menggunakan class logic original dari Freqtrade official:
    - File: open_source_original/freqtrade/sample_strategy.py
    - Indicators: RSI (14), EMA 9, EMA 20, Bollinger Bands (20, 2.0).
    - Entry: RSI < 30 & EMA 9 > EMA 20 & Close > BB Lower.
    - Exit: RSI > 70 & Minimal ROI (4% / 2% / 1%).
    """
    def __init__(self):
        super().__init__(name="Freqtrade Original SampleStrategy", is_long_only=True)
        self.freq_strat = SampleStrategy()
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
        
        # Mapping sinyal Freqtrade ke engine backtest
        if 'enter_long' in df.columns:
            df.loc[df['enter_long'] == 1, 'signal'] = 1
        if 'exit_long' in df.columns:
            df.loc[df['exit_long'] == 1, 'signal'] = -1
        
        for i in range(1, len(df)):
            if df['signal'].iloc[i] == 1:
                close_p = df['close'].iloc[i]
                # Freqtrade default stoploss: -10%
                sl_val = close_p * (1.0 + self.freq_strat.stoploss)
                # Freqtrade default ROI target: +4%
                tp_val = close_p * 1.04
                df.iloc[i, df.columns.get_loc('stop_loss')] = sl_val
                df.iloc[i, df.columns.get_loc('take_profit')] = tp_val
                df.iloc[i, df.columns.get_loc('sl_price')] = sl_val
                df.iloc[i, df.columns.get_loc('tp_price')] = tp_val

        return df
