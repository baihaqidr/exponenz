from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    def __init__(self, name: str, is_long_only: bool = False):
        self.name = name
        self.is_long_only = is_long_only

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Menerima DataFrame OHLCV dan mengembalikan DataFrame yang sudah diperkaya dengan:
        - 'signal': 1 (Long entry), -1 (Short entry), 0 (No signal / Exit)
        - 'sl_price' atau 'sl_pct' (optional, untuk dynamic SL)
        - 'tp_price' atau 'tp_pct' (optional, untuk dynamic TP)
        """
        pass
