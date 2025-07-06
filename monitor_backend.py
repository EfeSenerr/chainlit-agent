#!/usr/bin/env python3
"""
Backend Health Monitor
Monitors the FastAPI backend for hanging requests and connection issues
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime

BACKEND_URL = "http://localhost:8000"
CHECK_INTERVAL = 30  # seconds
TIMEOUT = 10  # seconds for health checks

async def check_health():
    """Check if the backend is responding"""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
            async with session.get(f"{BACKEND_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    return True, data
                else:
                    return False, f"HTTP {response.status}"
    except asyncio.TimeoutError:
        return False, "Health check timeout"
    except Exception as e:
        return False, str(e)

async def test_api_endpoint():
    """Test the main API endpoint with a simple question"""
    try:
        test_data = {
            "question": "Hello, are you working?",
            "thread_id": "test-thread-123"
        }
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=35)) as session:
            async with session.post(
                f"{BACKEND_URL}/api/generate_response", 
                json=test_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return True, "API test successful"
                else:
                    return False, f"API test failed: HTTP {response.status}"
    except asyncio.TimeoutError:
        return False, "API test timeout (>35s)"
    except Exception as e:
        return False, f"API test error: {str(e)}"

def log_status(message, is_error=False):
    """Log status with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "❌ ERROR" if is_error else "✅ OK"
    print(f"[{timestamp}] {status}: {message}")

async def monitor_backend():
    """Main monitoring loop"""
    print("🔍 Starting Backend Health Monitor")
    print(f"📍 Monitoring: {BACKEND_URL}")
    print(f"⏱️ Check interval: {CHECK_INTERVAL} seconds")
    print("=" * 60)
    
    consecutive_failures = 0
    last_api_test = 0
    
    while True:
        try:
            # Check basic health
            health_ok, health_result = await check_health()
            
            if health_ok:
                log_status(f"Backend healthy: {health_result}")
                consecutive_failures = 0
                
                # Test API endpoint every 5 minutes
                if time.time() - last_api_test > 300:
                    log_status("Testing API endpoint...")
                    api_ok, api_result = await test_api_endpoint()
                    
                    if api_ok:
                        log_status(f"API test passed: {api_result}")
                    else:
                        log_status(f"API test failed: {api_result}", is_error=True)
                    
                    last_api_test = time.time()
            else:
                consecutive_failures += 1
                log_status(f"Backend health check failed: {health_result}", is_error=True)
                
                if consecutive_failures >= 3:
                    log_status(f"Backend has been unhealthy for {consecutive_failures} checks", is_error=True)
                    log_status("Consider restarting the backend service", is_error=True)
            
            await asyncio.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
            break
        except Exception as e:
            log_status(f"Monitor error: {e}", is_error=True)
            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(monitor_backend())
    except KeyboardInterrupt:
        print("\nExiting...")
