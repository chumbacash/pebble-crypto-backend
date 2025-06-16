"""
LLM-based Symbol Extraction for Cryptocurrency Queries
Using Gemini with OpenRouter as backup to intelligently extract crypto symbols from natural language.
"""

import logging
import json
import asyncio
import requests
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import os

logger = logging.getLogger("CryptoPredictAPI")

class LLMSymbolExtractor:
    """
    AI-powered symbol extractor using Gemini (primary) and OpenRouter (backup) to intelligently identify
    cryptocurrency symbols and query intent from natural language.
    
    This replaces regex-based extraction with true language understanding.
    """
    
    def __init__(self):
        """Initialize the LLM symbol extractor with multiple providers"""
        self.gemini_client = None
        self.gemini_available = False
        self.openrouter_available = False
        self.openrouter_api_key = None
        
        # Try to initialize Gemini client
        try:
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.gemini_client = genai.GenerativeModel('gemini-1.5-flash')
                self.gemini_available = True
                logger.info("Gemini LLM initialized successfully")
            else:
                logger.warning("GEMINI_API_KEY not found")
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini: {e}")
        
        # Try to initialize OpenRouter
        try:
            openrouter_key = os.getenv('OPENROUTER_API_KEY')
            if openrouter_key:
                self.openrouter_api_key = openrouter_key
                self.openrouter_available = True
                logger.info("OpenRouter backup LLM initialized successfully")
            else:
                logger.warning("OPENROUTER_API_KEY not found")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenRouter: {e}")
        
        # Overall availability
        self.available = self.gemini_available or self.openrouter_available
        
        if not self.available:
            logger.warning("No LLM providers available - using regex fallback only")
        
        # Known cryptocurrency symbols for validation
        self.known_crypto_symbols = {
            "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOT", "DOGE", "AVAX", "MATIC", 
            "SHIB", "LTC", "ATOM", "LINK", "UNI", "XLM", "BCH", "ALGO", "MANA", "SAND", 
            "AXS", "GMT", "APE", "GALA", "THE", "FTM", "NEAR", "ICP", "VET", "HBAR",
            "FIL", "TRX", "ETC", "AAVE", "MKR", "SNX", "COMP", "YFI", "SUSHI", "CRV",
            "1INCH", "ZEC", "ENJ", "BAT", "ZRX", "REP", "KNC", "LRC", "REN", "BNT",
            "STORJ", "GRT", "SKL", "ANKR", "NKN", "BAND", "KAVA", "SXP", "RLC", "OCEAN"
        }
        
        # Common crypto name mappings
        self.crypto_name_mappings = {
            "bitcoin": "BTC",
            "ethereum": "ETH", 
            "solana": "SOL",
            "binance coin": "BNB",
            "cardano": "ADA",
            "dogecoin": "DOGE",
            "avalanche": "AVAX",
            "polygon": "MATIC",
            "polkadot": "DOT",
            "chainlink": "LINK",
            "uniswap": "UNI",
            "litecoin": "LTC",
            "stellar": "XLM",
            "bitcoin cash": "BCH",
            "algorand": "ALGO",
            "decentraland": "MANA",
            "the sandbox": "SAND",
            "axie infinity": "AXS",
            "stepn": "GMT",
            "apecoin": "APE",
            "gala": "GALA",
            "the": "THE"
        }
    
    async def extract_query_info(self, query: str, valid_symbols: Set[str] = None) -> Dict[str, Any]:
        """
        Extract cryptocurrency symbols and query information using LLM intelligence.
        
        Args:
            query: The natural language query
            valid_symbols: Set of valid trading symbols for validation
            
        Returns:
            Dictionary containing extracted symbols, query type, intent, etc.
        """
        if not self.available:
            # Fallback to regex extraction
            return self._fallback_extraction(query, valid_symbols)
        
        # Try Gemini first, then OpenRouter as backup
        for provider in ["gemini", "openrouter"]:
            try:
                llm_result = await self._llm_extract_symbols(query, valid_symbols, provider)
                
                # Validate and enhance the result
                validated_result = self._validate_and_enhance(llm_result, query, valid_symbols, provider)
                
                return validated_result
                
            except Exception as e:
                logger.error(f"{provider} extraction failed: {e}")
                continue
        
        # If all LLM providers fail, fallback to regex
        logger.warning("All LLM providers failed, using regex fallback")
        return self._fallback_extraction(query, valid_symbols)
    
    async def _llm_extract_symbols(self, query: str, valid_symbols: Set[str] = None, provider: str = "gemini") -> Dict[str, Any]:
        """Use LLM to extract cryptocurrency information from the query"""
        
        # Create the prompt
        prompt = f"""
You are a cryptocurrency market analysis assistant. Analyze this user query and extract relevant information:

Query: "{query}"

Please respond with a JSON object containing:
1. "symbols" - Array of cryptocurrency symbols mentioned (e.g., ["BTC", "ETH"])
2. "query_type" - One of: "single_asset", "multi_asset", "comparison", "portfolio", "general"
3. "intent" - One of: "price", "trend", "volatility", "levels", "prediction", "volume", "order_book", "indicators", "analysis", "advice", "comparison", "portfolio", "general"
4. "timeframe" - One of: "1h", "4h", "1d", "1w", "1M" (default "1h")
5. "confidence" - Float between 0-1 indicating confidence in extraction
6. "reasoning" - Brief explanation of your analysis

Rules:
- Extract only legitimate cryptocurrency symbols (BTC, ETH, SOL, ADA, etc.)
- DO NOT extract common English words like "the", "and", "or" unless clearly referring to "THE" token in crypto context
- For "THE" specifically, only extract if there are clear crypto context words like "token", "coin", "price", "trading"
- Convert full names to symbols (bitcoin → BTC, ethereum → ETH)
- If multiple cryptos mentioned, determine if it's comparison, portfolio, or multi-asset query
- Consider context carefully - "What is the price of ADA" should extract ADA, but "What is the current trend" should not extract "the"

Examples:
- "What is the price of Bitcoin?" → {{"symbols": ["BTC"], "intent": "price"}}
- "Compare BTC vs ETH" → {{"symbols": ["BTC", "ETH"], "query_type": "comparison", "intent": "comparison"}}
- "Show me THE token price" → {{"symbols": ["THE"], "intent": "price"}}
- "What is the market trend?" → {{"symbols": [], "intent": "trend"}}

Respond only with valid JSON:
"""

        if provider == "gemini" and self.gemini_available:
            try:
                # Call Gemini API
                response = await asyncio.to_thread(
                    self.gemini_client.generate_content,
                    prompt
                )
                response_text = response.text.strip()
                
            except Exception as e:
                logger.error(f"Gemini API call failed: {e}")
                raise
                
        elif provider == "openrouter" and self.openrouter_available:
            try:
                # Call OpenRouter API
                response = await asyncio.to_thread(
                    requests.post,
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openrouter_api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://pebble-crypto-backend.com",
                        "X-Title": "Pebble Crypto Backend",
                    },
                    data=json.dumps({
                        "model": "deepseek/deepseek-chat-v3-0324:free",
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.1,
                        "max_tokens": 1000
                    })
                )
                
                if response.status_code != 200:
                    raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")
                
                response_data = response.json()
                response_text = response_data['choices'][0]['message']['content'].strip()
                
            except Exception as e:
                logger.error(f"OpenRouter API call failed: {e}")
                raise
        else:
            raise Exception(f"Provider {provider} not available")
        
        # Extract JSON from response
        if response_text.startswith('```json'):
            response_text = response_text[7:-3]
        elif response_text.startswith('```'):
            response_text = response_text[3:-3]
        
        try:
            result = json.loads(response_text)
            logger.info(f"{provider} extraction result: {result}")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse {provider} JSON response: {e}")
            logger.error(f"Response text: {response_text}")
            raise
    
    def _validate_and_enhance(self, llm_result: Dict[str, Any], query: str, valid_symbols: Set[str] = None, provider: str = "unknown") -> Dict[str, Any]:
        """Validate LLM results and enhance with additional information"""
        
        # Initialize result structure
        result = {
            "symbols": [],
            "primary_symbol": None,
            "query_type": "single_asset",
            "interval": "1h",
            "intent": "general",
            "confidence": 0.8,
            "extraction_method": f"llm_{provider}"
        }
        
        # Extract and validate symbols
        symbols = llm_result.get("symbols", [])
        validated_symbols = []
        
        for symbol in symbols:
            symbol = symbol.upper()
            
            # Convert to USDT pairs
            if not symbol.endswith("USDT"):
                symbol = f"{symbol}USDT"
            
            # Validate against known symbols or valid_symbols
            if valid_symbols and symbol in valid_symbols:
                validated_symbols.append(symbol)
            elif symbol.replace("USDT", "") in self.known_crypto_symbols:
                validated_symbols.append(symbol)
        
        result["symbols"] = validated_symbols
        if validated_symbols:
            result["primary_symbol"] = validated_symbols[0]
        
        # Set query type
        result["query_type"] = llm_result.get("query_type", "single_asset")
        if len(validated_symbols) > 1 and result["query_type"] == "single_asset":
            result["query_type"] = "multi_asset"
        elif len(validated_symbols) == 0:
            result["query_type"] = "general"
        
        # Set intent
        result["intent"] = llm_result.get("intent", "general")
        
        # Set timeframe
        timeframe = llm_result.get("timeframe", "1h")
        if timeframe in ["1h", "4h", "1d", "1w", "1M"]:
            result["interval"] = timeframe
        
        # Set confidence
        result["confidence"] = llm_result.get("confidence", 0.8)
        
        # Add LLM reasoning
        result["llm_reasoning"] = llm_result.get("reasoning", "")
        result["llm_provider"] = provider
        
        return result
    
    def _fallback_extraction(self, query: str, valid_symbols: Set[str] = None) -> Dict[str, Any]:
        """Fallback regex-based extraction when LLM is not available"""
        
        result = {
            "symbols": [],
            "primary_symbol": None,
            "query_type": "single_asset",
            "interval": "1h",
            "intent": "general",
            "confidence": 0.6,
            "extraction_method": "regex_fallback"
        }
        
        # Simple symbol detection
        import re
        query_upper = query.upper()
        detected_symbols = []
        
        # Check for known crypto symbols
        for symbol in self.known_crypto_symbols:
            # More precise word boundary detection
            pattern = rf'\b{re.escape(symbol)}\b'
            if re.search(pattern, query_upper):
                # Special case for THE - require crypto context
                if symbol == "THE":
                    # Look for crypto context words
                    crypto_context_words = ["token", "coin", "crypto", "price", "trading", "buy", "sell", "investment", "analysis", "chart", "market cap", "pump", "dump", "hodl"]
                    crypto_context = any(word in query.lower() for word in crypto_context_words)
                    
                    # Also check if THE is used in a crypto-specific way (not as article)
                    # If THE appears with other crypto symbols, it's likely the token
                    other_cryptos = [s for s in self.known_crypto_symbols if s != "THE"]
                    has_other_crypto = any(re.search(rf'\b{re.escape(crypto)}\b', query_upper) for crypto in other_cryptos)
                    
                    # Check if THE is used as article (common patterns to exclude)
                    article_patterns = [
                        r'\bthe\s+(price|chart|market|trend|analysis|strategy|best|current|dip|moon)\b',
                        r'\bwhat\s+is\s+the\b',
                        r'\bshow\s+me\s+the\b',
                        r'\bin\s+the\b',
                        r'\bof\s+the\b'
                    ]
                    is_article = any(re.search(pattern, query.lower()) for pattern in article_patterns)
                    
                    # Only extract THE if there's crypto context and it's not used as an article
                    if not crypto_context and not has_other_crypto:
                        continue
                    if is_article and not crypto_context:
                        continue
                
                symbol_with_usdt = f"{symbol}USDT"
                if not valid_symbols or symbol_with_usdt in valid_symbols:
                    detected_symbols.append(symbol_with_usdt)
        
        # Check for full names
        for name, symbol in self.crypto_name_mappings.items():
            if name.lower() in query.lower():
                symbol_with_usdt = f"{symbol}USDT"
                if not valid_symbols or symbol_with_usdt in valid_symbols:
                    detected_symbols.append(symbol_with_usdt)
        
        result["symbols"] = list(set(detected_symbols))  # Remove duplicates
        if result["symbols"]:
            result["primary_symbol"] = result["symbols"][0]
        
        # Basic intent detection
        intent_keywords = {
            "price": ["price", "worth", "value", "cost"],
            "trend": ["trend", "direction", "moving"],
            "prediction": ["predict", "forecast", "future", "should I buy"],
            "comparison": ["compare", "vs", "versus", "better"],
            "analysis": ["analysis", "analyze", "explain"]
        }
        
        for intent, keywords in intent_keywords.items():
            if any(keyword in query.lower() for keyword in keywords):
                result["intent"] = intent
                break
        
        return result 