# Backtesting module init
from .strategy import (
    BaseStrategy,
    SMACrossStrategy,
    MAAlignmentStrategy,
    RSIStrategy,
    MACDStrategy,
    BollingerBandsStrategy,
    BollingerSqueezeStrategy,
    KDStrategy,
    DualKDRSIStrategy
)
from .engine import BacktestEngine
from .evaluator import PerformanceEvaluator

__all__ = [
    "BaseStrategy",
    "SMACrossStrategy",
    "MAAlignmentStrategy",
    "RSIStrategy",
    "MACDStrategy",
    "BollingerBandsStrategy",
    "BollingerSqueezeStrategy",
    "KDStrategy",
    "DualKDRSIStrategy",
    "BacktestEngine",
    "PerformanceEvaluator"
]
