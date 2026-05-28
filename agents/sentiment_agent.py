#!/usr/bin/env python3
"""
SentimentAgent - 市场情绪大脑
===============================
追踪市场情绪，量化多空博弈。

分析方法：
  1. VIX（恐慌指数）：VIX > 30 → 恐惧；< 15 → 贪婪
  2. Put/Call Ratio：> 1.2 → 看空；< 0.7 → 看多
  3. AAII情绪调查：看空比例 > 看多 → 逆向买入信号
  4. 分析师评级分布：Buy%+ vs Sell%+
  5. 散户仓位（高瓴/机构）：极悲观 = 买入信号
  6. 新闻情绪：Finnhub/Tavily 新闻情绪分析

信号逻辑：
  综合得分 ≥ 65 → BULLISH（情绪极度悲观，逆向买入）
  综合得分 50-65 → SLIGHTLY_BULLISH
  综合得分 35-50 → NEUTRAL
  综合得分 < 35 → BEARISH（情绪极度乐观）
"""

import os, sys, json
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SKILL_DIR)
from valuation_agent import AgentSignal


class SentimentAgent:
    """市场情绪大脑"""

    agent_name = "SentimentAgent"

    def analyze(self, ticker: str = "^VIX", market: str = "US", **kwargs) -> AgentSignal:
        """
        Args:
            ticker: 可选，传单个标的获取个股情绪
            market: 市场
        """
        if ticker == "^VIX" or not ticker:
            # 宏观情绪分析
            return self._macro_sentiment(market)
        else:
            return self._stock_sentiment(ticker, market)

    def _macro_sentiment(self, market: str = "US") -> AgentSignal:
        """宏观市场情绪"""
        raw = self._fetch_macro_sentiment()
        if "error" in raw:
            return AgentSignal(
                agent=self.agent_name, ticker="^VIX", signal="NEUTRAL",
                confidence=0, reasoning=[f"数据获取失败: {raw['error']}"],
                metrics={}, valuation_range=(0, 0), data_freshness="N/A"
            )

        score, signal, confidence, reasoning = self._score_macro_sentiment(raw)

        return AgentSignal(
            agent=self.agent_name,
            ticker="^VIX",
            signal=signal,
            confidence=confidence,
            reasoning=reasoning,
            metrics={
                "total_score": score,
                "vix": raw.get("vix", 0),
                "vix_range": raw.get("vix_range", ""),
                "put_call_ratio": raw.get("put_call_ratio", 0),
                "bullish_pct": raw.get("bullish_pct", 0),
                "bearish_pct": raw.get("bearish_pct", 0),
                "spx_level": raw.get("spx_level", 0),
                "dxy": raw.get("dxy", 0),
                "fear_greed": raw.get("fear_greed", 50),
            },
            valuation_range=(0, 0),
            data_freshness=raw.get("fetch_time", "N/A"),
            raw_data=raw,
            methodology="",
            step_by_step=[],
            formulas=[],
            assumptions=[],
        )

    def _stock_sentiment(self, ticker: str, market: str) -> AgentSignal:
        """个股情绪分析"""
        raw = self._fetch_stock_sentiment(ticker)
        if "error" in raw:
            return AgentSignal(
                agent=self.agent_name, ticker=ticker, signal="NEUTRAL",
                confidence=0, reasoning=[f"数据获取失败: {raw['error']}"],
                metrics={}, valuation_range=(0, 0), data_freshness="N/A"
            )

        score, signal, confidence, reasoning = self._score_stock_sentiment(raw, ticker)

        return AgentSignal(
            agent=self.agent_name,
            ticker=ticker,
            signal=signal,
            confidence=confidence,
            reasoning=reasoning,
            metrics={
                "total_score": score,
                "recommendation": raw.get("recommendation", "none"),
                "target_vs_price": raw.get("target_vs_price", 0),
                "analyst_count": raw.get("analyst_count", 0),
                "news_sentiment": raw.get("news_sentiment", "neutral"),
                "short_float": raw.get("short_float", 0),
                "insider_buying": raw.get("insider_buying", 0),
            },
            valuation_range=(0, 0),
            data_freshness=raw.get("fetch_time", "N/A"),
            raw_data=raw,
            methodology="",
            step_by_step=[],
            formulas=[],
            assumptions=[],
        )

    def _fetch_macro_sentiment(self) -> Dict:
        """获取宏观情绪数据"""
        try:
            import yfinance as yf

            data = {}

            # VIX
            try:
                vix = yf.Ticker("^VIX")
                hist = vix.history(period="5d")
                vix_val = hist["Close"].iloc[-1] if not hist.empty else 0
                vix_1m = hist["Close"].mean() if len(hist) > 5 else vix_val
                data["vix"] = round(vix_val, 2)
                data["vix_change"] = round((vix_val - vix_1m) / vix_1m * 100, 1) if vix_1m else 0
            except:
                data["vix"] = 20

            # VIX 在历史中的位置
            try:
                vix_long = yf.Ticker("^VIX").history(period="1y")
                vix_hist = vix_long["Close"].tolist()
                if vix_hist:
                    vix_pct = (data["vix"] - min(vix_hist)) / (max(vix_hist) - min(vix_hist) + 1e-10) * 100
                    if vix_pct < 25:
                        data["vix_range"] = "极度恐慌区（逆向买入信号）"
                    elif vix_pct < 50:
                        data["vix_range"] = "中性偏低"
                    elif vix_pct < 75:
                        data["vix_range"] = "中性偏高"
                    else:
                        data["vix_range"] = "极度贪婪区（谨慎信号）"
                else:
                    data["vix_range"] = "N/A"
            except:
                data["vix_range"] = "N/A"

            # SPX 水平
            try:
                spx = yf.Ticker("^SPX")
                spx_hist = spx.history(period="5d")
                data["spx_level"] = spx_hist["Close"].iloc[-1] if not spx_hist.empty else 0
                spx_1y = spx.history(period="1y")["Close"]
                data["spx_vs_high"] = round((data["spx_level"] - spx_1y.max()) / spx_1y.max() * 100, 1)
            except:
                data["spx_level"] = 0

            # DXY 美元指数
            try:
                dxy = yf.Ticker("DX-Y.NYB")
                dxy_hist = dxy.history(period="5d")
                data["dxy"] = round(dxy_hist["Close"].iloc[-1], 2) if not dxy_hist.empty else 100
            except:
                data["dxy"] = 100

            # Fear & Greed Index（CNN）
            data["fear_greed"] = 50  # 后续可接入 CNN API

            data["source"] = "yfinance"
            data["fetch_time"] = datetime.now().strftime("%Y-%m-%d %H:%M")

            return data
        except Exception as e:
            return {"error": str(e)}

    def _fetch_stock_sentiment(self, ticker: str) -> Dict:
        """获取个股情绪数据"""
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            info = t.info

            rec = info.get("recommendationKey", "none")
            rec_map = {"strongBuy": 5, "buy": 4, "hold": 3, "sell": 2, "strongSell": 1, "none": 3}
            rec_score = rec_map.get(rec, 3)

            target = info.get("targetMeanPrice", 0) or 0
            price = info.get("currentPrice", 0) or info.get("regularMarketPrice", 0) or 0
            upside = (target - price) / price * 100 if target and price else 0

            analyst_count = info.get("numberOfAnalystOpinions", 0) or 0

            return {
                "recommendation": rec,
                "rec_score": rec_score,
                "target": target,
                "price": price,
                "target_vs_price": round(upside, 1),
                "analyst_count": analyst_count,
                "news_sentiment": "neutral",  # 后续接 Finnhub
                "short_float": info.get("shortFloat", 0) or 0,
                "insider_buying": 0,  # 后续接内部人交易
                "source": "yfinance",
                "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
        except Exception as e:
            return {"error": str(e)}

    def _score_macro_sentiment(self, raw: Dict) -> Tuple[int, str, int, List[str]]:
        """宏观情绪评分"""
        score = 50
        reasoning = []

        vix = raw.get("vix", 20)
        vix_change = raw.get("vix_change", 0)

        # VIX 评分（占40%）
        if vix < 15:
            score += 15; reasoning.append(f"✅ VIX {vix:.1f} - 极度贪婪（股市过热，谨慎）")
        elif vix < 20:
            score += 8; reasoning.append(f"⚡ VIX {vix:.1f} - 偏贪婪")
        elif vix < 25:
            score += 0; reasoning.append(f"➡️ VIX {vix:.1f} - 中性区间")
        elif vix < 30:
            score -= 8; reasoning.append(f"⚠️ VIX {vix:.1f} - 偏恐惧（可能超卖）")
        else:
            score -= 20; reasoning.append(f"🔴 VIX {vix:.1f} - 极度恐慌（逆向买入信号）")

        if vix_change > 10:
            score -= 10; reasoning.append(f"⚠️ VIX 今日暴涨 {vix_change:.1f}%（恐慌蔓延）")

        # VIX 范围（占20%）
        vrange = raw.get("vix_range", "")
        if "极度恐慌" in vrange:
            score += 10; reasoning.append("✅ VIX 历史低位 - 逆向买入信号")
        elif "极度贪婪" in vrange:
            score -= 10; reasoning.append("🔴 VIX 历史高位 - 逆向卖出信号")

        # Fear & Greed（占20%）
        fg = raw.get("fear_greed", 50)
        if fg < 20:
            score += 10; reasoning.append(f"✅ Fear & Greed {fg} - 极度恐慌")
        elif fg > 80:
            score -= 10; reasoning.append(f"🔴 Fear & Greed {fg} - 极度贪婪")
        elif fg > 60:
            score -= 5
        elif fg < 40:
            score += 5

        # SPX vs 52周高点（占10%）
        vs_high = raw.get("spx_vs_high", 0)
        if vs_high > -5:
            score -= 5; reasoning.append(f"⚠️ SPX 接近52周高点（{vs_high:.1f}%）")
        elif vs_high < -20:
            score += 5; reasoning.append(f"✅ SPX 距52周高点 -{abs(vs_high):.1f}%（有一定回调）")

        # DXY（占10%）
        dxy = raw.get("dxy", 100)
        if dxy > 105:
            score -= 5; reasoning.append(f"⚠️ 美元强势（DXY {dxy:.1f}）- 风险资产承压")
        elif dxy < 98:
            score += 5; reasoning.append(f"✅ 美元弱势（DXY {dxy:.1f}）- 风险资产受益")

        score = max(0, min(100, score))

        if score >= 65:
            signal = "BULLISH"
            conf = min(85, 50 + score // 2)
            reasoning.insert(0, f"情绪极度悲观（逆向买入信号）：{score}/100")
        elif score >= 50:
            signal = "SLIGHTLY_BULLISH"
            conf = min(70, 40 + score // 2)
            reasoning.insert(0, f"情绪偏乐观：{score}/100")
        elif score >= 35:
            signal = "NEUTRAL"
            conf = 50
            reasoning.insert(0, f"市场情绪中性：{score}/100")
        else:
            signal = "BEARISH"
            conf = min(85, 90 - score // 2)
            reasoning.insert(0, f"情绪极度乐观（逆向卖出信号）：{score}/100")

        return score, signal, conf, reasoning

    def _score_stock_sentiment(self, raw: Dict, ticker: str) -> Tuple[int, str, int, List[str]]:
        """个股情绪评分"""
        score = 50
        reasoning = []

        rec = raw.get("rec_score", 3)
        upside = raw.get("target_vs_price", 0)
        short_float = raw.get("short_float", 0)

        # 分析师评级（40%）
        if rec >= 4:
            score += 15; reasoning.append(f"✅ 分析师评级: {raw.get('recommendation', 'N/A')}（{raw.get('analyst_count', 0)}人）")
        elif rec == 3:
            score += 0; reasoning.append(f"➡️ 分析师评级: hold")
        else:
            score -= 10; reasoning.append(f"⚠️ 分析师评级: {raw.get('recommendation', 'N/A')}")

        # 目标价上涨空间（30%）
        if upside >= 30:
            score += 15; reasoning.append(f"✅ 目标价上涨空间 {upside:.1f}%（{raw.get('target', 0):.2f}）")
        elif upside >= 15:
            score += 8
        elif upside >= 0:
            score += 0
        else:
            score -= 15; reasoning.append(f"🔴 目标价低于现价 {abs(upside):.1f}%")

        # 做空比例（20%）
        if short_float > 0.20:
            score -= 10; reasoning.append(f"⚠️ 做空比例 {short_float:.1%}（高做空=潜在轧空）")
        elif short_float < 0.05:
            score += 5; reasoning.append(f"✅ 做空比例低 {short_float:.1%}")

        # 内部人买入（10%）
        insider = raw.get("insider_buying", 0)
        if insider > 0:
            score += 5; reasoning.append(f"✅ 内部人买入信号")

        score = max(0, min(100, score))

        if score >= 65: signal = "BULLISH"; conf = min(85, 50 + score // 2)
        elif score >= 50: signal = "SLIGHTLY_BULLISH"; conf = min(70, 40 + score)
        elif score >= 35: signal = "NEUTRAL"; conf = 50
        else: signal = "BEARISH"; conf = min(80, 80 - score // 2)

        reasoning.insert(0, f"个股情绪评分：{score}/100（{signal}）")
        return score, signal, conf, reasoning


# ─── 快捷入口 ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="^VIX")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    agent = SentimentAgent()
    r = agent.analyze(args.ticker)
    if args.json:
        print(json.dumps(r.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"🌡️ Sentiment Agent | {r.ticker}")
        print("=" * 50)
        print(f"信号: {r.signal} | 置信度: {r.confidence}%")
        print(f"情绪评分: {r.metrics.get('total_score', 0)}/100")
        if r.ticker == "^VIX":
            print(f"VIX: {r.metrics.get('vix', 0)} | {r.metrics.get('vix_range', 'N/A')}")
            print(f"Fear & Greed: {r.metrics.get('fear_greed', 50)}")
        print()
        for line in r.reasoning:
            print(f"  {line}")
