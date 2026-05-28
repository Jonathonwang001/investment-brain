#!/usr/bin/env python3
"""
ValuationAgent — 估值大脑
===========================
计算内在价值，生成估值交易信号。

方法论（按场景选择）：
  1. DCF（自由现金流折现）— 适用于盈利稳定的成熟公司
  2. DDM（股利折现模型）— 适用于高分红、稳定的蓝筹股
  3. PE Band（市盈率通道）— 适用于大盘股，快速参考
  4. EV/EBITDA — 适用于周期股、重资产公司
  5. PEG — 适用于成长股
  6. 净资产折价（PB）— 适用于金融、地产、保险

信号逻辑：
  当前价格 < 内在价值 × 0.8  → BULLISH（显著低估）
  当前价格 < 内在价值         → SLIGHTLY_BULLISH（略低估）
  当前价格 ≈ 内在价值 ±10%   → NEUTRAL（合理区间）
  当前价格 > 内在价值 × 1.2  → BEARISH（显著高估）

使用数据：
  yfinance（美股）、AKShare（A股/港股）
  Finnhub（分析师目标价）
"""

import os
import sys
import json
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

# ─── 路径配置 ────────────────────────────────────────────────────────────────
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(SKILL_DIR)))
sys.path.insert(0, SKILL_DIR)

# ─── Agent 基类 ─────────────────────────────────────────────────────────────
@dataclass
class AgentSignal:
    """
    标准化信号格式（所有 Agent 统一）
    
    新增字段（2026-04-13）：
    - methodology: 完整方法论说明
    - step_by_step: 分步计算过程
    - formulas: 使用的公式
    - assumptions: 关键假设
    - raw_data: 原始数据
    """
    agent: str
    ticker: str
    signal: str          # BULLISH / BEARISH / NEUTRAL / SLIGHTLY_BULLISH / SLIGHTLY_BEARISH
    confidence: int       # 0-100
    reasoning: List[str]
    metrics: Dict         # 各方法论的具体数值
    valuation_range: Tuple[float, float]  # (低估价格, 高估价格)
    data_freshness: str   # 数据时间戳
    # === 完整方法论字段 ===
    methodology: str = ""      # 方法论完整说明
    step_by_step: List[Dict] = None  # 分步计算 [{step, formula, input, output}]
    formulas: List[str] = None       # 使用的公式列表
    assumptions: List[str] = None     # 关键假设
    raw_data: Optional[Dict] = None
    
    def __post_init__(self):
        if self.step_by_step is None:
            self.step_by_step = []
        if self.formulas is None:
            self.formulas = []
        if self.assumptions is None:
            self.assumptions = []
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        # 序列化时保持兼容性
        return d
    
    def full_report(self) -> str:
        """生成完整的分析报告（含方法论）"""
        lines = [
            f"## {self.agent} — {self.ticker}",
            f"**信号**: {self.signal} | **置信度**: {self.confidence}%",
            "",
        ]
        if self.methodology:
            lines.append(f"### 📚 方法论")
            lines.append(self.methodology)
            lines.append("")
        if self.step_by_step:
            lines.append(f"### 🔢 分步计算")
            for i, step in enumerate(self.step_by_step, 1):
                lines.append(f"**Step {i}**: {step.get('step', '')}")
                if step.get('formula'):
                    lines.append(f"  公式: `{step['formula']}`")
                if step.get('input'):
                    lines.append(f"  输入: {step['input']}")
                if step.get('output') is not None:
                    lines.append(f"  输出: {step['output']}")
                lines.append("")
        if self.formulas:
            lines.append(f"### 🧮 公式")
            for f in self.formulas:
                lines.append(f"  - `{f}`")
            lines.append("")
        if self.assumptions:
            lines.append(f"### ⚠️ 假设")
            for a in self.assumptions:
                lines.append(f"  - {a}")
            lines.append("")
        lines.append(f"### 📊 指标汇总")
        for k, v in self.metrics.items():
            lines.append(f"  - {k}: {v}")
        lines.append("")
        if self.valuation_range != (0, 0):
            lines.append(f"### 🎯 估值区间")
            lines.append(f"  低估: ${self.valuation_range[0]:.2f}")
            lines.append(f"  高估: ${self.valuation_range[1]:.2f}")
        lines.append("")
        lines.append(f"### 💡 结论")
        for r in self.reasoning:
            lines.append(f"  {r}")
        lines.append("")
        lines.append(f"数据时间: {self.data_freshness}")
        return "\n".join(lines)


class BaseAgent:
    """所有 Agent 的基类"""
    agent_name: str = "BaseAgent"
    
    def analyze(self, ticker: str, market: str = "US", **kwargs) -> AgentSignal:
        raise NotImplementedError
    
    def _get_data(self, ticker: str, market: str = "US") -> Dict:
        """获取原始财务数据"""
        if market == "US":
            return self._get_yfinance_data(ticker)
        elif market in ("CN", "HK"):
            return self._get_akshare_data(ticker, market)
        return {}
    
    def _get_yfinance_data(self, ticker: str) -> Dict:
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            info = t.info
            hist = t.history(period="2y")
            
            # 计算财务指标
            fcf = info.get("freeCashflow") or 0
            net_income = info.get("netIncomeToCommon") or info.get("netIncome", 0)
            shares = info.get("sharesOutstanding", 0)
            bvps = info.get("bookValue", 0)
            eps = info.get("trailingEps", 0) or info.get("forwardEps", 0) or 0
            dps = info.get("dividendRate", 0) or 0
            pe = info.get("trailingPE", 0) or 0
            pb = info.get("priceToBook", 0) or 0
            ev_ebitda = info.get("enterpriseToEbitda", 0) or 0
            beta = info.get("beta", 1.0)
            market_cap = info.get("marketCap", 0)
            price = info.get("currentPrice", 0) or info.get("regularMarketPrice", 0) or 0
            revenue_growth = info.get("revenueGrowth", 0) or 0
            earnings_growth = info.get("earningsGrowth", 0) or 0
            
            # 计算 FCF yield
            fcf_per_share = fcf / shares if shares > 0 else 0
            fcf_yield = fcf_per_share / price if price > 0 else 0
            
            return {
                "price": price,
                "market_cap": market_cap,
                "eps_trailing": eps,
                "eps_forward": info.get("forwardEps", 0) or 0,
                "book_value_per_share": bvps,
                "dps": dps,
                "fcf_per_share": fcf_per_share,
                "fcf_yield": fcf_yield,
                "pe_trailing": pe,
                "pe_forward": info.get("forwardPE", 0) or 0,
                "pb": pb,
                "ev_ebitda": ev_ebitda,
                "beta": beta,
                "revenue_growth": revenue_growth,
                "earnings_growth": earnings_growth,
                "dividend_yield": info.get("dividendYield", 0) or 0,
                "shares_outstanding": shares,
                "free_cash_flow": fcf,
                "net_income": net_income,
                "revenue": info.get("totalRevenue", 0) or 0,
                "ebitda": info.get("ebitda", 0) or 0,
                "net_debt": (info.get("totalDebt", 0) or 0) - (info.get("totalCash", 0) or 0),
                "sector": info.get("sector", "Unknown"),
                "industry": info.get("industry", "Unknown"),
                "analyst_target": info.get("targetMeanPrice", 0) or 0,
                "analyst_count": info.get("numberOfAnalystOpinions", 0) or 0,
                "recommendation": info.get("recommendationKey", "none"),
                "hist_prices": hist["Close"].tolist() if not hist.empty else [],
                "hist_dates": [str(d.date()) for d in hist.index] if not hist.empty else [],
                "price_high_52w": info.get("fiftyTwoWeekHigh", 0) or 0,
                "price_low_52w": info.get("fiftyTwoWeekLow", 0) or 0,
                "source": "yfinance",
                "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
        except Exception as e:
            return {"error": str(e), "source": "yfinance"}
    
    def _get_akshare_data(self, ticker: str, market: str = "CN") -> Dict:
        """AKShare 数据获取"""
        try:
            import akshare as ak
            symbol = ticker.replace(".", "_") if "." in ticker else ticker
            
            if market == "CN":
                # A股
                df = ak.stock_individual_info_em(symbol=symbol)
                info_dict = dict(zip(df["item"].tolist(), df["value"].tolist()))
                
                # 获取财务数据
                try:
                    df_fina = ak.stock_financial_analysis_indicator(symbol=symbol, start_year="2022")
                    latest = df_fina.iloc[-1] if not df_fina.empty else {}
                except:
                    latest = {}
                
                return {
                    "source": "akshare",
                    "info": info_dict,
                    "financial_latest": latest.to_dict() if hasattr(latest, "to_dict") else {},
                    "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
            return {"source": "akshare", "error": "unsupported market"}
        except Exception as e:
            return {"error": str(e), "source": "akshare"}


class ValuationAgent(BaseAgent):
    """
    估值大脑 — Valuation Agent
    ==============================
    6种估值方法论，计算内在价值区间，生成交易信号。
    
    适用场景：
      DCF      → 盈利稳定、有自由现金流的成熟公司（NVDA、MSFT、BRK）
      DDM      → 高分红蓝筹（JNJ、PG、PFE）
      PE Band  → 快速参考大盘股（SPY、AAPL）
      EV/EBITDA → 周期股、重资产（XOM、JPM）
      PEG      → 成长股（TSLA、PLTR）
      PB       → 金融、地产、保险（BRK、JPM）
    """
    
    agent_name = "ValuationAgent"
    DEFAULT_WACC = 0.085   # 默认加权平均资本成本 8.5%
    DEFAULT_G  = 0.025    # 默认永续增长率 2.5%
    
    def __init__(self, wacc: float = None, terminal_g: float = None):
        self.wacc = wacc or self.DEFAULT_WACC
        self.terminal_g = terminal_g or self.DEFAULT_G
    
    def analyze(self, ticker: str, market: str = "US", **kwargs) -> AgentSignal:
        """
        主分析入口。
        
        Args:
            ticker: 股票代码
            market: "US" | "CN" | "HK"
            **kwargs: 可选参数
                wacc: 加权平均资本成本（默认 8.5%）
                terminal_g: 永续增长率（默认 2.5%）
                fcff_override: 手动传入 FCFF（避免计算误差）
        
        Returns:
            AgentSignal
        """
        if "wacc" in kwargs:
            self.wacc = kwargs["wacc"]
        if "terminal_g" in kwargs:
            self.terminal_g = kwargs["terminal_g"]
        
        raw = self._get_data(ticker, market)
        if "error" in raw:
            return AgentSignal(
                agent=self.agent_name, ticker=ticker, signal="NEUTRAL",
                confidence=0, reasoning=[f"数据获取失败: {raw['error']}"],
                metrics={}, valuation_range=(0, 0), data_freshness="N/A"
            )
        
        # ── 计算6种估值 ───────────────────────────────────────────────
        valuations = {}
        methods_used = []
        
        price = raw.get("price", 0)
        if not price:
            return AgentSignal(
                agent=self.agent_name, ticker=ticker, signal="NEUTRAL",
                confidence=0, reasoning=["价格数据缺失"],
                metrics={}, valuation_range=(0, 0), data_freshness="N/A"
            )
        
        # ── 方法论总览 ──────────────────────────────────────────
        methodology = (
            "ValuationAgent 综合6种估值方法论，取去掉最高最低后的中间均值作为内在价值。"
            "各方法适用场景：DCF→盈利稳定成熟公司；DDM→高分红蓝筹；"
            "PE Band→大盘股快速参考；EV/EBITDA→周期股/重资产；"
            "PEG→成长股；PB→金融/地产/保险。"
        )
        
        all_steps = []
        
        # 1. DCF
        dcf_value, dcf_steps = self._dcf(raw)
        if dcf_value > 0:
            valuations["DCF"] = dcf_value
            methods_used.append("DCF")
            all_steps.extend(dcf_steps)
        
        # 2. DDM
        ddm_value, ddm_steps = self._ddm(raw)
        if ddm_value > 0:
            valuations["DDM"] = ddm_value
            methods_used.append("DDM")
            all_steps.extend(ddm_steps)
        
        # 3. PE Band
        pe_value, pe_steps = self._pe_band(raw)
        if pe_value > 0:
            valuations["PE_BAND"] = pe_value
            methods_used.append("PE_BAND")
            all_steps.extend(pe_steps)
        
        # 4. EV/EBITDA
        ev_value, ev_steps = self._ev_ebitda(raw)
        if ev_value > 0:
            valuations["EV_EBITDA"] = ev_value
            methods_used.append("EV_EBITDA")
            all_steps.extend(ev_steps)
        
        # 5. PEG
        peg_value, peg_steps = self._peg(raw)
        if peg_value > 0:
            valuations["PEG"] = peg_value
            methods_used.append("PEG")
            all_steps.extend(peg_steps)
        
        # 6. PB
        pb_value, pb_steps = self._pb(raw)
        if pb_value > 0:
            valuations["PB"] = pb_value
            methods_used.append("PB")
            all_steps.extend(pb_steps)
        
        # ── 综合估值：去掉最高最低，取中间均值 ─────────────────────────
        valid_vals = [v for v in valuations.values() if v > 0]
        if not valid_vals:
            return AgentSignal(
                agent=self.agent_name, ticker=ticker, signal="NEUTRAL",
                confidence=10, reasoning=["所有估值方法均失败"],
                metrics={"raw_data_keys": list(raw.keys())},
                valuation_range=(price * 0.8, price * 1.2), data_freshness=raw.get("fetch_time", "N/A"),
                raw_data=raw,
            )
        
        valid_vals_sorted = sorted(valid_vals)
        # 去掉最高1个和最低1个（极端值）
        if len(valid_vals_sorted) >= 3:
            trimmed = valid_vals_sorted[1:-1]
        else:
            trimmed = valid_vals_sorted
        
        intrinsic = sum(trimmed) / len(trimmed)
        intrinsic_low = min(trimmed)
        intrinsic_high = max(trimmed)
        
        # ── 信号判定 ──────────────────────────────────────────────────
        margin = (price - intrinsic) / intrinsic
        upside = (intrinsic - price) / price * 100
        
        if margin < -0.20:
            signal = "BULLISH"
            confidence = int(min(95, 60 + abs(margin) * 200))
            reasoning = [
                f"✅ 显著低估：当前价 ${price:.2f} vs 内在价值 ${intrinsic:.2f}",
                f"   上涨空间: +{upside:.1f}% | 安全边际: {-margin:.1%}",
                f"   估值方法: {', '.join(methods_used)}",
            ]
        elif margin < -0.05:
            signal = "SLIGHTLY_BULLISH"
            confidence = int(min(75, 50 + abs(margin) * 400))
            reasoning = [
                f"⚡ 略低估：当前价 ${price:.2f} vs 内在价值 ${intrinsic:.2f}",
                f"   上涨空间: +{upside:.1f}% | 安全边际: {-margin:.1%}",
                f"   估值方法: {', '.join(methods_used)}",
            ]
        elif margin > 0.20:
            signal = "BEARISH"
            confidence = int(min(95, 60 + margin * 200))
            reasoning = [
                f"🔴 显著高估：当前价 ${price:.2f} vs 内在价值 ${intrinsic:.2f}",
                f"   下行风险: {margin:.1%} | 高估幅度: {margin:.1%}",
                f"   估值方法: {', '.join(methods_used)}",
            ]
        elif margin > 0.05:
            signal = "SLIGHTLY_BEARISH"
            confidence = int(min(75, 50 + margin * 400))
            reasoning = [
                f"⚠️ 略高估：当前价 ${price:.2f} vs 内在价值 ${intrinsic:.2f}",
                f"   下行风险: {margin:.1%}",
                f"   估值方法: {', '.join(methods_used)}",
            ]
        else:
            signal = "NEUTRAL"
            confidence = 50
            reasoning = [
                f"➡️ 合理区间：当前价 ${price:.2f} ≈ 内在价值 ${intrinsic:.2f}",
                f"   偏离度: {margin:.1%}（±10% 内）",
                f"   估值方法: {', '.join(methods_used)}",
            ]
        
        # ── 分析师目标价参考 ───────────────────────────────────────────
        analyst_target = raw.get("analyst_target", 0)
        if analyst_target and analyst_target > 0:
            analyst_upside = (analyst_target - price) / price * 100
            reasoning.append(f"   分析师目标价: ${analyst_target:.2f} ({analyst_upside:+.1f}%)")
        
        # ── 详细估值区间 ──────────────────────────────────────────────
        valuation_detail = {}
        for method, val in valuations.items():
            pct_diff = (val - price) / price * 100
            valuation_detail[method] = {
                "value": round(val, 2),
                "vs_price_pct": round(pct_diff, 1),
                "vs_intrinsic_pct": round((val - intrinsic) / intrinsic * 100, 1),
            }
        
        # ── 公式列表 ──────────────────────────────────────────────
        formulas = [
            "DCF: V = Σ(FCFF_t / (1+WACC)^t) + TV/(1+WACC)^n, TV = FCFF_n×(1+g)/(WACC-g)",
            "DDM: V = D₁ / (WACC - g)",
            "PE Band: V = Mean(PE_hist) × Forward EPS",
            "EV/EBITDA: V = (EBITDA × 合理倍数 - 净债务) / 股数",
            "PEG: V = (增长率 × 0.8) × Forward EPS  (彼得林奇标准)",
            "PB: V = BVPS × 合理PB倍数",
            "综合: 内在价值 = trim_mean(valid_vals) — 去掉最高最低，取中间均值",
        ]
        
        # ── 假设列表 ──────────────────────────────────────────────
        assumptions = [
            f"WACC = {self.wacc:.1%}（可通过 kwargs.wacc 调整）",
            f"永续增长率 g = {self.terminal_g:.1%}（可通过 kwargs.terminal_g 调整）",
            "FCFF 增长率 ≈ 营收增长率（可通过 kwargs.fcff_override 手动指定）",
            "综合估值去掉最高/最低方法论以消除极端值影响",
        ]
        
        return AgentSignal(
            agent=self.agent_name,
            ticker=ticker,
            signal=signal,
            confidence=confidence,
            reasoning=reasoning,
            metrics={
                **valuation_detail,
                "intrinsic_value": round(intrinsic, 2),
                "intrinsic_range": [round(intrinsic_low, 2), round(intrinsic_high, 2)],
                "current_price": price,
                "upside_pct": round(upside, 1),
                "margin_of_safety": round(-margin, 3) if margin < 0 else 0,
                "wacc": self.wacc,
                "terminal_g": self.terminal_g,
                "methods_count": len(valid_vals),
                "methods_used": methods_used,
            },
            valuation_range=(round(intrinsic_low, 2), round(intrinsic_high, 2)),
            data_freshness=raw.get("fetch_time", "N/A"),
            methodology=methodology,
            step_by_step=all_steps,
            formulas=formulas,
            assumptions=assumptions,
            raw_data=raw,
        )
    
    def _dcf(self, raw: Dict):
        """
        DCF 自由现金流折现 — 返回 (每股价值, 推导步骤)
        
        公式：
          V = Σ(FCFF_t / (1+WACC)^t) + TV / (1+WACC)^n
          TV = FCFF_n × (1+g) / (WACC - g)
        
        参数：
          WACC = 8.5%（美国大盘股基准，可调整）
          g    = 2.5%（永续增长率）
          n    = 5年（显性预测期）
        """
        steps = []
        fcf = raw.get("free_cash_flow", 0) or raw.get("fcf_per_share", 0) * raw.get("shares_outstanding", 0)
        shares = raw.get("shares_outstanding", 0)
        price = raw.get("price", 0)
        net_debt = raw.get("net_debt", 0)
        growth = raw.get("revenue_growth", 0) or 0.10
        growth = min(max(growth, -0.20), 0.40)
        wacc = self.wacc
        g = self.terminal_g
        n = 5

        # Step 1: 确定 FCFF
        if not fcf or fcf <= 0:
            net_income = raw.get("net_income", 0)
            if net_income > 0:
                fcf = net_income * 0.8
                steps.append({
                    "step": "Step 1 — 确定 FCFF（自由现金流）",
                    "formula": "FCFF ≈ 净利润 × 80% = ${:.2f} × 80% = ${:.2f}".format(
                        raw.get("net_income", 0), fcf),
                    "input": f"净利润=${raw.get('net_income', 0):.2f}, 假设FCF margin=80%",
                    "output": f"FCFF = ${fcf:.2f}"
                })
        else:
            steps.append({
                "step": "Step 1 — 确定 FCFF（自由现金流）",
                "formula": "FCFF = free_cash_flow",
                "input": f"FCFF = ${fcf:.2f}",
                "output": f"FCFF = ${fcf:.2f}"
            })
        
        if not fcf or fcf <= 0 or not shares:
            steps.append({"step": "DCF 失败", "formula": "N/A", "input": "FCFF≤0 或 shares=0", "output": None})
            return 0.0, steps
        
        # Step 2: 5年 FCF 预测
        fcf_vals = []
        rows = []
        for t in range(1, n + 1):
            fcf_t = fcf * (1 + growth) ** t
            disc = fcf_t / (1 + wacc) ** t
            fcf_vals.append((t, fcf_t, disc))
            rows.append(
                f"  t={t}: FCF={fcf_t:.2f} → 折现={fcf_t:.2f}/(1+{wacc})^{t}={disc:.2f}"
            )
        
        steps.append({
            "step": f"Step 2 — 5年 FCF 预测（增长率 g={growth:.1%}）",
            "formula": f"FCF_t = FCF_0 × (1+{growth:.1%})^{t}",
            "input": f"FCFF=${fcf:.2f}, g={growth:.1%}, n=5年",
            "output": "\n".join(rows)
        })
        
        sum_discounted = sum(d[2] for d in fcf_vals)
        
        # Step 3: 终值
        fcf_n = fcf_vals[-1][1] * (1 + g)
        terminal_value = fcf_n / (wacc - g) if wacc > g else 0
        discounted_tv = terminal_value / (1 + wacc) ** n
        
        steps.append({
            "step": "Step 3 — 终值计算（Gordon Growth Model）",
            "formula": f"TV = FCF_n × (1+g) / (WACC-g) = {fcf_n:.2f}×(1+{g:.1%})/({wacc:.1%}-{g:.1%})",
            "input": f"FCF_5=${fcf_n:.2f}, g={g:.1%}, WACC={wacc:.1%}",
            "output": f"TV=${terminal_value:.2f} → 折现TV=${discounted_tv:.2f}"
        })
        
        # Step 4: 企业价值 → 权益价值
        enterprise_value = sum_discounted + discounted_tv
        equity_value = enterprise_value - net_debt
        value_per_share = equity_value / shares if shares > 0 else 0
        
        steps.append({
            "step": "Step 4 — 企业价值 → 每股权益价值",
            "formula": "EV = Σ(FCF折现) + PV(TV) = ${:.2f} + ${:.2f}",
            "input": f"企业价值=${enterprise_value:.2f}, 净债务=${net_debt:.2f}, 股数={shares:.0f}",
            "output": f"权益价值=${equity_value:.2f} → 每股 DCF = ${value_per_share:.2f}"
        })
        
        steps.append({
            "step": "假设",
            "formula": "",
            "input": f"WACC={wacc:.1%}, 永续增长率={g:.1%}, 营收增速={growth:.1%}",
            "output": f"每股内在价值: ${value_per_share:.2f} (vs 当前价${price:.2f})"
        })
        
        return value_per_share, steps
    
    def _ddm(self, raw: Dict):
        """
        DDM 股利折现模型 — 返回 (每股价值, 推导步骤)
        适用于高分红股票（JNJ、PG、可乐等）
        
        公式：V = D₁ / (WACC - g)
        """
        steps = []
        dps = raw.get("dps", 0)
        eps = raw.get("eps_trailing", 0)
        price = raw.get("price", 0)
        div_yield = raw.get("dividend_yield", 0)
        earnings_g = raw.get("earnings_growth", 0) or raw.get("revenue_growth", 0) or 0.02
        earnings_g = min(max(earnings_g, -0.10), 0.15)
        wacc = self.wacc
        
        # Step 1: 确定 DPS
        if dps <= 0:
            if div_yield > 0 and eps > 0:
                dps = div_yield * price
                steps.append({
                    "step": "Step 1 — 确定每股股利（DPS）",
                    "formula": "DPS = 股息率 × 当前价 = {:.1%} × ${:.2f}".format(div_yield, price),
                    "input": f"股息率={div_yield:.1%}, 当前价=${price:.2f}",
                    "output": f"DPS = ${dps:.2f}"
                })
            elif eps > 0:
                dps = eps * 0.60
                steps.append({
                    "step": "Step 1 — 确定每股股利（DPS）",
                    "formula": "DPS ≈ EPS × 60% = ${:.2f} × 60%".format(eps),
                    "input": f"EPS=${eps:.2f}, 假设分红率=60%",
                    "output": f"DPS = ${dps:.2f}"
                })
            else:
                steps.append({"step": "DDM 失败", "formula": "DPS=0且无法估算", "input": "", "output": None})
                return 0.0, steps
        else:
            steps.append({
                "step": "Step 1 — 确定每股股利（DPS）",
                "formula": "DPS = dividendRate",
                "input": f"DPS = ${dps:.2f}",
                "output": f"DPS = ${dps:.2f}"
            })
        
        if dps <= 0:
            return 0.0, steps
        
        # Step 2: Gordon Growth Model
        d1 = dps * (1 + earnings_g)
        fair_value = d1 / (wacc - earnings_g) if wacc > earnings_g else 0
        
        steps.append({
            "step": f"Step 2 — Gordon Growth Model",
            "formula": f"V = D₁ / (WACC - g) = {d1:.2f} / ({wacc:.1%} - {earnings_g:.1%})",
            "input": f"D₁=${d1:.2f}, WACC={wacc:.1%}, g={earnings_g:.1%}",
            "output": f"每股价值 = ${fair_value:.2f} (vs 当前价${price:.2f})"
        })
        
        return fair_value, steps
    
    def _pe_band(self, raw: Dict):
        """
        PE Band（市盈率通道）— 返回 (每股价值, 推导步骤)
        
        用历史 PE 分位数 + 未来 EPS 推算合理价格。
        """
        import numpy as np
        steps = []
        eps_fwd = raw.get("eps_forward", 0) or raw.get("eps_trailing", 0)
        eps_trail = raw.get("eps_trailing", 0)
        hist_prices = raw.get("hist_prices", [])
        price = raw.get("price", 0)
        pe_trail = raw.get("pe_trailing", 0)
        
        if not eps_fwd or eps_fwd <= 0:
            steps.append({"step": "PE Band 失败", "formula": "无 Forward EPS", "input": "", "output": None})
            return 0.0, steps
        
        steps.append({
            "step": "Step 1 — 确定 Forward EPS",
            "formula": "Forward EPS = info.forwardEps",
            "input": f"Forward EPS = ${eps_fwd:.2f}",
            "output": f"Forward EPS = ${eps_fwd:.2f}"
        })
        
        if hist_prices and len(hist_prices) >= 60:
            arr = np.array(hist_prices)
            pe_hist = arr / eps_fwd
            pe_mean = np.mean(pe_hist)
            pe_p20 = np.percentile(pe_hist, 20)
            pe_p80 = np.percentile(pe_hist, 80)
            pe_trail_calc = price / eps_fwd if price and eps_fwd > 0 else 0
            
            steps.append({
                "step": f"Step 2 — 历史 PE 分位数（{len(hist_prices)}日数据）",
                "formula": "PE_t = 历史价格_t / Forward EPS",
                "input": f"历史价格序列({len(hist_prices)}天), Forward EPS=${eps_fwd:.2f}",
                "output": f"PE均值={pe_mean:.1f}x, P20={pe_p20:.1f}x, P80={pe_p80:.1f}x"
            })
            
            fair_pe = pe_mean
            fair_price = fair_pe * eps_fwd
            steps.append({
                "step": "Step 3 — 合理价格 = PE均值 × Forward EPS",
                "formula": f"Fair Price = {pe_mean:.1f} × ${eps_fwd:.2f}",
                "input": f"合理PE={pe_mean:.1f}x, Forward EPS=${eps_fwd:.2f}",
                "output": f"每股价值 = ${fair_price:.2f} (当前PE={pe_trail_calc:.1f}x)"
            })
        else:
            # 回退：PE 15-25
            fair_pe = min(max(pe_trail if pe_trail > 0 else 20, 15), 30)
            fair_price = fair_pe * eps_fwd
            steps.append({
                "step": "Step 2 — 回退方案（PE 15-30 区间）",
                "formula": f"Fair Price = PE × Forward EPS = {fair_pe:.0f} × ${eps_fwd:.2f}",
                "input": f"合理PE={fair_pe:.0f}x, Forward EPS=${eps_fwd:.2f}",
                "output": f"每股价值 = ${fair_price:.2f}"
            })
        
        return fair_price, steps
    
    def _ev_ebitda(self, raw: Dict):
        """
        EV/EBITDA 估值 — 返回 (每股价值, 推导步骤)
        适用于周期股、重资产公司（XOM、JPM、BA）
        
        公式：
          Equity Value = (EBITDA × 合理EV/EBITDA倍数) - 净债务
          每股价值 = Equity Value / 股数
        """
        steps = []
        ev_ebitda = raw.get("ev_ebitda", 0)
        ebitda = raw.get("ebitda", 0)
        market_cap = raw.get("market_cap", 0)
        net_debt = raw.get("net_debt", 0)
        shares = raw.get("shares_outstanding", 1)
        price = raw.get("price", 0)
        
        if not ebitda or ebitda <= 0:
            steps.append({"step": "EV/EBITDA 失败", "formula": "EBITDA=0", "input": "", "output": None})
            return 0.0, steps
        
        steps.append({
            "step": "Step 1 — 确定 EBITDA",
            "formula": "EBITDA = earnings before interest, taxes, depreciation & amortization",
            "input": f"EBITDA = ${ebitda:.2f}",
            "output": f"EBITDA = ${ebitda:.2f}"
        })
        
        if ev_ebitda > 0:
            steps.append({
                "step": "Step 2 — 当前 EV/EBITDA",
                "formula": "当前EV/EBITDA = enterpriseToEbitda",
                "input": f"当前EV/EBITDA = {ev_ebitda:.1f}x",
                "output": f"当前EV/EBITDA = {ev_ebitda:.1f}x"
            })
        
        # 合理 EV/EBITDA 倍数
        fair_multiple = min(max(ev_ebitda if ev_ebitda > 0 else 12, 8), 18)
        steps.append({
            "step": "Step 3 — 确定合理 EV/EBITDA 倍数",
            "formula": f"合理EV/EBITDA = clamp(当前值, 8, 18) = {fair_multiple:.1f}x",
            "input": f"合理区间: 8x-18x，取{fair_multiple:.1f}x",
            "output": f"合理EV/EBITDA = {fair_multiple:.1f}x"
        })
        
        fair_ev = ebitda * fair_multiple
        equity_value = fair_ev - net_debt
        value_per_share = equity_value / shares if shares > 0 else 0
        
        steps.append({
            "step": "Step 4 — 权益价值 = EV - 净债务",
            "formula": f"EV = EBITDA × {fair_multiple:.1f} = ${ebitda:.2f} × {fair_multiple:.1f}x = ${fair_ev:.2f}",
            "input": f"EBITDA=${ebitda:.2f}, 净债务=${net_debt:.2f}, 股数={shares:.0f}",
            "output": f"权益价值=${equity_value:.2f} → 每股=${value_per_share:.2f}"
        })
        
        return value_per_share, steps
    
    def _peg(self, raw: Dict):
        """
        PEG 估值 — 返回 (每股价值, 推导步骤)
        适用于成长股（TSLA、PLTR、NVDA）
        
        公式：
          PEG = PE(forward) / 增长率(%)
          PEG = 1 → 合理估值
          PEG < 1 → 被低估；PEG > 1.5 → 被高估
          合理 PE = 增长率 × 0.8（彼得林奇标准）
        """
        steps = []
        pe_fwd = raw.get("pe_forward", 0) or raw.get("pe_trailing", 0)
        growth = (raw.get("earnings_growth", 0) or raw.get("revenue_growth", 0)) * 100
        eps_fwd = raw.get("eps_forward", 0) or raw.get("eps_trailing", 0)
        price = raw.get("price", 0)
        
        if not pe_fwd or pe_fwd <= 0 or growth == 0 or eps_fwd <= 0:
            steps.append({
                "step": "PEG 失败",
                "formula": "PEG = PE_forward / 增长率",
                "input": f"PE_forward={pe_fwd:.1f}, 增长率={growth:.1f}%, EPS_forward={eps_fwd:.2f}",
                "output": None
            })
            return 0.0, steps
        
        # 当前 PEG
        peg_current = pe_fwd / growth if growth != 0 else 0
        steps.append({
            "step": "Step 1 — 当前 PEG",
            "formula": f"PEG = PE_forward / 增长率 = {pe_fwd:.1f} / {growth:.1f}% = {peg_current:.2f}",
            "input": f"PE_forward={pe_fwd:.1f}x, 增长率={growth:.1f}%",
            "output": f"当前PEG = {peg_current:.2f} ({'被低估' if peg_current < 1 else '被高估' if peg_current > 1.5 else '合理区间'})"
        })
        
        # 彼得林奇：合理PEG=1 → 合理PE = 增长率 × 0.8
        fair_pe = min(max(growth * 0.8, 10), 60)
        fair_price = fair_pe * eps_fwd
        
        steps.append({
            "step": f"Step 2 — 彼得林奇合理 PE（PEG=1）",
            "formula": f"合理PE = 增长率 × 0.8 = {growth:.1f}% × 0.8 = {fair_pe:.1f}x",
            "input": f"增长率={growth:.1f}%, EPS_forward=${eps_fwd:.2f}",
            "output": f"合理PE={fair_pe:.1f}x → 每股价值=${fair_price:.2f}"
        })
        
        return fair_price, steps
    
    def _pb(self, raw: Dict):
        """
        PB 净资产估值 — 返回 (每股价值, 推导步骤)
        适用于金融、地产、保险（BRK、JPM、GS）
        
        公式：
          每股价值 = BVPS × 合理 PB 倍数
          合理 PB = 当前 PB（行业中性）
        """
        steps = []
        bvps = raw.get("book_value_per_share", 0)
        pb = raw.get("pb", 0)
        price = raw.get("price", 0)
        
        if not bvps or bvps <= 0:
            steps.append({"step": "PB 失败", "formula": "BVPS=0", "input": "", "output": None})
            return 0.0, steps
        
        steps.append({
            "step": "Step 1 — 每股净资产（BVPS）",
            "formula": "BVPS = bookValue (股东权益 / 流通股)",
            "input": f"BVPS = ${bvps:.2f}",
            "output": f"BVPS = ${bvps:.2f}"
        })
        
        fair_pb = min(max(pb if pb > 0 else 1.5, 0.8), 3.5)
        fair_price = fair_pb * bvps
        steps.append({
            "step": "Step 2 — 合理 PB（行业中性）",
            "formula": f"合理PB = clamp(当前PB, 0.8, 3.5) = {fair_pb:.1f}x",
            "input": f"当前PB={pb:.1f}x → 取{fair_pb:.1f}x",
            "output": f"每股价值 = BVPS ${bvps:.2f} × {fair_pb:.1f}x = ${fair_price:.2f}"
        })
        
        return fair_price, steps
    
    def batch_analyze(self, tickers: List[str], market: str = "US", **kwargs) -> Dict[str, AgentSignal]:
        """批量分析多个标的"""
        results = {}
        for t in tickers:
            try:
                results[t] = self.analyze(t, market, **kwargs)
            except Exception as e:
                results[t] = AgentSignal(
                    agent=self.agent_name, ticker=t, signal="NEUTRAL",
                    confidence=0, reasoning=[f"分析失败: {e}"],
                    metrics={}, valuation_range=(0, 0), data_freshness="N/A"
                )
        return results
    
    def summary(self, signals: Dict[str, AgentSignal]) -> str:
        """生成汇总报告"""
        lines = ["## 📊 ValuationAgent 汇总报告", ""]
        
        # 按信号排序
        bull = {t: s for t, s in signals.items() if s.signal in ("BULLISH", "SLIGHTLY_BULLISH")}
        bear = {t: s for t, s in signals.items() if s.signal in ("BEARISH", "SLIGHTLY_BEARISH")}
        neut = {t: s for t, s in signals.items() if s.signal == "NEUTRAL"}
        
        if bull:
            lines.append("📈 **低估（买入候选）**")
            for t, s in bull.items():
                lines.append(f"  {t}: ${s.metrics.get('current_price', 0):.2f} | "
                           f"内在价值 ${s.metrics.get('intrinsic_value', 0):.2f} | "
                           f"上涨 {s.metrics.get('upside_pct', 0):.1f}% | "
                           f"置信 {s.confidence}%")
            lines.append("")
        
        if neut:
            lines.append("➡️ **合理区间**")
            for t, s in neut.items():
                lines.append(f"  {t}: ${s.metrics.get('current_price', 0):.2f} | "
                           f"内在价值 ${s.metrics.get('intrinsic_value', 0):.2f}")
            lines.append("")
        
        if bear:
            lines.append("📉 **高估（回避）**")
            for t, s in bear.items():
                lines.append(f"  {t}: ${s.metrics.get('current_price', 0):.2f} | "
                           f"内在价值 ${s.metrics.get('intrinsic_value', 0):.2f}")
        
        return "\n".join(lines)


# ─── 快捷调用入口 ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ValuationAgent")
    parser.add_argument("ticker", help="股票代码，如 NVDA")
    parser.add_argument("--market", default="US", choices=["US", "CN", "HK"])
    parser.add_argument("--wacc", type=float, default=0.085, help="加权平均资本成本 (默认 0.085)")
    parser.add_argument("--g", type=float, default=0.025, help="永续增长率 (默认 0.025)")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    
    args = parser.parse_args()
    
    agent = ValuationAgent(wacc=args.wacc, terminal_g=args.g)
    result = agent.analyze(args.ticker, args.market)
    
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"🎯 Valuation Agent | {result.ticker}")
        print("=" * 50)
        print(f"信号: {result.signal} | 置信度: {result.confidence}%")
        print(f"当前价格: ${result.metrics.get('current_price', 0):.2f}")
        print(f"内在价值: ${result.metrics.get('intrinsic_value', 0):.2f}")
        print(f"内在区间: ${result.valuation_range[0]:.2f} ~ ${result.valuation_range[1]:.2f}")
        print(f"上涨空间: {result.metrics.get('upside_pct', 0):+.1f}%")
        print()
        for r in result.reasoning:
            print(f"  {r}")
        print()
        print(f"方法: {result.metrics.get('methods_used', [])}")
        print(f"数据: {result.data_freshness}")
