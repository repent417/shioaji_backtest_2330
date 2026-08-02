"""
Taiwan Stock Backtest Engine with Smart Risk Controls (Solution 1: Wait for new signal after risk exit)
考量台股交易成本與主動風控（停損/停利離場後需等待全新指標買訊才可再次進場）
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from .strategy import BaseStrategy

class BacktestEngine:
    def __init__(
        self,
        initial_capital: float = 3_000_000.0,
        commission_rate: float = 0.001425,
        discount: float = 0.6,          # 手續費 6 折
        min_commission: float = 20.0,
        tax_rate: float = 0.003,        # 賣出證交稅 0.3%
        shares_per_lot: int = 1000,
        stop_loss_pct: Optional[float] = None,   # 停損百分比 (例如 0.05 代表 -5%)
        take_profit_pct: Optional[float] = None  # 停利百分比 (例如 0.15 代表 +15%)
    ):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.discount = discount
        self.min_commission = min_commission
        self.tax_rate = tax_rate
        self.shares_per_lot = shares_per_lot
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    def run(self, df: pd.DataFrame, strategy: BaseStrategy) -> Dict[str, Any]:
        data = strategy.generate_signals(df)
        
        cash = self.initial_capital
        position_shares = 0
        entry_price = 0.0
        portfolio_records = []
        trade_logs = []
        force_exit = False
        exit_reason = ""
        risk_exited = False  # 標記是否因為停損/停利離場 (需等待新買訊重置)

        for i, row in data.iterrows():
            date = row["ts"]
            close_price = row["close"]
            open_price = row["open"]
            raw_signal = row.get("signal", 0)  # 當天未 shift 的指標訊號 (0 或 1)

            # 當指標訊號歸零 (如均線死亡交叉離場) 時，重置風控鎖定狀態
            if raw_signal == 0:
                risk_exited = False

            target_signal = row["position"]  # 前一日 signal 轉移而來的目標部位

            # 1. 處理上一日觸發之風控離場 (STOP_LOSS / TAKE_PROFIT)
            if force_exit and position_shares > 0:
                sell_shares = position_shares
                sell_val = sell_shares * open_price
                comm = max(self.min_commission, sell_val * self.commission_rate * self.discount)
                tax = sell_val * self.tax_rate
                net_revenue = sell_val - comm - tax

                cash += net_revenue
                trade_logs.append({
                    "date": date,
                    "action": "SELL (RISK)",
                    "price": open_price,
                    "shares": sell_shares,
                    "amount": sell_val,
                    "fee": comm,
                    "tax": tax,
                    "reason": exit_reason
                })
                position_shares = 0
                entry_price = 0.0
                force_exit = False
                risk_exited = True  # 鎖定離場狀態，在舊趨勢結束前禁止再次買入

            # 2. 正常買賣處理
            # 若處於 risk_exited 鎖定狀態，無視舊趨勢訊號，禁止買進
            effective_target_signal = 0 if risk_exited else target_signal
            current_target_shares = effective_target_signal * self.shares_per_lot
            share_diff = current_target_shares - position_shares

            if share_diff > 0 and position_shares == 0:
                # 買進 (Buy)
                desired_shares = share_diff
                raw_buy_cost = desired_shares * open_price
                raw_comm = max(self.min_commission, raw_buy_cost * self.commission_rate * self.discount)
                
                if cash < (raw_buy_cost + raw_comm):
                    affordable_shares = int((cash - self.min_commission) / (open_price * (1 + self.commission_rate * self.discount)))
                    actual_shares = max(0, (affordable_shares // 10) * 10)
                else:
                    actual_shares = desired_shares

                if actual_shares > 0:
                    buy_cost = actual_shares * open_price
                    comm = max(self.min_commission, buy_cost * self.commission_rate * self.discount)
                    total_spend = buy_cost + comm

                    cash -= total_spend
                    position_shares += actual_shares
                    entry_price = open_price
                    trade_logs.append({
                        "date": date,
                        "action": "BUY",
                        "price": open_price,
                        "shares": actual_shares,
                        "amount": buy_cost,
                        "fee": comm,
                        "tax": 0.0,
                        "reason": "SIGNAL"
                    })
            elif share_diff < 0 and position_shares > 0:
                # 指標正常平倉賣出 (Sell)
                sell_shares = position_shares
                sell_val = sell_shares * open_price
                comm = max(self.min_commission, sell_val * self.commission_rate * self.discount)
                tax = sell_val * self.tax_rate
                net_revenue = sell_val - comm - tax

                cash += net_revenue
                position_shares = 0
                entry_price = 0.0
                trade_logs.append({
                    "date": date,
                    "action": "SELL",
                    "price": open_price,
                    "shares": sell_shares,
                    "amount": sell_val,
                    "fee": comm,
                    "tax": tax,
                    "reason": "SIGNAL"
                })

            # 3. 盤後檢視是否觸發停損停利 (提供下一個交易日開盤離場)
            if position_shares > 0 and entry_price > 0:
                current_pnl_pct = (close_price - entry_price) / entry_price
                if self.stop_loss_pct and self.stop_loss_pct > 0 and current_pnl_pct <= -abs(self.stop_loss_pct):
                    force_exit = True
                    exit_reason = f"STOP_LOSS ({current_pnl_pct*100:.1f}%)"
                elif self.take_profit_pct and self.take_profit_pct > 0 and current_pnl_pct >= abs(self.take_profit_pct):
                    force_exit = True
                    exit_reason = f"TAKE_PROFIT (+{current_pnl_pct*100:.1f}%)"

            # 4. 紀錄資產
            equity = cash + (position_shares * close_price)
            portfolio_records.append({
                "ts": date,
                "open": open_price,
                "high": row["high"] if "high" in row else open_price,
                "low": row["low"] if "low" in row else open_price,
                "close": close_price,
                "volume": row.get("volume", 0),
                "cash": cash,
                "position_shares": position_shares,
                "stock_value": position_shares * close_price,
                "total_equity": equity,
                "signal": row.get("signal", 0)
            })

        portfolio_df = pd.DataFrame(portfolio_records)
        
        # 保留指標欄位
        indicator_cols = [col for col in data.columns if col not in portfolio_df.columns and col not in ["ts", "open", "high", "low", "close", "volume", "position"]]
        for col in indicator_cols:
            portfolio_df[col] = data[col].values

        portfolio_df["daily_return"] = portfolio_df["total_equity"].pct_change().fillna(0)
        portfolio_df["cum_return"] = (portfolio_df["total_equity"] / self.initial_capital) - 1.0

        return {
            "strategy_name": strategy.name,
            "portfolio": portfolio_df,
            "trades": pd.DataFrame(trade_logs),
            "initial_capital": self.initial_capital,
            "final_equity": portfolio_df["total_equity"].iloc[-1] if not portfolio_df.empty else self.initial_capital
        }
