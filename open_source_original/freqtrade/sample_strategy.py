# --- Do not remove these libs ---
from datetime import datetime
from typing import Dict, List, Optional
from pandas import DataFrame
import numpy as np
import pandas as pd

# Original Freqtrade IStrategy Interface simulation for standalone compatibility
class IStrategy:
    """
    Interface for freqtrade strategies
    """
    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if a value is specified in the config.
    minimal_roi: Dict = {
        "60": 0.01,
        "30": 0.02,
        "0": 0.04
    }

    # Optimal stoploss designed for the strategy.
    # This attribute will be overridden if a value is specified in the config.
    stoploss: float = -0.10

    # Trailing stoploss
    trailing_stop: bool = False
    trailing_stop_positive: float = 0.01
    trailing_stop_positive_offset: float = 0.02
    trailing_only_offset_is_reached: bool = False

    # Optimal ticker interval for the strategy
    timeframe: str = '5m'

    # Run "populate_indicators()" only for new candle.
    process_only_new_candles: bool = True

    # These values can be overridden in the config.
    use_exit_signal: bool = True
    exit_profit_only: bool = False
    ignore_roi_if_entry_signal: bool = False

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 30


class SampleStrategy(IStrategy):
    """
    This is a sample strategy from official Freqtrade repository (freqtrade/templates/sample_strategy.py).
    Original logic:
    - Indicators: RSI (14), Fast EMA (9), Slow EMA (20), MACD, Bollinger Bands (20, 2.0).
    - Entry Rule: RSI < 30 & Fast EMA > Slow EMA & Bollinger Lower Band Bounce.
    - Exit Rule: RSI > 70.
    """

    # Strategy interface version - allow new iterations of the interface both in
    # user_data and in the freqtrade repo
    INTERFACE_VERSION = 3

    # Minimal ROI designed for the strategy.
    minimal_roi = {
        "60": 0.01,
        "30": 0.02,
        "0": 0.04
    }

    stoploss = -0.10
    timeframe = '5m'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict = None) -> DataFrame:
        """
        Populate technical indicators on the given dataframe.
        """
        # RSI 14
        delta = dataframe['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        dataframe['rsi'] = 100 - (100 / (1 + rs))

        # Exponential Moving Averages
        dataframe['ema9'] = dataframe['close'].ewm(span=9, adjust=False).mean()
        dataframe['ema20'] = dataframe['close'].ewm(span=20, adjust=False).mean()
        dataframe['ema50'] = dataframe['close'].ewm(span=50, adjust=False).mean()

        # Simple Moving Averages
        dataframe['sma200'] = dataframe['close'].rolling(window=200).mean()

        # Bollinger Bands 20, 2.0
        dataframe['bb_middleband'] = dataframe['close'].rolling(window=20).mean()
        dataframe['bb_std'] = dataframe['close'].rolling(window=20).std()
        dataframe['bb_lowerband'] = dataframe['bb_middleband'] - (dataframe['bb_std'] * 2.0)
        dataframe['bb_upperband'] = dataframe['bb_middleband'] + (dataframe['bb_std'] * 2.0)

        # MACD
        ema12 = dataframe['close'].ewm(span=12, adjust=False).mean()
        ema26 = dataframe['close'].ewm(span=26, adjust=False).mean()
        dataframe['macd'] = ema12 - ema26
        dataframe['macdsignal'] = dataframe['macd'].ewm(span=9, adjust=False).mean()
        dataframe['macdhist'] = dataframe['macd'] - dataframe['macdsignal']

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict = None) -> DataFrame:
        """
        Based on TA indicators, populates the entry signal for the given dataframe
        """
        dataframe.loc[
            (
                (dataframe['rsi'] < 30) &
                (dataframe['ema9'] > dataframe['ema20']) &
                (dataframe['close'] > dataframe['bb_lowerband']) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict = None) -> DataFrame:
        """
        Based on TA indicators, populates the exit signal for the given dataframe
        """
        dataframe.loc[
            (
                (dataframe['rsi'] > 70) &
                (dataframe['volume'] > 0)
            ),
            'exit_long'] = 1

        return dataframe
