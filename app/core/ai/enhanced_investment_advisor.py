#!/usr/bin/env python3
"""
Enhanced Investment Advisor
Provides clear, data-driven investment recommendations based on comprehensive technical analysis
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class EnhancedInvestmentAdvisor:
    """
    Advanced investment advisor that provides clear, actionable recommendations
    based on multi-timeframe technical analysis and market conditions
    """
    
    def __init__(self):
        self.risk_levels = {
            "conservative": {"max_volatility": 3.0, "rsi_range": (40, 60)},
            "moderate": {"max_volatility": 5.0, "rsi_range": (30, 70)},
            "aggressive": {"max_volatility": 10.0, "rsi_range": (20, 80)}
        }
    
    def generate_investment_advice(self, query: str, data: Dict[str, Any], 
                                 query_info: Dict[str, Any]) -> str:
        """
        Generate comprehensive investment advice based on technical analysis
        """
        try:
            symbol = query_info.get("primary_symbol", "")
            price_data = data.get("price_data", {})
            technical_indicators = data.get("technical_indicators", {})
            timeframe_analysis = data.get("timeframe_analysis", {})
            
            if not price_data or not technical_indicators:
                return self._fallback_response(symbol)
            
            # Perform comprehensive analysis
            analysis = self._perform_technical_analysis(price_data, technical_indicators, timeframe_analysis)
            
            # Generate actionable recommendation
            recommendation = self._generate_recommendation(analysis, symbol)
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Investment advice generation error: {str(e)}")
            return self._fallback_response(query_info.get("primary_symbol", ""))
    
    def _perform_technical_analysis(self, price_data: Dict[str, Any], 
                                  technical_indicators: Dict[str, Any],
                                  timeframe_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive technical analysis across multiple timeframes
        """
        analysis = {
            "current_price": price_data.get("current_price", 0),
            "price_change_24h": price_data.get("price_change_24h", 0),
            "signals": [],
            "risk_level": "moderate",
            "confidence": 0,
            "recommendation": "HOLD",
            "reasoning": []
        }
        
        # RSI Analysis
        rsi = technical_indicators.get("rsi", 50)
        analysis["rsi"] = rsi
        
        if rsi > 70:
            analysis["signals"].append({"type": "BEARISH", "strength": "strong", "indicator": "RSI", "value": rsi})
            analysis["reasoning"].append(f"RSI at {rsi:.1f} indicates overbought conditions")
        elif rsi < 30:
            analysis["signals"].append({"type": "BULLISH", "strength": "strong", "indicator": "RSI", "value": rsi})
            analysis["reasoning"].append(f"RSI at {rsi:.1f} indicates oversold conditions - potential buying opportunity")
        elif 45 <= rsi <= 55:
            analysis["signals"].append({"type": "NEUTRAL", "strength": "weak", "indicator": "RSI", "value": rsi})
            analysis["reasoning"].append(f"RSI at {rsi:.1f} shows neutral momentum")
        
        # Moving Average Analysis
        sma_20_diff = technical_indicators.get("sma_20_diff", 0)
        sma_50_diff = technical_indicators.get("sma_50_diff", 0)
        
        if sma_20_diff > 2 and sma_50_diff > 1:
            analysis["signals"].append({"type": "BULLISH", "strength": "strong", "indicator": "SMA"})
            analysis["reasoning"].append("Price trading well above both 20 and 50 SMAs - strong uptrend")
        elif sma_20_diff < -2 and sma_50_diff < -1:
            analysis["signals"].append({"type": "BEARISH", "strength": "strong", "indicator": "SMA"})
            analysis["reasoning"].append("Price trading below moving averages - downtrend confirmed")
        
        # Bollinger Bands Analysis
        bb_signal = technical_indicators.get("bb_signal", {})
        if bb_signal:
            percent_b = bb_signal.get("percent_b", 0.5)
            bandwidth = bb_signal.get("bandwidth", 2.0)
            
            if percent_b > 0.8:
                analysis["signals"].append({"type": "BEARISH", "strength": "moderate", "indicator": "BB"})
                analysis["reasoning"].append("Price near upper Bollinger Band - potential resistance")
            elif percent_b < 0.2:
                analysis["signals"].append({"type": "BULLISH", "strength": "moderate", "indicator": "BB"})
                analysis["reasoning"].append("Price near lower Bollinger Band - potential support")
            
            if bandwidth > 4.0:
                analysis["reasoning"].append("High volatility environment - increased risk")
                analysis["risk_level"] = "high"
            elif bandwidth < 2.0:
                analysis["reasoning"].append("Low volatility - potential breakout incoming")
        
        # Multi-timeframe Analysis
        timeframe_signals = self._analyze_timeframes(timeframe_analysis)
        analysis["timeframe_signals"] = timeframe_signals
        
        # Determine overall recommendation
        analysis = self._calculate_recommendation(analysis)
        
        return analysis
    
    def _analyze_timeframes(self, timeframe_analysis: Dict[str, Any]) -> Dict[str, str]:
        """
        Analyze trends across multiple timeframes
        """
        timeframe_signals = {}
        
        for timeframe, tf_data in timeframe_analysis.items():
            trend = tf_data.get("trend", "NEUTRAL")
            rsi = tf_data.get("rsi", 50)
            volatility = tf_data.get("volatility", 0)
            
            # Classify timeframe signal
            if "STRONG BULLISH" in trend and rsi < 70:
                timeframe_signals[timeframe] = "STRONG_BUY"
            elif "BULLISH" in trend and rsi < 65:
                timeframe_signals[timeframe] = "BUY"
            elif "STRONG BEARISH" in trend and rsi > 30:
                timeframe_signals[timeframe] = "STRONG_SELL"
            elif "BEARISH" in trend and rsi > 35:
                timeframe_signals[timeframe] = "SELL"
            else:
                timeframe_signals[timeframe] = "HOLD"
        
        return timeframe_signals
    
    def _calculate_recommendation(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate overall recommendation based on all signals
        """
        signals = analysis["signals"]
        timeframe_signals = analysis.get("timeframe_signals", {})
        
        # Weight timeframes (longer timeframes get more weight)
        timeframe_weights = {"1w": 3, "1d": 2, "4h": 1.5, "1h": 1}
        
        bullish_score = 0
        bearish_score = 0
        total_weight = 0
        
        # Score technical indicators
        for signal in signals:
            strength_multiplier = {"strong": 2, "moderate": 1, "weak": 0.5}.get(signal.get("strength", "weak"), 0.5)
            
            if signal["type"] == "BULLISH":
                bullish_score += strength_multiplier
            elif signal["type"] == "BEARISH":
                bearish_score += strength_multiplier
        
        # Score timeframe signals
        for timeframe, signal in timeframe_signals.items():
            weight = timeframe_weights.get(timeframe, 1)
            total_weight += weight
            
            if signal in ["STRONG_BUY", "BUY"]:
                multiplier = 2 if signal == "STRONG_BUY" else 1
                bullish_score += weight * multiplier
            elif signal in ["STRONG_SELL", "SELL"]:
                multiplier = 2 if signal == "STRONG_SELL" else 1
                bearish_score += weight * multiplier
        
        # Calculate confidence
        total_signals = bullish_score + bearish_score
        confidence = min(total_signals / 10, 0.95)  # Cap at 95%
        
        # Determine recommendation
        score_difference = bullish_score - bearish_score
        
        if score_difference > 3:
            recommendation = "STRONG_BUY"
        elif score_difference > 1:
            recommendation = "BUY"
        elif score_difference < -3:
            recommendation = "STRONG_SELL"
        elif score_difference < -1:
            recommendation = "SELL"
        else:
            recommendation = "HOLD"
        
        analysis["recommendation"] = recommendation
        analysis["confidence"] = confidence
        analysis["bullish_score"] = bullish_score
        analysis["bearish_score"] = bearish_score
        
        return analysis
    
    def _generate_recommendation(self, analysis: Dict[str, Any], symbol: str) -> str:
        """
        Generate human-readable investment recommendation
        """
        recommendation = analysis["recommendation"]
        confidence = analysis["confidence"]
        current_price = analysis["current_price"]
        price_change_24h = analysis.get("price_change_24h", 0)
        reasoning = analysis.get("reasoning", [])
        timeframe_signals = analysis.get("timeframe_signals", {})
        
        # Build response
        response_parts = []
        
        # Current price and momentum
        change_pct = price_change_24h * 100
        change_dir = "up" if change_pct > 0 else "down"
        response_parts.append(f"🔍 **{symbol} Analysis** - Current: ${current_price:.2f} ({change_pct:+.2f}%)")
        
        # Main recommendation
        rec_emoji = {
            "STRONG_BUY": "🚀",
            "BUY": "📈", 
            "HOLD": "⏸️",
            "SELL": "📉",
            "STRONG_SELL": "🔻"
        }.get(recommendation, "⏸️")
        
        response_parts.append(f"\n{rec_emoji} **Recommendation: {recommendation}** (Confidence: {confidence:.0%})")
        
        # Action-oriented advice
        if recommendation in ["STRONG_BUY", "BUY"]:
            entry_advice = self._generate_entry_advice(analysis, timeframe_signals)
            response_parts.append(f"\n💡 **Entry Strategy:** {entry_advice}")
        elif recommendation in ["STRONG_SELL", "SELL"]:
            exit_advice = self._generate_exit_advice(analysis)
            response_parts.append(f"\n⚠️ **Exit Strategy:** {exit_advice}")
        else:
            hold_advice = self._generate_hold_advice(analysis)
            response_parts.append(f"\n🎯 **Hold Strategy:** {hold_advice}")
        
        # Key reasons
        if reasoning:
            response_parts.append(f"\n📊 **Key Factors:**")
            for reason in reasoning[:3]:  # Top 3 reasons
                response_parts.append(f"   • {reason}")
        
        # Timeframe analysis
        if timeframe_signals:
            response_parts.append(f"\n⏰ **Multi-Timeframe View:**")
            for tf, signal in timeframe_signals.items():
                signal_emoji = {"STRONG_BUY": "🟢", "BUY": "🟢", "HOLD": "🟡", "SELL": "🔴", "STRONG_SELL": "🔴"}.get(signal, "🟡")
                response_parts.append(f"   {tf}: {signal_emoji} {signal.replace('_', ' ')}")
        
        # Risk warning
        rsi = analysis.get("rsi", 50)
        if rsi > 75 or rsi < 25:
            response_parts.append(f"\n⚠️ **Risk Note:** Extreme RSI levels ({rsi:.1f}) suggest high volatility - consider position sizing carefully.")
        
        return "\n".join(response_parts)
    
    def _generate_entry_advice(self, analysis: Dict[str, Any], timeframe_signals: Dict[str, str]) -> str:
        """Generate specific entry advice for buy recommendations"""
        current_price = analysis["current_price"]
        rsi = analysis.get("rsi", 50)
        
        advice_parts = []
        
        # Entry timing
        if rsi < 40:
            advice_parts.append("Good entry opportunity with oversold conditions")
        elif rsi > 60:
            advice_parts.append("Consider waiting for pullback or enter gradually")
        else:
            advice_parts.append("Neutral RSI allows for immediate entry")
        
        # Position sizing
        if analysis.get("risk_level") == "high":
            advice_parts.append("Use smaller position size due to high volatility")
        else:
            advice_parts.append("Normal position sizing appropriate")
        
        # Stop loss suggestion
        stop_loss_pct = 5 if analysis.get("risk_level") == "high" else 8
        stop_loss_price = current_price * (1 - stop_loss_pct/100)
        advice_parts.append(f"Consider stop-loss near ${stop_loss_price:.2f} ({stop_loss_pct}% below current)")
        
        return ". ".join(advice_parts) + "."
    
    def _generate_exit_advice(self, analysis: Dict[str, Any]) -> str:
        """Generate specific exit advice for sell recommendations"""
        reasoning = analysis.get("reasoning", [])
        
        if any("overbought" in reason.lower() for reason in reasoning):
            return "Consider taking profits as overbought conditions typically lead to corrections. Set alerts for RSI dropping below 65 for potential re-entry."
        elif any("downtrend" in reason.lower() for reason in reasoning):
            return "Exit positions to preserve capital. Wait for trend reversal signals before considering re-entry."
        else:
            return "Reduce exposure and monitor for further weakness. Consider scaling out of positions rather than full exit."
    
    def _generate_hold_advice(self, analysis: Dict[str, Any]) -> str:
        """Generate specific hold advice"""
        rsi = analysis.get("rsi", 50)
        
        if 45 <= rsi <= 55:
            return "Market in consolidation phase. Monitor for breakout signals in either direction. Good time to accumulate on any dips."
        else:
            return "Mixed signals suggest patience. Wait for clearer directional bias before making major position changes."
    
    def _fallback_response(self, symbol: str) -> str:
        """Fallback response when analysis fails"""
        return f"Unable to perform comprehensive analysis for {symbol} at this time. Please check data availability and try again." 