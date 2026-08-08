# 📚 台股量化回測系統 - 策略邏輯與風控機制手冊 (Strategy Documentation)

本資料夾包含了 **永豐金 Shioaji 台股量化回測與風控系統** 中所有已實作技術指標策略與風控機制的完整邏輯、數學公式、進出場條件與台股實務應用說明。

---

## 📑 策略目錄 (Table of Contents)

| 策略編號 | 策略名稱 (Strategy Name) | 核心類型 | 適用行情 | 說明文件 |
| :---: | :--- | :---: | :---: | :---: |
| **01** | [雙移動平均線交叉策略 (SMA Cross)](./01_sma_cross.md) | 趨勢跟隨 | 波段趨勢 | [01_sma_cross.md](./01_sma_cross.md) |
| **02** | [均線多頭排列策略 (MA Bullish Alignment)](./02_ma_alignment.md) | 強勢趨勢 | 飆股主升段 | [02_ma_alignment.md](./02_ma_alignment.md) |
| **03** | [RSI 相對強弱指標策略 (RSI Strategy)](./03_rsi.md) | 擺盪反轉 | 區間震盪 | [03_rsi.md](./03_rsi.md) |
| **04** | [MACD 平滑異同移動平均線策略 (MACD)](./04_macd.md) | 動量趨勢 | 中長線波段 | [04_macd.md](./04_macd.md) |
| **05** | [布林通道策略 (Bollinger Bands)](./05_bollinger_bands.md) | 通道反轉 | 箱型震盪 | [05_bollinger_bands.md](./05_bollinger_bands.md) |
| **06** | [布林通道擠壓突破策略 (Bollinger Squeeze)](./06_bollinger_squeeze.md) | 波動度突破 | 盤整爆量起漲 | [06_bollinger_squeeze.md](./06_bollinger_squeeze.md) |
| **07** | [KD 隨機指標策略 (KD Stochastic)](./07_kd.md) | 短線擺盪 | 短線轉折 | [07_kd.md](./07_kd.md) |
| **08** | [KD + RSI 雙重驗證過濾策略 (Dual KD+RSI)](./08_dual_kd_rsi.md) | 多指標驗證 | 降低假突破 | [08_dual_kd_rsi.md](./08_dual_kd_rsi.md) |
| **09** | [兩階段移動停利與突破前高接回風控 (Risk Controls)](./09_risk_controls.md) | 主動風控 | 全行情避險 | [09_risk_controls.md](./09_risk_controls.md) |

---

## 🏗️ 策略程式碼結構

所有策略類別均繼承自 `src/backtest/strategy.py` 中之 `BaseStrategy` 基礎類別：

```python
class BaseStrategy(ABC):
    def __init__(self, name: str = "Base Strategy"):
        self.name = name

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        給定包含 OHLCV 的 DataFrame
        回傳計算後帶有 signal (當日訊號) 與 position (次日執行目標部位) 的 DataFrame
        """
        pass
```

- **`signal = 1`**：代表技術指標發出多頭買進或持股訊號。
- **`signal = 0`**：代表技術指標發出空頭平倉或觀望訊號。
- **`position = signal.shift(1)`**：模擬台股交易實務，當日收盤判定訊號後，於**下一個交易日開盤**執行買賣操作。
