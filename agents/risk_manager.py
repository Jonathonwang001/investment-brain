#!/usr/bin/env python3
"""
RiskManager — 风险管理大脑
============================
测算风险敞口，设定仓位上限。

风险管理维度：
  1. VaR（Value at Risk）：95%/99% 置信度下的最大损失
  2. CVaR（Conditional VaR）：极端损失的平均值
  3. 最大回撤容忍：根据账户规模和风险偏好设定
  4. 仓位上限：单标的、板块、相关资产
  5. Greeks（期权）：Delta/Gamma/Vega/Theta
  6. 相关性风险：持仓之间的相关性

信号输出：
  标的风险评级 → 可以建仓的最大仓位
  组合风险评级 → 整体敞口是否超限
  止损建议 → 入场价 ± 百分比
"""

import os, sys, json, math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SKILL_DIR)
from valuation_agent import AgentSignal


@dataclass
class RiskMetrics:
    """风险指标结构"""
    var_95: float       # 95% VaR（%）
    var_99: float       # 99% VaR（%）
    cvar_95: float      # 95% CVaR（%）
    max_position_size: float  # 最大仓位（%）
    stop_loss_pct: float      # 止损比例（%）
    beta: float
    volatility_ann: float    # 年化波动率（%）
    sharpe_ratio: float
    correlation_risk: float   # 相关性风险
    sector_concentration: float  # 板块集中度
    total_risk_score: int     # 0-100，风险越大越高


class RiskManager:
    """风险管理大脑"""
    
    agent_name = "RiskManager"
    
    # 默认风险参数
    DEFAULT_PORTFOLIO_SIZE = 100_0000  # 100万账户
    DEFAULT_MAX_LOSS = 0.15            # 最大亏损 15%
    DEFAULT_MAX_POSITION = 0.20          # 单标的最大 20%
    DEFAULT_MAX_SECTOR = 0.40           # 板块最大 40%
    
    def __init__(self, 
                 portfolio_size: float = None,
                 max_loss: float = None,
                 max_position: float = None,
                 max_sector: float = None):
        self.portfolio_size = portfolio_size or self.DEFAULT_PORTFOLIO_SIZE
        self.max_loss = max_loss or self.DEFAULT_MAX_LOSS
        self.max_position = max_position or self.DEFAULT_MAX_POSITION
        self.max_sector = max_sector or self.DEFAULT_MAX_SECTOR
    
    def analyze(self, ticker: str, price: float = None,
                position_type: str = "stock",
                shares: int = None,
                option_delta: float = None,
                option_gamma: float = None,
                option_vega: float = None,
                option_theta: float = None,
                **kwargs) -> AgentSignal:
        """
        分析单个标的的风险。
        
        Args:
            ticker: 股票代码
            price: 当前价格（可选，自动获取）
            position_type: "stock" | "call" | "put" | "straddle"
            shares: 持仓股数
            option_*: 期权 Greeks
        """
        raw = self._fetch_risk_data(ticker)
        if "error" in raw:
            return AgentSignal(
                agent=self.agent_name, ticker=ticker, signal="NEUTRAL",
                confidence=0, reasoning=[f"数据获取失败: {raw['error']}"],
                metrics={}, valuation_range=(0, 0), data_freshness="N/A"
            )
        
        # 计算风险指标
        metrics = self._calculate_risk(raw, position_type, option_delta)
        
        # 仓位建议
        position_signal, position_conf, position_reasoning = \
            self._position_recommendation(metrics, position_type)
        
        # 止损建议
        stop_loss = self._calculate_stop_loss(raw, position_type)
        
        return AgentSignal(
            agent=self.agent_name,
            ticker=ticker,
            signal=position_signal,
            confidence=position_conf,
            reasoning=position_reasoning,
            metrics={
                "var_95": round(metrics["var_95"], 2),
                "var_99": round(metrics["var_99"], 2),
                "cvar_95": round(metrics["cvar_95"], 2),
                "beta": round(raw.get("beta", 1.0), 2),
                "volatility_ann": round(metrics["volatility_ann"], 1),
                "sharpe_ratio": round(metrics["sharpe_ratio"], 2),
                "max_position_pct": round(metrics["max_position"] * 100, 1),
                "stop_loss_pct": round(stop_loss * 100, 1),
                "risk_score": metrics["risk_score"],
                "risk_level": metrics["risk_level"],
                "position_type": position_type,
            },
            valuation_range=(round(price * (1 - stop_loss), 2) if price else 0,
                           round(price * (1 + stop_loss * 1.5), 2) if price else 0),
            data_freshness=raw.get("fetch_time", "N/A"),
            raw_data=raw,
            methodology="",
            step_by_step=[],
            formulas=[],
            assumptions=[],
        )
    
    def analyze_portfolio(self, holdings: List[Dict], **kwargs) -> AgentSignal:
        """
        分析组合整体风险。
        
        Args:
            holdings: [{ticker, shares, price, sector}]
        """
        total_value = sum(h.get("shares", 0) * h.get("price", 0) for h in holdings)
        if total_value <= 0:
            return AgentSignal(
                agent=self.agent_name, ticker="PORTFOLIO", signal="NEUTRAL",
                confidence=0, reasoning=["总持仓价值为0"],
                metrics={}, valuation_range=(0, 0), data_freshness="N/A"
            )
        
        # 计算板块集中度
        sector_values = {}
        for h in holdings:
            sector = h.get("sector", "Unknown")
            val = h.get("shares", 0) * h.get("price", 0)
            sector_values[sector] = sector_values.get(sector, 0) + val
        
        sector_conc = max(sector_values.values()) / total_value if sector_values else 0
        
        # 计算加权 beta
        weighted_beta = 0
        for h in holdings:
            beta = h.get("beta", 1.0)
            val = h.get("shares", 0) * h.get("price", 0)
            weighted_beta += beta * val / total_value
        
        # 计算组合 VaR（简化：使用加权波动率）
        weighted_vol = 0
        for h in holdings:
            vol = h.get("volatility_ann", 0.20)
            val = h.get("shares", 0) * h.get("price", 0)
            weighted_vol += vol * val / total_value
        
        var_95 = weighted_vol * 1.65  # 95% VaR
        cvar_95 = weighted_vol * 2.33  # 95% CVaR
        
        risk_score = self._calculate_portfolio_risk_score(
            var_95, sector_conc, weighted_beta, len(holdings)
        )
        
        # 信号
        if risk_score < 30:
            signal = "BULLISH"
            conf = 75
            reasoning = [f"✅ 组合风险低（{risk_score}/100）", f"板块集中度 {sector_conc:.0%}（安全）"]
        elif risk_score < 50:
            signal = "SLIGHTLY_BULLISH"
            conf = 60
            reasoning = [f"⚡ 组合风险中等（{risk_score}/100）"]
        elif risk_score < 70:
            signal = "NEUTRAL"
            conf = 50
            reasoning = [f"⚠️ 组合风险偏高（{risk_score}/100）"]
        else:
            signal = "BEARISH"
            conf = 75
            reasoning = [f"🔴 组合风险极高（{risk_score}/100）— 建议减仓"]
        
        return AgentSignal(
            agent=self.agent_name,
            ticker="PORTFOLIO",
            signal=signal,
            confidence=conf,
            reasoning=reasoning,
            metrics={
                "total_value": round(total_value, 0),
                "var_95": round(var_95, 2),
                "cvar_95": round(cvar_95, 2),
                "weighted_beta": round(weighted_beta, 2),
                "weighted_volatility": round(weighted_vol * 100, 1),
                "sector_concentration": round(sector_conc, 3),
                "risk_score": risk_score,
                "num_holdings": len(holdings),
            },
            valuation_range=(0, 0),
            data_freshness=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
    
    def _fetch_risk_data(self, ticker: str) -> Dict:
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            info = t.info
            
            beta = info.get("beta", 1.0)
            vol = info.get("volatility", 0) or 0.20  # 默认20%
            price = info.get("currentPrice", 0) or info.get("regularMarketPrice", 0) or 0
            sector = info.get("sector", "Unknown")
            
            # 获取历史数据计算波动率
            try:
                hist = t.history(period="3mo")
                if not hist.empty and len(hist) > 20:
                    returns = hist["Close"].pct_change().dropna()
                    vol_ann = returns.std() * math.sqrt(252)
                else:
                    vol_ann = vol
            except:
                vol_ann = vol
            
            return {
                "price": price,
                "beta": beta,
                "volatility": vol,
                "volatility_ann": vol_ann,
                "sector": sector,
                "market_cap": info.get("marketCap", 0),
                "pe": info.get("trailingPE", 0) or 0,
                "source": "yfinance",
                "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _calculate_risk(self, raw: Dict, position_type: str, 
                        option_delta: float = None) -> Dict:
        price = raw.get("price", 0)
        vol = raw.get("volatility_ann", 0.20)
        beta = raw.get("beta", 1.0)
        
        # VaR 计算（Parametric）
        var_95 = vol * 1.65    # 95%
        var_99 = vol * 2.33    # 99%
        cvar_95 = vol * 2.33   # 近似
        cvar_99 = vol * 3.00   # 近似
        
        # 最大仓位
        # 高 beta → 降低仓位；高波动 → 降低仓位
        vol_factor = max(0.3, 1.5 - vol * 3)  # vol 越高，factor 越低
        beta_factor = max(0.3, 1.5 - beta * 0.5)  # beta 越高，factor 越低
        
        base_max = self.max_position
        max_position = base_max * vol_factor * beta_factor
        max_position = min(max_position, self.max_position)
        
        # 止损设置
        if position_type in ("call", "stock"):
            stop_loss = var_95 * 1.5  # 止损 = 1.5 × VaR95
        elif position_type in ("put", "straddle"):
            stop_loss = var_95 * 1.2
        else:
            stop_loss = var_95 * 1.5
        
        # 夏普比率（简化：假设无风险利率 4%）
        risk_free = 0.04
        expected_return = 0.10  # 假设预期收益 10%
        sharpe = (expected_return - risk_free) / vol if vol > 0 else 0
        
        # 风险评分
        risk_score = min(100, int(vol * 500 + beta * 20))
        if risk_score < 25: risk_level = "低风险"
        elif risk_score < 50: risk_level = "中等风险"
        elif risk_score < 75: risk_level = "高风险"
        else: risk_level = "极高风险"
        
        return {
            "var_95": var_95,
            "var_99": var_99,
            "cvar_95": cvar_95,
            "max_position": max_position,
            "stop_loss": stop_loss,
            "beta": beta,
            "volatility_ann": vol,
            "sharpe_ratio": sharpe,
            "risk_score": risk_score,
            "risk_level": risk_level,
        }
    
    def _position_recommendation(self, metrics: Dict,
                                  position_type: str) -> Tuple[str, int, List[str]]:
        risk_score = metrics["risk_score"]
        max_pos = metrics["max_position"]
        
        if risk_score < 25:
            signal = "BULLISH"
            conf = 75
            reasoning = [f"✅ 低风险标的（评分 {risk_score}/100）",
                       f"建议仓位: {max_pos:.0%} | 可满仓操作"]
        elif risk_score < 50:
            signal = "SLIGHTLY_BULLISH"
            conf = 60
            reasoning = [f"⚡ 中等风险（评分 {risk_score}/100）",
                       f"建议仓位: {max_pos:.0%} | 建议分批建仓"]
        elif risk_score < 75:
            signal = "NEUTRAL"
            conf = 50
            reasoning = [f"⚠️ 高风险（评分 {risk_score}/100）",
                       f"建议仓位: {max_pos * 0.5:.0%} | 严格止损"]
        else:
            signal = "BEARISH"
            conf = 75
            reasoning = [f"🔴 极高风险（评分 {risk_score}/100）",
                       f"建议仓位: ≤{max_pos * 0.25:.0%} | 不建议建仓"]
        
        reasoning.append(f"止损: {metrics['stop_loss']:.1%} | "
                       f"VaR95: {metrics['var_95']:.1%} | "
                       f"Beta: {metrics['beta']:.2f}")
        
        return signal, conf, reasoning
    
    def _calculate_stop_loss(self, raw: Dict, position_type: str) -> float:
        price = raw.get("price", 0)
        vol = raw.get("volatility_ann", 0.20)
        
        # ATR-based stop loss
        atr_stop = vol * 1.5
        
        # VaR-based stop
        var_stop = vol * 1.65
        
        stop = max(atr_stop, var_stop, 0.05)  # 最小止损 5%
        stop = min(stop, 0.25)  # 最大止损 25%
        
        return stop


# ─── 快捷入口 ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker")
    parser.add_argument("--type", default="stock", choices=["stock", "call", "put"])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    
    rm = RiskManager()
    r = rm.analyze(args.ticker, position_type=args.type)
    if args.json:
        print(json.dumps(r.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"⚠️ Risk Manager | {r.ticker}")
        print("=" * 50)
        print(f"风险评级: {r.metrics.get('risk_level', 'N/A')}（{r.metrics.get('risk_score', 0)}/100）")
        print(f"信号: {r.signal} | 置信度: {r.confidence}%")
        print(f"建议仓位: ≤{r.metrics.get('max_position_pct', 0):.1f}%")
        print(f"止损位: -{r.metrics.get('stop_loss_pct', 0):.1f}%")
        print(f"VaR(95%): {r.metrics.get('var_95', 0):.1f}% | Beta: {r.metrics.get('beta', 0):.2f}")
        print()
        for line in r.reasoning:
            print(f"  {line}")
