# 📈 01 - 雙移動平均線交叉策略 (SMA Cross Strategy)

## 📌 1. 策略概述
雙移動平均線 (Simple Moving Average, SMA) 交叉策略是量化交易中最經典的趨勢跟隨 (Trend Following) 策略。經由短週期均線與長週期均線的相對位置變化，捕捉價格趨勢的起伏與轉折。

---

## 🧮 2. 數學公式與算則

簡單移動平均線定義為過去 $N$ 個交易日收盤價的算術平均：

$$\text{SMA}_N(t) = \frac{1}{N} \sum_{i=0}^{N-1} P_{t-i}$$

- **快線 (Short MA)**：$\text{SMA}_{\text{short}}$（預設 $N=10$ 或 $N=5$）
- **慢線 (Long MA)**：$\text{SMA}_{\text{long}}$（預設 $N=60$ 或 $N=10$）

---

## 🟢🔴 3. 進出場條件

### 買進條件 (Golden Cross / 黃金交叉)
當短天期快線向上突破長天期慢線時：
$$\text{SMA}_{\text{short}}(t) > \text{SMA}_{\text{long}}(t) \implies \text{Signal}(t) = 1$$
次日開盤執行 `BUY` 建倉。

### 賣出條件 (Death Cross / 死亡交叉)
當短天期快線向下跌破長天期慢線時：
$$\text{SMA}_{\text{short}}(t) \le \text{SMA}_{\text{long}}(t) \implies \text{Signal}(t) = 0$$
次日開盤執行 `SELL` 平倉。

---

## 💡 4. 台股最佳化組合實測
根據網格搜尋 (Grid Search) 在台積電 (2330) 之 241 日 K 線實測：
- **最佳參數組合**: **10MA / 60MA**
- **績效**: 期末資產 NT$ 4,139,361 (**總報酬率 +37.98%**，夏普比率 2.09，勝率 50.0%)。
