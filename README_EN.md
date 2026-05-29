# investment-brain v2.0 — Lightweight Six-Brain Decision System

> **⚠️ Note for new users**: This is the **basic v2.0** release. For the full-featured version with Chokepoint analysis, Moat assessment, Serenity Alpha model, Six-Brain deep analysis, and 11-person investment committee, please use **[new-investment-brain](https://github.com/Jonathonwang001/new-investment-brain)** (v3.1+), which is actively maintained and far more powerful.
>
> investment-brain v2.0 is kept only as a lightweight fallback.

---

## What is this?

investment-brain is an **AI investment analysis skill** based on **six-agent collaborative decision making**.

Each of the six "brains" analyzes independently, then signals are aggregated into a final recommendation.

### Six-Agent Architecture

| # | Agent | Weight | Key Question |
|---|-------|--------|--------------|
| 1 | ValuationAgent | 30% | Is valuation cheap? Enough margin of safety? |
| 2 | FundamentalsAgent | 25% | Is fundamentals healthy? ROE/margins/cash flow? |
| 3 | TechnicalsAgent | 20% | What's the technical trend? MA/RSI/MACD? |
| 4 | SentimentAgent | 15% | What's market sentiment? Money flow? |
| 5 | RiskManager | 10% | Is risk controlled? Forensic red flags? |

---

## Quick Start

### Install

```bash
skillhub_install install_skill investment-brain
```

### Usage

Just chat:

```
Analyze AAPL using investment-brain
```

The skill auto-invokes six brains and outputs a structured analysis report.

---

## Output Format

```
🧠 ValuationAgent | Valuation Analysis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Conclusion: BULLISH (Score: 72/100)
P/E: 28.5x (sector avg 32x, -11% discount)
DCF Intrinsic Value: $185 (MOS +18%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧠 FundamentalsAgent | Fundamentals Analysis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Conclusion: BULLISH (Score: 78/100)
ROE: 42% (>15% ✅)
Net Margin: 28% (>20% ✅)
FCF Yield: 3.2% (healthy ✅)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

...

【Composite Signal】: 🟢 Bullish (4/5 brains bullish)
【Recommendation】: 🟠 Core Buy (Suggested position 10-15%)
```

---

## v2.0 vs new-investment-brain

| Feature | investment-brain v2.0 | new-investment-brain v4.0 |
|---------|----------------------|--------------------------|
| Six-Brain Analysis | ✅ | ✅ Deep version (with reasoning + formulas) |
| Chokepoint Diagnosis | ❌ | ✅ 4-dimension screening |
| Moat Assessment | ❌ | ✅ SOIC framework |
| Three Moments | ❌ | ✅ AJI🍶/RPI🍓/GATE🛡️ |
| 11-Person Committee | ❌ | ✅ Buffett~Dalio |
| 5-Tier Color Blocks | ❌ | ✅ Rounded CSS blocks |

**Recommendation**: Just use **new-investment-brain** — it's strictly better.

---

## File Structure

```
investment-brain/
├── SKILL.md          # Skill master protocol
├── agents/           # Six-brain code
│   └── __init__.py
├── docs/            # Documentation
│   └── QUICKSTART.md
├── README.md         # This file
├── README_EN.md      # English README
├── ABOUT.md         # About (Chinese)
└── ABOUT_EN.md      # About (English)
```

---

## Version History

- **v2.0** (2026-03): Six-brain connected decision system, initial release
- **v3.0**: Merged SOIC + Chokepoint + financial analysis (moved to new-investment-brain)
- **v4.0**: Six-brain deep analysis + 11-person committee (new-investment-brain only)

---

## License

MIT License

---

**🧠 investment-brain v2.0** — Lightweight Six-Brain Decision System
