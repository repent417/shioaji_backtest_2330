"""
Matplotlib Backtest Visualizer
支援切換「紅漲綠跌 K 線 (Candlesticks)」或「收盤價折線 (Line Chart)」，並動態繪製均線 / 布林通道 / RSI / MACD / KD 指標與權益曲線
"""
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from typing import Dict, Any

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "SimHei", "Arial"]
plt.rcParams["axes.unicode_minus"] = False

class BacktestPlotter:
    @staticmethod
    def _draw_candlesticks(ax, df: pd.DataFrame, width: float = 0.6):
        """在 Matplotlib ax 上繪製紅漲綠跌之真實 K 線 (Candlesticks)"""
        up_df = df[df["close"] >= df["open"]]
        down_df = df[df["close"] < df["open"]]

        if not up_df.empty:
            ax.vlines(up_df["ts"], up_df["low"], up_df["high"], color="red", linewidth=1.0, zorder=2)
            heights = np.maximum(abs(up_df["close"] - up_df["open"]), 0.5)
            bottoms = np.minimum(up_df["open"], up_df["close"])
            ax.bar(up_df["ts"], heights, bottom=bottoms, width=width, color="red", edgecolor="red", zorder=3)

        if not down_df.empty:
            ax.vlines(down_df["ts"], down_df["low"], down_df["high"], color="green", linewidth=1.0, zorder=2)
            heights = np.maximum(abs(down_df["close"] - down_df["open"]), 0.5)
            bottoms = np.minimum(down_df["open"], down_df["close"])
            ax.bar(down_df["ts"], heights, bottom=bottoms, width=width, color="green", edgecolor="green", zorder=3)

    @staticmethod
    def create_figure(result: Dict[str, Any], stock_code: str = "2330", chart_type: str = "candlestick") -> plt.Figure:
        """
        建立 Matplotlib Figure 圖表
        :param chart_type: "candlestick" (K線圖) 或 "line" (收盤折線圖)
        """
        portfolio = result["portfolio"]
        trades = result["trades"]
        strategy_name = result.get("strategy_name", "Backtest Strategy")

        if portfolio.empty:
            fig, ax = plt.subplots(figsize=(9, 6))
            ax.text(0.5, 0.5, "無回測資料可供顯示", ha="center", va="center", fontsize=14)
            return fig

        has_sub_indicator = any(col in portfolio.columns for col in ["rsi", "dif", "k"])

        if has_sub_indicator:
            fig, (ax1, ax_ind, ax_eq) = plt.subplots(
                3, 1, figsize=(10, 8.5), sharex=True, 
                gridspec_kw={"height_ratios": [2.4, 1.2, 1.2]}
            )
        else:
            fig, (ax1, ax_eq) = plt.subplots(
                2, 1, figsize=(10, 7.5), sharex=True, 
                gridspec_kw={"height_ratios": [2.5, 1.2]}
            )
            ax_ind = None

        # 1. 主圖：根據 chart_type 選擇繪製 K 線還是折線
        if chart_type == "line":
            ax1.plot(portfolio["ts"], portfolio["close"], label=f"[{stock_code}] 收盤價", color="#1f77b4", linewidth=1.5, zorder=3)
        else: # "candlestick" (預設)
            BacktestPlotter._draw_candlesticks(ax1, portfolio, width=0.6)
            ax1.plot([], [], color="red", label="紅棒 (漲)", linewidth=3)
            ax1.plot([], [], color="green", label="綠棒 (跌)", linewidth=3)

        # 繪製均線 (SMA)
        if "sma_5" in portfolio.columns and "sma_10" in portfolio.columns and "sma_20" in portfolio.columns and "sma_60" in portfolio.columns:
            ax1.plot(portfolio["ts"], portfolio["sma_5"], label="5MA (週線)", color="#e377c2", linestyle="-", linewidth=1.2, zorder=4)
            ax1.plot(portfolio["ts"], portfolio["sma_10"], label="10MA (雙週)", color="#ff7f0e", linestyle="--", linewidth=1.2, zorder=4)
            ax1.plot(portfolio["ts"], portfolio["sma_20"], label="20MA (月線)", color="#2ca02c", linestyle="-.", linewidth=1.2, zorder=4)
            ax1.plot(portfolio["ts"], portfolio["sma_60"], label="60MA (季線)", color="#9467bd", linestyle=":", linewidth=1.5, zorder=4)
        elif "sma_short" in portfolio.columns and "sma_long" in portfolio.columns:
            ax1.plot(portfolio["ts"], portfolio["sma_short"], label="快線 (Short MA)", color="#ff7f0e", linestyle="--", linewidth=1.3, zorder=4)
            ax1.plot(portfolio["ts"], portfolio["sma_long"], label="慢線 (Long MA)", color="#9467bd", linestyle="--", linewidth=1.3, zorder=4)
        elif "sma" in portfolio.columns:
            ax1.plot(portfolio["ts"], portfolio["sma"], label="中軌 (SMA)", color="#ff7f0e", linestyle="--", linewidth=1.3, zorder=4)

        # 繪製布林通道 (Bollinger Bands)
        if "upper_band" in portfolio.columns and "lower_band" in portfolio.columns:
            ax1.plot(portfolio["ts"], portfolio["upper_band"], label="布林上軌", color="#2ca02c", linestyle=":", linewidth=1.2, zorder=4)
            ax1.plot(portfolio["ts"], portfolio["lower_band"], label="布林下軌", color="#d62728", linestyle=":", linewidth=1.2, zorder=4)
            ax1.fill_between(portfolio["ts"], portfolio["lower_band"], portfolio["upper_band"], color="#2ca02c", alpha=0.1, label="布林通道區域")

        # 標記買賣點 (Buy/Sell Arrow Signals)
        if not trades.empty:
            buy_trades = trades[trades["action"].str.contains("BUY")]
            sell_trades = trades[trades["action"].str.contains("SELL")]

            if not buy_trades.empty:
                ax1.scatter(buy_trades["date"], buy_trades["price"], marker="^", color="darkred", s=110, label="買進 (BUY)", zorder=6)
            if not sell_trades.empty:
                ax1.scatter(sell_trades["date"], sell_trades["price"], marker="v", color="darkgreen", s=110, label="賣出 (SELL)", zorder=6)

        title_type = "日 K 線 (紅漲綠跌)" if chart_type == "candlestick" else "收盤折線"
        ax1.set_title(f"[{stock_code}] 歷史股價 ({title_type}) 與指標 - {strategy_name}", fontsize=12, fontweight="bold")
        ax1.set_ylabel("股價 (TWD)", fontsize=10)
        ax1.grid(True, linestyle="--", alpha=0.5)
        ax1.legend(loc="upper left", fontsize=8)

        # 2. 中圖 (若有 RSI / MACD / KD 指標)
        if ax_ind is not None:
            if "rsi" in portfolio.columns and "k" in portfolio.columns:
                ax_ind.plot(portfolio["ts"], portfolio["k"], label="K 線", color="#1f77b4", linewidth=1.2)
                ax_ind.plot(portfolio["ts"], portfolio["d"], label="D 線", color="#ff7f0e", linewidth=1.2)
                ax_ind.plot(portfolio["ts"], portfolio["rsi"], label="RSI(14)", color="#8c564b", linestyle="--", linewidth=1.3)
                ax_ind.axhline(50, color="gray", linestyle=":", alpha=0.7, label="RSI強勢線 (50)")
                ax_ind.set_ylabel("KD / RSI 數值", fontsize=10)
                ax_ind.set_ylim(0, 100)
            elif "rsi" in portfolio.columns:
                ax_ind.plot(portfolio["ts"], portfolio["rsi"], label="RSI(14)", color="#8c564b", linewidth=1.3)
                ax_ind.axhline(70, color="red", linestyle="--", alpha=0.6, label="超買線 (70)")
                ax_ind.axhline(30, color="green", linestyle="--", alpha=0.6, label="超賣線 (30)")
                ax_ind.set_ylabel("RSI 數值", fontsize=10)
                ax_ind.set_ylim(0, 100)
            elif "dif" in portfolio.columns and "macd_signal" in portfolio.columns:
                ax_ind.plot(portfolio["ts"], portfolio["dif"], label="DIF 快線", color="#1f77b4", linewidth=1.2)
                ax_ind.plot(portfolio["ts"], portfolio["macd_signal"], label="DEM 慢線", color="#ff7f0e", linewidth=1.2)
                macd_hist = portfolio["dif"] - portfolio["macd_signal"]
                colors = np.where(macd_hist >= 0, "red", "green")
                ax_ind.bar(portfolio["ts"], macd_hist, color=colors, alpha=0.5, label="柱狀體 (Hist)")
                ax_ind.set_ylabel("MACD", fontsize=10)
            elif "k" in portfolio.columns and "d" in portfolio.columns:
                ax_ind.plot(portfolio["ts"], portfolio["k"], label="K 線", color="#1f77b4", linewidth=1.2)
                ax_ind.plot(portfolio["ts"], portfolio["d"], label="D 線", color="#ff7f0e", linewidth=1.2)
                ax_ind.axhline(80, color="red", linestyle="--", alpha=0.6)
                ax_ind.axhline(20, color="green", linestyle="--", alpha=0.6)
                ax_ind.set_ylabel("KD 數值", fontsize=10)
                ax_ind.set_ylim(0, 100)

            ax_ind.grid(True, linestyle="--", alpha=0.5)
            ax_ind.legend(loc="upper left", fontsize=8)

        # 3. 底圖：權益資產走勢圖 (Equity Curve)
        ax_eq.plot(portfolio["ts"], portfolio["total_equity"], label="總資產 (Total Equity)", color="#ff7f0e", linewidth=2)
        ax_eq.axhline(y=result["initial_capital"], color="gray", linestyle="--", alpha=0.7, label="初始資金")
        ax_eq.set_title("策略權益資產走勢曲線 (Equity Curve)", fontsize=10, fontweight="bold")
        ax_eq.set_xlabel("日期", fontsize=10)
        ax_eq.set_ylabel("資產 (TWD)", fontsize=10)
        ax_eq.grid(True, linestyle="--", alpha=0.5)
        ax_eq.legend(loc="upper left", fontsize=8)

        ax_eq.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        fig.autofmt_xdate()
        fig.tight_layout()

        return fig

    @classmethod
    def plot(cls, result: Dict[str, Any], save_path: str = os.path.join("output", "backtest_result.png"), stock_code: str = "2330", chart_type: str = "candlestick"):
        dir_name = os.path.dirname(save_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
            
        fig = cls.create_figure(result, stock_code=stock_code, chart_type=chart_type)
        fig.savefig(save_path, dpi=300)
        plt.close(fig)
        print(f"回測分析圖表已成功儲存至: {os.path.abspath(save_path)}")
