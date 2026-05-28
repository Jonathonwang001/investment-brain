---
title: Investment Brain - 六大脑联网决策系统（含完整方法论）
version: v2.0.0 精准深化版（2026-04-15）
description: 六个专业 Agent 联网分析 + PortfolioManager 汇总决策，覆盖估值/基本面/技术面/情绪/风险。每一个信号都包含：完整方法论 + 分步计算推导 + 公式 + 关键假设。
source: custom
created: 2026-04-13
updated: 2026-04-13
tags: [investment-brain, six-agents, methodology, permanent, valuation, fundamentals, technicals, sentiment, risk, portfolio]
status: current
---

# Investment Brain - 六大脑联网决策系统

> **Skill 位置**: `~/.qclaw/workspace/skills/investment-brain/`
> **版本**: V2.0 沐沐定制版（含完整方法论）
> **状态**: 活跃

---

## 🧠 系统架构

```
PortfolioManager（决策大脑）
    ↑ 汇总
    ├── ValuationAgent     → DCF/DDM/PE Band → 内在价值（30%权重）
    ├── FundamentalsAgent  → ROE/ROIC/FCF    → 财务质量（25%权重）
    ├── TechnicalsAgent    → MACD/RSI/KDJ    → 技术趋势（20%权重）
    ├── SentimentAgent    → VIX/Fear&Greed  → 市场情绪（15%权重）
    └── RiskManager       → VaR/止损/仓位   → 风险控制（10%权重）
```

---

## 🔬 核心创新：完整方法论输出

**每个 AgentSignal 现在都包含 4 个方法论字段**：

| 字段 | 类型 | 内容 |
|------|------|------|
| `methodology` | str | 方法论完整说明 |
| `step_by_step` | List[Dict] | 分步计算，每步含：step/formula/input/output |
| `formulas` | List[str] | 所有使用的公式 |
| `assumptions` | List[str] | 关键假设 |

**调用 `.full_report()` 方法可生成完整推导报告**：

```python
result = ValuationAgent().analyze("NVDA")
print(result.full_report())  # 输出完整推导过程
```

---

## 📊 ValuationAgent — 估值大脑

### 方法论
综合6种估值方法论，取去掉最高最低后的中间均值作为内在价值。

### 6种方法适用场景

| 方法 | 公式 | 适用场景 |
|------|------|---------|
| **DCF** | `V = Σ(FCFF_t/(1+WACC)^t) + TV/(1+WACC)^n` | 盈利稳定的成熟公司（NVDA、MSFT、BRK）|
| **DDM** | `V = D₁ / (WACC - g)` | 高分红蓝筹（JNJ、PG、可乐）|
| **PE Band** | `V = Mean(PE_hist) × Forward EPS` | 快速参考大盘股（SPY、AAPL）|
| **EV/EBITDA** | `V = (EBITDA × 合理倍数 - 净债务) / 股数` | 周期股/重资产（XOM、JPM）|
| **PEG** | `V = (增长率 × 0.8) × Forward EPS` | 成长股（TSLA、PLTR）|
| **PB** | `V = BVPS × 合理PB倍数` | 金融/地产/保险（BRK、JPM）|

### 信号逻辑

```
显著低估（margin < -20%） → BULLISH
略低估（margin < -5%）   → SLIGHTLY_BULLISH
合理区间（|margin| ≤ 10%） → NEUTRAL
略高估（margin > 5%）    → SLIGHTLY_BEARISH
显著高估（margin > 20%） → BEARISH
```

### 分步推导示例（DCF）

```
Step 1 — 确定 FCFF
  公式: FCFF = free_cash_flow
  输入: FCFF = $58,128,998,400
  输出: FCFF = $58.1B

Step 2 — 5年 FCF 预测（g=40%）
  公式: FCF_t = FCF_0 × (1+g)^t
  输出:
    t=1: FCF=$81.4B → 折现=$75.0B
    t=2: FCF=$113.9B → 折现=$96.8B
    ...

Step 3 — 终值计算（Gordon Growth Model）
  公式: TV = FCF_n × (1+g) / (WACC - g)
  输出: TV=$5.34T → 折现TV=$3.55T

Step 4 — 企业价值 → 每股价值
  公式: EV = Σ(FCF折现) + PV(TV)
  输出: 每股 DCF = $140.70
```

---

## 📊 FundamentalsAgent — 基本面大脑

### 方法论
14维度综合评分（100分制）：
- 盈利能力（30分）：ROE + ROA + ROIC + 毛利率 + 净利率
- 成长性（20分）：营收增速 + 盈利增速
- 财务健康（20分）：负债率 + FCF yield
- 估值支撑（15分）：分析师评级 + 目标价
- 股息安全（15分）：股息率 + 分红率

### 核心公式

| 指标 | 公式 | 优秀标准 |
|------|------|---------|
| ROE | `净利润 / 股东权益 × 100%` | >25%（巴菲特标准）|
| 毛利率 | `毛利润 / 营收 × 100%` | >40% |
| 净利率 | `净利润 / 营收 × 100%` | >15% |
| 负债率 | `总债务 / 股东权益` | <50% |
| FCF Yield | `FCF / 市值 × 100%` | >5% |

### 信号逻辑

| 得分 | 信号 |
|------|------|
| ≥ 75 | BULLISH |
| 55-75 | SLIGHTLY_BULLISH |
| 45-55 | NEUTRAL |
| 30-45 | SLIGHTLY_BEARISH |
| < 30 | BEARISH |

---

## 📈 TechnicalsAgent — 技术面大脑

### 方法论
4维度综合评分（100分制）：
- 趋势（30分）：价格 vs MA200 + MA 多头排列
- 动量（40分）：RSI + MACD + Stochastic
- 相对强弱（20分）：52周位置 + 布林带
- 量价（10分）：成交量比率

### 核心公式

```python
RSI(14) = 100 - 100/(1 + RS), RS = AvgGain(14) / AvgLoss(14)

MACD = EMA(close, 12) - EMA(close, 26)
Signal = EMA(MACD, 9)
Histogram = MACD - Signal

布林带上轨 = MA20 + 2×σ
布林带下轨 = MA20 - 2×σ

ATR(14) = MA(TR, 14)
TR = max(H-L, |H-PC|, |L-PC|)

Stochastic %K = 100×(C-L14)/(H14-L14)
```

### 信号逻辑

| 得分 | 信号 |
|------|------|
| ≥ 65 | BULLISH |
| 50-65 | SLIGHTLY_BULLISH |
| 35-50 | NEUTRAL |
| 20-35 | SLIGHTLY_BEARISH |
| < 20 | BEARISH |

---

## 🌡️ SentimentAgent — 情绪大脑

### 方法论
宏观情绪 + 个股情绪双模式：
- VIX > 30 → 极度恐慌（逆向买入信号）
- VIX < 15 → 极度贪婪（逆向卖出信号）
- Fear & Greed Index < 20 → 逆向买入
- 分析师 Buy%+ > Sell%+ → 看多信号

---

## ⚠️ RiskManager — 风险大脑

### 方法论

```python
VaR(95%) = 波动率 × 1.65    # 95% 置信度最大损失
CVaR(95%) = 波动率 × 2.33   # 极端损失平均值

止损 = max(VaR×1.5, ATR止损, 5%)，最小5%，最大25%

最大仓位 = 基础20% × vol_factor × beta_factor
  vol_factor = max(0.3, 1.5 - vol×3)
  beta_factor = max(0.3, 1.5 - beta×0.5)
```

### 信号逻辑

| 风险评分 | 级别 | 仓位建议 |
|---------|------|---------|
| < 25 | 低风险 | 满仓 |
| 25-50 | 中等风险 | 分批建仓 |
| 50-75 | 高风险 | 严格止损 |
| > 75 | 极高风险 | ≤5% 或回避 |

---

## 🎯 PortfolioManager — 决策大脑

### 权重配置（可调整）

| Agent | 权重 | 理由 |
|-------|------|------|
| ValuationAgent | 30% | 内在价值是安全边际的锚 |
| FundamentalsAgent | 25% | 盈利质量是长期驱动力 |
| TechnicalsAgent | 20% | 择时是短期催化剂 |
| SentimentAgent | 15% | 逆向思维是超额收益来源 |
| RiskManager | 10% | 控制下行是生存之道 |

### 算法

```python
信号分 = {"BULLISH": 100, "SLIGHTLY_BULLISH": 75,
          "NEUTRAL": 50, "SLIGHTLY_BEARISH": 25, "BEARISH": 0}

加权得分 = Σ(信号分 × 权重)
综合得分 → 操作：
  ≥70 → BUY（建仓/加仓）
  55-70 → ACCUMULATE（逐步建仓）
  45-55 → HOLD（观望）
  30-45 → REDUCE（减仓）
  <30 → SELL（清仓）
```

**分歧自动降置信**：一致性低（2:3分歧）→ 置信度 × 0.7

---

## ⚙️ 使用方式

### 方式1：完整六大脑 + 方法论
```python
from investment_brain.agents import (
    ValuationAgent, FundamentalsAgent, TechnicalsAgent,
    SentimentAgent, RiskManager, PortfolioManager
)

ticker = "NVDA"
signals = {
    "ValuationAgent":     ValuationAgent().analyze(ticker),
    "FundamentalsAgent":  FundamentalsAgent().analyze(ticker),
    "TechnicalsAgent":    TechnicalsAgent().analyze(ticker),
    "SentimentAgent":    SentimentAgent().analyze(ticker),
    "RiskManager":       RiskManager().analyze(ticker),
}
decision = PortfolioManager().analyze(ticker, signals)

# 输出完整方法论报告
for name, sig in signals.items():
    print(sig.full_report())
    print()
```

### 方式2：单 Agent + 方法论
```bash
cd ~/.qclaw/workspace/skills/investment-brain/agents
python3 valuation_agent.py NVDA --json  # 包含分步推导
python3 fundamentals_agent.py NVDA --json
python3 technicals_agent.py NVDA --period 1y --json
```

---

## ⚠️ 使用规范（铁律5）

1. **数据源优先级**：yfinance（美股）> AKShare（A股）> Finnhub（新闻，需代理）
2. **代理规则**：Finnhub → `http_proxy=http://127.0.0.1:1082`
3. **置信度调整**：信号分歧时自动降低置信度
4. **止损永远存在**：即使信号看多，也必须有止损建议
5. **仓位上限**：RiskManager 自动限制 ≤ 20%
6. **方法论必须呈现**：不能只给结论，必须给推导过程
