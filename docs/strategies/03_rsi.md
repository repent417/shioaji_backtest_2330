# 📊 03 - RSI 相對強弱指標策略 (RSI Strategy)

## 📌 1. 策略概述
相對強弱指標 (Relative Strength Index, RSI) 由 Welles Wilder 提出，用以衡量一定期間內股價買賣動量的強弱。在箱型震盪行情中，RSI 具備優秀的超買/超賣反轉預警功能。

---

## 🧮 2. 數學公式與算則

1. 計算每日價格變動：$\Delta P_t = P_t - P_{t-1}$
2. 分別計算 $N$ 日平均上漲幅度 $\text{Gain}_N$ 與平均下跌幅度 $\text{Loss}_N$：
   $$\text{Gain}_N = \text{SMA}_N(\max(\Delta P_t, 0)), \quad \text{Loss}_N = \text{SMA}_N(\max(-\Delta P_t, 0))$$
3. 計算相對強弱值 $\text{RS}$ 與 $\text{RSI}_N$：
   $$\text{RS} = \frac{\text{Gain}_N}{\text{Loss}_N + 10^{-9}}, \quad \text{RSI}_N = 100 - \frac{100}{1 + \text{RS}}$$

---

## 🟢🔴 3. 進出場條件

- **預設參數**: 週期 $N=14$，超賣門檻 $\text{Oversold}=35.0$，超買門檻 $\text{Overbought}=65.0$

### 買進條件 (Oversold Buy / 低檔超賣)
當 RSI 跌破超賣線，顯示市場過度悲觀、具備逢低反彈空間：
$$\text{RSI}_{14}(t) < 35.0 \implies \text{Signal}(t) = 1$$

### 賣出條件 (Overbought Sell / 高檔超買)
當 RSI 突破超買線，顯示市場過度過熱、獲利離場：
$$\text{RSI}_{14}(t) > 65.0 \implies \text{Signal}(t) = 0$$

---

## 💡 4. 特點與注意事項
RSI 在箱型震盪盤中表現優異（MDD 僅 2.99%），但在強烈單邊趨勢中易出現「高檔鈍化」，建議配合均線或風控停利使用。
