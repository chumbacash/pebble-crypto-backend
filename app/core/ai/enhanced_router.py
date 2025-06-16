"""
Enhanced Query Router implementing Anthropic's Agent Patterns

This module enhances the existing MarketAgent with:
🎯 ROUTING: Smart query classification for better handling
⚡ PARALLELIZATION: Optimized multi-asset processing  
🔍 TRANSPARENCY: Clear reasoning steps and confidence scoring
📊 EVALUATOR: Response quality assessment and improvement

Based on: https://www.anthropic.com/engineering/building-effective-agents
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger("CryptoPredictAPI")

class QueryType(Enum):
    """Enhanced query types for better routing"""
    SIMPLE_PRICE = "simple_price"           # "What's BTC price?"
    MULTI_ASSET = "multi_asset"             # "Show me BTC, ETH, SOL prices"
    COMPARISON = "comparison"               # "Compare BTC vs ETH"
    TECHNICAL_ANALYSIS = "technical_analysis" # "BTC technical indicators"
    PORTFOLIO = "portfolio"                 # "Analyze my portfolio"
    PREDICTION = "prediction"               # "Should I buy BTC?"
    MARKET_OVERVIEW = "market_overview"     # "How's the market today?"

class QueryComplexity(Enum):
    """Complexity levels for routing optimization"""
    SIMPLE = "simple"      # 1 symbol, basic data
    MODERATE = "moderate"  # 2-5 symbols, some analysis
    COMPLEX = "complex"    # 5+ symbols, predictions, correlations

@dataclass
class QueryInsights:
    """Structured query analysis results"""
    query_type: QueryType
    complexity: QueryComplexity
    symbols: List[str]
    confidence: float
    reasoning: List[str]
    estimated_response_time: float

class EnhancedQueryRouter:
    """
    Lightweight enhancement module for existing MarketAgent
    Implements Anthropic's routing and transparency patterns
    """
    
    def __init__(self):
        """Initialize router with pattern configurations"""
        self.routing_patterns = self._setup_patterns()
        self.performance_metrics = {
            "queries_processed": 0,
            "average_confidence": 0.0,
            "routing_accuracy": 0.0
        }
        logger.info("🚀 Enhanced Query Router initialized")
    
    def _setup_patterns(self) -> Dict[QueryType, Dict[str, Any]]:
        """Setup routing patterns for query classification"""
        return {
            QueryType.SIMPLE_PRICE: {
                "patterns": [
                    r'\b(?:price|cost|worth|value)\s+(?:of\s+)?(?:BTC|ETH|SOL|ADA|DOGE)\b',
                    r'\b(?:current|now)\s+(?:price|value)\b',
                    r'\b(?:how much|what.*cost)\b'
                ],
                "keywords": ["price", "current", "cost", "worth", "value"],
                "complexity_factor": 1.0
            },
            QueryType.MULTI_ASSET: {
                "patterns": [
                    r'\b(?:BTC|ETH|SOL|ADA|DOGE).*(?:and|,).*(?:BTC|ETH|SOL|ADA|DOGE)\b',
                    r'\b(?:prices|values)\s+(?:of|for)\s+(?:multiple|several)\b'
                ],
                "keywords": ["and", "multiple", "all", "prices", "list"],
                "complexity_factor": 2.0
            },
            QueryType.COMPARISON: {
                "patterns": [
                    r'\b(?:compare|vs|versus|against)\b',
                    r'\b(?:better|best|which)\s+(?:is\s+)?(?:better|performing)\b'
                ],
                "keywords": ["compare", "vs", "versus", "better", "which"],
                "complexity_factor": 2.5
            },
            QueryType.TECHNICAL_ANALYSIS: {
                "patterns": [
                    r'\b(?:technical|indicator|analysis|rsi|macd|bollinger)\b',
                    r'\b(?:trend|momentum|volatility|support|resistance)\b'
                ],
                "keywords": ["technical", "analysis", "indicator", "trend", "volatility"],
                "complexity_factor": 3.0
            },
            QueryType.PORTFOLIO: {
                "patterns": [
                    r'\b(?:portfolio|diversification|allocation|correlation)\b',
                    r'\b(?:my|our)\s+(?:holdings|investments)\b'
                ],
                "keywords": ["portfolio", "diversification", "allocation", "holdings"],
                "complexity_factor": 4.0
            },
            QueryType.PREDICTION: {
                "patterns": [
                    r'\b(?:should I|advice|recommend|suggest)\b',
                    r'\b(?:predict|forecast|future|will|going)\b'
                ],
                "keywords": ["should", "predict", "forecast", "advice", "recommend"],
                "complexity_factor": 5.0
            }
        }
    
    def analyze_query(self, query: str) -> QueryInsights:
        """
        🎯 ROUTING PATTERN: Analyze and classify incoming query
        
        Returns structured insights for optimized processing
        """
        start_time = datetime.now(timezone.utc)
        
        # Extract symbols first
        symbols = self._extract_symbols(query)
        
        # Classify query type
        query_type, confidence = self._classify_query_type(query)
        
        # Determine complexity  
        complexity = self._assess_complexity(query, symbols, query_type)
        
        # Estimate processing time
        estimated_time = self._estimate_response_time(complexity, len(symbols))
        
        # Build reasoning for transparency
        reasoning = [
            f"🔍 Detected {len(symbols)} cryptocurrency symbols",
            f"📋 Classified as '{query_type.value}' query (confidence: {confidence:.1%})",
            f"⚡ Complexity: {complexity.value}",
            f"⏱️ Estimated response time: {estimated_time:.1f}s"
        ]
        
        # Update metrics
        self.performance_metrics["queries_processed"] += 1
        self.performance_metrics["average_confidence"] = (
            (self.performance_metrics["average_confidence"] * (self.performance_metrics["queries_processed"] - 1) + confidence) /
            self.performance_metrics["queries_processed"]
        )
        
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(f"Query analyzed in {processing_time*1000:.1f}ms: {query_type.value} | {complexity.value}")
        
        return QueryInsights(
            query_type=query_type,
            complexity=complexity,
            symbols=symbols,
            confidence=confidence,
            reasoning=reasoning,
            estimated_response_time=estimated_time
        )
    
    def _classify_query_type(self, query: str) -> Tuple[QueryType, float]:
        """Classify query type using pattern matching"""
        best_match = QueryType.SIMPLE_PRICE  # default
        highest_score = 0.0
        
        for query_type, config in self.routing_patterns.items():
            score = 0.0
            
            # Pattern matching (70% weight)
            pattern_matches = 0
            for pattern in config["patterns"]:
                if re.search(pattern, query, re.IGNORECASE):
                    pattern_matches += 1
            
            if pattern_matches > 0:
                score += 0.7 * (pattern_matches / len(config["patterns"]))
            
            # Keyword presence (30% weight)
            keyword_matches = 0
            for keyword in config["keywords"]:
                if re.search(rf'\b{keyword}\b', query, re.IGNORECASE):
                    keyword_matches += 1
            
            if keyword_matches > 0:
                score += 0.3 * (keyword_matches / len(config["keywords"]))
            
            if score > highest_score:
                highest_score = score
                best_match = query_type
        
        # Boost confidence if we found strong matches
        confidence = min(0.9, max(0.5, highest_score))
        
        return best_match, confidence
    
    def _assess_complexity(self, query: str, symbols: List[str], query_type: QueryType) -> QueryComplexity:
        """Assess query complexity for resource allocation"""
        
        complexity_score = 0
        
        # Symbol count factor
        if len(symbols) > 5:
            complexity_score += 3
        elif len(symbols) > 1:
            complexity_score += 1
        
        # Query type factor
        type_complexity = {
            QueryType.SIMPLE_PRICE: 0,
            QueryType.MULTI_ASSET: 1,
            QueryType.COMPARISON: 2,
            QueryType.TECHNICAL_ANALYSIS: 2,
            QueryType.PORTFOLIO: 3,
            QueryType.PREDICTION: 3,
            QueryType.MARKET_OVERVIEW: 1
        }
        complexity_score += type_complexity.get(query_type, 1)
        
        # Content complexity indicators
        complex_indicators = [
            r'\b(?:correlation|diversification|volatility)\b',
            r'\b(?:should I|recommend|predict)\b',
            r'\b(?:analysis|technical|indicators)\b'
        ]
        
        for indicator in complex_indicators:
            if re.search(indicator, query, re.IGNORECASE):
                complexity_score += 1
        
        # Map score to complexity enum
        if complexity_score >= 5:
            return QueryComplexity.COMPLEX
        elif complexity_score >= 2:
            return QueryComplexity.MODERATE
        else:
            return QueryComplexity.SIMPLE
    
    def _estimate_response_time(self, complexity: QueryComplexity, symbol_count: int) -> float:
        """Estimate response time based on complexity and symbol count"""
        base_times = {
            QueryComplexity.SIMPLE: 0.5,
            QueryComplexity.MODERATE: 1.5,
            QueryComplexity.COMPLEX: 3.0
        }
        
        base_time = base_times[complexity]
        symbol_overhead = symbol_count * 0.2  # 200ms per additional symbol
        
        return base_time + symbol_overhead
    
    def _extract_symbols(self, query: str) -> List[str]:
        """Enhanced symbol extraction"""
        # Common crypto symbols with their variants
        symbol_patterns = {
            "BTC": [r'\b(?:bitcoin|btc)\b'],
            "ETH": [r'\b(?:ethereum|eth)\b'],
            "SOL": [r'\b(?:solana|sol)\b'],
            "ADA": [r'\b(?:cardano|ada)\b'],
            "DOGE": [r'\b(?:dogecoin|doge)\b'],
            "BNB": [r'\b(?:binance\s*coin|bnb)\b'],
            "XRP": [r'\b(?:ripple|xrp)\b'],
            "DOT": [r'\b(?:polkadot|dot)\b']
        }
        
        detected_symbols = []
        
        for symbol, patterns in symbol_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    detected_symbols.append(f"{symbol}USDT")
                    break
        
        # Direct symbol matching (BTCUSDT, BTC, etc.)
        direct_matches = re.findall(r'\b([A-Z]{2,5}(?:USDT)?)\b', query.upper())
        for match in direct_matches:
            if not match.endswith('USDT'):
                match = f"{match}USDT"
            if match not in detected_symbols and len(match) <= 8:
                detected_symbols.append(match)
        
        return list(set(detected_symbols))  # Remove duplicates
    
    def create_enhanced_metadata(self, insights: QueryInsights, processing_time: float) -> Dict[str, Any]:
        """Create enhanced metadata with routing insights"""
        return {
            "routing_insights": {
                "query_type": insights.query_type.value,
                "complexity": insights.complexity.value,
                "confidence": insights.confidence,
                "estimated_time": insights.estimated_response_time,
                "actual_time": processing_time,
                "symbols_detected": len(insights.symbols),
                "reasoning_steps": insights.reasoning
            },
            "anthropic_patterns_used": [
                "routing_workflow",
                "transparency_principle", 
                "complexity_assessment"
            ],
            "performance_optimizations": [
                "smart_symbol_extraction",
                "complexity_based_routing",
                "confidence_scoring"
            ]
        }
    
    def suggest_query_improvements(self, insights: QueryInsights) -> List[str]:
        """🔍 TRANSPARENCY: Suggest query improvements for better results"""
        suggestions = []
        
        if insights.confidence < 0.7:
            suggestions.append("💡 Try being more specific about what you want to know")
        
        if len(insights.symbols) == 0:
            suggestions.append("💡 Mention specific cryptocurrencies (e.g., BTC, ETH, SOL)")
        
        if insights.complexity == QueryComplexity.COMPLEX:
            suggestions.append("💡 Consider breaking complex queries into simpler parts")
        
        if insights.query_type == QueryType.PREDICTION:
            suggestions.append("💡 Remember: Crypto predictions are speculative - always DYOR")
        
        return suggestions

def enhance_agent_response(original_response: Dict[str, Any], 
                          insights: QueryInsights,
                          processing_time: float) -> Dict[str, Any]:
    """
    Enhance existing agent response with Anthropic patterns
    
    🔍 TRANSPARENCY: Add reasoning steps and confidence scoring
    📊 EVALUATOR: Assess and improve response quality
    """
    
    # Create router instance for metadata
    router = EnhancedQueryRouter()
    
    # Calculate response quality score
    quality_score = _assess_response_quality(original_response, insights)
    
    # Enhanced response structure
    enhanced_response = original_response.copy()
    
    # Add routing insights to metadata
    if "metadata" not in enhanced_response:
        enhanced_response["metadata"] = {}
    
    enhanced_response["metadata"].update(
        router.create_enhanced_metadata(insights, processing_time)
    )
    
    # Add quality assessment
    enhanced_response["quality_assessment"] = {
        "overall_score": quality_score,
        "confidence_level": insights.confidence,
        "response_completeness": len(original_response.get("response", "")) > 100,
        "data_source_diversity": len(original_response.get("supporting_data", {})) > 1
    }
    
    # Add improvement suggestions
    suggestions = router.suggest_query_improvements(insights)
    if suggestions:
        enhanced_response["suggestions"] = suggestions
    
    # Enhanced reasoning steps
    if "reasoning_steps" not in enhanced_response:
        enhanced_response["reasoning_steps"] = []
    
    enhanced_response["reasoning_steps"] = insights.reasoning + enhanced_response["reasoning_steps"]
    
    # Add performance metrics
    enhanced_response["performance"] = {
        "processing_time_seconds": processing_time,
        "estimated_vs_actual": {
            "estimated": insights.estimated_response_time,
            "actual": processing_time,
            "accuracy": abs(insights.estimated_response_time - processing_time) < 1.0
        }
    }
    
    return enhanced_response

def _assess_response_quality(response: Dict[str, Any], insights: QueryInsights) -> float:
    """📊 EVALUATOR: Assess response quality"""
    quality_factors = []
    
    # Response completeness (0-0.3)
    response_text = response.get("response", "")
    if len(response_text) > 200:
        quality_factors.append(0.3)
    elif len(response_text) > 100:
        quality_factors.append(0.2)
    else:
        quality_factors.append(0.1)
    
    # Data availability (0-0.3)
    supporting_data = response.get("supporting_data", {})
    if len(supporting_data) > 2:
        quality_factors.append(0.3)
    elif len(supporting_data) > 0:
        quality_factors.append(0.2)
    else:
        quality_factors.append(0.1)
    
    # Confidence level (0-0.2)
    quality_factors.append(insights.confidence * 0.2)
    
    # Relevance to query type (0-0.2)
    if insights.query_type.value.lower() in response_text.lower():
        quality_factors.append(0.2)
    else:
        quality_factors.append(0.1)
    
    return sum(quality_factors)

# Integration example for existing agent
async def process_query_enhanced(agent, query: str) -> Dict[str, Any]:
    """
    Enhanced query processing wrapper that can be used with existing MarketAgent
    
    Usage:
        from app.core.ai.enhanced_router import process_query_enhanced
        result = await process_query_enhanced(market_agent, user_query)
    """
    start_time = datetime.now(timezone.utc)
    
    # 🎯 ROUTING: Analyze query first
    router = EnhancedQueryRouter()
    insights = router.analyze_query(query)
    
    # Process with existing agent
    original_response = await agent.process_query(query)
    
    # Calculate processing time
    processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
    
    # 🔍 TRANSPARENCY & 📊 EVALUATOR: Enhance response
    enhanced_response = enhance_agent_response(original_response, insights, processing_time)
    
    logger.info(f"Enhanced processing complete: {insights.query_type.value} | {processing_time:.2f}s")
    
    return enhanced_response 