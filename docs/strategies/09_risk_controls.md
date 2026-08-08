# 🛡️ 09 - 兩階段移動停利與突破前高接回風控機制 (Risk Control Mechanism)

## 📌 1. 機制概述
本風控機制獨立於各個技術指標策略之外，運作於 `BacktestEngine` 引擎核心層。包含硬停損 (Stop Loss)、兩階段高點拉回移動停利 (Two-Step Trailing Stop) 與 停利後突破前高重新接回 (Breakout Re-entry)。

---

## ⚙️ 2. 核心機制運作細節

### A. 硬停損 (Hard Stop Loss)
- **設定參數**: `stop_loss_pct` (如 5.0%)
- **觸發邏輯**: 當持股未扣除交易成本之虧損趴數達到門檻時：
  $$\frac{P_{\text{close}} - P_{\text{entry}}}{P_{\text{entry}}} \le -0.05 \implies \text{ForceExit} = \text{True}$$
- **動作與標示**: 次日開盤執行 `SELL (RISK)`，離場原因標示 `STOP_LOSS (-5.0%)`。

---

### B. 兩階段移動停利 (Two-Step Trailing Stop)
- **設定參數**: 
  - `take_profit_pct`：目標獲利激活門檻 (如 15.0%)
  - `trailing_stop_pct`：高點拉回離場趴數 (如 5.0%)

- **第一階段（目標達標激活）**:
  當最高價收益率達到目標門檻時，正式激活高點追蹤模式：
  $$\frac{P_{\text{high}} - P_{\text{entry}}}{P_{\text{entry}}} \ge 0.15 \implies \text{TrailingActive} = \text{True}$$

- **第二階段（高點拉回平倉）**:
  激活後，即時追蹤持股期間最高價 $P_{\text{peak}} = \max(P_{\text{peak}}, P_{\text{high}})$。當收盤價自最高價拉回幅度達到拉回門檻時：
  $$\frac{P_{\text{peak}} - P_{\text{close}}}{P_{\text{peak}}} \ge 0.05 \implies \text{ForceExit} = \text{True}$$
- **動作與標示**: 次日開盤執行 `SELL (RISK)`，離場原因標示 `TRAILING_STOP (Peak: 1525.0, Pullback: -6.2%)`，在 GUI 與圖表中以**紫色向下箭頭與粗體字**獨立高亮標示。

---

### C. 停利後突破前高重新接回 (Breakout Re-entry)
- **設定參數**: `enable_reentry = True`
- **運作邏輯**:
  1. 移動停利平倉後，記住當時的波段最高價 $P_{\text{last\_peak}}$。
  2. 風控離場後啟動觀望鎖定 (`risk_exited = True`)，無視舊型態訊號不隨意買回。
  3. 若價格隨後**強勢突破上一次波段最高價** $P_{\text{close}} > P_{\text{last\_peak}}$：
     $$\text{ReentryTriggered} = \text{True}$$
- **動作與標示**: 次日開盤執行 `BUY (RE-ENTRY)` 追價建倉，離場原因標示 `BREAKOUT_REENTRY (Peak: 1525.0)`，在 GUI 與圖表中以**橘色特大向上箭頭與粗體字**獨立高亮標示。
