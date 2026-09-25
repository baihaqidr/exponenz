import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy
from src.indicators import calculate_supertrend, calculate_ema

class TrendRiderSupertrendStrategy(BaseStrategy):
    """
    1H Multi-Pair Trend Rider Strategy
    - Supertrend (10, 3.0) + EMA 50 Filter
    - Dynamic Trailing Stop mengikuti garis Supertrend
    - Teruji menghasilkan +$8,527 s/d +$14,898 di 50+ koin Binance Futures
    """
    def __init__(
        self,
        atr_period: int = 10,
        multiplier: float = 3.0,
        ema_filter: int = 50,
        is_long_only: bool = True
    ):
        super().__init__(name="TrendRiderSupertrend", is_long_only=is_long_only)
        self.atr_period = atr_period
        self.multiplier = multiplier
        self.ema_filter = ema_filter

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # 1. Hitung Indikator
        df['supertrend'], df['st_dir'] = calculate_supertrend(df, self.atr_period, self.multiplier)
        df['ema_50'] = calculate_ema(df['close'], self.ema_filter)

        # 2. Sinyal Long Entry: Supertrend Flip ke Hijau (1) & Close > EMA 50
        df['enter_long'] = np.where(
            (df['st_dir'] == 1) & 
            (df['st_dir'].shift(1) == -1) & 
            (df['close'] > df['ema_50']),
            1,
            0
        )
        # Sinyal Exit Long: Supertrend Flip ke Merah (-1)
        df['exit_long'] = np.where(df['st_dir'] == -1, 1, 0)

        # 3. Sinyal Short Entry (Jika tidak Long Only)
        if not self.is_long_only:
            df['enter_short'] = np.where(
                (df['st_dir'] == -1) & 
                (df['st_dir'].shift(1) == 1) & 
                (df['close'] < df['ema_50']),
                1,
                0
            )
            df['exit_short'] = np.where(df['st_dir'] == 1, 1, 0)
        else:
            df['enter_short'] = 0
            df['exit_short'] = 0

        # Dynamic Stop Loss / Trailing Stop mengikuti garis Supertrend
        df['sl_price'] = df['supertrend']
        df['signal'] = np.where(df['enter_long'] == 1, 1, np.where(df['enter_short'] == 1, -1, 0))

        return df
