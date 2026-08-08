"""
Technical Analysis Strategies for Taiwan Stock Backtesting
包含雙均線 (SMA)、均線多頭排列 (MA Bullish Alignment)、RSI、MACD、布林通道 (Bollinger Bands)、布林擠壓突破與 KD+RSI 雙重驗證策略
"""
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np

class BaseStrategy(ABC):
    def __init__(self, name: str = "Base Strategy"):
        self.name = name

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """給定包含 ohlcv 的 DataFrame，回傳帶有 signal 與 position 的 DataFrame"""
        pass

class SMACrossStrategy(BaseStrategy):
    """雙移動平均線 (SMA) 交叉策略"""
    def __init__(self, short_window: int = 5, long_window: int = 20):
        super().__init__(name=f"SMA Cross ({short_window}/{long_window})")
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        data["sma_short"] = data["close"].rolling(window=self.short_window, min_periods=1).mean()
        data["sma_long"] = data["close"].rolling(window=self.long_window, min_periods=1).mean()

        data["signal"] = 0
        data.loc[data["sma_short"] > data["sma_long"], "signal"] = 1
        data["position"] = data["signal"].shift(1).fillna(0)
        return data

class MAAlignmentStrategy(BaseStrategy):
    """
    均線多頭排列策略 (5MA > 10MA > 20MA > 60MA)
    專抓台股飆股主升段
    """
    def __init__(self):
        super().__init__(name="MA Bullish Alignment (5/10/20/60)")

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        data["sma_5"] = data["close"].rolling(window=5, min_periods=1).mean()
        data["sma_10"] = data["close"].rolling(window=10, min_periods=1).mean()
        data["sma_20"] = data["close"].rolling(window=20, min_periods=1).mean()
        data["sma_60"] = data["close"].rolling(window=60, min_periods=1).mean()

        alignment = (
            (data["sma_5"] > data["sma_10"]) &
            (data["sma_10"] > data["sma_20"]) &
            (data["sma_20"] > data["sma_60"])
        )

        data["signal"] = 0
        data.loc[alignment, "signal"] = 1
        data["position"] = data["signal"].shift(1).fillna(0)
        return data

class RSIStrategy(BaseStrategy):
    """
    RSI 相對強弱指標策略
    - 當 RSI < oversold (如 35) 時買進 (Signal = 1)
    - 當 RSI > overbought (如 65) 時賣出平倉 (Signal = 0)
    """
    def __init__(self, period: int = 14, oversold: float = 35.0, overbought: float = 65.0):
        super().__init__(name=f"RSI Strategy ({period}, {oversold}/{overbought})")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        delta = data["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period, min_periods=1).mean()
        
        rs = gain / (loss + 1e-9)
        data["rsi"] = 100 - (100 / (1 + rs))

        data["signal"] = np.nan
        data.loc[data["rsi"] < self.oversold, "signal"] = 1
        data.loc[data["rsi"] > self.overbought, "signal"] = 0
        data["signal"] = data["signal"].ffill().fillna(0)
        data["position"] = data["signal"].shift(1).fillna(0)
        return data

class MACDStrategy(BaseStrategy):
    """
    MACD 平滑異同移動平均線策略
    - 當 DIF (快線) 向上突破 DEM (慢線/訊號線) 時買進
    - 當 DIF 向下突破 DEM 時賣出
    """
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        super().__init__(name=f"MACD Strategy ({fast_period}/{slow_period}/{signal_period})")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        ema_fast = data["close"].ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = data["close"].ewm(span=self.slow_period, adjust=False).mean()
        data["dif"] = ema_fast - ema_slow
        data["macd_signal"] = data["dif"].ewm(span=self.signal_period, adjust=False).mean()

        data["signal"] = 0
        data.loc[data["dif"] > data["macd_signal"], "signal"] = 1
        data["position"] = data["signal"].shift(1).fillna(0)
        return data

class BollingerBandsStrategy(BaseStrategy):
    """
    布林通道 (Bollinger Bands) 策略
    - 當收盤價跌破下軌 (Lower Band) 時做多買進
    - 當收盤價突破上軌 (Upper Band) 或中軌時平倉賣出
    """
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__(name=f"Bollinger Bands ({period}, {std_dev}std)")
        self.period = period
        self.std_dev = std_dev

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        data["sma"] = data["close"].rolling(window=self.period, min_periods=1).mean()
        data["std"] = data["close"].rolling(window=self.period, min_periods=1).std()
        data["upper_band"] = data["sma"] + (self.std_dev * data["std"])
        data["lower_band"] = data["sma"] - (self.std_dev * data["std"])

        data["signal"] = np.nan
        data.loc[data["close"] < data["lower_band"], "signal"] = 1
        data.loc[data["close"] > data["upper_band"], "signal"] = 0
        data["signal"] = data["signal"].ffill().fillna(0)
        data["position"] = data["signal"].shift(1).fillna(0)
        return data

class BollingerSqueezeStrategy(BaseStrategy):
    """
    布林通道擠壓與爆量突破策略 (Bollinger Squeeze & Breakout)
    通道頻寬極致收窄後強勢突破上軌買進
    """
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__(name=f"Bollinger Squeeze ({period}, {std_dev}std)")
        self.period = period
        self.std_dev = std_dev

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        data["sma"] = data["close"].rolling(window=self.period, min_periods=1).mean()
        data["std"] = data["close"].rolling(window=self.period, min_periods=1).std()
        data["upper_band"] = data["sma"] + (self.std_dev * data["std"])
        data["lower_band"] = data["sma"] - (self.std_dev * data["std"])
        data["bandwidth"] = (data["upper_band"] - data["lower_band"]) / (data["sma"] + 1e-9)

        bw_mean = data["bandwidth"].rolling(window=60, min_periods=1).mean()
        squeeze = data["bandwidth"] < (bw_mean * 0.85)

        recent_squeeze = squeeze.rolling(window=5, min_periods=1).max() > 0
        breakout = data["close"] > data["upper_band"]

        data["signal"] = np.nan
        data.loc[recent_squeeze & breakout, "signal"] = 1
        data.loc[data["close"] < data["sma"], "signal"] = 0
        data["signal"] = data["signal"].ffill().fillna(0)
        data["position"] = data["signal"].shift(1).fillna(0)
        return data

class KDStrategy(BaseStrategy):
    """
    KD 隨機指標策略
    - 當 K < 20 且 K 向上突破 D (低檔黃金交叉) 時買進
    - 當 K > 80 且 K 向下突破 D (高檔死亡交叉) 時賣出
    """
    def __init__(self, period: int = 9):
        super().__init__(name=f"KD Strategy ({period})")
        self.period = period

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        low_min = data["low"].rolling(window=self.period, min_periods=1).min()
        high_max = data["high"].rolling(window=self.period, min_periods=1).max()
        rsv = ((data["close"] - low_min) / (high_max - low_min + 1e-9)) * 100

        k_list, d_list = [50.0], [50.0]
        for val in rsv:
            k = (2/3) * k_list[-1] + (1/3) * val
            d = (2/3) * d_list[-1] + (1/3) * k
            k_list.append(k)
            d_list.append(d)

        data["k"] = k_list[1:]
        data["d"] = d_list[1:]

        data["signal"] = 0
        data.loc[data["k"] > data["d"], "signal"] = 1
        data["position"] = data["signal"].shift(1).fillna(0)
        return data

class DualKDRSIStrategy(BaseStrategy):
    """
    KD + RSI 雙重驗證策略
    KD 黃金交叉 且 RSI > 50 (多方強勢區) 才准許買進
    """
    def __init__(self, kd_period: int = 9, rsi_period: int = 14):
        super().__init__(name=f"Dual KD+RSI Filter (KD{kd_period}/RSI{rsi_period})")
        self.kd_period = kd_period
        self.rsi_period = rsi_period

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()

        # 計算 KD
        low_min = data["low"].rolling(window=self.kd_period, min_periods=1).min()
        high_max = data["high"].rolling(window=self.kd_period, min_periods=1).max()
        rsv = ((data["close"] - low_min) / (high_max - low_min + 1e-9)) * 100

        k_list, d_list = [50.0], [50.0]
        for val in rsv:
            k = (2/3) * k_list[-1] + (1/3) * val
            d = (2/3) * d_list[-1] + (1/3) * k
            k_list.append(k)
            d_list.append(d)

        data["k"] = k_list[1:]
        data["d"] = d_list[1:]

        # 計算 RSI
        delta = data["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period, min_periods=1).mean()
        rs = gain / (loss + 1e-9)
        data["rsi"] = 100 - (100 / (1 + rs))

        data["signal"] = 0
        data.loc[(data["k"] > data["d"]) & (data["rsi"] > 50.0), "signal"] = 1
        data["position"] = data["signal"].shift(1).fillna(0)
        return data
