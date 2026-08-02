"""
Matplotlib Backtest Visualizer
繪製日 K 線、均線、買賣點標籤與權益資產走勢圖 (Equity Curve)
"""
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from typing import Dict, Any

# 設定中文字體支援
plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "SimHei", "Arial"]
plt.rcParams["axes.unicode_minus"] = False

class BacktestPlotter:
    @staticmethod
    def plot(result: Dict[str, Any], save_path: str = os.path.join("output", "backtest_result.png")):
        dir_name = os.path.dirname(save_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
            
        portfolio = result["portfolio"]
        trades = result["trades"]
        strategy_name = result.get("strategy_name", "Backtest Strategy")

        if portfolio.empty:
            print("無法繪製圖表：回測數據為空。")
            return

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9), sharex=True, gridspec_kw={"height_ratios": [2.5, 1]})

        # 1. 主圖：股價與買賣交易標籤
        ax1.plot(portfolio["ts"], portfolio["close"], label="Close Price", color="#1f77b4", linewidth=1.5)
        
        if not trades.empty:
            buy_trades = trades[trades["action"].str.contains("BUY")]
            sell_trades = trades[trades["action"].str.contains("SELL")]

            if not buy_trades.empty:
                ax1.scatter(buy_trades["date"], buy_trades["price"], marker="^", color="red", s=100, label="BUY Signal", zorder=5)
            if not sell_trades.empty:
                ax1.scatter(sell_trades["date"], sell_trades["price"], marker="v", color="green", s=100, label="SELL Signal", zorder=5)

        ax1.set_title(f"2330 台積電歷史股價與買賣點標記 - {strategy_name}", fontsize=14, fontweight="bold")
        ax1.set_ylabel("股價 (TWD)", fontsize=12)
        ax1.grid(True, linestyle="--", alpha=0.5)
        ax1.legend(loc="upper left")

        # 2. 副圖：權益資產走勢圖 (Equity Curve)
        ax2.plot(portfolio["ts"], portfolio["total_equity"], label="Total Equity (TWD)", color="#ff7f0e", linewidth=2)
        ax2.axhline(y=result["initial_capital"], color="gray", linestyle="--", alpha=0.7, label="Initial Capital")
        
        ax2.set_title("策略權益資產走勢曲線 (Equity Curve)", fontsize=12, fontweight="bold")
        ax2.set_xlabel("日期", fontsize=12)
        ax2.set_ylabel("總資產 (TWD)", fontsize=12)
        ax2.grid(True, linestyle="--", alpha=0.5)
        ax2.legend(loc="upper left")

        # 格式化 X 軸日期
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        fig.autofmt_xdate()

        plt.tight_layout()
        plt.savefig(save_path, dpi=300)
        plt.close()
        print(f"回測分析圖表已成功儲存至: {os.path.abspath(save_path)}")
