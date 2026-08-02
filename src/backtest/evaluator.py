"""
Performance Evaluator for Backtesting
計算策略評估指標：累積報酬率、最大回撤 (MDD)、夏普比率 (Sharpe Ratio)、勝率與交易次數
"""
import pandas as pd
import numpy as np
from typing import Dict, Any

class PerformanceEvaluator:
    @staticmethod
    def evaluate(result: Dict[str, Any]) -> Dict[str, Any]:
        portfolio = result["portfolio"]
        trades = result["trades"]
        initial_capital = result["initial_capital"]
        final_equity = result["final_equity"]

        if portfolio.empty:
            return {}

        total_return = (final_equity - initial_capital) / initial_capital

        # 計算最大回撤 (Max Drawdown, MDD)
        equity_series = portfolio["total_equity"]
        cum_max = equity_series.cummax()
        drawdown = (equity_series - cum_max) / cum_max
        max_drawdown = abs(drawdown.min())

        # 計算夏普比率 (Sharpe Ratio, 假設無風險利率 1%)
        daily_returns = portfolio["daily_return"]
        rf_daily = 0.01 / 252
        mean_ret = daily_returns.mean() - rf_daily
        std_ret = daily_returns.std()
        sharpe_ratio = (mean_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0.0

        # 計算勝率
        total_trades = len(trades)
        if total_trades > 1:
            # 以買賣對結算的損益計算勝率 (包含風控平倉與突破接回交易)
            buy_trades = trades[trades["action"].str.contains("BUY")].reset_index(drop=True)
            sell_trades = trades[trades["action"].str.contains("SELL")].reset_index(drop=True)
            
            n_completed = min(len(buy_trades), len(sell_trades))
            wins = 0
            for i in range(n_completed):
                buy_cost = buy_trades.loc[i, "amount"] + buy_trades.loc[i, "fee"]
                sell_revenue = sell_trades.loc[i, "amount"] - sell_trades.loc[i, "fee"] - sell_trades.loc[i, "tax"]
                if sell_revenue > buy_cost:
                    wins += 1
            win_rate = wins / n_completed if n_completed > 0 else 0.0
        else:
            win_rate = 0.0

        metrics = {
            "策略名稱": result.get("strategy_name", "策略"),
            "初始資金 (TWD)": f"{initial_capital:,.0f}",
            "期末資產 (TWD)": f"{final_equity:,.0f}",
            "總報酬率 (%)": f"{total_return * 100:.2f}%",
            "最大回撤 MDD (%)": f"{max_drawdown * 100:.2f}%",
            "夏普比率 (Sharpe)": f"{sharpe_ratio:.2f}",
            "總交易次數": total_trades,
            "交易勝率 (%)": f"{win_rate * 100:.1f}%"
        }
        return metrics

    @staticmethod
    def print_summary(metrics: Dict[str, Any]):
        print("\n" + "="*45)
        print("         策略歷史回測績效報告")
        print("="*45)
        for k, v in metrics.items():
            print(f"  {k:<18}: {v}")
        print("="*45 + "\n")
