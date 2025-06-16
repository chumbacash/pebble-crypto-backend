# models.py
import numpy as np
from fastapi import HTTPException 
from datetime import datetime, timezone
from typing import List, Dict, Tuple
import logging
from app.core.ai.gemini_client import GeminiInsightsGenerator
from functools import lru_cache, wraps
import asyncio
from cachetools import TTLCache
from scipy.stats import linregress
from scipy.signal import savgol_filter
import math

logger = logging.getLogger("CryptoPredictAPI")

class KalmanFilter:
    def __init__(self, process_variance=1e-5, measurement_variance=0.1**2):
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance
        self.estimate = None
        self.estimate_error = 1.0

    def update(self, measurement):
        if self.estimate is None:
            self.estimate = measurement
            return measurement

        prediction = self.estimate
        prediction_error = self.estimate_error + self.process_variance

        kalman_gain = prediction_error / (prediction_error + self.measurement_variance)
        self.estimate = prediction + kalman_gain * (measurement - prediction)
        self.estimate_error = (1 - kalman_gain) * prediction_error

        return self.estimate

class TechnicalAnalyzer:
    def __init__(self, prices: List[float], volumes: List[float] = None):
        self.prices = np.array(prices)
        self.volumes = np.array(volumes) if volumes is not None else None
        self.kf = KalmanFilter()
        self.filtered_prices = np.array([self.kf.update(p) for p in prices])
        
    def calculate_volatility(self, window: int = None) -> float:
        """Calculate adaptive volatility based on available data"""
        if window is None:
            window = min(24, len(self.prices) // 3)
        returns = np.diff(self.filtered_prices[-window:]) / self.filtered_prices[-window:-1]
        return float(np.std(returns))

    def find_key_levels(self) -> Dict:
        """Identify support/resistance using dynamic clustering with limited data handling"""
        available_points = len(self.prices)
        
        # For very limited data, use simple percentage-based levels
        if available_points < 10:
            current_price = self.prices[-1]
            recent_volatility = np.std(np.diff(self.prices)) / current_price
            level_range = max(0.02, min(0.1, recent_volatility * 2))  # 2-10% range based on volatility
            
            return {
                "support": float(current_price * (1 - level_range)),
                "resistance": float(current_price * (1 + level_range)),
                "trend_strength": 0.1  # Low trend strength for limited data
            }
        
        # For limited but usable data, use adaptive percentiles
        lookback = min(available_points, 100)
        prices = self.filtered_prices[-lookback:]
        
        # Adjust percentile range based on available data
        if available_points < 20:
            percentile_range = (35, 65)  # Narrower range for very limited data
        elif available_points < 50:
            percentile_range = (30, 70)  # Wider range for more data
        else:
            percentile_range = (25, 75)  # Full range for sufficient data
        
        recent_highs = prices[prices >= np.percentile(prices, percentile_range[1])]
        recent_lows = prices[prices <= np.percentile(prices, percentile_range[0])]
        
        # Calculate trend with available data
        trend = self._calculate_trend()
        trend_adjustment = trend * np.std(prices) * 0.05  # Reduced adjustment for limited data
        
        support = float(np.mean(recent_lows)) if len(recent_lows) > 0 else float(prices[-1] * 0.98)
        resistance = float(np.mean(recent_highs)) if len(recent_highs) > 0 else float(prices[-1] * 1.02)
        
        if support:
            support += trend_adjustment
        if resistance:
            resistance += trend_adjustment
            
        # Ensure support is below current price and resistance is above
        current_price = float(prices[-1])
        support = min(support, current_price * 0.99)
        resistance = max(resistance, current_price * 1.01)
            
        return {
            "support": support,
            "resistance": resistance,
            "trend_strength": min(0.5, abs(trend))  # Limit trend strength for limited data
        }

    def _calculate_trend(self) -> float:
        """Calculate trend strength using linear regression"""
        x = np.arange(len(self.filtered_prices))
        slope, _, r_value, _, _ = linregress(x, self.filtered_prices)
        return slope * r_value**2  # Weighted by R-squared

    def calculate_volume_profile(self) -> Dict:
        """Analyze volume profile if available"""
        if self.volumes is None or len(self.volumes) < 2:
            return {"volume_trend": 0, "volume_signal": "neutral"}
            
        recent_vol = np.mean(self.volumes[-5:])
        older_vol = np.mean(self.volumes[-20:-5])
        vol_change = (recent_vol - older_vol) / older_vol
        
        return {
            "volume_trend": float(vol_change),
            "volume_signal": "increasing" if vol_change > 0.1 else "decreasing" if vol_change < -0.1 else "neutral"
        }

    def generate_messages(self, indicators: Dict) -> Dict:
        """Create human-readable insights with confidence levels"""
        messages = {
            "summary": "",
            "key_insights": [],
            "action_guide": {},
            "confidence_factors": {}
        }

        # Dynamic trend analysis
        trend_strength = abs(indicators.get('trend_strength', 0))
        if trend_strength > 0.5:
            confidence_mult = min(1.0, trend_strength)
            if indicators['sma_20'] > indicators['sma_50']:
                messages['key_insights'].append(f"Strong Bullish Trend (Confidence: {confidence_mult:.2f})")
            else:
                messages['key_insights'].append(f"Strong Bearish Trend (Confidence: {confidence_mult:.2f})")

        # RSI analysis with dynamic thresholds
        rsi_thresholds = (30, 70) if len(self.prices) >= 50 else (20, 80)
        if indicators['rsi'] > rsi_thresholds[1]:
            messages['key_insights'].append(f"Overbought (RSI: {indicators['rsi']:.1f})")
        elif indicators['rsi'] < rsi_thresholds[0]:
            messages['key_insights'].append(f"Oversold (RSI: {indicators['rsi']:.1f})")

        # Volume analysis if available
        vol_profile = self.calculate_volume_profile()
        if vol_profile['volume_signal'] != "neutral":
            messages['key_insights'].append(f"Volume {vol_profile['volume_signal']} ({vol_profile['volume_trend']:.1%} change)")

        # Generate weighted action guide
        bull_signals = sum(1 for insight in messages['key_insights'] if "Bullish" in insight or "Oversold" in insight)
        bear_signals = sum(1 for insight in messages['key_insights'] if "Bearish" in insight or "Overbought" in insight)
        
        # Weight signals by data quality
        data_quality = min(1.0, len(self.prices) / 100)
        signal_strength = (bull_signals - bear_signals) * data_quality
        
        messages['action_guide'] = {
            "buy": max(0.3, min(0.7, 0.5 + signal_strength * 0.1)),
            "sell": max(0.3, min(0.7, 0.5 - signal_strength * 0.1)),
            "hold": 0.5 + (0.1 if abs(signal_strength) < 0.2 else 0)
        }
        
        messages['confidence_factors'] = {
            "data_quality": data_quality,
            "trend_strength": trend_strength,
            "volume_confidence": 0.5 + abs(vol_profile['volume_trend'])
        }

        return messages

class AdvancedPredictor:
    def __init__(self):
        # Initialize AI insights generator (optional)
        try:
            self.gemini = GeminiInsightsGenerator()
            self.gemini_available = True
        except Exception as e:
            logger.warning(f"Gemini AI not available: {str(e)}")
            self.gemini = None
            self.gemini_available = False
        # Reduce TTL to 60 seconds to ensure more frequent refreshes
        self.analysis_cache = TTLCache(maxsize=500, ttl=60)
        self.prices = []
        self.volumes = []
        self.indicators = {
            "sma_20": None,
            "sma_50": None,
            "rsi": None,
            "macd": {},
            "trend": None,
            "volume_profile": None
        }
        # Schedule cache clearing
        self._schedule_cache_clear()
        
    def _schedule_cache_clear(self):
        """Schedule periodic cache clearing"""
        try:
            asyncio.create_task(self._clear_cache_periodically())
        except RuntimeError:
            # If we're not in an event loop, just clear the cache now
            self.analysis_cache.clear()
            
    async def _clear_cache_periodically(self):
        """Clear the cache every 5 minutes"""
        while True:
            await asyncio.sleep(300)  # 5 minutes
            self.analysis_cache.clear()
            logger.info("Analysis cache cleared")
        
    def _calculate_sma(self, window: int) -> float:
        """Calculate SMA with dynamic window size for limited data"""
        if len(self.prices) < window:
            window = max(5, len(self.prices) // 2)
        return float(np.mean(self.prices[-window:]))

    def validate_data_length(window):
        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                available_points = len(self.prices)
                if available_points < 5:  # Absolute minimum required
                    return func(self, *args, actual_window=5, **kwargs)
                elif available_points < window:
                    # For limited data, use what we have
                    actual_window = max(5, available_points - 1)
                else:
                    # For sufficient data, use requested window
                    actual_window = window
                try:
                    return func(self, *args, actual_window=actual_window, **kwargs)
                except Exception as e:
                    logger.warning(f"{func.__name__} calculation failed with window {actual_window}: {str(e)}")
                    # Return safe defaults based on function
                    if func.__name__ == '_calculate_rsi':
                        return 50.0
                    elif func.__name__ == '_calculate_macd':
                        return {'macd_line': [0], 'signal_line': [0], 'histogram': [0]}
                    return None
            return wrapper
        return decorator

    def _calculate_adaptive_window(self, base_window: int) -> int:
        """Calculate adaptive window size based on available data"""
        available_points = len(self.prices)
        if available_points < base_window:
            return max(5, available_points - 1)  # Ensure we have at least 5 points
        return base_window

    @validate_data_length(14)
    def _calculate_rsi(self, actual_window: int = 14) -> float:
        """Calculate RSI with noise filtering and limited data handling"""
        try:
            kf = KalmanFilter()
            filtered_prices = np.array([kf.update(p) for p in self.prices[-actual_window-1:]])
            deltas = np.diff(filtered_prices)
            gains = deltas[deltas > 0]
            losses = -deltas[deltas < 0]
            
            avg_gain = np.mean(gains) if len(gains) > 0 else 0
            avg_loss = np.mean(losses) if len(losses) > 0 else 1e-6
            
            rs = avg_gain / avg_loss
            return float(100 - (100 / (1 + rs)))
        except Exception as e:
            logger.error(f"RSI calculation failed: {str(e)}")
            return 50.0  # Neutral RSI for limited data

    def _calculate_ema(self, window: int, prices: np.ndarray = None) -> np.ndarray:
        """Calculate EMA with Savitzky-Golay filtering for smoother results"""
        # Input validation
        if prices is None:
            prices = self.prices
        if not isinstance(prices, np.ndarray):
            prices = np.array(prices, dtype=float)
        if len(prices) == 0:
            return np.array([])
            
        # Ensure minimum window size
        if len(prices) < window:
            window = max(2, len(prices) // 2)
            
        # Apply Savitzky-Golay filter for noise reduction
        window_length = min(7, len(prices) - 1 if len(prices) % 2 == 0 else len(prices))
        if window_length > 2:
            try:
                prices = savgol_filter(prices, window_length, 3)
            except Exception as e:
                logger.warning(f"Savitzky-Golay filtering failed, using raw prices: {str(e)}")
            
        # Calculate EMA
        alpha = 2 / (window + 1)
        ema = np.zeros_like(prices)
        ema[0] = prices[0]
        
        for i in range(1, len(prices)):
            ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]
            
        return ema

    @validate_data_length(26)
    def _calculate_macd(self, actual_window: int = 26) -> dict:
        """Calculate MACD with adaptive windows"""
        try:
            # Input validation
            if not isinstance(self.prices, (list, np.ndarray)) or len(self.prices) == 0:
                return {'macd_line': [0], 'signal_line': [0], 'histogram': [0]}

            prices = np.array(self.prices, dtype=float)
            
            # Ensure we have enough data
            min_required = actual_window + 10  # Add buffer for signal line
            if len(prices) < min_required:
                actual_window = max(10, len(prices) // 3)
            
            short_window = max(5, actual_window // 2)
            long_window = actual_window
            signal_window = max(3, actual_window // 3)
            
            # Calculate EMAs
            ema_short = self._calculate_ema(short_window, prices)
            ema_long = self._calculate_ema(long_window, prices)
            
            # Ensure we have valid data
            if len(ema_short) == 0 or len(ema_long) == 0:
                return {'macd_line': [0], 'signal_line': [0], 'histogram': [0]}
            
            # Align the arrays by trimming from the end
            min_len = min(len(ema_short), len(ema_long))
            macd_line = ema_short[-min_len:] - ema_long[-min_len:]
            
            # Calculate signal line
            signal_line = self._calculate_ema(signal_window, macd_line)
            
            # Ensure arrays are of equal length for histogram calculation
            min_len = min(len(macd_line), len(signal_line))
            if min_len == 0:
                return {'macd_line': [0], 'signal_line': [0], 'histogram': [0]}
                
            macd_line = macd_line[-min_len:]
            signal_line = signal_line[-min_len:]
            histogram = macd_line - signal_line
            
            return {
                'macd_line': macd_line.tolist(),
                'signal_line': signal_line.tolist(),
                'histogram': histogram.tolist()
            }
            
        except Exception as e:
            logger.error(f"MACD calculation error: {str(e)}")
            return {'macd_line': [0], 'signal_line': [0], 'histogram': [0]}

    def handle_analysis_errors(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            try:
                return await func(self, *args, **kwargs)
            except ValueError as e:
                logging.error(f"Validation error: {str(e)}")
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logging.error(f"Analysis error: {str(e)}")
                raise HTTPException(status_code=500, detail="Internal analysis error")
        return wrapper

    def _sanitize_nan_values(self, data):
        """Replace NaN values with None for JSON serialization"""
        if isinstance(data, dict):
            return {k: self._sanitize_nan_values(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_nan_values(item) for item in data]
        elif isinstance(data, (float, np.float64, np.float32)) and (math.isnan(data) or math.isinf(data)):
            return None
        elif isinstance(data, np.ndarray):
            return self._sanitize_nan_values(data.tolist())
        elif isinstance(data, np.integer):
            return int(data)
        elif isinstance(data, np.floating):
            return None if math.isnan(float(data)) or math.isinf(float(data)) else float(data)
        else:
            return data
        
    @handle_analysis_errors
    async def analyze_market(self, prices: List[float], volumes: List[float] = None, interval: str = "1h") -> Dict:
        # Debug logging for interval
        logger.debug(f"analyze_market called with interval: {interval}")
        
        # Use a cache key that includes the interval
        prices_str = '-'.join(str(p) for p in prices[-5:])  # Use last 5 prices for faster cache key
        cache_key = f"{prices_str}-{interval}"
        
        # Check cache to avoid recalculation
        if cache_key in self.analysis_cache:
            logger.debug(f"Returning cached analysis for interval: {interval}")
            return self.analysis_cache[cache_key]
        
        # Proceed with analysis
        try:
            self.prices = np.array(prices)
            self.volumes = np.array(volumes) if volumes is not None else None
            data_points = len(prices)
            
            analyzer = TechnicalAnalyzer(self.prices, self.volumes)
            
            # Calculate indicators with noise reduction and error handling
            self.indicators = {}
            
            # Adaptive SMA calculations
            try:
                if data_points >= 20:
                    self.indicators["sma_20"] = self._calculate_sma(20)
                else:
                    self.indicators["sma_20"] = float(prices[-1])
            except Exception as e:
                logger.error(f"SMA-20 calculation failed: {str(e)}")
                self.indicators["sma_20"] = float(prices[-1])
                
            try:
                if data_points >= 50:
                    self.indicators["sma_50"] = self._calculate_sma(50)
                else:
                    self.indicators["sma_50"] = float(prices[-1])
            except Exception as e:
                logger.error(f"SMA-50 calculation failed: {str(e)}")
                self.indicators["sma_50"] = float(prices[-1])
                
            # Calculate other indicators with adaptive windows
            try:
                self.indicators["rsi"] = self._calculate_rsi()
            except Exception as e:
                logger.error(f"RSI calculation failed: {str(e)}")
                self.indicators["rsi"] = 50.0
                
            try:
                self.indicators["macd"] = self._calculate_macd()
            except Exception as e:
                logger.error(f"MACD calculation failed: {str(e)}")
                self.indicators["macd"] = {'macd_line': [0], 'signal_line': [0], 'histogram': [0]}
                
            try:
                self.indicators["volatility"] = float(analyzer.calculate_volatility())
            except Exception as e:
                logger.error(f"Volatility calculation failed: {str(e)}")
                self.indicators["volatility"] = 0.01
                
            try:
                self.indicators["key_levels"] = analyzer.find_key_levels()
            except Exception as e:
                logger.error(f"Key levels calculation failed: {str(e)}")
                current_price = float(prices[-1])
                self.indicators["key_levels"] = {
                    "support": current_price * 0.95,
                    "resistance": current_price * 1.05,
                    "trend_strength": 0.0
                }
                
            try:
                self.indicators["volume_profile"] = analyzer.calculate_volume_profile()
            except Exception as e:
                logger.error(f"Volume profile calculation failed: {str(e)}")
                self.indicators["volume_profile"] = {"volume_trend": 0.0, "volume_signal": "neutral"}

            # Generate insights with data quality awareness
            try:
                messages = analyzer.generate_messages(self.indicators)
                if data_points < 20:
                    messages["summary"] = "Limited historical data available. Analysis may be less reliable."
            except Exception as e:
                logger.error(f"Message generation failed: {str(e)}")
                messages = {
                    "summary": "Limited data available for comprehensive analysis",
                    "key_insights": [],
                    "action_guide": {"buy": 0.5, "sell": 0.5, "hold": 0.5},
                    "confidence_factors": {"data_quality": data_points/100, "trend_strength": 0, "volume_confidence": 0.5}
                }
            
            # Get AI insights with confidence weighting (if available)
            if self.gemini_available and self.gemini:
                try:
                    gemini_analysis = await asyncio.to_thread(
                        self.gemini.generate_analysis,
                        {
                            "current_price": float(prices[-1]),
                            **self.indicators,
                            "data_quality": min(0.99, len(prices)/100),
                            "interval": interval
                        }
                    )
                except Exception as e:
                    logger.error(f"Gemini analysis failed: {str(e)}")
                    gemini_analysis = {
                            "market_summary": "AI analysis temporarily unavailable",
                            "technical_observations": ["Technical indicators show current market conditions"],
                            "trading_recommendations": ["Monitor technical indicators for trading signals"],
                            "risk_factors": ["Market volatility and external factors"]
                        }
            else:
                # Fallback analysis without AI
                gemini_analysis = {
                    "market_summary": f"Technical analysis shows current price at ${float(prices[-1]):.4f}",
                    "technical_observations": [
                        f"RSI at {self.indicators['rsi']:.1f} indicating {'overbought' if self.indicators['rsi'] > 70 else 'oversold' if self.indicators['rsi'] < 30 else 'neutral'} conditions",
                        f"Price volatility at {self.indicators['volatility']*100:.2f}%",
                        f"Current trend shows {'bullish' if self.indicators['key_levels']['trend_strength'] > 0 else 'bearish'} momentum"
                    ],
                    "trading_recommendations": [
                        "Monitor key support and resistance levels",
                        "Consider risk management strategies"
                    ],
                    "risk_factors": [
                        "Market volatility may affect price movements",
                        "External market conditions should be considered"
                    ]
                }

            result = {
                "metadata": {
                    "interval": interval,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "data_points": data_points,
                    "data_quality": min(0.99, data_points/100),
                    "confidence_score": self._calculate_confidence()
                },
                "price_analysis": {
                    "current": float(prices[-1]),
                    "prediction": self._generate_prediction(),
                    "prediction_range": self._calculate_prediction_range(),
                    **self.indicators
                },
                "frontend_insights": messages,
                "ai_insights": gemini_analysis
            }
            
            # Log the interval being used in the result
            logger.info(f"Analysis completed with interval: {interval}, result interval: {result['metadata']['interval']}")
            
            # Sanitize data to remove NaN values before caching
            sanitized_result = self._sanitize_nan_values(result)
            
            self.analysis_cache[cache_key] = sanitized_result
            return sanitized_result
            
        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Analysis failed: {str(e)}"
            )

    def _generate_prediction(self) -> float:
        """Generate price prediction using weighted moving averages and trend"""
        try:
            current_price = float(self.prices[-1])
            available_points = len(self.prices)
            
            # For very limited data, use simple trend-based prediction
            if available_points < 10:
                # Calculate simple momentum
                price_change = (self.prices[-1] - self.prices[0]) / self.prices[0]
                # Limit the change to ±1%
                max_change = 0.01
                change = np.clip(price_change, -max_change, max_change)
                return round(current_price * (1 + change), 8 if current_price < 1 else 6 if current_price < 10 else 2)
            
            # Calculate weighted average of recent prices
            weights = np.linspace(1, 2, min(24, available_points))
            weights = weights / np.sum(weights)  # Normalize weights
            weighted_avg = np.sum(self.prices[-len(weights):] * weights)
            
            # Calculate trend
            short_term_change = (self.prices[-1] - self.prices[-min(5, available_points)]) / self.prices[-min(5, available_points)]
            
            # Combine weighted average with trend
            trend_impact = np.clip(short_term_change, -0.02, 0.02)  # Limit trend impact to ±2%
            prediction = weighted_avg * (1 + trend_impact)
            
            # Ensure prediction is within reasonable bounds (±3% of current price)
            min_pred = current_price * 0.97
            max_pred = current_price * 1.03
            prediction = np.clip(prediction, min_pred, max_pred)
            
            # Round based on price scale
            return round(float(prediction), 8 if current_price < 1 else 6 if current_price < 10 else 2)
            
        except Exception as e:
            logger.error(f"Simple prediction calculation error: {str(e)}")
            return self.prices[-1]  # Return current price as fallback

    def _calculate_prediction_range(self) -> Dict[str, float]:
        """Calculate prediction range based on recent price volatility"""
        try:
            current_price = float(self.prices[-1])
            available_points = len(self.prices)
            
            # For very limited data, use fixed percentage range
            if available_points < 10:
                range_multiplier = 0.02  # ±2% range
            else:
                # Calculate recent price changes
                changes = np.diff(self.prices[-min(24, available_points):]) / self.prices[-min(24, available_points):-1]
                # Use standard deviation of changes, with minimum and maximum bounds
                range_multiplier = np.clip(np.std(changes) * 2, 0.01, 0.05)  # Between 1% and 5%
            
            base_prediction = self._generate_prediction()
            
            # Calculate range
            range_low = base_prediction * (1 - range_multiplier)
            range_high = base_prediction * (1 + range_multiplier)
            
            # Round based on price scale
            decimals = 8 if current_price < 1 else 6 if current_price < 10 else 2
            return {
                "low": round(float(range_low), decimals),
                "high": round(float(range_high), decimals)
            }
            
        except Exception as e:
            logger.error(f"Range calculation error: {str(e)}")
            current_price = float(self.prices[-1])
            # Fallback to ±1% of current price
            decimals = 8 if current_price < 1 else 6 if current_price < 10 else 2
            return {
                "low": round(float(current_price * 0.99), decimals),
                "high": round(float(current_price * 1.01), decimals)
            }

    def _calculate_confidence(self) -> float:
        """Calculate enhanced confidence score 0-1 with limited data handling"""
        if not self.indicators:
            return 0.1  # Very low confidence for no indicators
            
        # Start with lower base confidence for limited data
        data_points = len(self.prices)
        if data_points < 20:
            confidence = 0.2
        elif data_points < 50:
            confidence = 0.3
        else:
            confidence = 0.5
        
        # Data quality impact - more forgiving for new pairs
        data_quality = min(1.0, len(self.prices) / 50)  # Reduced from 100 to 50 for faster quality gain
        confidence *= (0.5 + 0.5 * data_quality)  # Less aggressive quality penalty
        
        # Trend strength impact - reduced for limited data
        trend_strength = abs(self.indicators['key_levels']['trend_strength'])
        confidence += 0.05 * min(1.0, trend_strength)  # Reduced from 0.1 to 0.05
        
        # Volatility impact (inverse) - reduced for limited data
        confidence -= self.indicators['volatility'] * 0.3  # Reduced from 0.5 to 0.3
        
        # Volume confirmation if available - reduced impact
        if self.indicators['volume_profile']['volume_signal'] != "neutral":
            volume_trend = abs(self.indicators['volume_profile']['volume_trend'])
            confidence += 0.05 * min(1.0, volume_trend)  # Reduced from 0.1 to 0.05
        
        # Technical indicator agreement - reduced thresholds for limited data
        rsi_value = self.indicators['rsi']
        if 25 < rsi_value < 75:  # Wider range for limited data
            confidence += 0.05  # Reduced from 0.1 to 0.05
            
        macd_hist = self.indicators['macd']['histogram'][-1]
        if abs(macd_hist) > 0:  # Any MACD signal
            confidence += 0.05  # Reduced from 0.1 to 0.05
            
        # Ensure minimum confidence for any prediction
        return max(0.1, min(0.8, confidence))  # Reduced max confidence for limited data

predictor = AdvancedPredictor()