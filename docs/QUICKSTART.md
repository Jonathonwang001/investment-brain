---
title: Investment Brain 使用手册
source: custom
created: 2026-04-13
tags: [investment-brain, manual, guide, quickstart]
status: current
---

# Investment Brain 使用手册

## 快速开始

### 1. 完整分析（推荐）

```python
from investment_brain.agents import (
    ValuationAgent, FundamentalsAgent, TechnicalsAgent,
    SentimentAgent, RiskManager, PortfolioManager
)

ticker = "NVDA"

# 调用各大脑
signals = {
    "ValuationAgent":     ValuationAgent().analyze(ticker),
    "FundamentalsAgent":  FundamentalsAgent().analyze(ticker),
    "TechnicalsAgent":    TechnicalsAgent().analyze(ticker),
    "SentimentAgent":     SentimentAgent().analyze(ticker),
    "RiskManager":        RiskManager().analyze(ticker),
}

# PortfolioManager 汇总
decision = PortfolioManager().analyze(ticker, signals)
print(decision.action)       # BUY / HOLD / SELL
print(decision.position_size)  # 0.25 (= 25%)
print(decision.stop_loss)    # 止损价
```

### 2. 单标的快速参考

```bash
cd ~/.qclaw/workspace/skills/investment-brain/agents
python3 valuation_agent.py NVDA --json
python3 technicals_agent.py NVDA --period 1y --json
```

### 3. 批量分析

```python
tickers = ["NVDA", "TSLA", "AAPL"]
results = {}

for t in tickers:
    va = ValuationAgent().analyze(t)
    results[t] = va

# 输出汇总
agent = ValuationAgent()
agent.summary(results)
```

## 信号含义

| 信号 | 含义 | PortfolioManager 操作 |
|------|------|----------------------|
| BULLISH | 强烈看多 | BUY |
| SLIGHTLY_BULLISH | 偏看多 | ACCUMULATE |
| NEUTRAL | 中性 | HOLD |
| SLIGHTLY_BEARISH | 偏看空 | REDUCE |
| BEARISH | 强烈看空 | SELL |

## 数据源

| 市场 | 首选 | 备选 |
|------|------|------|
| 美股 | yfinance | Finnhub（需代理） |
| A股/港股 | AKShare | — |
| 宏观情绪 | yfinance (^VIX, ^SPX) | — |

## 定时任务集成

在 cron 任务中使用：

```python
from investment_brain.agents import ValuationAgent, PortfolioManager

def run_morning_analysis(ticker):
    signals = {
        "ValuationAgent": ValuationAgent().analyze(ticker),
        # ... 其他大脑
    }
    return PortfolioManager().analyze(ticker, signals)
```

详见：`standards/specs/investment-weekly-review-spec.md`
