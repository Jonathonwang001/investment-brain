"""
investment-brain: 沐沐投资大脑 — 六大脑联网决策系统
==================================================
每个 Agent 独立可运行，最终由 PortfolioManager 汇总。

Agent 架构：
  ValuationAgent     → 计算内在价值，生成估值交易信号
  FundamentalsAgent → 解读财务数据，生成基本面信号
  TechnicalsAgent    → 分析技术指标，捕捉趋势与动量
  SentimentAgent    → 追踪市场情绪，量化多空博弈
  RiskManager       → 测算风险敞口，设定仓位上限
  PortfolioManager  → 汇总所有信号，拍板最终交易决策
"""

from .valuation_agent import ValuationAgent
from .fundamentals_agent import FundamentalsAgent
from .technicals_agent import TechnicalsAgent
from .sentiment_agent import SentimentAgent
from .risk_manager import RiskManager
from .portfolio_manager import PortfolioManager

__all__ = [
    "ValuationAgent",
    "FundamentalsAgent", 
    "TechnicalsAgent",
    "SentimentAgent",
    "RiskManager",
    "PortfolioManager",
]
