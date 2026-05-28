#!/usr/bin/env python3
"""
PortfolioManager — 投资决策大脑
=================================
汇总六个大脑的信号，拍板最终交易决策。

信号权重（可调整）：
  估值 Valuation    → 30%：内在价值是安全边际的锚
  基本面 Fundamentals → 25%：盈利质量是长期驱动力
  技术面 Technicals  → 20%：择时是短期催化剂
  情绪 Sentiment    → 15%：逆向思维是超额收益来源
  风险 Risk         → 10%：控制下行是生存之道

综合信号算法：
  加权得分 = Σ(信号分 × 权重)
  BULLISH:   ≥ 70分
  SLIGHTLY_BULLISH: 55-70分
  NEUTRAL:   45-55分
  SLIGHTLY_BEARISH: 30-45分
  BEARISH:   < 30分

最终输出：
  ✅ 建仓/加仓（BUY, ACCUMULATE）
  ⚠️ 持有（HOLD）
  ❌ 减仓/清仓（SELL, REDUCE）
"""

import os, sys, json, math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SKILL_DIR)
from valuation_agent import AgentSignal

# 信号分映射
SIGNAL_SCORE = {
    "BULLISH": 100,
    "SLIGHTLY_BULLISH": 75,
    "NEUTRAL": 50,
    "SLIGHTLY_BEARISH": 25,
    "BEARISH": 0,
}

# 信号权重（可配置）
DEFAULT_WEIGHTS = {
    "ValuationAgent": 0.30,
    "FundamentalsAgent": 0.25,
    "TechnicalsAgent": 0.20,
    "SentimentAgent": 0.15,
    "RiskManager": 0.10,
}

# 最终操作映射
ACTION_MAP = {
    "BULLISH": "BUY",
    "SLIGHTLY_BULLISH": "ACCUMULATE",
    "NEUTRAL": "HOLD",
    "SLIGHTLY_BEARISH": "REDUCE",
    "BEARISH": "SELL",
}


@dataclass
class FinalDecision:
    """最终投资决策"""
    ticker: str
    action: str            # BUY / ACCUMULATE / HOLD / REDUCE / SELL
    confidence: int
    composite_score: int   # 0-100 综合得分
    consensus: str         # 最终信号
    signals: Dict           # 各大脑信号名
    weights: Dict           # 各大脑权重
    reasoning: List[str]
    agent_signals: Dict     # 各大脑 AgentSignal（含完整 methodology）
    position_size: float    # 建议仓位（%）
    entry_price: float     # 建议入场价
    stop_loss: float       # 止损价
    target_price: float    # 目标价
    timeframe: str         # 建议持仓周期
    risks: List[str]       # 主要风险点
    opportunities: List[str]  # 主要机会点


class PortfolioManager:
    """
    投资决策大脑
    =============
    1. 接收各 Agent 的信号
    2. 加权汇总，得出综合得分
    3. 考虑信号一致性（全部看多 vs 分歧）
    4. 结合风险约束，输出最终决策
    """
    
    agent_name = "PortfolioManager"
    
    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or DEFAULT_WEIGHTS.copy()
    
    def analyze(self,
                ticker: str,
                signals: Dict[str, AgentSignal],
                current_price: float = None,
                current_position: float = 0,
                **kwargs) -> FinalDecision:
        """
        主分析入口。
        
        Args:
            ticker: 股票代码
            signals: 各大脑的信号 dict
                {
                  "ValuationAgent": AgentSignal,
                  "FundamentalsAgent": AgentSignal,
                  "TechnicalsAgent": AgentSignal,
                  "SentimentAgent": AgentSignal,
                  "RiskManager": AgentSignal,
                }
            current_price: 当前价格
            current_position: 当前持仓（%）
        """
        # ── 步骤1：计算加权得分 ─────────────────────────────────────
        scores = {}
        for agent_name, signal in signals.items():
            weight = self.weights.get(agent_name, 0)
            signal_score = SIGNAL_SCORE.get(signal.signal, 50)
            weighted_score = signal_score * weight
            scores[agent_name] = {
                "signal": signal.signal,
                "confidence": signal.confidence,
                "weight": weight,
                "raw_score": signal_score,
                "weighted_score": weighted_score,
                "reasoning": signal.reasoning[:2] if signal.reasoning else [],
            }
        
        # 综合得分
        composite = sum(s["weighted_score"] for s in scores.values())
        composite = int(composite)
        
        # 信号一致性分析
        signal_list = [s["signal"] for s in scores.values()]
        bull_count = sum(1 for s in signal_list if "BULLISH" in s)
        bear_count = sum(1 for s in signal_list if "BEARISH" in s)
        
        # 分歧惩罚：信号不一致时降低置信度
        disagreement = abs(bull_count - bear_count)
        if disagreement <= 1:
            consensus_label = "高度一致"
            conf_factor = 1.0
        elif disagreement == 2:
            consensus_label = "略有分歧"
            conf_factor = 0.85
        elif disagreement == 3:
            consensus_label = "分歧较大"
            conf_factor = 0.7
        else:
            consensus_label = "严重分歧"
            conf_factor = 0.5
        
        avg_confidence = sum(s["confidence"] for s in scores.values()) / len(scores)
        confidence = int(avg_confidence * conf_factor)
        
        # ── 步骤2：确定最终信号 ─────────────────────────────────────
        if composite >= 70:
            consensus = "BULLISH"
        elif composite >= 55:
            consensus = "SLIGHTLY_BULLISH"
        elif composite >= 45:
            consensus = "NEUTRAL"
        elif composite >= 30:
            consensus = "SLIGHTLY_BEARISH"
        else:
            consensus = "BEARISH"
        
        # ── 步骤3：确定操作建议 ─────────────────────────────────────
        action = ACTION_MAP.get(consensus, "HOLD")
        
        # 结合当前持仓调整
        if current_position > 0 and consensus in ("BEARISH", "SLIGHTLY_BEARISH"):
            action = "REDUCE"
        elif current_position == 0 and consensus == "BULLISH":
            action = "BUY"
        
        # ── 步骤4：仓位建议 ─────────────────────────────────────────
        position_size = self._calculate_position_size(
            composite, confidence, scores, current_position, consensus
        )
        
        # ── 步骤5：价格建议 ─────────────────────────────────────────
        entry_price = current_price or self._get_price_from_signals(signals)
        
        # 止损 = 当前价 × (1 - 各大脑平均止损比例)
        risk_signals = [s for s in scores.values() 
                       if "RiskManager" in str(s)]
        avg_risk_loss = 0.10  # 默认 10%
        if risk_signals:
            for s in scores.values():
                if "RiskManager" in str(s):
                    avg_risk_loss = min(avg_risk_loss, 
                        s.get("metrics", {}).get("stop_loss_pct", 10) / 100 or 0.10)
        
        stop_loss = entry_price * (1 - avg_risk_loss) if entry_price else 0
        
        # 目标价：基于估值大脑内在价值
        target_price = self._get_target_price(signals, entry_price)
        
        # ── 步骤6：持仓周期 ─────────────────────────────────────────
        timeframe = self._get_timeframe(consensus, scores)
        
        # ── 步骤7：风险和机会 ──────────────────────────────────────
        risks = self._extract_risks(scores, consensus)
        opportunities = self._extract_opportunities(scores, consensus)
        
        # ── 步骤8：综合理由 ────────────────────────────────────────
        reasoning = self._build_reasoning(ticker, scores, composite, consensus, 
                                        action, consensus_label, scores)
        
        return FinalDecision(
            ticker=ticker,
            action=action,
            confidence=confidence,
            composite_score=composite,
            consensus=consensus,
            signals={k: v.signal for k, v in signals.items()},
            weights=self.weights.copy(),
            reasoning=reasoning,
            agent_signals=signals,          # ← 完整 AgentSignal（含 methodology）
            position_size=position_size,
            entry_price=entry_price,
            stop_loss=round(stop_loss, 2),
            target_price=round(target_price, 2) if target_price else 0,
            timeframe=timeframe,
            risks=risks,
            opportunities=opportunities,
        )
    
    def _calculate_position_size(self, composite: int, confidence: int,
                                scores: Dict, current_pos: float,
                                consensus: str) -> float:
        """计算建议仓位"""
        base = composite / 100  # 基础仓位 = 综合得分/100
        
        # 置信度调整
        conf_factor = confidence / 100
        
        position = base * conf_factor
        
        # 风险约束
        for name, s in scores.items():
            if "RiskManager" in name:
                risk_pos = s.get("metrics", {}).get("max_position_pct", 100) / 100
                position = min(position, risk_pos)
        
        # 现有持仓调整
        if current_pos > 0 and consensus in ("BULLISH", "SLIGHTLY_BULLISH"):
            # 持有偏多，可加仓
            position = max(position, current_pos)
        elif current_pos > 0 and consensus in ("BEARISH", "SLIGHTLY_BEARISH"):
            # 持有偏空，应减仓
            position = min(position, current_pos * 0.5)
        
        # 限制范围
        position = max(0, min(position, 1.0))
        
        return round(position, 3)
    
    def _get_price_from_signals(self, signals: Dict) -> float:
        for sig in signals.values():
            if hasattr(sig, "raw_data") and sig.raw_data:
                price = sig.raw_data.get("price", 0)
                if price > 0:
                    return price
        return 0
    
    def _get_target_price(self, signals: Dict, entry: float) -> float:
        """从估值大脑获取目标价"""
        for name, sig in signals.items():
            if "Valuation" in name:
                metrics = sig.metrics
                intrinsic = metrics.get("intrinsic_value", 0)
                if intrinsic > 0:
                    # 目标 = 内在价值 × 0.95（留5%安全边际）
                    return intrinsic * 0.95
        
        # 回退：用分析师目标价
        for sig in signals.values():
            if hasattr(sig, "raw_data") and sig.raw_data:
                target = sig.raw_data.get("analyst_target", 0)
                if target > 0:
                    return target
        
        # 最保守：当前价上涨15%
        return entry * 1.15 if entry else 0
    
    def _get_timeframe(self, consensus: str, scores: Dict) -> str:
        """判断持仓周期"""
        if consensus in ("BULLISH", "SLIGHTLY_BULLISH"):
            tech_score = scores.get("TechnicalsAgent", {}).get("raw_score", 50)
            if tech_score >= 75:
                return "短线1-4周（技术突破）"
            elif tech_score >= 50:
                return "中线1-3月（趋势持仓）"
            else:
                return "长线6-12月（价值投资）"
        elif consensus == "NEUTRAL":
            return "观望1-2周"
        else:
            return "立即减仓"
    
    def _extract_risks(self, scores: Dict, consensus: str) -> List[str]:
        risks = []
        
        for name, s in scores.items():
            if s["signal"] in ("BEARISH", "SLIGHTLY_BEARISH"):
                if s["reasoning"]:
                    risks.append(f"⚠️ {name}: {s['reasoning'][0][:80]}")
        
        if consensus in ("BULLISH", "SLIGHTLY_BULLISH"):
            risks.append("⚠️ 高信号标的波动性较大")
        
        return risks[:3]
    
    def _extract_opportunities(self, scores: Dict, consensus: str) -> List[str]:
        opportunities = []
        
        for name, s in scores.items():
            if s["signal"] in ("BULLISH", "SLIGHTLY_BULLISH"):
                if s["reasoning"]:
                    opportunities.append(f"✅ {name}: {s['reasoning'][0][:80]}")
        
        if consensus == "BULLISH":
            opportunities.append("✅ 多大脑共振，建仓机会")
        
        return opportunities[:3]
    
    def _build_reasoning(self, ticker: str, scores: Dict, composite: int,
                        consensus: str, action: str,
                        consensus_label: str, _scores) -> List[str]:
        reasoning = [
            f"🎯 {ticker} 投资决策 | 综合得分 {composite}/100（{consensus}）| {consensus_label}",
            f"操作建议: {action} | 置信度: {sum(s['confidence'] for s in scores.values()) // len(scores)}%",
        ]
        
        # 各大脑信号摘要
        reasoning.append("")
        for name, s in scores.items():
            emoji = "📈" if "BULLISH" in s["signal"] else "📉" if "BEARISH" in s["signal"] else "➡️"
            reasoning.append(
                f"  {emoji} {name}: {s['signal']} ({s['confidence']}%) "
                f"权重{s['weight']:.0%} 得分{int(s['weighted_score'])}"
            )
        
        # 关键理由
        if consensus == "BULLISH":
            bull_reasons = [s['reasoning'][0] for n, s in scores.items() 
                          if "BULLISH" in s['signal'] and s['reasoning']]
            if bull_reasons:
                reasoning.append("")
                reasoning.append("买入理由：")
                for r in bull_reasons[:2]:
                    reasoning.append(f"  • {r[:100]}")
        
        return reasoning
    
    def batch_decide(self, ticker_signals: Dict[str, Dict[str, AgentSignal]],
                     **kwargs) -> Dict[str, FinalDecision]:
        """批量决策"""
        decisions = {}
        for ticker, signals in ticker_signals.items():
            decisions[ticker] = self.analyze(ticker, signals, **kwargs)
        return decisions
    
    def summary(self, decisions: Dict[str, FinalDecision]) -> str:
        """生成汇总表格"""
        lines = [
            "## 🎯 PortfolioManager 决策汇总",
            "",
            "| 标的 | 操作 | 得分 | 置信 | 仓位 | 止损 | 周期 |",
            "|------|------|------|------|------|------|------|",
        ]
        
        for ticker, d in sorted(decisions.items(), 
                               key=lambda x: x[1].composite_score, reverse=True):
            lines.append(
                f"| {d.ticker} | {d.action} | {d.composite_score} | "
                f"{d.confidence}% | {d.position_size:.0%} | "
                f"-{d.stop_loss if d.entry_price else 0:+.2f} | {d.timeframe[:8]} |"
            )
        
        lines.append("")
        
        buys = {t: d for t, d in decisions.items() if d.action in ("BUY", "ACCUMULATE")}
        sells = {t: d for t, d in decisions.items() if d.action in ("SELL", "REDUCE")}
        
        if buys:
            lines.append("**买入候选：** " + ", ".join(buys.keys()))
        if sells:
            lines.append("**减仓回避：** " + ", ".join(sells.keys()))
        
        return "\n".join(lines)

    def full_report(self, decision: FinalDecision) -> str:
        """
        输出完整推导过程报告（精准深化版）。
        用于持仓诊断和周末复盘场景。
        """
        lines = []
        lines.append(f"╔══════════════════════════════════════════════════════╗")
        lines.append(f"║   六大脑完整推导报告 · {decision.ticker:6s}              ║")
        lines.append(f"╚══════════════════════════════════════════════════════╝")
        lines.append("")

        # ── 步骤1：综合得分计算 ───────────────────────────────────
        lines.append("📊 PortfolioManager 综合得分计算")
        lines.append("─" * 50)
        for name, sig in decision.agent_signals.items():
            w = decision.weights.get(name, 0)
            ss_map = {"BULLISH":100,"SLIGHTLY_BULLISH":75,"NEUTRAL":50,
                      "SLIGHTLY_BEARISH":25,"BEARISH":0}
            ss = ss_map.get(sig.signal, 50)
            contrib = ss * w
            emoji = "📈" if "BULLISH" in sig.signal else "📉" if "BEARISH" in sig.signal else "➡️"
            lines.append(
                f"  {emoji} {name:<22s} {sig.signal:<20s} x 权重{w:.0%} = {contrib:.1f}分"
            )
        lines.append(f"  {'─'*45}")
        lines.append(f"  综合得分: {decision.composite_score:.1f} → {decision.action} | 置信: {decision.confidence}%")
        lines.append("")

        # ── 步骤2：各 Agent 完整推导 ──────────────────────────────
        for name, sig in decision.agent_signals.items():
            lines.append(f"📊 {name} 完整推导")
            lines.append("─" * 50)
            # 方法论（多行说明）
            if sig.methodology:
                for mline in sig.methodology.strip().split("\n"):
                    if mline.strip():
                        lines.append(f"  {mline}")
            # 推理过程
            if sig.reasoning:
                lines.append("  推理过程:")
                for r in sig.reasoning:
                    lines.append(f"    • {r}")
            # 核心指标（前6个）
            if sig.metrics:
                lines.append("  核心指标:")
                for k, v in list(sig.metrics.items())[:6]:
                    lines.append(f"    • {k}: {v}")
            lines.append("")

        # ── 步骤3：最终决策摘要 ──────────────────────────────────
        lines.append(f"🎯 PortfolioManager 最终决策")
        lines.append("─" * 50)
        lines.append(f"  操作:     {decision.action}")
        lines.append(f"  综合得分: {decision.composite_score}/100")
        lines.append(f"  置信度:   {decision.confidence}%")
        lines.append(f"  建议仓位: {decision.position_size:.0%}")
        lines.append(f"  入场价:   ${decision.entry_price:.2f}")
        lines.append(f"  止损价:   ${decision.stop_loss:.2f}")
        lines.append(f"  目标价:   ${decision.target_price:.2f}")
        lines.append(f"  持仓周期: {decision.timeframe}")
        if decision.reasoning:
            lines.append("  综合理由:")
            for r in decision.reasoning[:4]:
                lines.append(f"    • {r[:120]}")
        if decision.risks:
            lines.append("  主要风险:")
            for r in decision.risks[:3]:
                lines.append(f"    • {r}")
        if decision.opportunities:
            lines.append("  主要机会:")
            for o in decision.opportunities[:3]:
                lines.append(f"    • {o}")

        return "\n".join(lines)

    def run_full(self, ticker: str, current_price: float = None,
                 current_position: float = 0) -> FinalDecision:
        """
        完整运行：调用所有 Agent → PortfolioManager。
        一步完成，等价于手动调用5个Agent + analyze()。
        """
        # 避免循环导入，在函数内部导入
        import importlib
        ValuationAgent = getattr(
            importlib.import_module('valuation_agent'), 'ValuationAgent')
        FundamentalsAgent = getattr(
            importlib.import_module('fundamentals_agent'), 'FundamentalsAgent')
        TechnicalsAgent = getattr(
            importlib.import_module('technicals_agent'), 'TechnicalsAgent')
        SentimentAgent = getattr(
            importlib.import_module('sentiment_agent'), 'SentimentAgent')
        RiskManager = getattr(
            importlib.import_module('risk_manager'), 'RiskManager')

        signals = {
            "ValuationAgent":    ValuationAgent().analyze(ticker),
            "FundamentalsAgent": FundamentalsAgent().analyze(ticker),
            "TechnicalsAgent":   TechnicalsAgent().analyze(ticker),
            "SentimentAgent":    SentimentAgent().analyze(ticker),
            "RiskManager":       RiskManager().analyze(ticker),
        }
        return self.analyze(ticker, signals, current_price, current_position)


# ─── 快捷入口 ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PortfolioManager - 投资决策大脑")
    parser.add_argument("ticker", help="股票代码")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()
    
    # 演示：同时调用所有大脑
    sys.path.insert(0, SKILL_DIR)
    from valuation_agent import ValuationAgent
    from fundamentals_agent import FundamentalsAgent
    from technicals_agent import TechnicalsAgent
    from sentiment_agent import SentimentAgent
    from risk_manager import RiskManager
    
    ticker = args.ticker
    print(f"🎯 运行 {ticker} 全脑分析...", file=sys.stderr)
    
    # 调用各大脑
    va = ValuationAgent()
    fa = FundamentalsAgent()
    ta = TechnicalsAgent()
    sa = SentimentAgent()
    rm = RiskManager()
    
    signals = {
        "ValuationAgent": va.analyze(ticker),
        "FundamentalsAgent": fa.analyze(ticker),
        "TechnicalsAgent": ta.analyze(ticker),
        "SentimentAgent": sa.analyze(ticker),
        "RiskManager": rm.analyze(ticker),
    }
    
    pm = PortfolioManager()
    decision = pm.analyze(ticker, signals)
    
    if args.json:
        print(json.dumps({
            "ticker": decision.ticker,
            "action": decision.action,
            "confidence": decision.confidence,
            "composite_score": decision.composite_score,
            "consensus": decision.consensus,
            "position_size": decision.position_size,
            "entry_price": decision.entry_price,
            "stop_loss": decision.stop_loss,
            "target_price": decision.target_price,
            "timeframe": decision.timeframe,
            "reasoning": decision.reasoning,
            "risks": decision.risks,
            "opportunities": decision.opportunities,
            "signals": decision.signals,
        }, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'='*60}")
        print(f"🎯 {decision.ticker} 最终决策报告")
        print(f"{'='*60}")
        print(f"操作: {decision.action} | 置信度: {decision.confidence}%")
        print(f"综合得分: {decision.composite_score}/100 | 信号: {decision.consensus}")
        print(f"建议仓位: {decision.position_size:.0%} | 入场价: ${decision.entry_price:.2f}")
        print(f"止损价: ${decision.stop_loss:.2f} | 目标价: ${decision.target_price:.2f}")
        print(f"持仓周期: {decision.timeframe}")
        print()
        print("各大脑信号：")
        for k, v in decision.signals.items():
            print(f"  {k}: {v}")
        print()
        for line in decision.reasoning:
            print(f"  {line}")
        if decision.risks:
            print("\n风险：")
            for r in decision.risks: print(f"  {r}")
        if decision.opportunities:
            print("\n机会：")
            for o in decision.opportunities: print(f"  {o}")
