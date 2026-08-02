"""
Shioaji API 台股策略回測 GUI 系統
提供桌面 GUI 介面，支援切換股票代碼、可選紅漲綠跌 K 線或收盤折線、調整策略與風控參數，並可下載分析圖表。
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from dotenv import load_dotenv

from src.client import ShioajiClient
from src.data import LocalDataCache
from src.backtest import (
    SMACrossStrategy,
    RSIStrategy,
    MACDStrategy,
    BollingerBandsStrategy,
    KDStrategy,
    BacktestEngine,
    PerformanceEvaluator
)

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "SimHei", "Arial"]
plt.rcParams["axes.unicode_minus"] = False

class BacktestGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("永豐金 Shioaji 台股策略回測與風控系統 GUI")
        self.geometry("1280x850")
        self.minsize(1024, 720)

        # 狀態紀錄
        self.current_fig = None
        self.last_result = None
        self.stock_code = "2330"

        # 載入環境變數
        load_dotenv()
        self.db_cache = LocalDataCache(db_path=os.path.join("data", "kbars_cache.db"))

        # 設定視窗關閉 (點擊 X) 時的處理機制
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self._build_ui()

    def on_closing(self):
        """關閉視窗時清理資源並完全結束 Terminal 進程"""
        plt.close("all")
        try:
            self.quit()
            self.destroy()
        except Exception:
            pass
        os._exit(0)

    def _build_ui(self):
        # 主面板劃分：左邊控制欄，右邊圖表呈現欄
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左側控制區塊 Frame
        left_frame = ttk.LabelFrame(main_paned, text=" 回測與策略參數設定 ", padding=15)
        main_paned.add(left_frame, weight=1)

        # 1. 股票代碼輸入
        ttk.Label(left_frame, text="股票代號 (例: 2330, 2317, 0050):", font=("Microsoft JhengHei", 10, "bold")).pack(anchor=tk.W, pady=(0, 2))
        self.entry_code = ttk.Entry(left_frame, font=("Microsoft JhengHei", 10))
        self.entry_code.insert(0, "2330")
        self.entry_code.pack(fill=tk.X, pady=(0, 10))

        # 2. 回測天數 (日曆天)
        ttk.Label(left_frame, text="回測天數 (1年=365):", font=("Microsoft JhengHei", 10)).pack(anchor=tk.W, pady=(0, 2))
        self.entry_days = ttk.Entry(left_frame, font=("Microsoft JhengHei", 10))
        self.entry_days.insert(0, "365")
        self.entry_days.pack(fill=tk.X, pady=(0, 10))

        # 3. 策略選擇
        ttk.Label(left_frame, text="選擇技術指標策略:", font=("Microsoft JhengHei", 10, "bold")).pack(anchor=tk.W, pady=(0, 2))
        self.combo_strategy = ttk.Combobox(left_frame, state="readonly", font=("Microsoft JhengHei", 10))
        self.combo_strategy["values"] = [
            "SMA Cross (10/60) [最佳化推薦]",
            "SMA Cross (5/10) [短期均線]",
            "RSI Strategy (14, 35/65) [低風險]",
            "MACD Strategy (12/26/9)",
            "Bollinger Bands (20, 2.0std)",
            "KD Strategy (9)"
        ]
        self.combo_strategy.current(0)
        self.combo_strategy.pack(fill=tk.X, pady=(0, 10))

        # 4. 主圖類型 (K線 vs 折線)
        ttk.Label(left_frame, text="主圖繪製類型:", font=("Microsoft JhengHei", 10, "bold")).pack(anchor=tk.W, pady=(0, 2))
        self.combo_chart_type = ttk.Combobox(left_frame, state="readonly", font=("Microsoft JhengHei", 10))
        self.combo_chart_type["values"] = [
            "紅漲綠跌 K線 (Candlestick)",
            "收盤價折線 (Line Chart)"
        ]
        self.combo_chart_type.current(0)
        self.combo_chart_type.pack(fill=tk.X, pady=(0, 10))
        self.combo_chart_type.bind("<<ComboboxSelected>>", self.on_chart_type_changed)

        # 5. 初始資金 (TWD)
        ttk.Label(left_frame, text="初始資金 (TWD):", font=("Microsoft JhengHei", 10)).pack(anchor=tk.W, pady=(0, 2))
        self.entry_capital = ttk.Entry(left_frame, font=("Microsoft JhengHei", 10))
        self.entry_capital.insert(0, "3000000")
        self.entry_capital.pack(fill=tk.X, pady=(0, 10))

        # 6. 風控參數 (停損 / 停利 %)
        risk_frame = ttk.Frame(left_frame)
        risk_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(risk_frame, text="停損 (%):").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.entry_sl = ttk.Entry(risk_frame, width=8)
        self.entry_sl.insert(0, "5.0")
        self.entry_sl.grid(row=0, column=1, padx=(0, 15))

        ttk.Label(risk_frame, text="停利 (%):").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.entry_tp = ttk.Entry(risk_frame, width=8)
        self.entry_tp.insert(0, "15.0")
        self.entry_tp.grid(row=0, column=3)

        # 7. [🚀 開始回測] 按鈕
        self.btn_run = tk.Button(
            left_frame, 
            text="🚀 開始執行歷史回測", 
            font=("Microsoft JhengHei", 11, "bold"),
            bg="#007bff", 
            fg="white",
            activebackground="#0056b3",
            activeforeground="white",
            relief=tk.RAISED,
            bd=3,
            command=self.run_backtest
        )
        self.btn_run.pack(fill=tk.X, pady=(0, 15))

        # 8. 績效顯示卡片 (LabelFrame)
        self.perf_frame = ttk.LabelFrame(left_frame, text=" 策略歷史績效報告 ", padding=10)
        self.perf_frame.pack(fill=tk.X, pady=(0, 15))

        self.lbl_init_cap = ttk.Label(self.perf_frame, text="初始資金 (TWD): --", font=("Microsoft JhengHei", 10))
        self.lbl_init_cap.pack(anchor=tk.W, pady=2)

        self.lbl_final_eq = ttk.Label(self.perf_frame, text="現有資產 (TWD): --", font=("Microsoft JhengHei", 10, "bold"))
        self.lbl_final_eq.pack(anchor=tk.W, pady=2)

        self.lbl_ret = ttk.Label(self.perf_frame, text="總報酬率 (%): --", font=("Microsoft JhengHei", 10, "bold"))
        self.lbl_ret.pack(anchor=tk.W, pady=2)

        self.lbl_mdd = ttk.Label(self.perf_frame, text="最大回撤 MDD (%): --", font=("Microsoft JhengHei", 10))
        self.lbl_mdd.pack(anchor=tk.W, pady=2)

        self.lbl_sharpe = ttk.Label(self.perf_frame, text="夏普比率 (Sharpe): --", font=("Microsoft JhengHei", 10))
        self.lbl_sharpe.pack(anchor=tk.W, pady=2)

        self.lbl_winrate = ttk.Label(self.perf_frame, text="交易勝率 (%): --", font=("Microsoft JhengHei", 10))
        self.lbl_winrate.pack(anchor=tk.W, pady=2)

        self.lbl_trades = ttk.Label(self.perf_frame, text="總交易次數: --", font=("Microsoft JhengHei", 10))
        self.lbl_trades.pack(anchor=tk.W, pady=2)

        # 9. [💾 下載/儲存圖表] 按鈕 (初始為未啟用狀態)
        self.btn_download = tk.Button(
            left_frame,
            text="💾 下載 / 儲存分析圖表 (.png)",
            font=("Microsoft JhengHei", 11, "bold"),
            bg="#28a745",
            fg="white",
            activebackground="#1e7e34",
            activeforeground="white",
            relief=tk.RAISED,
            bd=3,
            state=tk.DISABLED,
            command=self.download_chart
        )
        self.btn_download.pack(fill=tk.X, pady=(5, 0))

        # 右側圖表呈現區塊 Frame
        right_frame = ttk.LabelFrame(main_paned, text=" 回測圖表預覽 (K線/折線與權益曲線) ", padding=10)
        main_paned.add(right_frame, weight=3)

        self.chart_container = ttk.Frame(right_frame)
        self.chart_container.pack(fill=tk.BOTH, expand=True)

        self.canvas_widget = None

    def on_chart_type_changed(self, event=None):
        """當使用者切換主圖類型 (K線 vs 折線) 時即時重繪"""
        if self.last_result:
            self._render_chart(self.last_result, self.stock_code)

    def run_backtest(self):
        code = self.entry_code.get().strip().upper()
        if not code:
            messagebox.showwarning("警告", "請輸入有效的股票代號！")
            return

        try:
            days = int(self.entry_days.get().strip())
            capital = float(self.entry_capital.get().strip())
            sl_pct = float(self.entry_sl.get().strip()) / 100.0 if self.entry_sl.get().strip() else None
            tp_pct = float(self.entry_tp.get().strip()) / 100.0 if self.entry_tp.get().strip() else None
        except ValueError:
            messagebox.showerror("錯誤", "請確認天數、資金與風控數值皆為合法的數字！")
            return

        self.stock_code = code
        self.btn_run.config(state=tk.DISABLED, text="⏳ 資料處理中...")
        self.update_idletasks()

        try:
            # 1. 取得數據 (優先查詢本地 DB 快取)
            cutoff_dt = pd.to_datetime(datetime.now() - timedelta(days=days))
            df_kbars = self.db_cache.load_kbars(code=code)

            # 若本地 DB 無資料或覆蓋天數不夠，向 Shioaji API 增量抓取
            if df_kbars.empty or df_kbars["ts"].min() > cutoff_dt:
                simulation_env = os.getenv("SIMULATION", "True").lower() == "true"
                client = ShioajiClient(simulation=simulation_env)
                if client.login():
                    fetched_df = client.get_daily_kbars(code=code, days=days)
                    self.db_cache.save_kbars(code=code, df=fetched_df)
                    df_kbars = self.db_cache.load_kbars(code=code)
                    client.logout()
                else:
                    df_kbars = client._generate_mock_kbars(code=code, days=int(days*0.7))

            # 根據使用者輸入之天數 (days) 進行精確日期區間過濾
            if not df_kbars.empty:
                df_kbars = df_kbars[df_kbars["ts"] >= cutoff_dt].reset_index(drop=True)

            if df_kbars.empty:
                messagebox.showerror("錯誤", f"無法取得股票 [{code}] 的歷史數據。")
                self.btn_run.config(state=tk.NORMAL, text="🚀 開始執行歷史回測")
                return

            # 2. 實例化策略
            strat_name = self.combo_strategy.get()
            if "10/60" in strat_name:
                strategy = SMACrossStrategy(short_window=10, long_window=60)
            elif "5/10" in strat_name:
                strategy = SMACrossStrategy(short_window=5, long_window=10)
            elif "RSI" in strat_name:
                strategy = RSIStrategy(period=14, oversold=35, overbought=65)
            elif "MACD" in strat_name:
                strategy = MACDStrategy(fast_period=12, slow_period=26, signal_period=9)
            elif "Bollinger" in strat_name:
                strategy = BollingerBandsStrategy(period=20, std_dev=2.0)
            else:
                strategy = KDStrategy(period=9)

            # 3. 執行回測引擎
            engine = BacktestEngine(
                initial_capital=capital,
                stop_loss_pct=sl_pct,
                take_profit_pct=tp_pct
            )
            result = engine.run(df=df_kbars, strategy=strategy)
            self.last_result = result

            # 4. 更新績效顯示卡片
            metrics = PerformanceEvaluator.evaluate(result)
            ret_val = metrics.get("總報酬率 (%)", "0.00%")
            ret_color = "red" if float(ret_val.replace("%", "")) > 0 else ("green" if float(ret_val.replace("%", "")) < 0 else "black")
            
            self.lbl_init_cap.config(text=f"初始資金 (TWD):  NT$ {metrics.get('初始資金 (TWD)', '0')}")
            self.lbl_final_eq.config(text=f"現有資產 (TWD):  NT$ {metrics.get('期末資產 (TWD)', '0')}", foreground=ret_color)
            self.lbl_ret.config(text=f"總報酬率 (%):  {ret_val}", foreground=ret_color)
            self.lbl_mdd.config(text=f"最大回撤 MDD (%):  {metrics.get('最大回撤 MDD (%)', '0.00%')}")
            self.lbl_sharpe.config(text=f"夏普比率 (Sharpe):  {metrics.get('夏普比率 (Sharpe)', '0.00')}")
            self.lbl_winrate.config(text=f"交易勝率 (%):  {metrics.get('交易勝率 (%)', '0.0%')}")
            self.lbl_trades.config(text=f"總交易次數:  {metrics.get('總交易次數', 0)}")

            # 5. 繪製圖表並內嵌置 GUI
            self._render_chart(result, code)

            # 啟用下載按鈕
            self.btn_download.config(state=tk.NORMAL)

        except Exception as e:
            messagebox.showerror("執行錯誤", f"回測過程發生例外: {e}")
        finally:
            self.btn_run.config(state=tk.NORMAL, text="🚀 開始執行歷史回測")

    def _render_chart(self, result: dict, code: str):
        if self.canvas_widget:
            self.canvas_widget.destroy()

        from src.backtest.plotter import BacktestPlotter
        chart_type_str = self.combo_chart_type.get()
        chart_type = "line" if "折線" in chart_type_str else "candlestick"

        fig = BacktestPlotter.create_figure(result, stock_code=code, chart_type=chart_type)
        self.current_fig = fig

        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        self.canvas_widget = canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)

    def download_chart(self):
        if not self.current_fig:
            messagebox.showwarning("警告", "目前尚無產生的圖表可供下載！")
            return

        default_filename = f"{self.stock_code}_backtest_chart.png"
        filepath = filedialog.asksaveasfilename(
            title="儲存 / 下載分析圖表",
            initialdir=os.path.abspath("output"),
            initialfile=default_filename,
            defaultextension=".png",
            filetypes=[("PNG 圖片檔", "*.png"), ("JPG 圖片檔", "*.jpg"), ("所有檔案", "*.*")]
        )

        if filepath:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            self.current_fig.savefig(filepath, dpi=300)
            messagebox.showinfo("儲存成功", f"圖表已成功下載儲存至：\n{filepath}")

if __name__ == "__main__":
    app = BacktestGUI()
    app.mainloop()
