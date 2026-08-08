# 🎯 05 - 布林通道策略 (Bollinger Bands Strategy)

## 📌 1. 策略概述
布林通道 (Bollinger Bands) 由 John Bollinger 於 1980 年代提出。結合統計學中的標準差 (Standard Deviation) 與移動平均線，假設股價遵循常態分佈，95.4% 的價格變動會落在上下軌兩倍標準差通道之內。

---

## 🧮 2. 數學公式與算則

- 中軌 (Middle Band)：$\text{MA}_{20} = \text{SMA}_{20}(\text{close})$
- 標準差 $\sigma_{20}$：$\sigma_{20} = \text{StdDev}_{20}(\text{close})$
- 上軌 (Upper Band)：$\text{UB} = \text{MA}_{20} + 2.0 \times \sigma_{20}$
- 下軌 (Lower Band)：$\text{LB} = \text{MA}_{20} - 2.0 \times \sigma_{20}$

---

## 🟢🔴 3. 進出場條件

### 買進條件 (Touch Lower Band / 低檔超賣)
當收盤價跌破布林下軌時，視為股價過度偏離均值、具備極高回歸中軌之機率：
$$\text{Close}(t) < \text{LB}(t) \implies \text{Signal}(t) = 1$$

### 賣出條件 (Touch Upper Band / 高檔超買)
當收盤價強勢突破上軌或回歸中軌時：
$$\text{Close}(t) > \text{UB}(t) \implies \text{Signal}(t) = 0$$
平倉離場。
