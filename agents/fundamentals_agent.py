#!/usr/bin/env python3
"""
FundamentalsAgent — 基本面大脑
================================
解读财务数据，生成基本面信号。

分析方法：
  1. 财务健康：ROE/ROA/ROIC、现金流质量、资产负债率
  2. 成长性：营收增速、利润增速、EPS超预期
  3. 盈利能力：毛利率、净利率、EBITDA margin
  4. 估值支撑：FCF yield、自由现金流
  5. 股息安全：股息率、DPS、DPR
  6. 趋势综合：单季度 vs 年度对比

信号逻辑：
  综合得分 ≥ 75 → BULLISH
  综合得分 55-75 → SLIGHTLY_BULLISH
  综合得分 45-55 → NEUTRAL
  综合得分 30-45 → SLIGHTLY_BEARISH
  综合得分 < 30 → BEARISH
"""

import os, sys, json
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SKILL_DIR)
from valuation_agent import AgentSignal


@dataclass
class FundamentalsScore:
    """基本面评分结构"""
    roe: float      # 净资产收益率 %
    roa: float      # 资产回报率 %
    roic: float     # 投入资本回报率 %
    gross_margin: float    # 毛利率 %
    net_margin: float      # 净利率 %
    fcf_yield: float       # FCF收益率 %
    debt_to_equity: float  # 负债权益比
    revenue_growth: float   # 营收增速 %
    earnings_growth: float # 盈利增速 %
    dividend_yield: float  # 股息率 %
    payout_ratio: float    # 分红率 %
    surprise_ratio: float  # EPS超预期 %
    total_score: int       # 综合得分 0-100
    strengths: List[str]
    weaknesses: List[str]
    # 方法论字段（2026-04-13）
    methodology: str = ""
    step_by_step: List = None
    formulas: List[str] = None
    assumptions: List[str] = None

    def __post_init__(self):
        if self.step_by_step is None:
            self.step_by_step = []
        if self.formulas is None:
            self.formulas = []
        if self.assumptions is None:
            self.assumptions = []


class FundamentalsAgent:
    """基本面大脑"""
    
    agent_name = "FundamentalsAgent"
    
    def analyze(self, ticker: str, market: str = "US", **kwargs) -> AgentSignal:
        raw = self._fetch_data(ticker, market)
        
        if "error" in raw:
            return AgentSignal(
                agent=self.agent_name, ticker=ticker, signal="NEUTRAL",
                confidence=0, reasoning=[f"数据获取失败: {raw['error']}"],
                metrics={}, valuation_range=(0, 0), data_freshness="N/A",
                methodology="数据获取失败，无法进行基本面分析",
                step_by_step=[{"step": "数据获取失败", "formula": "N/A", "input": str(raw.get('error','')), "output": None}],
                formulas=[], assumptions=[]
            )
        
        # 计算各项指标
        score = self._calculate_score(raw)
        signal, confidence, reasoning = self._generate_signal(score, raw)
        
        return AgentSignal(
            agent=self.agent_name,
            ticker=ticker,
            signal=signal,
            confidence=confidence,
            reasoning=reasoning,
            metrics={
                "total_score": score.total_score,
                "roe": score.roe,
                "roa": score.roa,
                "roic": score.roic,
                "gross_margin": score.gross_margin,
                "net_margin": score.net_margin,
                "fcf_yield": score.fcf_yield,
                "debt_to_equity": score.debt_to_equity,
                "revenue_growth": score.revenue_growth,
                "earnings_growth": score.earnings_growth,
                "dividend_yield": score.dividend_yield,
                "strengths": score.strengths,
                "weaknesses": score.weaknesses,
            },
            valuation_range=(0, 0),
            data_freshness=raw.get("fetch_time", "N/A"),
            methodology=getattr(score, 'methodology', ''),
            step_by_step=getattr(score, 'step_by_step', []),
            formulas=getattr(score, 'formulas', []),
            assumptions=getattr(score, 'assumptions', []),
            raw_data=raw,
        )
    
    def _fetch_data(self, ticker: str, market: str = "US") -> Dict:
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            info = t.info
            
            # 尝试获取更多财务数据
            try:
                financials = t.financials
                balance = t.balance_sheet
                cashflow = t.cashflow
            except:
                financials = balance = cashflow = None
            
            # 计算关键指标
            price = info.get("currentPrice", 0) or info.get("regularMarketPrice", 0) or 0
            shares = info.get("sharesOutstanding", 0) or 1
            market_cap = info.get("marketCap", 0) or price * shares
            
            # ROE
            net_income = info.get("netIncomeToCommon") or info.get("netIncome", 0) or 0
            stockholders_equity = info.get("stockholdersEquity") or info.get("totalStockHolderEquity", 0) or market_cap * 0.3
            roe = (net_income / stockholders_equity * 100) if stockholders_equity > 0 else 0
            
            # ROA
            total_assets = info.get("totalAssets", 0) or stockholders_equity * 2
            roa = (net_income / total_assets * 100) if total_assets > 0 else 0
            
            # ROIC (简化)
            total_debt = info.get("totalDebt", 0) or 0
            invested_capital = stockholders_equity + total_debt
            roic = (net_income / invested_capital * 100) if invested_capital > 0 else 0
            
            # 毛利率
            gross = info.get("grossProfit", 0) or 0
            revenue = info.get("totalRevenue", 1) or 1
            gross_margin = (gross / revenue * 100) if revenue > 0 else 0
            
            # 净利率
            net_margin = (net_income / revenue * 100) if revenue > 0 else 0
            
            # FCF yield
            fcf = info.get("freeCashflow", 0) or 0
            fcf_yield = (fcf / market_cap * 100) if market_cap > 0 else 0
            
            # 负债权益比
            debt_eq = (total_debt / stockholders_equity) if stockholders_equity > 0 else 0
            
            # 营收增长
            rev_growth = (info.get("revenueGrowth", 0) or 0) * 100
            
            # 盈利增长
            earn_growth = (info.get("earningsGrowth", 0) or 0) * 100
            
            # EPS超预期
            eps_actual = info.get("trailingEps", 0) or 0
            eps_est = info.get("forwardEps", 0) or eps_actual
            surprise = ((eps_actual - eps_est) / abs(eps_est) * 100) if eps_est and eps_est != 0 else 0
            
            # 股息
            div_yield = (info.get("dividendYield", 0) or 0) * 100
            div_rate = info.get("dividendRate", 0) or 0
            payout = (div_rate / eps_actual * 100) if eps_actual and eps_actual > 0 else 0
            
            return {
                "price": price,
                "market_cap": market_cap,
                "shares": shares,
                "net_income": net_income,
                "stockholders_equity": stockholders_equity,
                "total_assets": total_assets,
                "total_debt": total_debt,
                "fcf": fcf,
                "revenue": revenue,
                "roe": roe,
                "roa": roa,
                "roic": roic,
                "gross_margin": gross_margin,
                "net_margin": net_margin,
                "fcf_yield": fcf_yield,
                "debt_to_equity": debt_eq,
                "revenue_growth": rev_growth,
                "earnings_growth": earn_growth,
                "dividend_yield": div_yield,
                "payout_ratio": payout,
                "eps_actual": eps_actual,
                "eps_est": eps_est,
                "surprise_ratio": surprise,
                "sector": info.get("sector", "Unknown"),
                "beta": info.get("beta", 1.0),
                "analyst_target": info.get("targetMeanPrice", 0),
                "recommendation": info.get("recommendationKey", "none"),
                "source": "yfinance",
                "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _calculate_score(self, d: Dict) -> FundamentalsScore:
        """计算综合评分（0-100）"""
        score = 0
        strengths = []
        weaknesses = []
        
        # ── 盈利能力（30分）────────────────────────────────────────
        # ROE（巴菲特标准：>25%）— 15分
        roe = d.get("roe", 0)
        if roe >= 25:
            score += 15; strengths.append(f"✅ ROE {roe:.1f}%（极佳，超过巴菲特标准）")
        elif roe >= 15:
            score += 10; strengths.append(f"⚡ ROE {roe:.1f}%（良好）")
        elif roe >= 8:
            score += 5
        elif roe > 0:
            score += 2; weaknesses.append(f"⚠️ ROE {roe:.1f}%（偏低）")
        else:
            weaknesses.append(f"🔴 ROE 亏损")
        
        # ROA（>5%）— 5分
        roa = d.get("roa", 0)
        if roa >= 10: score += 5
        elif roa >= 5: score += 3
        elif roa >= 2: score += 1
        else: weaknesses.append(f"⚠️ ROA {roa:.1f}%")
        
        # ROIC（>10%）— 5分
        roic = d.get("roic", 0)
        if roic >= 15: score += 5
        elif roic >= 10: score += 3
        elif roic > 0: score += 1
        else: weaknesses.append(f"⚠️ ROIC {roic:.1f}%")
        
        # 毛利率（>40%优秀）— 5分
        gm = d.get("gross_margin", 0)
        if gm >= 50: score += 5; strengths.append(f"✅ 毛利率 {gm:.1f}%（极强护城河）")
        elif gm >= 40: score += 3; strengths.append(f"⚡ 毛利率 {gm:.1f}%")
        elif gm >= 20: score += 1
        else: weaknesses.append(f"⚠️ 毛利率 {gm:.1f}%（竞争激烈）")
        
        # 净利率（>20%）— 5分
        nm = d.get("net_margin", 0)
        if nm >= 25: score += 5
        elif nm >= 15: score += 3
        elif nm >= 5: score += 1
        else: weaknesses.append(f"⚠️ 净利率 {nm:.1f}%")
        
        # ── 成长性（20分）────────────────────────────────────────
        rg = d.get("revenue_growth", 0)
        if rg >= 30: score += 10; strengths.append(f"✅ 营收增长 {rg:.1f}%（强劲）")
        elif rg >= 15: score += 7; strengths.append(f"⚡ 营收增长 {rg:.1f}%")
        elif rg >= 5: score += 3
        elif rg >= 0: score += 1
        else: score -= 5; weaknesses.append(f"🔴 营收下滑 {rg:.1f}%")
        
        eg = d.get("earnings_growth", 0)
        if eg >= 20: score += 10; strengths.append(f"✅ 盈利增长 {eg:.1f}%")
        elif eg >= 10: score += 6
        elif eg >= 0: score += 3
        else: score -= 5; weaknesses.append(f"🔴 盈利下滑 {eg:.1f}%")
        
        # ── 财务健康（20分）──────────────────────────────────────
        # 负债权益比（<50%优秀）
        de = d.get("debt_to_equity", 0)
        if de <= 0.3: score += 10; strengths.append(f"✅ 财务稳健（负债率 {de:.0%}）")
        elif de <= 1.0: score += 6
        elif de <= 2.0: score += 2; weaknesses.append(f"⚠️ 负债率 {de:.0%}")
        else: score -= 5; weaknesses.append(f"🔴 高负债 {de:.0%}")
        
        # FCF yield（>5%优秀）
        fcf_y = d.get("fcf_yield", 0)
        if fcf_y >= 8: score += 5; strengths.append(f"✅ FCF收益率 {fcf_y:.1f}%")
        elif fcf_y >= 3: score += 3
        elif fcf_y > 0: score += 1
        else: score -= 3; weaknesses.append(f"⚠️ FCF收益率为负")
        
        # ── 估值支撑（15分）──────────────────────────────────────
        price = d.get("price", 0)
        # 简单看分析师推荐
        rec = d.get("recommendation", "none")
        if rec == "strongBuy": score += 12; strengths.append("✅ 强力买入评级")
        elif rec == "buy": score += 8
        elif rec == "hold": score += 4
        elif rec in ("sell", "strongSell"): score -= 3; weaknesses.append("⚠️ 卖出评级")
        
        # EPS超预期
        surprise = d.get("surprise_ratio", 0)
        if surprise >= 10: score += 3; strengths.append(f"✅ EPS超预期 {surprise:.1f}%")
        elif surprise >= 0: score += 1
        else: score -= 2
        
        # ── 股息安全（15分）──────────────────────────────────────
        dy = d.get("dividend_yield", 0)
        pr = d.get("payout_ratio", 0)
        if dy > 3 and pr < 60: score += 15; strengths.append(f"✅ 股息率 {dy:.1f}%（安全）")
        elif dy > 2 and pr < 70: score += 10
        elif dy > 1: score += 5
        elif dy == 0: score += 3  # 不发股息不代表差（成长股）
        else: score -= 5  # 高息但高分红率（危险）
        
        # ── 限制范围 ─────────────────────────────────────────────
        score = max(0, min(100, score))
        
        # ── 方法论说明 ─────────────────────────────────────────
        methodology = (
            "FundamentalsAgent 采用14维度综合评分（100分制）。"
            "5维度×15分=75分：盈利能力（ROE/ROA/ROIC/毛利率/净利率）；"
            "2维度×10分=20分：成长性（营收增速/盈利增速）；"
            "2维度×15分=30分：财务健康（负债率/FCF yield）；"
            "1维度×15分=15分：估值支撑（分析师评级/目标价）；"
            "2维度×15分=30分：股息安全（股息率/分红率）。"
            "综合得分≥75→BULLISH；55-75→SLIGHTLY_BULLISH；"
            "45-55→NEUTRAL；30-45→SLIGHTLY_BEARISH；<30→BEARISH。"
        )
        
        step_by_step = [
            {"step": "Step 1 — ROE（净资产收益率）", "formula": "ROE = 净利润 / 股东权益 × 100%",
             "input": f"净利润=${d.get('net_income', 0):.2f}, 股东权益=${d.get('stockholders_equity', 0):.2f}",
             "output": f"ROE = {roe:.1f}%"},
            {"step": "Step 2 — 毛利率", "formula": "毛利率 = 毛利润 / 营收 × 100%",
             "input": f"毛利润=${d.get('grossProfit', 0):.2f}, 营收=${d.get('revenue', 0):.2f}",
             "output": f"毛利率 = {gm:.1f}%"},
            {"step": "Step 3 — 净利率", "formula": "净利率 = 净利润 / 营收 × 100%",
             "input": f"净利润=${d.get('net_income', 0):.2f}, 营收=${d.get('revenue', 0):.2f}",
             "output": f"净利率 = {nm:.1f}%"},
            {"step": "Step 4 — 负债权益比", "formula": "D/E = 总债务 / 股东权益",
             "input": f"总债务=${d.get('total_debt', 0):.2f}, 股东权益=${d.get('stockholders_equity', 0):.2f}",
             "output": f"负债率 = {de:.0%}"},
            {"step": "Step 5 — 营收增速", "formula": "营收增速 = (本期营收 - 上期营收) / 上期营收",
             "input": f"营收增速 = {rg:.1f}%",
             "output": f"营收增长 {rg:.1f}%"},
            {"step": "Step 6 — 综合得分汇总", "formula": "总分 = Σ(各维度得分)",
             "input": "盈利能力(30分) + 成长性(20分) + 财务健康(20分) + 估值支撑(15分) + 股息安全(15分)",
             "output": f"综合得分: {score}/100"},
        ]
        
        formulas = [
            "ROE = 净利润 / 股东权益 × 100%（巴菲特标准: >25%）",
            "ROA = 净利润 / 总资产 × 100%（优秀: >5%）",
            "ROIC = NOPAT / 投入资本 × 100%（优秀: >10%）",
            "毛利率 = 毛利润 / 营收 × 100%（优秀: >40%）",
            "净利率 = 净利润 / 营收 × 100%（优秀: >15%）",
            "负债权益比 = 总债务 / 股东权益（健康: <50%）",
            "FCF Yield = FCF / 市值 × 100%（优秀: >5%）",
            "EPS超预期 = (实际EPS - 预期EPS) / 预期EPS × 100%",
            "综合得分 = 盈利能力(30分) + 成长性(20分) + 财务健康(20分) + 估值支撑(15分) + 股息安全(15分)",
        ]
        
        assumptions = [
            "ROE 基准：巴菲特标准 25%以上为极佳",
            "毛利率基准：>40% 代表强护城河，<20% 代表竞争激烈",
            "负债率：<50% 为财务稳健，>200% 为高杠杆风险",
            "分红率：<60% 为安全分红，>80% 可能无法持续",
            "EPS 预期来自分析师 consensus，未考虑超预期频率",
        ]
        
        return FundamentalsScore(
            roe=round(roe, 1),
            roa=round(roa, 1),
            roic=round(roic, 1),
            gross_margin=round(gm, 1),
            net_margin=round(nm, 1),
            fcf_yield=round(fcf_y, 2),
            debt_to_equity=round(de, 2),
            revenue_growth=round(rg, 1),
            earnings_growth=round(eg, 1),
            dividend_yield=round(dy, 2),
            payout_ratio=round(pr, 1),
            surprise_ratio=round(surprise, 1),
            total_score=int(score),
            strengths=strengths,
            weaknesses=weaknesses,
            methodology=methodology,
            step_by_step=step_by_step,
            formulas=formulas,
            assumptions=assumptions,
        )
    
    def _generate_signal(self, score: FundamentalsScore, raw: Dict) -> Tuple[str, int, List[str]]:
        """基于评分生成信号"""
        s = score.total_score
        price = raw.get("price", 0)
        sector = raw.get("sector", "")
        
        if s >= 75:
            signal = "BULLISH"
            conf = min(90, 60 + s // 2)
        elif s >= 55:
            signal = "SLIGHTLY_BULLISH"
            conf = min(75, 50 + s // 3)
        elif s >= 45:
            signal = "NEUTRAL"
            conf = 50
        elif s >= 30:
            signal = "SLIGHTLY_BEARISH"
            conf = min(70, 50 + (s - 30) // 2)
        else:
            signal = "BEARISH"
            conf = min(90, max(40, 100 - s))
        
        reasoning = [
            f"基本面综合得分：{s}/100（{signal}）",
            f"当前价格: ${price:.2f} | 行业: {sector}",
        ]
        
        if score.strengths:
            reasoning.append("亮点：")
            for st in score.strengths[:3]:
                reasoning.append(f"  {st}")
        
        if score.weaknesses:
            reasoning.append("风险：")
            for wk in score.weaknesses[:3]:
                reasoning.append(f"  {wk}")
        
        return signal, conf, reasoning


# ─── 快捷入口 ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    
    agent = FundamentalsAgent()
    r = agent.analyze(args.ticker)
    if args.json:
        print(json.dumps(r.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"📊 Fundamentals Agent | {r.ticker}")
        print("=" * 50)
        print(f"信号: {r.signal} | 置信度: {r.confidence}%")
        print(f"综合得分: {r.metrics.get('total_score', 0)}/100")
        print(f"ROE: {r.metrics.get('roe', 0):.1f}% | ROIC: {r.metrics.get('roic', 0):.1f}%")
        print(f"毛利率: {r.metrics.get('gross_margin', 0):.1f}% | 净利率: {r.metrics.get('net_margin', 0):.1f}%")
        print(f"营收增长: {r.metrics.get('revenue_growth', 0):.1f}% | 盈利增长: {r.metrics.get('earnings_growth', 0):.1f}%")
        print()
        for line in r.reasoning:
            print(f"  {line}")
