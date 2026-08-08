# 📉 04 - MACD 平滑異同移動平均線策略 (MACD Strategy)

## 📌 1. 策略概述
MACD (Moving Average Convergence Divergence) 由 Gerald Appel 提出，結合了指數移動平均線 (EMA) 的發散與收斂特性，兼具趨勢跟隨與動量轉折的雙重功能。

---

## 🧮 2. 數學公式與算則

1. 計算快線 EMA(12) 與慢線 EMA(26)：
   $$\text{EMA}_N(t) = P_t \times \left(\frac{2}{N+1}\right) + \text{EMA}_N(t-1) \times \left(1 - \frac{2}{N+1}\right)$$
2. 計算差離值 快線 $\text{DIF}$：
   $$\text{DIF}(t) = \text{EMA}_{12}(t) - \text{EMA}_{26}(t)$$
3. 計算訊號線 慢線 $\text{DEM}$ (MACD Signal)：
   $$\text{DEM}(t) = \text{EMA}_9(\text{DIF}(t))$$
4. 計算 MACD 柱狀體 (Histogram)：
   $$\text{Hist}(t) = \text{DIF}(t) - \text{DEM}(t)$$

---

## 🟢🔴 3. 進出場條件

### 買進條件 (DIF 突破 DEM / 柱狀體轉正)
當快線 DIF 向上突破慢線 DEM 時：
$$\text{DIF}(t) > \text{DEM}(t) \implies \text{Signal}(t) = 1$$
次日開盤執行 `BUY` 建倉。

### 賣出條件 (DIF 跌破 DEM / 柱狀體轉負)
當快線 DIF 向下跌破慢線 DEM 時：
$$\text{DIF}(t) \le \text{DEM}(t) \implies \text{Signal}(t) = 0$$
次日開盤執行 `SELL` 平倉。
