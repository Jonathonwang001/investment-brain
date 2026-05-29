# 🧠 investment-brain — v2.0 六大脑联网决策系统

> **⚠️ 新手注意**：本技能是**基础版v2.0**。如果你想要更强大的功能（Chokepoint瓶颈分析、护城河评估、Serenity Alpha模型、六大脑深度分析、11人投资委员会），请直接使用 **[new-investment-brain](https://github.com/Jonathonwang001/new-investment-brain)**（v3.1+），功能完整且持续更新。
>
> investment-brain v2.0 仅作为轻量级备选方案保留。

---

## 📖 这是什么？

investment-brain 是一个**基于六大脑联网协作**的投资分析技能。

六大脑各自独立分析，然后汇总信号，形成综合判断。

### 六大脑架构

| # | 大脑 | 权重 | 核心问题 |
|---|------|------|----------|
| 1 | ValuationAgent | 30% | 估值贵不贵？安全边际够不够？ |
| 2 | FundamentalsAgent | 25% | 基本面健康吗？ROE/利润率/现金流？ |
| 3 | TechnicalsAgent | 20% | 技术面趋势如何？MA/RSI/MACD？ |
| 4 | SentimentAgent | 15% | 市场情绪如何？资金流向？ |
| 5 | RiskManager | 10% | 风险可控吗？法医红旗？ |

---

## 🚀 快速开始

### 安装

```bash
skillhub_install install_skill investment-brain
```

### 使用

直接对话即可：

```
用investment-brain分析 AAPL
```

技能会自动调用六大脑，输出结构化分析报告。

---

## 📊 输出格式

```
🧠 ValuationAgent | 估值分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
结论：BULLISH（Score: 72/100）
P/E: 28.5x（行业均值32x，折价11%）
DCF内在价值：$185（安全边际+18%）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧠 FundamentalsAgent | 基本面分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
结论：BULLISH（Score: 78/100）
ROE: 42%（>15% ✅）
净利率: 28%（>20% ✅）
FCF Yield: 3.2%（健康 ✅）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

...

【综合信号】：🟢 看多（4/5大脑看多）
【推荐】：🟠 核心推荐（建议仓位10-15%）
```

---

## 🆚 v2.0 vs new-investment-brain

| 功能 | investment-brain v2.0 | new-investment-brain v4.0 |
|------|----------------------|--------------------------|
| 六大脑分析 | ✅ | ✅ 深度版（含分析过程+公式） |
| Chokepoint瓶颈 | ❌ | ✅ 四维诊断 |
| 护城河评估 | ❌ | ✅ SOIC框架 |
| 三种时刻 | ❌ | ✅ AJI🍶/RPI🍓/GATE🛡️ |
| 11人委员会 | ❌ | ✅ Buffett~Dalio |
| 五档色块 | ❌ | ✅ 圆角背景色块 |

**结论**：直接用 **new-investment-brain**，功能更完整。

---

## 📁 文件结构

```
investment-brain/
├── SKILL.md          # 技能主控协议
├── agents/           # 六大脑代码
│   └── __init__.py
├── docs/            # 文档
│   └── QUICKSTART.md
├── README.md         # 本文件
├── README_EN.md      # English README
├── ABOUT.md         # 关于（中文）
└── ABOUT_EN.md      # About (English)
```

---

## 📜 版本历史

- **v2.0** (2026-03): 六大脑联网决策系统，初始发布
- **v3.0**: 合并SOIC+Chokepoint+财务分析（移至new-investment-brain）
- **v4.0**: 六大脑深度分析+11人委员会（仅在new-investment-brain）

---

## 📄 License

MIT License

---

**🧠 investment-brain v2.0** — 轻量级六大脑决策系统
