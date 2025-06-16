#!/usr/bin/env python3
"""
Direct System Test
Tests the API endpoints directly via HTTP requests to avoid syntax errors in main.py
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(method: str, endpoint: str, data: Dict = None, timeout: int = 30) -> Dict[str, Any]:
    """Test an API endpoint and return standardized results"""
    result = {
        "endpoint": endpoint,
        "method": method,
        "success": False,
        "status_code": None,
        "response": None,
        "error": None,
        "response_time": None
    }
    
    start_time = time.time()
    
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=timeout)
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{endpoint}", json=data, timeout=timeout)
        else:
            result["error"] = f"Unsupported method: {method}"
            return result
        
        result["response_time"] = time.time() - start_time
        result["status_code"] = response.status_code
        
        if response.status_code == 200:
            result["response"] = response.json()
            result["success"] = True
        else:
            result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
            
    except requests.exceptions.Timeout:
        result["error"] = f"Request timeout after {timeout}s"
    except requests.exceptions.ConnectionError:
        result["error"] = "Connection error - is the server running?"
    except Exception as e:
        result["error"] = f"Request failed: {str(e)}"
        result["response_time"] = time.time() - start_time
    
    return result

def print_test_result(result: Dict[str, Any], description: str = ""):
    """Print formatted test results"""
    status_emoji = "✅" if result["success"] else "❌"
    endpoint = result["endpoint"]
    method = result["method"]
    response_time = result.get("response_time", 0)
    
    print(f"{status_emoji} {method} {endpoint}")
    if description:
        print(f"   📝 {description}")
    
    if result["success"]:
        print(f"   ⏱️ Response time: {response_time:.3f}s")
        if "response" in result and result["response"]:
            response_data = result["response"]
            if isinstance(response_data, dict):
                print(f"   📊 Response keys: {list(response_data.keys())}")
    else:
        print(f"   💥 Error: {result['error']}")
        if result["status_code"]:
            print(f"   📟 Status: {result['status_code']}")

def test_system_health():
    """Test basic system health endpoints"""
    print("\n" + "="*60)
    print("🏥 SYSTEM HEALTH TESTS")
    print("="*60)
    
    tests = [
        ("GET", "/api/health", None, "Health check endpoint"),
        ("GET", "/", None, "Root endpoint"),
        ("GET", "/symbols", None, "Trading symbols endpoint"),
    ]
    
    results = []
    for method, endpoint, data, description in tests:
        result = test_endpoint(method, endpoint, data)
        print_test_result(result, description)
        results.append(result)
    
    return results

def test_exchange_endpoints():
    """Test multi-exchange system endpoints"""
    print("\n" + "="*60)
    print("🏢 EXCHANGE SYSTEM TESTS")
    print("="*60)
    
    tests = [
        ("GET", "/api/exchanges/health", None, "Exchange health monitoring"),
        ("GET", "/api/exchanges/coverage", None, "Exchange coverage information"),
        ("POST", "/api/exchanges/best-prices", {"symbols": ["BTCUSDT", "ETHUSDT"]}, "Best prices across exchanges"),
    ]
    
    results = []
    for method, endpoint, data, description in tests:
        result = test_endpoint(method, endpoint, data)
        print_test_result(result, description)
        results.append(result)
        
        # Analyze best prices response in detail
        if endpoint == "/api/exchanges/best-prices" and result["success"]:
            analyze_best_prices_response(result["response"])
    
    return results

def analyze_best_prices_response(response_data: Dict[str, Any]):
    """Analyze the best prices response for data quality"""
    print("   🔍 Detailed Analysis:")
    
    if "results" not in response_data:
        print("   ❌ Missing 'results' field")
        return
    
    results = response_data["results"]
    
    for symbol, symbol_data in results.items():
        if "error" in symbol_data:
            print(f"   ❌ {symbol}: {symbol_data['error']}")
            continue
            
        if "all_prices" not in symbol_data:
            print(f"   ⚠️ {symbol}: Missing price data")
            continue
        
        all_prices = symbol_data["all_prices"]
        exchange_count = len(all_prices)
        best_price = symbol_data.get("best_price", 0)
        price_spread = symbol_data.get("price_spread", 0)
        
        print(f"   ✅ {symbol}: {exchange_count} exchanges, best: ${best_price:.2f}, spread: ${price_spread:.4f}")
        
        # Check data completeness for each exchange
        for price_info in all_prices:
            exchange = price_info["exchange"]
            data_obj = price_info["data"]
            
            # Count non-null fields
            fields = ["current_price", "price_change_24h", "high_24h", "low_24h", "volume_24h"]
            non_null_count = sum(1 for field in fields if data_obj.get(field) is not None)
            completeness = (non_null_count / len(fields)) * 100
            
            status_emoji = "✅" if completeness >= 60 else "⚠️" if completeness >= 40 else "❌"
            print(f"     {status_emoji} {exchange}: {completeness:.0f}% data complete")

def test_historical_and_prediction():
    """Test historical data and prediction endpoints"""
    print("\n" + "="*60)
    print("📈 HISTORICAL & PREDICTION TESTS")
    print("="*60)
    
    tests = [
        ("GET", "/historical/BTCUSDT?interval=1h&limit=10", None, "Historical OHLCV data"),
        ("GET", "/predict/BTCUSDT?interval=1h", None, "Price prediction"),
        ("GET", "/investment-advice/BTCUSDT?interval=1h", None, "Investment advice"),
    ]
    
    results = []
    for method, endpoint, data, description in tests:
        result = test_endpoint(method, endpoint, data, timeout=45)  # Longer timeout for complex endpoints
        print_test_result(result, description)
        results.append(result)
        
        # Additional analysis for specific endpoints
        if result["success"] and "/historical/" in endpoint:
            analyze_historical_data(result["response"])
        elif result["success"] and "/predict/" in endpoint:
            analyze_prediction_data(result["response"])
    
    return results

def analyze_historical_data(response_data: Dict[str, Any]):
    """Analyze historical data response"""
    if "historical_data" in response_data:
        data = response_data["historical_data"]
        print(f"   📊 {len(data)} candles received")
        if data:
            first_candle = data[0]
            required_fields = ["timestamp", "open", "high", "low", "close", "volume"]
            missing_fields = [field for field in required_fields if field not in first_candle]
            if missing_fields:
                print(f"   ⚠️ Missing fields: {missing_fields}")
            else:
                print("   ✅ Complete OHLCV data structure")

def analyze_prediction_data(response_data: Dict[str, Any]):
    """Analyze prediction data response"""
    if "price_analysis" in response_data:
        analysis = response_data["price_analysis"]
        current = analysis.get("current", 0)
        prediction = analysis.get("prediction", 0)
        print(f"   📊 Current: ${current:.2f}, Predicted: ${prediction:.2f}")
        
        if "prediction_range" in analysis:
            pred_range = analysis["prediction_range"]
            low = pred_range.get("low", 0)
            high = pred_range.get("high", 0)
            print(f"   📊 Range: ${low:.2f} - ${high:.2f}")

def test_ai_agent():
    """Test AI agent endpoints"""
    print("\n" + "="*60)
    print("🤖 AI AGENT TESTS")
    print("="*60)
    
    test_queries = [
        "What is the current price of Bitcoin?",
        "Compare Bitcoin and Ethereum prices",
        "Show me BTC, ETH, and SOL prices",
    ]
    
    results = []
    for i, query in enumerate(test_queries, 1):
        print(f"\n🧪 Test {i}: {query}")
        result = test_endpoint("POST", "/api/ask", {"query": query}, timeout=60)
        
        if result["success"]:
            response_data = result["response"]
            response_text = response_data.get("response", "")
            supporting_data = response_data.get("supporting_data", {})
            metadata = response_data.get("metadata", {})
            
            print(f"   ✅ Response generated ({len(response_text)} chars)")
            print(f"   📊 Supporting data: {len(supporting_data)} fields")
            print(f"   🏷️ Metadata: {list(metadata.keys())}")
            print(f"   💬 Preview: {response_text[:100]}...")
        else:
            print(f"   ❌ Query failed: {result['error']}")
        
        results.append(result)
        time.sleep(2)  # Rate limiting
    
    return results

def run_diagnostics(all_results: List[Dict[str, Any]]):
    """Run system diagnostics based on test results"""
    print("\n" + "="*60)
    print("🔧 SYSTEM DIAGNOSTICS")
    print("="*60)
    
    # Calculate success rates
    total_tests = len(all_results)
    successful_tests = sum(1 for r in all_results if r["success"])
    success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"📊 Overall Success Rate: {success_rate:.1f}% ({successful_tests}/{total_tests})")
    
    # Analyze response times
    response_times = [r["response_time"] for r in all_results if r["response_time"] is not None]
    if response_times:
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        print(f"⏱️ Average Response Time: {avg_response_time:.3f}s")
        print(f"⏱️ Max Response Time: {max_response_time:.3f}s")
    
    # Identify problematic endpoints
    failed_tests = [r for r in all_results if not r["success"]]
    if failed_tests:
        print(f"\n🚨 Failed Endpoints:")
        for test in failed_tests:
            print(f"   ❌ {test['method']} {test['endpoint']}: {test['error']}")
    
    # System recommendations
    print(f"\n💡 Recommendations:")
    if success_rate >= 90:
        print("   ✅ System is performing well")
    elif success_rate >= 70:
        print("   ⚠️ System has some issues but is mostly functional")
        print("   🔧 Consider investigating failed endpoints")
    else:
        print("   🚨 System has significant issues")
        print("   🔧 Immediate attention required")
    
    if avg_response_time > 5.0:
        print("   ⚠️ Response times are slow - consider optimization")
    
    return {
        "total_tests": total_tests,
        "successful_tests": successful_tests,
        "success_rate": success_rate,
        "avg_response_time": avg_response_time if response_times else 0,
        "failed_endpoints": len(failed_tests)
    }

def main():
    """Run comprehensive system tests"""
    print("🚀 STARTING DIRECT API SYSTEM TESTS")
    print("🔗 Testing server at:", BASE_URL)
    print("⏰ Started at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    all_results = []
    
    try:
        # Test system health
        health_results = test_system_health()
        all_results.extend(health_results)
        
        # Test exchange endpoints
        exchange_results = test_exchange_endpoints()
        all_results.extend(exchange_results)
        
        # Test historical and prediction endpoints
        historical_results = test_historical_and_prediction()
        all_results.extend(historical_results)
        
        # Test AI agent (only if basic endpoints are working)
        basic_health = any(r["success"] and r["endpoint"] == "/api/health" for r in health_results)
        if basic_health:
            ai_results = test_ai_agent()
            all_results.extend(ai_results)
        else:
            print("\n⚠️ Skipping AI agent tests due to basic connectivity issues")
        
        # Run diagnostics
        diagnostics = run_diagnostics(all_results)
        
        # Final summary
        print("\n" + "="*60)
        print("📋 FINAL SUMMARY")
        print("="*60)
        print(f"✅ Tests Passed: {diagnostics['successful_tests']}")
        print(f"❌ Tests Failed: {diagnostics['failed_endpoints']}")
        print(f"📊 Success Rate: {diagnostics['success_rate']:.1f}%")
        print(f"⏱️ Avg Response Time: {diagnostics['avg_response_time']:.3f}s")
        
        if diagnostics['success_rate'] >= 80:
            print("\n🎉 SYSTEM STATUS: HEALTHY")
            return True
        else:
            print("\n⚠️ SYSTEM STATUS: NEEDS ATTENTION")
            return False
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Tests interrupted by user")
        return False
    except Exception as e:
        print(f"\n\n💥 Test framework error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 