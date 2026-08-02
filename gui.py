"""
Shioaji API 台股策略回測 GUI 系統
提供桌面 GUI 介面，支援切換股票代碼、高點拉回移動停利 (Trailing Stop)、突破前高重新接回、K線/折線圖預覽、交易明細與圖表下載。
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
        self.geometry("1400x900")
        self.minsize(1024, 760)

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
        # 主面板劃分：左邊控制欄，右邊分頁欄 (圖表與交易明細)
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

        # 6. 風控選擇 (硬停損與高點拉回移動停利)
        self.var_enable_risk = tk.BooleanVar(value=True)
        self.chk_risk = ttk.Checkbutton(
            left_frame,
            text=" 啟用風控機制 (停損 & 移動停利)",
            variable=self.var_enable_risk,
            command=self.on_risk_toggle
        )
        self.chk_risk.pack(anchor=tk.W, pady=(0, 5))

        # 風控數值設定 Frame (硬停損 % 與 高點拉回停利 %)
        self.risk_frame = ttk.Frame(left_frame)
        self.risk_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(self.risk_frame, text="硬停損 (%):").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.entry_sl = ttk.Entry(self.risk_frame, width=7)
        self.entry_sl.insert(0, "5.0")
        self.entry_sl.grid(row=0, column=1, padx=(0, 10))

        ttk.Label(self.risk_frame, text="高點拉回停利 (%):").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.entry_ts = ttk.Entry(self.risk_frame, width=7)
        self.entry_ts.insert(0, "5.0")
        self.entry_ts.grid(row=0, column=3)

        # 7. 突破前高重新接回 勾選框 (可選)
        self.var_enable_reentry = tk.BooleanVar(value=True)
        self.chk_reentry = ttk.Checkbutton(
            left_frame,
            text=" 停利後若突破前高重新接回 (Re-entry)",
            variable=self.var_enable_reentry
        )
        self.chk_reentry.pack(anchor=tk.W, pady=(0, 15))

        # 8. [🚀 開始回測] 按鈕
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

        # 9. 績效顯示卡片 (LabelFrame)
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

        # 10. [💾 下載/儲存圖表] 按鈕 (初始為未啟用狀態)
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

        # 右側分頁面板 Notebook Frame
        right_notebook = ttk.Notebook(main_paned)
        main_paned.add(right_notebook, weight=3)

        # 分頁 1: 回測圖表預覽
        tab_chart = ttk.Frame(right_notebook, padding=10)
        right_notebook.add(tab_chart, text=" 📈 回測分析圖表 ")

        self.chart_container = ttk.Frame(tab_chart)
        self.chart_container.pack(fill=tk.BOTH, expand=True)

        # 分頁 2: 交易明細表格 (Trade Logs Table)
        tab_trades = ttk.Frame(right_notebook, padding=10)
        right_notebook.add(tab_trades, text=" 📋 交易明細紀錄 ")

        self._build_trades_table(tab_trades)

        self.canvas_widget = None

    def _build_trades_table(self, parent):
        """建立交易明細表格 Treeview"""
        columns = ("date", "action", "price", "shares", "amount", "fee", "tax", "reason")
        
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.tree_trades = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        
        headers = {
            "date": "交易日期",
            "action": "買賣動作",
            "price": "成交單價 (TWD)",
            "shares": "成交股數",
            "amount": "成交總額 (TWD)",
            "fee": "手續費 (TWD)",
            "tax": "證交稅 (TWD)",
            "reason": "觸發原因"
        }

        for col, text in headers.items():
            self.tree_trades.heading(col, text=text)
            self.tree_trades.column(col, anchor=tk.CENTER, width=110)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree_trades.yview)
        self.tree_trades.configure(yscrollcommand=scrollbar.set)

        self.tree_trades.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_trades.tag_configure("BUY", foreground="red")
        self.tree_trades.tag_configure("SELL", foreground="green")

    def on_risk_toggle(self):
        """勾選/取消主動停損停利時動態切換輸入框狀態"""
        if self.var_enable_risk.get():
            self.entry_sl.config(state=tk.NORMAL)
            self.entry_ts.config(state=tk.NORMAL)
            self.chk_reentry.config(state=tk.NORMAL)
        else:
            self.entry_sl.config(state=tk.DISABLED)
            self.entry_ts.config(state=tk.DISABLED)
            self.chk_reentry.config(state=tk.DISABLED)

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
            
            if self.var_enable_risk.get():
                sl_pct = float(self.entry_sl.get().strip()) / 100.0 if self.entry_sl.get().strip() else None
                ts_pct = float(self.entry_ts.get().strip()) / 100.0 if self.entry_ts.get().strip() else None
                enable_reentry = self.var_enable_reentry.get()
            else:
                sl_pct = None
                ts_pct = None
                enable_reentry = False
        except ValueError:
            messagebox.showerror("錯誤", "請確認天數、資金與風控數值皆為合法的數字！")
            return

        self.stock_code = code
        self.btn_run.config(state=tk.DISABLED, text="⏳ 資料處理中...")
        self.update_idletasks()

        try:
            # 1. 優先從本地 DB 讀取歷史數據
            cutoff_dt = pd.to_datetime(datetime.now() - timedelta(days=days))
            df_kbars = self.db_cache.load_kbars(code=code)

            needs_api_fetch = False
            if df_kbars.empty:
                needs_api_fetch = True
            else:
                db_min = df_kbars["ts"].min()
                db_max = df_kbars["ts"].max()
                days_behind = (datetime.now() - db_max).days
                if db_min > cutoff_dt or days_behind > 3:
                    needs_api_fetch = True

            if needs_api_fetch:
                simulation_env = os.getenv("SIMULATION", "True").lower() == "true"
                client = ShioajiClient(simulation=simulation_env)
                if client.login():
                    fetched_df = client.get_daily_kbars(code=code, days=days)
                    self.db_cache.save_kbars(code=code, df=fetched_df)
                    df_kbars = self.db_cache.load_kbars(code=code)
                    client.logout()
                else:
                    df_kbars = client._generate_mock_kbars(code=code, days=int(days*0.7))

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

            # 3. 執行回測引擎 (含移動停利與突破前高接回)
            engine = BacktestEngine(
                initial_capital=capital,
                stop_loss_pct=sl_pct,
                trailing_stop_pct=ts_pct,
                enable_reentry=enable_reentry
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

            # 5. 填入交易明細表格 (Trade Logs Table)
            self._update_trades_table(result["trades"])

            # 6. 繪製圖表並內嵌置 GUI
            self._render_chart(result, code)

            # 啟用下載按鈕
            self.btn_download.config(state=tk.NORMAL)

        except Exception as e:
            messagebox.showerror("執行錯誤", f"回測過程發生例外: {e}")
        finally:
            self.btn_run.config(state=tk.NORMAL, text="🚀 開始執行歷史回測")

    def _update_trades_table(self, trades_df: pd.DataFrame):
        """刷新並充填交易明細表格"""
        for item in self.tree_trades.get_children():
            self.tree_trades.delete(item)

        if trades_df.empty:
            return

        for _, row in trades_df.iterrows():
            date_str = row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"])
            action_str = str(row["action"])
            tag = "BUY" if "BUY" in action_str else "SELL"
            
            price_str = f"{row['price']:,.1f}"
            shares_str = f"{int(row['shares']):,}"
            amount_str = f"{row['amount']:,.0f}"
            fee_str = f"{row['fee']:,.1f}"
            tax_str = f"{row['tax']:,.1f}"
            reason_str = str(row.get("reason", "SIGNAL"))

            self.tree_trades.insert(
                "",
                tk.END,
                values=(date_str, action_str, price_str, shares_str, amount_str, fee_str, tax_str, reason_str),
                tags=(tag,)
            )

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
