# 永豐金 Shioaji API 2330 30日日 K 抓取與策略回測系統

本專案參考 [chuangtc/shioaji_api](https://github.com/chuangtc/shioaji_api) 實作，提供標準化的 **SinoPac Shioaji Python API** 串接環境、2330 (台積電) 30 日日 K 線抓取，以及專門針對台股交易成本設計的模組化策略回測系統。

---

## 專案亮點

1. **資安防護 (Git 安全)**：
   - 敏感憑證 (`API_KEY`, `SECRET_KEY`, `*.pfx`) 嚴格透過 `.env` 檔案隔離管理，並於 `.gitignore` 中明確排除，**絕不出現在 Git 版本控制中**。
2. **模擬/正式環境切換與容錯 (Mock Fallback)**：
   - 支援 `simulation=True` 模擬環境與正式環境。
   - 若離線或無金鑰環境，會自動切換至 Mock Data 模式，不中斷開發測試流程。
3. **專屬台股交易成本回測引擎 (`src/backtest/`)**：
   - 支援每張 1,000 股基準。
   - 計算券商手續費 (0.1425% × 折扣，最低 20 元) 與賣出證交稅 (0.3%)。
   - 自動生成夏普比率 (Sharpe Ratio)、最大回撤 (MDD)、總報酬率與交易日誌 (Trade Logs)。

---

## 快速開始

### 1. 安裝環境依賴

```bash
pip install -r requirements.txt
```

*(可選高效率套件)*：
```bash
pip install "shioaji[speed]"
```

---

### 2. 設定 API 金鑰 (.env)

複製 `.env.template` 建立本機 `.env` 檔：

```bash
cp .env.template .env
```

在 `.env` 中填入永豐金 API 金鑰：
```env
API_KEY="YOUR_API_KEY"
SECRET_KEY="YOUR_SECRET_KEY"
SIMULATION=True
```

> [!CAUTION]
> 切勿將包含真實 `API_KEY` 與 `SECRET_KEY` 的 `.env` 上傳至 GitHub 或公開檔案庫！

---

### 3. 執行 GUI 圖形化介面 (切換股票與下載圖表)

```bash
python gui.py
```

提供桌面 GUI 操作介面：
- 可自由切換股票代碼 (例: `2330`, `2317`, `2454`, `0050`, `00878` 等)。
- 選擇回測策略 (SMA 均線、RSI、MACD、布林通道、KD) 與設定停損停利風控。
- 即時預覽 K 線買賣訊號標記與權益資產曲線。
- 提供 **[💾 下載 / 儲存分析圖表]** 按鈕，彈出檔案儲存視窗讓您決定是否儲存圖表。

---

### 4. 執行命令行腳本

```bash
python main_phase2.py
```

執行後將自動完成：
1. Shioaji API 登入驗證
2. 下載 2330 (台積電) 近 30 個交易日日 K 線 (ts, open, high, low, close, volume)
3. 執行 5SMA / 20SMA 雙均線交叉策略歷史回測
4. 印出策略績效報告與交易日誌

---

## 專案架構說明

```
20260802_Shiaoji_測試/
├── .env.template               # 憑證設定範本
├── .env                        # 本地密鑰設定 (被 .gitignore 排除)
├── .gitignore                  # Git 忽略檔 (保護敏感憑證)
├── requirements.txt            # Python 依賴清單
├── README.md                   # 專案說明文件
├── main.py                     # 主執行腳本
└── src/
    ├── __init__.py
    ├── client.py               # Shioaji API 封裝 (登入、合約取得、KBar 轉 DataFrame)
    └── backtest/               # 策略回測模組
        ├── __init__.py
        ├── engine.py           # 台股回測引擎 (含手續費折扣與證交稅)
        ├── strategy.py         # 策略基類與 SMA 雙均線策略
        └── evaluator.py        # 策略績效評估 (Sharpe, MDD, 勝率)
```

---

## 策略擴充 (長遠目標)

若要新增客製化策略，只需在 `src/backtest/strategy.py` 繼承 `BaseStrategy` 並實作 `generate_signals` 方法即可：

```python
from src.backtest.strategy import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    def generate_signals(self, df):
        data = df.copy()
        # 撰寫您的技術指標邏輯 (如 RSI, MACD, 布林通道)
        data["signal"] = ... # 1 為買進, 0 為賣出
        data["position"] = data["signal"].shift(1).fillna(0)
        return data
```
