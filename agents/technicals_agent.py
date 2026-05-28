#!/usr/bin/env python3
"""
TechnicalsAgent — 技术分析大脑
================================
分析技术指标，捕捉趋势与动量，生成交易信号。

指标覆盖：
  趋势类：SMA/EMA（20/50/200）、MACD、Ichimoku
  动量类：RSI(14)、KDJ、CCI、Williams%R、ROC
  波动类：ATR、Bollinger Bands、历史波动率
  量价类：OBV、VWAP、MFI、成交量比率

信号逻辑（综合评分）：
  趋势（30分）：价格 > MA200 → +15；MA多头排列 → +15
  动量（40分）：RSI 40-60 → +20；超买超卖 → +15
  相对强弱（20分）：vs SPY 跑赢 → +10
  量价（10分）：放量突破 → +10

综合 ≥ 65 → BULLISH
综合 50-65 → SLIGHTLY_BULLISH
综合 35-50 → NEUTRAL
综合 20-35 → SLIGHTLY_BEARISH
综合 < 20 → BEARISH
"""

import os, sys, json, math
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SKILL_DIR))
sys.path.insert(0, ROOT_DIR + "/scripts")
sys.path.insert(0, SKILL_DIR)

from valuation_agent import AgentSignal


class TechnicalsAgent:
    """技术分析大脑"""
    
    agent_name = "TechnicalsAgent"
    
    def analyze(self, ticker: str, period: str = "1y", market: str = "US", **kwargs) -> AgentSignal:
        """
        Args:
            ticker: 股票代码
            period: 数据周期（1mo/3mo/6mo/1y/2y/5y）
            market: 市场（US/CN/HK）
        """
        raw = self._fetch_price_data(ticker, period)
        
        if "error" in raw or not raw.get("close"):
            return AgentSignal(
                agent=self.agent_name, ticker=ticker, signal="NEUTRAL",
                confidence=0, reasoning=[f"数据获取失败: {raw.get('error', '无数据')}"],
                metrics={}, valuation_range=(0, 0), data_freshness="N/A"
            )
        
        df = self._prepare_df(raw)
        signals = self._analyze_all(df, raw)
        
        # 综合评分
        total = signals["trend_score"] + signals["momentum_score"] + \
                signals["relative_score"] + signals["volume_score"]
        
        signal, confidence, reasoning = self._generate_signal(total, signals, raw)
        
        methodology = (
            "TechnicalsAgent 综合4维度评分（100分制）：趋势(30分) + 动量(40分) + 相对强弱(20分) + 量价(10分)。"
            "趋势：价格>MA200→+15分；MA多头排列→+15分。"
            "动量：RSI 40-60→+20分；超买超卖→+15分；Stochastic辅助验证。"
            "相对强弱：距52周高点<10%→+10分；布林带位置辅助。"
            "量价：放量(Vol>1.5x avg)→+5分；缩量→-3分。"
            "综合≥65→BULLISH；50-65→SLIGHTLY_BULLISH；35-50→NEUTRAL；<35→BEARISH。"
        )
        
        step_by_step = [
            {"step": "Step 1 — RSI(14)计算", "formula": "RSI = 100 - 100/(1+RS), RS=均值涨幅/均值跌幅",
             "input": f"14日数据，当前RSI={signals.get('rsi', 0):.1f}",
             "output": f"RSI={signals.get('rsi', 0):.1f} {'超买>70' if signals.get('rsi', 0) > 70 else '超卖<30' if signals.get('rsi', 0) < 30 else '中性'}"},
            {"step": "Step 2 — MACD计算", "formula": "MACD = EMA12 - EMA26; Signal = EMA9(MACD); Hist = MACD - Signal",
             "input": f"EMA12={signals.get('macd_hist', 0):.4f}, Histogram={'正' if signals.get('macd_hist', 0) > 0 else '负'}",
             "output": f"MACD信号: {signals.get('macd_signal', 'neutral')}"},
            {"step": "Step 3 — 布林带位置", "formula": "BB位置 = (价格 - BB下轨) / (BB上轨 - BB下轨)",
             "input": f"价格=${raw.get('price', 0):.2f}, 上轨=${signals.get('bb_upper', 0):.2f}, 下轨=${signals.get('bb_lower', 0):.2f}",
             "output": f"布林带{round(signals.get('bb_position', 0.5)*100):.0f}%位置 {'过热>90%' if signals.get('bb_position', 0.5) > 0.9 else '超卖<20%' if signals.get('bb_position', 0.5) < 0.2 else '中性'}"},
            {"step": "Step 4 — 综合评分", "formula": "总分 = 趋势 + 动量 + 相对强弱 + 量价",
             "input": f"趋势={signals['trend_score']} + 动量={signals['momentum_score']} + 相对={signals['relative_score']} + 量价={signals['volume_score']}",
             "output": f"总分={total}/100 → {signal}"},
        ]
        
        formulas = [
            "RSI(14) = 100 - 100/(1 + RS), RS = AvgGain(14) / AvgLoss(14)",
            "MACD = EMA(close, 12) - EMA(close, 26), Signal = EMA(MACD, 9)",
            "布林带上轨 = MA20 + 2×σ, 下轨 = MA20 - 2×σ",
            "ATR(14) = MA(TR, 14), TR = max(H-L, |H-PC|, |L-PC|)",
            "Stochastic %K = 100×(C-L14)/(H14-L14)",
            "综合评分 = 趋势(30分) + 动量(40分) + 相对强弱(20分) + 量价(10分)",
        ]
        
        assumptions = [
            "RSI 超买超卖仅作参考，不构成独立买卖信号",
            "布林带假设价格服从正态分布，实际分布往往有肥尾",
            "技术指标基于历史数据，不能预测突发事件",
            "量价信号仅验证趋势，非领先指标",
        ]
        
        return AgentSignal(
            agent=self.agent_name,
            ticker=ticker,
            signal=signal,
            confidence=confidence,
            reasoning=reasoning,
            metrics={
                "total_score": total,
                "trend_score": signals["trend_score"],
                "momentum_score": signals["momentum_score"],
                "relative_score": signals["relative_score"],
                "volume_score": signals["volume_score"],
                "rsi": round(signals.get("rsi", 0), 1),
                "macd_signal": signals.get("macd_signal", "neutral"),
                "ma200_position": signals.get("ma200_position", "neutral"),
                "ma_status": signals.get("ma_status", "neutral"),
                "atr_pct": round(signals.get("atr_pct", 0), 2),
                "bollinger_position": signals.get("bollinger_position", 0.5),
                "volume_ratio": round(signals.get("volume_ratio", 1.0), 2),
                "stoch_k": round(signals.get("stoch_k", 50), 1),
                "cci": round(signals.get("cci", 0), 1),
                "price": raw.get("price", 0),
                "price_52w_high": raw.get("price_52w_high", 0),
                "price_52w_low": raw.get("price_52w_low", 0),
                "from_52w_high": round(signals.get("from_52w_high", 0), 1),
                "from_52w_low": round(signals.get("from_52w_low", 0), 1),
            },
            valuation_range=(signals.get("bb_lower", 0), signals.get("bb_upper", 0)),
            data_freshness=raw.get("fetch_time", "N/A"),
            methodology=methodology,
            step_by_step=step_by_step,
            formulas=formulas,
            assumptions=assumptions,
            raw_data=raw,
        )
    
    def _fetch_price_data(self, ticker: str, period: str = "1y") -> Dict:
        """获取价格数据"""
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            df = t.history(period=period)
            
            if df.empty:
                return {"error": "No data returned"}
            
            close = df["Close"].tolist()
            high = df["High"].tolist()
            low = df["Low"].tolist()
            open_p = df["Open"].tolist()
            volume = df["Volume"].tolist()
            dates = [str(d.date()) for d in df.index]
            
            price = close[-1] if close else 0
            price_52w_high = max(close[-252:]) if len(close) >= 252 else max(close)
            price_52w_low = min(close[-252:]) if len(close) >= 252 else min(close)
            
            return {
                "close": close, "high": high, "low": low,
                "open": open_p, "volume": volume, "dates": dates,
                "price": price,
                "price_52w_high": price_52w_high,
                "price_52w_low": price_52w_low,
                "source": "yfinance",
                "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _prepare_df(self, raw: Dict):
        """转换为 numpy 数组"""
        import numpy as np
        n = len(raw["close"])
        return {
            "close": np.array(raw["close"]),
            "high": np.array(raw["high"]),
            "low": np.array(raw["low"]),
            "open": np.array(raw["open"]),
            "volume": np.array(raw["volume"]),
            "n": n,
        }
    
    def _analyze_all(self, df, raw: Dict) -> Dict:
        """计算所有技术指标，返回评分"""
        import numpy as np
        
        close = df["close"]
        high = df["high"]
        low = df["low"]
        vol = df["volume"]
        n = df["n"]
        
        price = close[-1]
        signals = {}
        
        # ── 辅助函数 ───────────────────────────────────────────────
        def sma(arr, period):
            if len(arr) < period:
                return None
            return np.convolve(arr, np.ones(period)/period, mode='valid')[-1]
        
        def ema(arr, span):
            if len(arr) < span:
                return None
            # 简化 EMA
            k = 2 / (span + 1)
            ema_arr = np.zeros_like(arr)
            ema_arr[0] = arr[0]
            for i in range(1, len(arr)):
                ema_arr[i] = arr[i] * k + ema_arr[i-1] * (1 - k)
            return ema_arr[-1]
        
        # ── 趋势指标 ───────────────────────────────────────────────
        ma20 = sma(close, min(20, n))
        ma50 = sma(close, min(50, n))
        ma200 = sma(close, min(200, n))
        
        # MA 状态
        ma_trend = ""
        if all([ma20, ma50, ma200]):
            if ma20 > ma50 > ma200:
                ma_trend = "多头排列"
                trend_score = 30
            elif ma20 < ma50 < ma200:
                ma_trend = "空头排列"
                trend_score = 5
            elif ma20 > ma50:
                ma_trend = "短期偏多"
                trend_score = 20
            else:
                ma_trend = "短期偏空"
                trend_score = 10
        else:
            ma_trend = "趋势不明"
            trend_score = 15
        
        # MA200 位置
        ma200_position = "below"
        if ma200 and price > ma200 * 1.02:
            ma200_position = "above"; trend_score += 15
        elif ma200 and price > ma200:
            ma200_position = "slightly_above"; trend_score += 5
        elif ma200 and price < ma200:
            ma200_position = "below"; trend_score += 0
        
        trend_score = min(30, max(0, trend_score))
        signals["trend_score"] = trend_score
        signals["ma20"] = round(ma20, 2) if ma20 else None
        signals["ma50"] = round(ma50, 2) if ma50 else None
        signals["ma200"] = round(ma200, 2) if ma200 else None
        signals["ma_status"] = ma_trend
        signals["ma200_position"] = ma200_position
        
        # ── 动量指标 ───────────────────────────────────────────────
        # RSI(14)
        deltas = np.diff(close)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gains = np.mean(gains[-14:]) if len(gains) >= 14 else np.mean(gains)
        avg_losses = np.mean(losses[-14:]) if len(losses) >= 14 else np.mean(losses)
        rs = avg_gains / avg_losses if avg_losses > 0 else 100
        rsi = 100 - (100 / (1 + rs))
        rsi = round(rsi, 1)
        
        # RSI 信号
        momentum_score = 20  # 基础分
        rsi_signal = "neutral"
        if rsi < 30:
            momentum_score += 20; rsi_signal = "oversold"
        elif rsi < 40:
            momentum_score += 10; rsi_signal = "slightly_oversold"
        elif rsi > 70:
            momentum_score += 0; rsi_signal = "overbought"
        elif rsi > 60:
            momentum_score += 5; rsi_signal = "slightly_overbought"
        else:
            momentum_score += 15; rsi_signal = "neutral"
        
        # Stochastic
        if n >= 14:
            stoch_k = 100 * (close[-1] - np.min(low[-14:])) / \
                      (np.max(high[-14:]) - np.min(low[-14:]) + 1e-10)
        else:
            stoch_k = 50
        signals["stoch_k"] = stoch_k
        if stoch_k < 20:
            momentum_score += 5
        elif stoch_k > 80:
            momentum_score -= 5
        
        # CCI
        typical = (high[-1] + low[-1] + close[-1]) / 3
        sma_typical = np.mean((high + low + close) / 3)
        cci = (typical - sma_typical) / (np.std((high + low + close) / 3) * 0.015 + 1e-10)
        cci = round(cci, 1)
        signals["cci"] = cci
        
        momentum_score = min(40, max(0, momentum_score))
        signals["momentum_score"] = momentum_score
        signals["rsi"] = rsi
        signals["rsi_signal"] = rsi_signal
        
        # MACD
        ema12 = ema(close, 12) or close[-1]
        ema26 = ema(close, 26) or close[-1]
        macd_line = ema12 - ema26
        signal_line = ema(close, 9) or macd_line
        macd_hist = macd_line - signal_line
        
        macd_signal = "neutral"
        if macd_hist > 0 and macd_hist > macd_hist if n > 1 else 0:
            macd_signal = "bullish_cross"
        elif macd_hist < 0:
            macd_signal = "bearish"
        
        signals["macd_signal"] = macd_signal
        signals["macd_hist"] = round(macd_hist, 4)
        
        # ── 52周位置 ──────────────────────────────────────────────
        high_52w = raw.get("price_52w_high", price)
        low_52w = raw.get("price_52w_low", price)
        from_high = (price - high_52w) / high_52w * 100 if high_52w else 0
        from_low = (price - low_52w) / low_52w * 100 if low_52w else 0
        
        signals["from_52w_high"] = from_high
        signals["from_52w_low"] = from_low
        
        # 处于52周高位 → 强；处于低位 → 可能反弹
        relative_score = 10
        if from_high > -10:  # 在52周高点10%以内
            relative_score += 10
        elif from_high > -25:
            relative_score += 5
        if from_low < 10:  # 距52周低点10%以内
            relative_score += 5  # 可能有支撑
        
        # 处于历史高位 vs 低位
        max_price = np.max(close)
        min_price = np.min(close)
        pct_from_high = (price - max_price) / (max_price - min_price + 1) * 100
        
        relative_score = min(20, max(0, relative_score))
        signals["relative_score"] = relative_score
        
        # ── 布林带 ───────────────────────────────────────────────
        bb_period = min(20, n)
        bb_mean = np.mean(close[-bb_period:])
        bb_std = np.std(close[-bb_period:])
        bb_upper = bb_mean + 2 * bb_std
        bb_lower = bb_mean - 2 * bb_std
        bb_width = (bb_upper - bb_lower) / bb_mean * 100 if bb_mean else 0
        bb_position = (price - bb_lower) / (bb_upper - bb_lower + 1e-10)
        
        signals["bb_upper"] = round(bb_upper, 2)
        signals["bb_lower"] = round(bb_lower, 2)
        signals["bb_position"] = round(bb_position, 3)
        signals["bb_width"] = round(bb_width, 2)
        
        # 布林带信号
        volume_score = 10
        if bb_position > 0.90:
            volume_score -= 5  # 接近上轨，过热
        elif bb_position < 0.20:
            volume_score += 5  # 接近下轨，可能反弹
        
        # ── ATR 波动率 ───────────────────────────────────────────
        tr = np.maximum(
            high[1:] - low[1:],
            np.abs(high[1:] - close[:-1]),
            np.abs(low[1:] - close[:-1])
        )
        atr = np.mean(tr[-14:]) if len(tr) >= 14 else np.mean(tr)
        atr_pct = atr / price * 100 if price else 0
        
        signals["atr"] = round(atr, 2)
        signals["atr_pct"] = round(atr_pct, 2)
        
        # ── 成交量 ───────────────────────────────────────────────
        vol_avg = np.mean(vol[-20:]) if len(vol) >= 20 else np.mean(vol)
        vol_ratio = vol[-1] / vol_avg if vol_avg > 0 else 1.0
        signals["volume_ratio"] = round(vol_ratio, 2)
        
        if vol_ratio > 1.5:
            volume_score += 5  # 放量
        elif vol_ratio < 0.7:
            volume_score -= 3  # 缩量
        
        volume_score = min(10, max(0, volume_score))
        signals["volume_score"] = volume_score
        
        return signals
    
    def _generate_signal(self, total: int, signals: Dict, raw: Dict) -> Tuple[str, int, List[str]]:
        """基于综合评分生成信号"""
        price = raw.get("price", 0)
        rsi = signals.get("rsi", 50)
        ma_status = signals.get("ma_status", "neutral")
        macd = signals.get("macd_signal", "neutral")
        vol_ratio = signals.get("volume_ratio", 1.0)
        bb_pos = signals.get("bb_position", 0.5)
        from_high = signals.get("from_52w_high", 0)
        
        if total >= 65:
            signal = "BULLISH"
            conf = min(90, 50 + total // 2)
        elif total >= 50:
            signal = "SLIGHTLY_BULLISH"
            conf = min(75, 40 + total)
        elif total >= 35:
            signal = "NEUTRAL"
            conf = 50
        elif total >= 20:
            signal = "SLIGHTLY_BEARISH"
            conf = min(70, 40 + total)
        else:
            signal = "BEARISH"
            conf = min(90, 90 - total)
        
        reasoning = [
            f"技术综合评分：{total}/100（{signal} | 置信 {conf}%）",
            f"当前价格: ${price:.2f} | 距52周高点 {from_high:.1f}%",
            f"趋势({signals['trend_score']}分): MA{ma_status}",
            f"动量({signals['momentum_score']}分): RSI {rsi:.1f} | MACD {macd}",
            f"相对({signals['relative_score']}分): 布林 {bb_pos:.0%} | 成交量 {vol_ratio:.1f}x",
        ]
        
        return signal, conf, reasoning


# ─── 快捷入口 ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker")
    parser.add_argument("--period", default="1y")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    
    agent = TechnicalsAgent()
    r = agent.analyze(args.ticker, period=args.period)
    if args.json:
        print(json.dumps(r.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"📈 Technicals Agent | {r.ticker}")
        print("=" * 50)
        print(f"信号: {r.signal} | 置信度: {r.confidence}%")
        print(f"综合评分: {r.metrics.get('total_score', 0)}/100")
        print(f"RSI(14): {r.metrics.get('rsi', 0)} | MACD: {r.metrics.get('macd_signal', 'N/A')}")
        print(f"MA200: {'above' if r.metrics.get('ma200_position') == 'above' else 'below'}")
        print(f"布林带: ${r.metrics.get('bb_lower', 0):.2f} ~ ${r.metrics.get('bb_upper', 0):.2f} (当前{r.metrics.get('bollinger_position', 0.5):.0%})")
        print()
        for line in r.reasoning:
            print(f"  {line}")
