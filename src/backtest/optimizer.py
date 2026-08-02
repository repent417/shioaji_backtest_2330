"""
Grid Search Parameter Optimizer for Strategies
對策略參數進行網格搜尋，自動找出最佳化參數組合 (Highest Return & Sharpe)
"""
import pandas as pd
from typing import List, Dict, Any, Type
from .strategy import BaseStrategy, SMACrossStrategy
from .engine import BacktestEngine
from .evaluator import PerformanceEvaluator

class GridSearchOptimizer:
    def __init__(self, df: pd.DataFrame, initial_capital: float = 3_000_000.0):
        self.df = df
        self.initial_capital = initial_capital

    def optimize_sma(self, short_range: List[int], long_range: List[int]) -> pd.DataFrame:
        results = []
        engine = BacktestEngine(initial_capital=self.initial_capital)

        for s in short_range:
            for l in long_range:
                if s >= l:
                    continue
                strategy = SMACrossStrategy(short_window=s, long_window=l)
                res = engine.run(self.df, strategy)
                metrics = PerformanceEvaluator.evaluate(res)
                
                total_ret_str = metrics.get("總報酬率 (%)", "0.00%").replace("%", "")
                sharpe_str = metrics.get("夏普比率 (Sharpe)", "0.00")
                mdd_str = metrics.get("最大回撤 MDD (%)", "0.00%").replace("%", "")
                
                results.append({
                    "short_sma": s,
                    "long_sma": l,
                    "total_return_pct": float(total_ret_str),
                    "sharpe_ratio": float(sharpe_str),
                    "mdd_pct": float(mdd_str),
                    "trades": metrics.get("總交易次數", 0),
                    "win_rate_pct": float(metrics.get("交易勝率 (%)", "0.0%").replace("%", ""))
                })

        opt_df = pd.DataFrame(results)
        if not opt_df.empty:
            opt_df.sort_values(by="total_return_pct", ascending=False, inplace=True)
            opt_df.reset_index(drop=True, inplace=True)
        return opt_df
