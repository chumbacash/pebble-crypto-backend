#!/usr/bin/env python3
"""
Multi-LLM Router
Intelligent routing of queries across multiple LLM providers for optimal performance and reliability
"""

import logging
import asyncio
import random
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

class MultiLLMRouter:
    """
    Intelligent router that distributes queries across multiple LLM providers
    based on availability, performance, and query complexity
    """
    
    def __init__(self):
        self.providers = {}
        self.provider_stats = {}
        self.circuit_breakers = {}
        self.load_balancer = LoadBalancer()
        
        # Provider configuration
        self.provider_config = {
            "gemini": {
                "weight": 1.0,
                "max_tokens": 4096,
                "good_for": ["general", "analysis", "technical"],
                "latency_threshold": 3.0
            },
            "openrouter": {
                "weight": 0.8,
                "max_tokens": 8192,
                "good_for": ["complex", "reasoning", "advice"],
                "latency_threshold": 5.0
            },
            "anthropic": {
                "weight": 0.9,
                "max_tokens": 8192,
                "good_for": ["analysis", "advice", "reasoning"],
                "latency_threshold": 4.0
            }
        }
        
        self._initialize_stats()
    
    def _initialize_stats(self):
        """Initialize provider statistics"""
        for provider in self.provider_config:
            self.provider_stats[provider] = {
                "requests": 0,
                "successes": 0,
                "failures": 0,
                "avg_latency": 0.0,
                "last_success": None,
                "last_failure": None,
                "health_score": 1.0
            }
            self.circuit_breakers[provider] = CircuitBreaker(provider)
    
    def register_provider(self, name: str, provider_instance: Any):
        """Register an LLM provider"""
        if name in self.provider_config:
            self.providers[name] = provider_instance
            logger.info(f"Registered LLM provider: {name}")
        else:
            logger.warning(f"Unknown provider configuration: {name}")
    
    async def route_query(self, query: str, query_type: str = "general", 
                         context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Route query to the best available LLM provider
        """
        context = context or {}
        
        try:
            # Select best provider for this query
            selected_provider = await self._select_provider(query, query_type, context)
            
            if not selected_provider:
                return {"error": "No available LLM providers", "provider": None}
            
            # Execute query with fallback strategy
            result = await self._execute_with_fallback(query, selected_provider, query_type, context)
            
            return result
            
        except Exception as e:
            logger.error(f"Multi-LLM routing error: {str(e)}")
            return {"error": f"Routing failed: {str(e)}", "provider": None}
    
    async def _select_provider(self, query: str, query_type: str, context: Dict[str, Any]) -> Optional[str]:
        """
        Select the best provider based on current conditions
        """
        available_providers = []
        
        # Filter available and healthy providers
        for provider_name, provider_instance in self.providers.items():
            if (provider_instance and 
                self.circuit_breakers[provider_name].is_available() and
                self._is_suitable_for_query(provider_name, query_type, len(query))):
                
                available_providers.append(provider_name)
        
        if not available_providers:
            logger.warning("No available LLM providers")
            return None
        
        # Score providers for this specific query
        scored_providers = []
        for provider in available_providers:
            score = self._calculate_provider_score(provider, query_type, context)
            scored_providers.append((provider, score))
        
        # Sort by score (descending) and apply load balancing
        scored_providers.sort(key=lambda x: x[1], reverse=True)
        
        # Use weighted random selection from top 3 providers
        top_providers = scored_providers[:3]
        return self.load_balancer.select_provider(top_providers)
    
    def _is_suitable_for_query(self, provider: str, query_type: str, query_length: int) -> bool:
        """
        Check if provider is suitable for the query type and length
        """
        config = self.provider_config.get(provider, {})
        
        # Check query type suitability
        good_for = config.get("good_for", [])
        if query_type not in good_for and "general" not in good_for:
            return False
        
        # Check token limits
        max_tokens = config.get("max_tokens", 4096)
        estimated_tokens = query_length // 4  # Rough estimation
        if estimated_tokens > max_tokens * 0.8:  # Leave buffer
            return False
        
        return True
    
    def _calculate_provider_score(self, provider: str, query_type: str, context: Dict[str, Any]) -> float:
        """
        Calculate a score for provider selection
        """
        stats = self.provider_stats[provider]
        config = self.provider_config[provider]
        
        # Base weight from configuration
        score = config.get("weight", 1.0)
        
        # Health score (success rate)
        if stats["requests"] > 0:
            success_rate = stats["successes"] / stats["requests"]
            score *= success_rate
        
        # Latency penalty
        avg_latency = stats.get("avg_latency", 0)
        latency_threshold = config.get("latency_threshold", 3.0)
        if avg_latency > latency_threshold:
            penalty = min(avg_latency / latency_threshold, 2.0)
            score /= penalty
        
        # Query type bonus
        good_for = config.get("good_for", [])
        if query_type in good_for:
            score *= 1.2
        
        # Recent failure penalty
        if stats.get("last_failure"):
            time_since_failure = (datetime.now() - stats["last_failure"]).total_seconds()
            if time_since_failure < 300:  # 5 minutes
                score *= 0.5
        
        # Load balancing factor
        current_load = self.load_balancer.get_provider_load(provider)
        if current_load > 0.8:
            score *= 0.7
        
        return max(score, 0.1)  # Minimum score
    
    async def _execute_with_fallback(self, query: str, primary_provider: str, 
                                   query_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute query with intelligent fallback strategy
        """
        providers_to_try = [primary_provider]
        
        # Add fallback providers
        for provider in self.providers.keys():
            if (provider != primary_provider and 
                self.circuit_breakers[provider].is_available() and
                self._is_suitable_for_query(provider, query_type, len(query))):
                providers_to_try.append(provider)
        
        last_error = None
        
        for provider_name in providers_to_try:
            try:
                provider_instance = self.providers[provider_name]
                if not provider_instance:
                    continue
                
                start_time = time.time()
                
                # Track request
                self._track_request_start(provider_name)
                
                # Execute query
                result = await self._call_provider(provider_instance, query, context)
                
                # Calculate latency
                latency = time.time() - start_time
                
                # Track success
                self._track_request_success(provider_name, latency)
                
                # Mark circuit breaker as successful
                self.circuit_breakers[provider_name].record_success()
                
                return {
                    "result": result,
                    "provider": provider_name,
                    "latency": latency,
                    "fallback_used": provider_name != primary_provider
                }
                
            except Exception as e:
                # Track failure
                self._track_request_failure(provider_name)
                self.circuit_breakers[provider_name].record_failure()
                
                last_error = e
                logger.warning(f"Provider {provider_name} failed: {str(e)}")
                continue
        
        # All providers failed
        return {
            "error": f"All providers failed. Last error: {str(last_error)}",
            "provider": None,
            "providers_tried": providers_to_try
        }
    
    async def _call_provider(self, provider_instance: Any, query: str, context: Dict[str, Any]) -> str:
        """
        Call the specific provider implementation
        """
        # This would be implemented based on the specific provider interface
        # For now, assuming a common interface
        if hasattr(provider_instance, 'process_query'):
            return await provider_instance.process_query(query, context)
        elif hasattr(provider_instance, 'generate'):
            return await provider_instance.generate(query)
        else:
            raise NotImplementedError(f"Provider interface not implemented")
    
    def _track_request_start(self, provider: str):
        """Track the start of a request"""
        self.provider_stats[provider]["requests"] += 1
        self.load_balancer.increment_load(provider)
    
    def _track_request_success(self, provider: str, latency: float):
        """Track successful request"""
        stats = self.provider_stats[provider]
        stats["successes"] += 1
        stats["last_success"] = datetime.now()
        
        # Update average latency
        if stats["avg_latency"] == 0:
            stats["avg_latency"] = latency
        else:
            stats["avg_latency"] = (stats["avg_latency"] * 0.8) + (latency * 0.2)
        
        # Update health score
        if stats["requests"] > 0:
            stats["health_score"] = stats["successes"] / stats["requests"]
        
        self.load_balancer.decrement_load(provider)
    
    def _track_request_failure(self, provider: str):
        """Track failed request"""
        stats = self.provider_stats[provider]
        stats["failures"] += 1
        stats["last_failure"] = datetime.now()
        
        # Update health score
        if stats["requests"] > 0:
            stats["health_score"] = stats["successes"] / stats["requests"]
        
        self.load_balancer.decrement_load(provider)
    
    def get_provider_stats(self) -> Dict[str, Any]:
        """Get current provider statistics"""
        return {
            "providers": dict(self.provider_stats),
            "circuit_breakers": {name: cb.get_state() for name, cb in self.circuit_breakers.items()},
            "load_balancer": self.load_balancer.get_stats()
        }


class CircuitBreaker:
    """Circuit breaker for individual providers"""
    
    def __init__(self, provider_name: str, failure_threshold: int = 5, 
                 recovery_timeout: int = 60):
        self.provider_name = provider_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def record_success(self):
        """Record a successful call"""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info(f"Circuit breaker for {self.provider_name} closed")
    
    def record_failure(self):
        """Record a failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold and self.state == "CLOSED":
            self.state = "OPEN"
            logger.warning(f"Circuit breaker for {self.provider_name} opened")
    
    def is_available(self) -> bool:
        """Check if the provider is available"""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            # Check if we should transition to HALF_OPEN
            if (self.last_failure_time and 
                (datetime.now() - self.last_failure_time).total_seconds() > self.recovery_timeout):
                self.state = "HALF_OPEN"
                logger.info(f"Circuit breaker for {self.provider_name} half-opened")
                return True
            return False
        elif self.state == "HALF_OPEN":
            return True
        
        return False
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None
        }


class LoadBalancer:
    """Simple load balancer for provider selection"""
    
    def __init__(self):
        self.provider_loads = {}
    
    def increment_load(self, provider: str):
        """Increment load for a provider"""
        self.provider_loads[provider] = self.provider_loads.get(provider, 0) + 1
    
    def decrement_load(self, provider: str):
        """Decrement load for a provider"""
        if provider in self.provider_loads:
            self.provider_loads[provider] = max(0, self.provider_loads[provider] - 1)
    
    def get_provider_load(self, provider: str) -> float:
        """Get normalized load for a provider (0.0 to 1.0)"""
        current_load = self.provider_loads.get(provider, 0)
        max_load = 10  # Configurable
        return min(current_load / max_load, 1.0)
    
    def select_provider(self, scored_providers: List[tuple]) -> str:
        """Select provider using weighted random selection"""
        if not scored_providers:
            return None
        
        # Calculate weights
        weights = []
        providers = []
        
        for provider, score in scored_providers:
            # Adjust score by current load
            load_factor = 1.0 - self.get_provider_load(provider)
            adjusted_score = score * load_factor
            
            weights.append(adjusted_score)
            providers.append(provider)
        
        # Weighted random selection
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(providers)
        
        rand_val = random.uniform(0, total_weight)
        cumulative = 0
        
        for i, weight in enumerate(weights):
            cumulative += weight
            if rand_val <= cumulative:
                return providers[i]
        
        return providers[-1]  # Fallback
    
    def get_stats(self) -> Dict[str, Any]:
        """Get load balancer statistics"""
        return {
            "provider_loads": dict(self.provider_loads),
            "total_requests": sum(self.provider_loads.values())
        } 