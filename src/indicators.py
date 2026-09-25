import pandas as pd
import numpy as np

def calculate_ema(series: pd.Series, length: int) -> pd.Series:
    """Menghitung Exponential Moving Average (EMA)."""
    return series.ewm(span=length, adjust=False).mean()

def calculate_sma(series: pd.Series, length: int) -> pd.Series:
    """Menghitung Simple Moving Average (SMA)."""
    return series.rolling(window=length).mean()

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Menghitung Average True Range (ATR)."""
    high = df['high']
    low = df['low']
    close = df['close']
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    return atr

def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Menghitung Average Directional Index (ADX) untuk mengukur kekuatan tren."""
    high = df['high']
    low = df['low']
    close = df['close']

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    atr = calculate_atr(df, period)
    plus_di = 100 * (pd.Series(plus_dm, index=df.index).ewm(alpha=1/period, adjust=False).mean() / (atr + 1e-10))
    minus_di = 100 * (pd.Series(minus_dm, index=df.index).ewm(alpha=1/period, adjust=False).mean() / (atr + 1e-10))

    dx = 100 * ((plus_di - minus_di).abs() / ((plus_di + minus_di) + 1e-10))
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    return adx

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Menghitung Relative Strength Index (RSI)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Menghitung MACD line, Signal line, dan Histogram."""
    fast_ema = calculate_ema(series, fast)
    slow_ema = calculate_ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = calculate_ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def calculate_bollinger_bands(series: pd.Series, length: int = 20, std_dev: float = 2.0):
    """Menghitung Bollinger Bands (Upper, Middle, Lower)."""
    mid = calculate_sma(series, length)
    std = series.rolling(window=length).std()
    upper = mid + (std * std_dev)
    lower = mid - (std * std_dev)
    return upper, mid, lower

def calculate_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
    """
    Menghitung Supertrend Indicator.
    Returns: (supertrend_value: pd.Series, direction: pd.Series)
    direction: 1 (Bullish / Uptrend), -1 (Bearish / Downtrend)
    """
    atr = calculate_atr(df, period)
    hl2 = (df['high'] + df['low']) / 2

    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)

    n = len(df)
    final_upper = np.zeros(n)
    final_lower = np.zeros(n)
    supertrend = np.zeros(n)
    direction = np.zeros(n, dtype=int)

    close = df['close'].values

    for i in range(1, n):
        # Final Upper Band
        if basic_upper.iloc[i] < final_upper[i-1] or close[i-1] > final_upper[i-1]:
            final_upper[i] = basic_upper.iloc[i]
        else:
            final_upper[i] = final_upper[i-1]

        # Final Lower Band
        if basic_lower.iloc[i] > final_lower[i-1] or close[i-1] < final_lower[i-1]:
            final_lower[i] = basic_lower.iloc[i]
        else:
            final_lower[i] = final_lower[i-1]

        # Trend Direction
        prev_dir = direction[i-1] if i > 1 else 1
        if prev_dir == 1:
            if close[i] < final_lower[i]:
                direction[i] = -1
                supertrend[i] = final_upper[i]
            else:
                direction[i] = 1
                supertrend[i] = final_lower[i]
        else:
            if close[i] > final_upper[i]:
                direction[i] = 1
                supertrend[i] = final_lower[i]
            else:
                direction[i] = -1
                supertrend[i] = final_upper[i]

    return pd.Series(supertrend, index=df.index), pd.Series(direction, index=df.index)
