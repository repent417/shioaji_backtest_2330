"""
Shioaji API & Strategy Backtesting System - Phase 2 Demonstration
包含多策略比較、動態停損停利風控、本機 SQLite 資料庫快取、圖表繪製與網格搜尋最佳化
"""
import os
import pandas as pd
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
from src.backtest.plotter import BacktestPlotter
from src.backtest.optimizer import GridSearchOptimizer

def main():
    print("="*65)
    print("  Shioaji API 台股策略回測與風控最佳化系統 (Phase 2 全功能示範)")
    print("="*65)

    # 1. 數據獲取與 SQLite 快取 (儲存於 data/ 資料夾)
    stock_code = "2330"
    db_path = os.path.join("data", "kbars_cache.db")
    db_cache = LocalDataCache(db_path=db_path)
    df_kbars = db_cache.load_kbars(code=stock_code)

    if df_kbars.empty or len(df_kbars) < 150:
        print(f"[步驟 1/5] 本機 DB 快取無資料，啟動 Shioaji API 下載 [{stock_code}] 一年歷史 K 線...")
        simulation_env = os.getenv("SIMULATION", "True").lower() == "true"
        client = ShioajiClient(simulation=simulation_env)
        if client.login():
            df_kbars = client.get_daily_kbars(code=stock_code, days=365)
            db_cache.save_kbars(code=stock_code, df=df_kbars)
            client.logout()
        else:
            print(" API 登入失敗，使用預設生成數據...")
            df_kbars = client._generate_mock_kbars(code=stock_code, days=240)
    else:
        print(f"[步驟 1/5] 成功自本機 SQLite 快取數據庫加載 [{stock_code}] 共 {len(df_kbars)} 筆日 K 線！")

    print("-" * 65)
    print(f"資料筆數：{len(df_kbars)} 筆 | 日期範圍：{df_kbars['ts'].dt.strftime('%Y-%m-%d').iloc[0]} ~ {df_kbars['ts'].dt.strftime('%Y-%m-%d').iloc[-1]}")
    print("-" * 65)

    # 2. 多技術指標策略比較 (SMA, RSI, MACD, Bollinger Bands, KD)
    print(f"\n[步驟 2/5] 執行多指標策略歷史績效大比拼...")
    strategies = [
        SMACrossStrategy(short_window=5, long_window=10),
        RSIStrategy(period=14, oversold=35, overbought=65),
        MACDStrategy(fast_period=12, slow_period=26, signal_period=9),
        BollingerBandsStrategy(period=20, std_dev=2.0),
        KDStrategy(period=9)
    ]

    engine = BacktestEngine(initial_capital=3_000_000.0)
    summary_list = []

    for strat in strategies:
        res = engine.run(df=df_kbars, strategy=strat)
        metrics = PerformanceEvaluator.evaluate(res)
        summary_list.append(metrics)

    summary_df = pd.DataFrame(summary_list)
    print("\n【多策略績效總表比較 (含資金變化)】")
    print(summary_df[["策略名稱", "初始資金 (TWD)", "期末資產 (TWD)", "總報酬率 (%)", "最大回撤 MDD (%)", "夏普比率 (Sharpe)", "總交易次數", "交易勝率 (%)"]].to_string(index=False))

    # 3. 風控機制示範 (加入 5% 停損與 15% 停利)
    print(f"\n[步驟 3/5] 風控機制測試 (5MA/10MA 策略 + 5% 停損 / 15% 停利)...")
    risk_engine = BacktestEngine(
        initial_capital=3_000_000.0,
        stop_loss_pct=0.05,    # 5% 強制停損
        take_profit_pct=0.15   # 15% 強制停利
    )
    best_strat = SMACrossStrategy(short_window=5, long_window=10)
    risk_res = risk_engine.run(df=df_kbars, strategy=best_strat)
    risk_metrics = PerformanceEvaluator.evaluate(risk_res)
    PerformanceEvaluator.print_summary(risk_metrics)

    # 4. 繪製並儲存 K 線與 Equity Curve 走勢圖 (儲存於 output/ 資料夾)
    print(f"[步驟 4/5] 繪製並輸出 2330 策略買賣點與權益資產走勢圖...")
    plot_path = os.path.join("output", "2330_strategy_equity_curve.png")
    BacktestPlotter.plot(result=risk_res, save_path=plot_path)

    # 5. 網格搜尋 (Grid Search) 均線參數最佳化
    print(f"\n[步驟 5/5] 執行 5MA / 20MA ~ 60MA 均線組合網格搜尋最佳化...")
    optimizer = GridSearchOptimizer(df=df_kbars, initial_capital=3_000_000.0)
    short_range = [3, 5, 8, 10]
    long_range = [15, 20, 30, 40, 60]
    opt_results = optimizer.optimize_sma(short_range=short_range, long_range=long_range)

    print("\n【均線參數最佳化排行榜 (Top 5)】")
    print(opt_results.head(5).to_string(index=False))

    print("\n Phase 2 全功能示範成功完成！")

if __name__ == "__main__":
    main()
