"""
Taiwan Stock Backtest Engine with Two-Step Trailing Stop & High-Breakout Re-entry
支援台股交易成本、目標停利達標後啟動高點拉回 X% 移動停利 (Two-Step Trailing Stop) 與 突破前高重新接回機制
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
        stop_loss_pct: Optional[float] = None,      # 硬停損 (例如 0.05 代表 -5%)
        take_profit_pct: Optional[float] = None,    # 目標獲利門檻 (例如 0.15 代表 +15% 達標後啟動高點追蹤)
        trailing_stop_pct: Optional[float] = None,  # 啟動高點追蹤後之拉回趴數 (例如 0.05 代表拉回 5%)
        enable_reentry: bool = False                # 停利後突破前高是否重新接回
    ):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.discount = discount
        self.min_commission = min_commission
        self.tax_rate = tax_rate
        self.shares_per_lot = shares_per_lot
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.enable_reentry = enable_reentry

    def run(self, df: pd.DataFrame, strategy: BaseStrategy) -> Dict[str, Any]:
        data = strategy.generate_signals(df)
        
        cash = self.initial_capital
        position_shares = 0
        entry_price = 0.0
        highest_price_since_entry = 0.0
        trailing_active = False          # 是否已達到目標獲利門檻並激活高點追蹤
        last_peak_price = 0.0            # 紀錄停利離場時的高點
        reentry_triggered = False        # 標記突破前高觸發接回

        portfolio_records = []
        trade_logs = []
        force_exit = False
        exit_reason = ""
        risk_exited = False

        for i, row in data.iterrows():
            date = row["ts"]
            close_price = row["close"]
            open_price = row["open"]
            high_price = row.get("high", close_price)
            raw_signal = row.get("signal", 0)  # 指標訊號 (0 或 1)

            # 當指標訊號歸零 (如均線死亡交叉離場) 時，重置風控鎖定狀態與前高紀錄
            if raw_signal == 0:
                risk_exited = False
                last_peak_price = 0.0

            target_signal = row["position"]

            # 1. 檢查目標獲利門檻，達標後激活高點追蹤 (Two-step Trailing Activation)
            if position_shares > 0 and entry_price > 0:
                current_high_gain_pct = (high_price - entry_price) / entry_price
                
                # 若未設定目標停利，預設一進場即激活；若有設定，需最高價收益達標才激活
                if self.take_profit_pct is None or self.take_profit_pct <= 0 or current_high_gain_pct >= abs(self.take_profit_pct):
                    trailing_active = True

                if trailing_active:
                    highest_price_since_entry = max(highest_price_since_entry, high_price)

            # 2. 處理上一日觸發之風控離場 (STOP_LOSS / TRAILING_STOP)
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
                highest_price_since_entry = 0.0
                trailing_active = False
                force_exit = False
                risk_exited = True  # 鎖定離場狀態

            # 3. 處理突破前高重新接回 (Breakout Re-entry)
            if reentry_triggered and position_shares == 0 and cash >= (open_price * self.shares_per_lot):
                buy_shares = self.shares_per_lot
                buy_cost = buy_shares * open_price
                comm = max(self.min_commission, buy_cost * self.commission_rate * self.discount)
                total_spend = buy_cost + comm

                cash -= total_spend
                position_shares = buy_shares
                entry_price = open_price
                highest_price_since_entry = open_price
                trailing_active = False
                risk_exited = False
                reentry_triggered = False
                
                trade_logs.append({
                    "date": date,
                    "action": "BUY (RE-ENTRY)",
                    "price": open_price,
                    "shares": buy_shares,
                    "amount": buy_cost,
                    "fee": comm,
                    "tax": 0.0,
                    "reason": f"BREAKOUT ({last_peak_price:.1f})"
                })

            # 4. 正常買賣處理
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
                    highest_price_since_entry = open_price
                    trailing_active = False
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
                highest_price_since_entry = 0.0
                trailing_active = False
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

            # 5. 盤後風控檢視：硬停損與 (達標後激活的) 移動停利 (Trailing Stop)
            if position_shares > 0 and entry_price > 0:
                current_pnl_pct = (close_price - entry_price) / entry_price
                
                # 硬停損檢視
                if self.stop_loss_pct and self.stop_loss_pct > 0 and current_pnl_pct <= -abs(self.stop_loss_pct):
                    force_exit = True
                    exit_reason = f"STOP_LOSS ({current_pnl_pct*100:.1f}%)"
                # 高點拉回移動停利檢視 (僅在達到目標獲利 take_profit_pct 且已激活時處置)
                elif trailing_active and self.trailing_stop_pct and self.trailing_stop_pct > 0 and highest_price_since_entry > 0:
                    pullback_pct = (highest_price_since_entry - close_price) / highest_price_since_entry
                    if pullback_pct >= abs(self.trailing_stop_pct):
                        force_exit = True
                        last_peak_price = highest_price_since_entry
                        exit_reason = f"TRAILING_STOP (Peak:{highest_price_since_entry:.1f}, Pullback:-{pullback_pct*100:.1f}%)"

            # 6. 檢視離場後是否突破前高準備接回 (Breakout Check)
            if position_shares == 0 and self.enable_reentry and last_peak_price > 0:
                if close_price > last_peak_price:
                    reentry_triggered = True

            # 7. 紀錄每日資產
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
