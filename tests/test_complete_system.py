#!/usr/bin/env python3
"""
Comprehensive System Test using FastAPI TestClient
Tests all endpoints, data quality, and multi-exchange functionality
Based on FastAPI testing best practices: https://fastapi.tiangolo.com/tutorial/testing/
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi.testclient import TestClient

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

# Create TestClient instance
client = TestClient(app)

class TestSystemHealth:
    """Test basic system health and connectivity"""
    
    def test_health_check(self):
        """Test the health check endpoint"""
        try:
            response = client.get("/api/health")
            assert response.status_code == 200, f"Health check failed with status {response.status_code}"
            data = response.json()
            assert "status" in data, "Status field missing from health response"
            assert data["status"] == "online", f"Expected status 'online', got '{data['status']}'"
            assert "timestamp" in data, "Timestamp field missing from health response"
            print("✅ Health check passed")
            return True
        except Exception as e:
            print(f"❌ Health check failed: {str(e)}")
            return False

    def test_symbols_endpoint(self):
        """Test symbols endpoint"""
        try:
            response = client.get("/symbols")
            assert response.status_code == 200, f"Symbols endpoint failed with status {response.status_code}"
            data = response.json()
            assert "symbols" in data, "Symbols field missing from response"
            assert isinstance(data["symbols"], list), "Symbols should be a list"
            assert len(data["symbols"]) > 0, "No symbols loaded"
            print(f"✅ Symbols endpoint: {len(data['symbols'])} symbols loaded")
            return True
        except Exception as e:
            print(f"❌ Symbols endpoint failed: {str(e)}")
            return False

class TestExchangeSystem:
    """Test multi-exchange system functionality"""
    
    def test_exchange_health(self):
        """Test exchange health monitoring"""
        try:
            response = client.get("/api/exchanges/health")
            assert response.status_code == 200, f"Exchange health failed with status {response.status_code}"
            data = response.json()
            assert "status" in data, "Status field missing"
            assert "exchanges" in data, "Exchanges field missing"
            
            exchanges = data["exchanges"]
            healthy_count = sum(1 for ex in exchanges.values() if ex.get("status") == "healthy")
            
            print(f"✅ Exchange health: {healthy_count}/{len(exchanges)} exchanges healthy")
            
            # Print detailed status
            for name, status in exchanges.items():
                status_emoji = "✅" if status.get("status") == "healthy" else "⚠️"
                response_time = status.get("response_time", "N/A")
                print(f"  {status_emoji} {name}: {status.get('status')} ({response_time}s)")
                
                if status.get("status") != "healthy":
                    print(f"    Error: {status.get('error', 'Unknown')}")
            return True
        except Exception as e:
            print(f"❌ Exchange health test failed: {str(e)}")
            return False

    def test_exchange_coverage(self):
        """Test exchange coverage information"""
        try:
            response = client.get("/api/exchanges/coverage")
            assert response.status_code == 200, f"Exchange coverage failed with status {response.status_code}"
            data = response.json()
            assert "exchanges" in data, "Exchanges field missing"
            assert "capabilities" in data, "Capabilities field missing"
            
            print(f"✅ Exchange coverage: {len(data['exchanges'])} exchanges configured")
            for name, info in data["exchanges"].items():
                print(f"  • {name}: {info['specialty']}")
            return True
        except Exception as e:
            print(f"❌ Exchange coverage test failed: {str(e)}")
            return False

    def test_best_prices_comprehensive(self):
        """Test best prices endpoint with comprehensive validation"""
        try:
            test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
            
            response = client.post(
                "/api/exchanges/best-prices",
                json={"symbols": test_symbols}
            )
            assert response.status_code == 200, f"Best prices failed with status {response.status_code}"
            data = response.json()
            assert "status" in data, "Status field missing"
            assert data["status"] == "success", f"Expected success status, got {data['status']}"
            assert "results" in data, "Results field missing"
            
            results = data["results"]
            successful_symbols = []
            
            for symbol in test_symbols:
                if symbol in results and "error" not in results[symbol]:
                    symbol_data = results[symbol]
                    
                    # Validate required fields
                    assert "best_exchange" in symbol_data, f"Missing best_exchange for {symbol}"
                    assert "best_price" in symbol_data, f"Missing best_price for {symbol}"
                    assert "all_prices" in symbol_data, f"Missing all_prices for {symbol}"
                    assert "price_spread" in symbol_data, f"Missing price_spread for {symbol}"
                    
                    # Validate price data quality
                    best_price = symbol_data["best_price"]
                    assert isinstance(best_price, (int, float)), f"Best price should be numeric for {symbol}"
                    assert best_price > 0, f"Best price should be positive for {symbol}"
                    
                    # Validate individual exchange data
                    all_prices = symbol_data["all_prices"]
                    exchanges_with_data = []
                    
                    for price_info in all_prices:
                        exchange_name = price_info["exchange"]
                        price = price_info["price"]
                        data_obj = price_info["data"]
                        
                        # Basic validation
                        assert isinstance(price, (int, float)), f"Price should be numeric for {exchange_name}"
                        assert price > 0, f"Price should be positive for {exchange_name}"
                        
                        # Check data completeness (access as dictionary since it's JSON)
                        completeness_score = 0
                        total_fields = 0
                        
                        if data_obj.get("current_price") and data_obj["current_price"] > 0:
                            completeness_score += 1
                        total_fields += 1
                        
                        if data_obj.get("price_change_24h") is not None:
                            completeness_score += 1
                        total_fields += 1
                        
                        if data_obj.get("high_24h") and data_obj["high_24h"] > 0:
                            completeness_score += 1
                        total_fields += 1
                        
                        if data_obj.get("low_24h") and data_obj["low_24h"] > 0:
                            completeness_score += 1
                        total_fields += 1
                        
                        if data_obj.get("volume_24h") and data_obj["volume_24h"] > 0:
                            completeness_score += 1
                        total_fields += 1
                        
                        completeness_percentage = (completeness_score / total_fields) * 100
                        status_emoji = "✅" if completeness_percentage >= 60 else "⚠️" if completeness_percentage >= 40 else "❌"
                        
                        exchanges_with_data.append({
                            "exchange": exchange_name,
                            "completeness": completeness_percentage,
                            "status": status_emoji
                        })
                    
                    successful_symbols.append({
                        "symbol": symbol,
                        "exchanges": len(all_prices),
                        "price_spread": symbol_data["price_spread"],
                        "arbitrage": symbol_data.get("arbitrage_opportunity", False),
                        "exchange_data": exchanges_with_data
                    })
                    
                    print(f"✅ {symbol}: {len(all_prices)} exchanges, spread: ${symbol_data['price_spread']:.4f}")
                    for ex_data in exchanges_with_data:
                        print(f"  {ex_data['status']} {ex_data['exchange']}: {ex_data['completeness']:.1f}% complete")
                else:
                    error = results.get(symbol, {}).get("error", "Unknown error")
                    print(f"❌ {symbol}: {error}")
            
            print(f"\n📊 Summary: {len(successful_symbols)}/{len(test_symbols)} symbols successful")
            return successful_symbols
        except Exception as e:
            print(f"❌ Best prices test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def test_market_summary_new_endpoint(self):
        """Test the new comprehensive market summary endpoint"""
        test_symbols = ["BTCUSDT", "ETHUSDT"]
        
        response = client.post(
            "/api/market-summary",
            json={"symbols": test_symbols}
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "success"
        assert "market_summary" in data
        
        market_summary = data["market_summary"]
        
        for symbol in test_symbols:
            if symbol in market_summary and "error" not in market_summary[symbol]:
                symbol_data = market_summary[symbol]
                
                print(f"✅ {symbol} market summary:")
                print(f"  • Primary exchange: {symbol_data.get('primary_exchange', 'N/A')}")
                print(f"  • Current price: ${symbol_data.get('current_price', 'N/A')}")
                print(f"  • 24h change: {symbol_data.get('price_change_24h', 'N/A')}")
                print(f"  • Exchange coverage: {symbol_data.get('exchange_coverage', 0)} exchanges")
                print(f"  • Price spread: ${symbol_data.get('price_spread', 'N/A')}")
                print(f"  • Arbitrage opportunity: {symbol_data.get('arbitrage_opportunity', False)}")
                
                # Validate market data from each exchange
                market_data = symbol_data.get("market_data", {})
                for exchange, ex_data in market_data.items():
                    health = ex_data.get("health_status", "unknown")
                    completeness = sum(1 for field in ["price", "price_change_24h", "high_24h", "low_24h", "volume_24h"] 
                                     if ex_data.get(field) is not None) / 5 * 100
                    print(f"    {exchange}: {health} ({completeness:.0f}% data)")

class TestAIAgent:
    """Test AI agent functionality"""
    
    def test_ai_basic_queries(self):
        """Test basic AI queries"""
        test_queries = [
            {
                "query": "What is the current price of Bitcoin?",
                "expected_symbols": ["BTCUSDT"],
                "description": "Single asset price query"
            },
            {
                "query": "Compare Bitcoin and Ethereum prices",
                "expected_symbols": ["BTCUSDT", "ETHUSDT"],
                "description": "Multi-asset comparison"
            },
            {
                "query": "Show me BTC, ETH, and SOL prices",
                "expected_symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
                "description": "Multi-asset price query"
            }
        ]
        
        for i, test_case in enumerate(test_queries, 1):
            print(f"\n🤖 Test {i}: {test_case['description']}")
            print(f"Query: '{test_case['query']}'")
            
            response = client.post(
                "/api/ask",
                json={"query": test_case["query"]}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Validate response structure
            assert "query" in data
            assert "response" in data
            assert "timestamp" in data
            
            # Check response quality
            response_text = data.get("response", "")
            assert len(response_text) > 50, f"Response too short: {len(response_text)} chars"
            
            # Check supporting data
            supporting_data = data.get("supporting_data", {})
            if supporting_data:
                print(f"✅ Supporting data: {len(supporting_data)} fields")
                for key in supporting_data.keys():
                    print(f"  • {key}")
            
            # Check metadata
            metadata = data.get("metadata", {})
            if metadata:
                print(f"✅ Metadata: {len(metadata)} fields")
                if "symbol" in metadata:
                    print(f"  • Symbol detected: {metadata['symbol']}")
                if "data_sources" in metadata:
                    print(f"  • Data sources: {metadata['data_sources']}")
            
            print(f"✅ Response ({len(response_text)} chars): {response_text[:100]}...")

class TestDataQuality:
    """Test data quality and completeness"""
    
    def test_historical_data_quality(self):
        """Test historical data quality"""
        response = client.get("/historical/BTCUSDT?interval=1h&limit=10")
        assert response.status_code == 200
        data = response.json()
        
        assert "historical_data" in data
        historical_data = data["historical_data"]
        assert len(historical_data) > 0
        
        # Validate OHLCV data structure
        for candle in historical_data[:3]:  # Check first 3 candles
            required_fields = ["timestamp", "open", "high", "low", "close", "volume"]
            for field in required_fields:
                assert field in candle, f"Missing field: {field}"
                assert candle[field] is not None, f"Null value in field: {field}"
                if field != "timestamp":
                    assert isinstance(candle[field], (int, float)), f"Invalid type for {field}"
                    assert candle[field] > 0, f"Invalid value for {field}: {candle[field]}"
        
        print(f"✅ Historical data: {len(historical_data)} candles with complete OHLCV")

    def test_prediction_data_quality(self):
        """Test prediction endpoint data quality"""
        response = client.get("/predict/BTCUSDT?interval=1h")
        assert response.status_code == 200
        data = response.json()
        
        # Validate prediction structure
        assert "metadata" in data
        assert "price_analysis" in data
        
        price_analysis = data["price_analysis"]
        required_fields = ["current", "prediction", "prediction_range"]
        for field in required_fields:
            assert field in price_analysis, f"Missing field: {field}"
        
        # Validate prediction values
        current_price = price_analysis["current"]
        prediction = price_analysis["prediction"]
        pred_range = price_analysis["prediction_range"]
        
        assert isinstance(current_price, (int, float))
        assert isinstance(prediction, (int, float))
        assert current_price > 0
        assert prediction > 0
        
        assert "low" in pred_range and "high" in pred_range
        assert pred_range["low"] < pred_range["high"]
        assert pred_range["low"] <= prediction <= pred_range["high"]
        
        print(f"✅ Prediction: ${prediction:.2f} (range: ${pred_range['low']:.2f} - ${pred_range['high']:.2f})")

    def test_investment_advice_quality(self):
        """Test investment advice data quality"""
        response = client.get("/investment-advice/BTCUSDT?interval=1h")
        assert response.status_code == 200
        data = response.json()
        
        assert "advice" in data
        advice = data["advice"]
        
        # Check for required advice components
        required_components = ["action", "confidence", "reasoning"]
        for component in required_components:
            if component in advice:
                print(f"✅ {component}: {advice[component]}")
        
        print("✅ Investment advice generated successfully")

def run_diagnostics():
    """Run system diagnostics to identify issues"""
    print("\n" + "="*60)
    print("🔧 SYSTEM DIAGNOSTICS")
    print("="*60)
    
    # Test exchange connectivity individually
    print("\n📡 Testing Exchange Connectivity:")
    
    # This would need to be implemented with direct exchange client testing
    # For now, we'll rely on the best-prices endpoint results
    
    test_client = TestExchangeSystem()
    best_prices_results = test_client.test_best_prices_comprehensive()
    
    # Analyze results for diagnostic information
    print("\n🔍 Diagnostic Analysis:")
    
    exchange_success_rates = {}
    total_tests = len(best_prices_results) if best_prices_results else 0
    
    if best_prices_results:
        for symbol_result in best_prices_results:
            for ex_data in symbol_result["exchange_data"]:
                exchange = ex_data["exchange"]
                if exchange not in exchange_success_rates:
                    exchange_success_rates[exchange] = {"success": 0, "total": 0}
                exchange_success_rates[exchange]["total"] += 1
                if ex_data["completeness"] >= 60:
                    exchange_success_rates[exchange]["success"] += 1
    
    print(f"\n📊 Exchange Performance Summary:")
    for exchange, stats in exchange_success_rates.items():
        success_rate = (stats["success"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        status_emoji = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 50 else "❌"
        print(f"  {status_emoji} {exchange}: {success_rate:.1f}% ({stats['success']}/{stats['total']})")

def main():
    """Run all tests"""
    print("🚀 Starting Comprehensive System Tests")
    print("="*60)
    
    # Initialize test classes
    health_tests = TestSystemHealth()
    exchange_tests = TestExchangeSystem()
    
    test_results = {"passed": 0, "failed": 0, "errors": []}
    
    try:
        # Run health tests
        print("\n1️⃣ SYSTEM HEALTH TESTS")
        print("-" * 40)
        
        if health_tests.test_health_check():
            test_results["passed"] += 1
        else:
            test_results["failed"] += 1
            test_results["errors"].append("Health check failed")
            
        if health_tests.test_symbols_endpoint():
            test_results["passed"] += 1
        else:
            test_results["failed"] += 1
            test_results["errors"].append("Symbols endpoint failed")
        
        # Run exchange tests
        print("\n2️⃣ EXCHANGE SYSTEM TESTS")
        print("-" * 40)
        
        if exchange_tests.test_exchange_health():
            test_results["passed"] += 1
        else:
            test_results["failed"] += 1
            test_results["errors"].append("Exchange health test failed")
            
        if exchange_tests.test_exchange_coverage():
            test_results["passed"] += 1
        else:
            test_results["failed"] += 1
            test_results["errors"].append("Exchange coverage test failed")
            
        best_prices_result = exchange_tests.test_best_prices_comprehensive()
        if best_prices_result:
            test_results["passed"] += 1
        else:
            test_results["failed"] += 1
            test_results["errors"].append("Best prices test failed")
        
        # Run diagnostics
        print("\n🔧 SYSTEM DIAGNOSTICS")
        print("-" * 40)
        run_diagnostics()
        
        # Print final summary
        print("\n" + "="*60)
        print("📋 TEST SUMMARY")
        print("="*60)
        print(f"✅ Passed: {test_results['passed']}")
        print(f"❌ Failed: {test_results['failed']}")
        print(f"📊 Total: {test_results['passed'] + test_results['failed']}")
        
        if test_results["errors"]:
            print(f"\n🚨 Errors encountered:")
            for error in test_results["errors"]:
                print(f"  • {error}")
        
        if test_results["failed"] == 0:
            print("\n🎉 ALL TESTS PASSED!")
            return True
        else:
            print(f"\n⚠️ {test_results['failed']} tests failed")
            return False
        
    except Exception as e:
        print(f"\n❌ Critical test failure: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 