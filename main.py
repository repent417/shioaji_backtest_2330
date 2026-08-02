"""
Shioaji API 登入、抓取 2330 台積電 30 日日 K 線與雙均線策略回測主程式
"""
import os
import pandas as pd
from dotenv import load_dotenv
from src.client import ShioajiClient
from src.backtest import BaseStrategy, SMACrossStrategy, BacktestEngine, PerformanceEvaluator

def main():
    print("="*60)
    print("  Shioaji API 2330 1年 K 線抓取 & 5MA/10MA 短期均線策略回測")
    print("="*60)

    # 1. 初始化 Shioaji 客戶端並嘗試登入
    simulation_env = os.getenv("SIMULATION", "True").lower() == "true"
    client = ShioajiClient(simulation=simulation_env)
    
    logged_in = client.login()
    if logged_in:
        print(" [系統訊息] 永豐金 Shioaji API 登入成功！")
    else:
        print(" [系統訊息] API 登入未完成，使用 Mock 行情數據進行功能演練。")

    # 2. 抓取 2330 台積電近 365 天 (一年) 日 K 線
    stock_code = "2330"
    days_count = 365
    print(f"\n[步驟 1/3] 正在取得 [{stock_code}] 近 {days_count} 天 (1年) 日 K 線資料...")
    
    df_kbars = client.get_daily_kbars(code=stock_code, days=days_count)

    print(f"\n成功取得 [{stock_code}] 一年日 K 線數據共 {len(df_kbars)} 筆 (展示前後 5 筆)：")
    print("-" * 60)
    df_display = df_kbars.copy()
    df_display["ts"] = df_display["ts"].dt.strftime("%Y-%m-%d")
    print(pd.concat([df_display.head(5), df_display.tail(5)]).to_string(index=False))
    print("-" * 60)

    # 3. 執行 5MA / 10MA 短期均線策略回測
    print(f"\n[步驟 2/3] 帶入 5MA / 10MA 短期均線策略回測引擎...")
    strategy = SMACrossStrategy(short_window=5, long_window=10)
    engine = BacktestEngine(
        initial_capital=3_000_000.0,
        commission_rate=0.001425,
        discount=0.6,
        tax_rate=0.003
    )

    result = engine.run(df=df_kbars, strategy=strategy)

    # 4. 輸出回測報告
    print(f"\n[步驟 3/3] 計算策略一年歷史績效指標...")
    metrics = PerformanceEvaluator.evaluate(result)
    PerformanceEvaluator.print_summary(metrics)

    # 若有交易明細，印出交易紀錄
    trades_df = result["trades"]
    if not trades_df.empty:
        print("【交易紀錄彙整 (Trade Logs)】")
        trades_display = trades_df.copy()
        trades_display["date"] = trades_display["date"].dt.strftime("%Y-%m-%d")
        print(trades_display.to_string(index=False))
    else:
        print("【交易紀錄彙整】近 30 日尚未觸發買賣交叉交易點。")

    # 5. 安全登出
    client.logout()
    print("\n執行完成！")

if __name__ == "__main__":
    main()
