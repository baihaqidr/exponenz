from pandas import DataFrame
import pandas as pd
import numpy as np

class BbandRsi:
    """
    Official Freqtrade Strategy: BbandRsi
    Source: freqtrade/freqtrade-strategies/bband_rsi.py
    
    Logic:
    - Indicators: RSI (14), Bollinger Bands (20, 2.0).
    - Entry: Close < BB Lower Band & RSI < 30 (Oversold Dip Buying).
    - Exit: RSI > 70 or Minimal ROI (4% in 0m, 2% in 30m, 1% in 60m).
    - Stoploss: -10%
    """
    minimal_roi = {
        "60": 0.01,
        "30": 0.02,
        "0": 0.04
    }
    stoploss = -0.10
    timeframe = '5m'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict = None) -> DataFrame:
        # RSI 14
        delta = dataframe['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        dataframe['rsi'] = 100 - (100 / (1 + rs))

        # Bollinger Bands 20, 2.0
        dataframe['bb_middleband'] = dataframe['close'].rolling(window=20).mean()
        dataframe['bb_std'] = dataframe['close'].rolling(window=20).std()
        dataframe['bb_lowerband'] = dataframe['bb_middleband'] - (dataframe['bb_std'] * 2.0)
        dataframe['bb_upperband'] = dataframe['bb_middleband'] + (dataframe['bb_std'] * 2.0)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict = None) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] < 30) &
                (dataframe['close'] < dataframe['bb_lowerband']) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict = None) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] > 70) &
                (dataframe['volume'] > 0)
            ),
            'exit_long'] = 1

        return dataframe
