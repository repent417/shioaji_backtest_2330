"""
Shioaji Client Wrapper
提供永豐金 Shioaji API 的登入、合約查詢、日 K 線抓取與 Dataframe 轉換功能。
"""
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import shioaji as sj

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class ShioajiClient:
    def __init__(self, simulation: bool = True):
        load_dotenv()
        self.simulation = simulation
        self.api_key = os.getenv("API_KEY", "")
        self.secret_key = os.getenv("SECRET_KEY", "")
        self.api = None
        self.is_logged_in = False

    def login(self) -> bool:
        """執行 Shioaji API 登入"""
        try:
            logger.info(f"正在初始化 Shioaji API (simulation={self.simulation})...")
            self.api = sj.Shioaji(simulation=self.simulation)
            
            if not self.api_key or not self.secret_key or self.api_key == "YOUR_API_KEY":
                logger.warning("未偵測到有效的 API_KEY 或 SECRET_KEY，無法完成線上 API 登入。")
                return False

            accounts = self.api.login(
                api_key=self.api_key,
                secret_key=self.secret_key
            )
            logger.info(f"登入成功！可用帳戶：{accounts}")
            self.is_logged_in = True
            
            # 若有 CA 憑證，嘗試啟用 (正式下單才強制需要)
            ca_path = os.getenv("CA_CERT_PATH", "")
            ca_passwd = os.getenv("CA_PASSWORD", "")
            if ca_path and ca_passwd and os.path.exists(ca_path):
                try:
                    self.api.activate_ca(ca_path=ca_path, ca_passwd=ca_passwd)
                    logger.info("CA 憑證啟用成功。")
                except Exception as ca_err:
                    logger.warning(f"CA 憑證啟用失敗 (一般行情查詢不影響): {ca_err}")

            return True

        except Exception as e:
            logger.error(f"Shioaji 登入發生例外: {e}")
            self.is_logged_in = False
            return False

    def get_daily_kbars(self, code: str = "2330", days: int = 365) -> pd.DataFrame:
        """
        抓取指定股票代碼 (預設 2330 台積電) 的日 K 線資料。
        :param code: 股票代號 (如 '2330')
        :param days: 欲抓取的日曆天數 (預設 365 天 / 一年)
        :return: pandas DataFrame (包含 ts, open, high, low, close, volume)
        """
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)

        if self.is_logged_in and self.api:
            try:
                logger.info(f"嘗試自 Shioaji API 分段下載 [{code}] 近 {days} 天 K 線 ({start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')})...")
                contract = self.api.Contracts.Stocks.get(code) or self.api.Contracts.Stocks[code]

                if contract:
                    df_list = []
                    curr_start = start_dt
                    # 每 27 天為一個區間以符合 Shioaji 30天上限
                    while curr_start < end_dt:
                        curr_end = min(curr_start + timedelta(days=27), end_dt)
                        s_str = curr_start.strftime("%Y-%m-%d")
                        e_str = curr_end.strftime("%Y-%m-%d")
                        
                        try:
                            kbars = self.api.kbars(
                                contract=contract,
                                start=s_str,
                                end=e_str
                            )
                            sub_df = pd.DataFrame({**kbars})
                            if not sub_df.empty:
                                df_list.append(sub_df)
                        except Exception as chunk_err:
                            logger.warning(f"下載區間 {s_str} ~ {e_str} 失敗或無資料: {chunk_err}")
                        
                        curr_start = curr_end + timedelta(days=1)

                    if df_list:
                        full_df = pd.concat(df_list, ignore_index=True)
                        full_df["ts"] = pd.to_datetime(full_df["ts"])
                        full_df.drop_duplicates(subset=["ts"], inplace=True)
                        full_df.sort_values("ts", inplace=True)

                        # 欄位統一小寫
                        rename_dict = {col: col.lower() for col in full_df.columns}
                        full_df.rename(columns=rename_dict, inplace=True)
                        
                        # 按日期 (Date) 聚合轉為日 K 線
                        full_df["date"] = full_df["ts"].dt.date
                        daily_df = full_df.groupby("date").agg({
                            "open": "first",
                            "high": "max",
                            "low": "min",
                            "close": "last",
                            "volume": "sum"
                        }).reset_index()
                        
                        daily_df.rename(columns={"date": "ts"}, inplace=True)
                        daily_df["ts"] = pd.to_datetime(daily_df["ts"])
                        
                        logger.info(f"成功自線上 API 取得 [{code}] 歷史日 K 線數據 {len(daily_df)} 筆。")
                        return daily_df
                    else:
                        logger.warning("Shioaji API 回傳之 K 線資料為空。")
                else:
                    logger.error(f"無法取得合約 [{code}]。")
            except Exception as e:
                logger.error(f"自 API 下載 K 線失敗: {e}")

        logger.info("切換至模擬生成樣本資料 (Mock Data Mode) 以供測試...")
        return self._generate_mock_kbars(code=code, days=days)

    def _generate_mock_kbars(self, code: str, days: int) -> pd.DataFrame:
        """生成逼真的台積電 2330 日 K 線模擬數據 (供本機離線與無金鑰狀態測試)"""
        np.random.seed(2330)
        end_date = datetime.now()
        dates = pd.date_range(end=end_date, periods=days, freq="B")
        actual_days = len(dates)
        
        base_price = 980.0
        returns = np.random.normal(0.001, 0.015, actual_days)
        prices = base_price * np.exp(np.cumsum(returns))
        
        opens = prices * (1 + np.random.uniform(-0.005, 0.005, actual_days))
        highs = np.maximum(prices, opens) * (1 + np.random.uniform(0.001, 0.012, actual_days))
        lows = np.minimum(prices, opens) * (1 - np.random.uniform(0.001, 0.012, actual_days))
        closes = prices
        volumes = np.random.randint(15000, 45000, actual_days) # 張量/千股

        df = pd.DataFrame({
            "ts": dates,
            "open": np.round(opens, 1),
            "high": np.round(highs, 1),
            "low": np.round(lows, 1),
            "close": np.round(closes, 1),
            "volume": volumes
        })
        return df

    def logout(self):
        """登出 API"""
        if self.is_logged_in and self.api:
            try:
                self.api.logout()
                logger.info("Shioaji API 已安全登出。")
            except Exception as e:
                logger.warning(f"登出時發生例外: {e}")
            finally:
                self.is_logged_in = False
