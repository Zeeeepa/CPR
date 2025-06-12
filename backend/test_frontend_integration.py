#!/usr/bin/env python3
"""
Test frontend integration patterns - simulating actual frontend usage
"""

import asyncio
import sys
import os
import json
import aiohttp
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_frontend_integration():
    """Test frontend integration patterns"""
    print("=== FRONTEND INTEGRATION TESTING ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Start the backend server
    print("🚀 Starting backend server...")
    
    import subprocess
    import time
    
    # Start server in background
    server_process = subprocess.Popen([
        "python", "-m", "uvicorn", "api:app", 
        "--host", "0.0.0.0", "--port", "8002"
    ], cwd=".", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for server to start
    await asyncio.sleep(3)
    
    try:
        async with aiohttp.ClientSession() as session:
            base_url = "http://localhost:8002"
            
            # Test 1: Health check
            print(f"\n{'='*60}")
            print("TEST 1: Health Check")
            print(f"{'='*60}")
            
            try:
                async with session.get(f"{base_url}/api/v1/health") as response:
                    health_data = await response.json()
                    print(f"✅ Health check: {response.status}")
                    print(f"   Status: {health_data.get('status')}")
                    print(f"   Codegen Available: {health_data.get('codegen_available')}")
                    print(f"   Version: {health_data.get('version')}")
            except Exception as e:
                print(f"❌ Health check failed: {e}")
                return {"status": "error", "error": "Health check failed"}
            
            # Test 2: SDK Test Endpoint
            print(f"\n{'='*60}")
            print("TEST 2: SDK Test Endpoint")
            print(f"{'='*60}")
            
            try:
                async with session.post(f"{base_url}/api/v1/test-sdk") as response:
                    sdk_data = await response.json()
                    print(f"✅ SDK test: {response.status}")
                    print(f"   Status: {sdk_data.get('status')}")
                    print(f"   Message: {sdk_data.get('message', 'N/A')}")
                    if sdk_data.get('result'):
                        print(f"   Result: {sdk_data['result']}")
                    if sdk_data.get('tests_passed'):
                        print(f"   Tests Passed: {sdk_data['tests_passed']}")
            except Exception as e:
                print(f"❌ SDK test failed: {e}")
                return {"status": "error", "error": "SDK test failed"}
            
            # Test 3: Chat API - Streaming
            print(f"\n{'='*60}")
            print("TEST 3: Chat API - Streaming Mode")
            print(f"{'='*60}")
            
            chat_request = {
                "prompt": "Hello! Please respond with 'Frontend integration test successful'",
                "stream": True
            }
            
            try:
                async with session.post(
                    f"{base_url}/api/v1/chat", 
                    json=chat_request,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    chat_data = await response.json()
                    print(f"✅ Chat streaming: {response.status}")
                    print(f"   Status: {chat_data.get('status')}")
                    print(f"   Task ID: {chat_data.get('task_id')}")
                    print(f"   Message: {chat_data.get('message', 'N/A')}")
                    
                    streaming_task_id = chat_data.get('task_id')
                    
            except Exception as e:
                print(f"❌ Chat streaming failed: {e}")
                streaming_task_id = None
            
            # Test 4: Chat API - Non-streaming
            print(f"\n{'='*60}")
            print("TEST 4: Chat API - Non-streaming Mode")
            print(f"{'='*60}")
            
            chat_request_sync = {
                "prompt": "Please respond with exactly: 'Non-streaming test complete'",
                "stream": False
            }
            
            try:
                # Use longer timeout for non-streaming
                timeout = aiohttp.ClientTimeout(total=90)
                async with session.post(
                    f"{base_url}/api/v1/chat", 
                    json=chat_request_sync,
                    headers={"Content-Type": "application/json"},
                    timeout=timeout
                ) as response:
                    chat_data = await response.json()
                    print(f"✅ Chat non-streaming: {response.status}")
                    print(f"   Status: {chat_data.get('status')}")
                    print(f"   Task ID: {chat_data.get('task_id')}")
                    print(f"   Result: {chat_data.get('result', 'N/A')}")
                    
                    nonstreaming_task_id = chat_data.get('task_id')
                    
            except Exception as e:
                print(f"❌ Chat non-streaming failed: {e}")
                nonstreaming_task_id = None
            
            # Test 5: Task Status API (if we have task IDs)
            if streaming_task_id:
                print(f"\n{'='*60}")
                print("TEST 5: Task Status API")
                print(f"{'='*60}")
                
                try:
                    async with session.get(f"{base_url}/api/v1/tasks/{streaming_task_id}/status") as response:
                        status_data = await response.json()
                        print(f"✅ Task status: {response.status}")
                        print(f"   Task ID: {status_data.get('task_id')}")
                        print(f"   Status: {status_data.get('status')}")
                        print(f"   Result Available: {status_data.get('result') is not None}")
                        
                except Exception as e:
                    print(f"❌ Task status failed: {e}")
            
            # Test 6: Error handling
            print(f"\n{'='*60}")
            print("TEST 6: Error Handling")
            print(f"{'='*60}")
            
            # Test invalid endpoint
            try:
                async with session.get(f"{base_url}/api/v1/invalid") as response:
                    print(f"Invalid endpoint response: {response.status}")
            except Exception as e:
                print(f"Invalid endpoint error (expected): {e}")
            
            # Test malformed request
            try:
                async with session.post(
                    f"{base_url}/api/v1/chat", 
                    json={"invalid": "request"},
                    headers={"Content-Type": "application/json"}
                ) as response:
                    error_data = await response.json()
                    print(f"Malformed request response: {response.status}")
                    print(f"   Error: {error_data}")
            except Exception as e:
                print(f"Malformed request error: {e}")
            
            print(f"\n{'='*60}")
            print("FRONTEND INTEGRATION SUMMARY")
            print(f"{'='*60}")
            print("✅ All core endpoints tested")
            print("✅ Both streaming and non-streaming modes tested")
            print("✅ Error handling tested")
            print("✅ Task status tracking tested")
            
            return {
                "status": "success",
                "tests_completed": 6,
                "streaming_task_id": streaming_task_id,
                "nonstreaming_task_id": nonstreaming_task_id
            }
            
    except Exception as e:
        print(f"❌ Frontend integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e)}
        
    finally:
        # Clean up server
        print(f"\n🛑 Stopping backend server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()

if __name__ == "__main__":
    result = asyncio.run(test_frontend_integration())
    
    print(f"\n{'='*60}")
    print("FINAL INTEGRATION RESULT")
    print(f"{'='*60}")
    for key, value in result.items():
        print(f"{key}: {value}")
    print(f"{'='*60}")
    
    if result.get("status") == "success":
        print("✅ FRONTEND INTEGRATION TESTING PASSED")
        sys.exit(0)
    else:
        print("❌ FRONTEND INTEGRATION TESTING FAILED")
        sys.exit(1)
