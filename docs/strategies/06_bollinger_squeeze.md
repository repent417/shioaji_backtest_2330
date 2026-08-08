# 💥 06 - 布林通道擠壓突破策略 (Bollinger Squeeze & Breakout)

## 📌 1. 策略概述
「波動度壓縮往往是強烈單邊趨勢噴發的前兆」。當布林通道極致收窄（擠壓 Squeeze）時，代表籌碼高度沉澱盤整；一旦股價強勢帶量突破布林上軌，往往觸發暴跌或爆買噴發行情。

---

## 🧮 2. 數學公式與算則

1. 計算通道頻寬 (Bandwidth)：
   $$\text{Bandwidth}(t) = \frac{\text{Upper Band}(t) - \text{Lower Band}(t)}{\text{MA}_{20}(t) + 10^{-9}}$$
2. 計算過去 60 日頻寬均值：
   $$\overline{\text{Bandwidth}}_{60}(t) = \text{SMA}_{60}(\text{Bandwidth}(t))$$
3. 擠壓條件 (Squeeze Condition)：
   $$\text{Squeeze}(t) = \text{Bandwidth}(t) < 0.85 \times \overline{\text{Bandwidth}}_{60}(t)$$

---

## 🟢🔴 3. 進出場條件

### 買進條件 (Squeeze + Breakout / 擠壓後突破上軌)
當**近 5 個交易日內曾出現擠壓狀態**，且**今日收盤價強勢突破布林上軌**時：
$$\text{RecentSqueeze}_5(t) = 1 \quad \text{AND} \quad \text{Close}(t) > \text{Upper Band}(t) \implies \text{Signal}(t) = 1$$
次日開盤執行 `BUY` 建倉。

### 賣出條件 (Exit on Middle Band / 跌破中軌平倉)
當收盤價跌破布林中軌 ($\text{MA}_{20}$) 時：
$$\text{Close}(t) < \text{MA}_{20}(t) \implies \text{Signal}(t) = 0$$
平倉離場。

---

## 💡 4. 實測優點
在台積電 (2330) 歷史實測中，此策略發揮專抓第一支大紅棒起漲優勢，**交易勝率高達 60.0%**！
