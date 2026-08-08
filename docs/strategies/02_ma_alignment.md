# 🚀 02 - 均線多頭排列策略 (MA Bullish Alignment Strategy)

## 📌 1. 策略概述
均線多頭排列是台股飆股與強勢主升段的核心型態。當短、中、長期 4 條均線呈依序向上發散且多頭排列時，代表市場法人與主力資金全力拉抬，個股具備極強的單邊噴發力。

---

## 🧮 2. 數學公式與算則

計算 4 條不同週期的移動平均線：
- 週線：$\text{MA}_5 = \text{SMA}_5(\text{close})$
- 雙週線：$\text{MA}_{10} = \text{SMA}_{10}(\text{close})$
- 月線：$\text{MA}_{20} = \text{SMA}_{20}(\text{close})$
- 季線：$\text{MA}_{60} = \text{SMA}_{60}(\text{close})$

---

## 🟢🔴 3. 進出場條件

### 買進條件 (Bullish Alignment / 多頭排列)
當 4 條均線同時滿足以下連續不等式時：
$$\text{MA}_5(t) > \text{MA}_{10}(t) > \text{MA}_{20}(t) > \text{MA}_{60}(t) \implies \text{Signal}(t) = 1$$
次日開盤執行 `BUY` 建倉。

### 賣出條件 (Alignment Broken / 排列破壞)
當均線結構不再滿足多頭排列條件（例如 $\text{MA}_5 \le \text{MA}_{10}$）時：
$$\text{Signal}(t) = 0$$
次日開盤執行 `SELL` 平倉。

---

## 🎨 4. 圖表繪製特色
Matplotlib 畫布會同時以彩色彩虹線繪製 5MA (粉紅)、10MA (橘色)、20MA (綠色) 與 60MA (紫色)，方便直觀辨識多頭排列區間。
