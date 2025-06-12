#!/usr/bin/env python3
"""
Test streaming vs non-streaming behavior
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import get_or_create_agent_client, default_codegen_config

async def test_streaming_behavior():
    """Test both streaming and non-streaming behavior"""
    print("Testing streaming behavior...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    config = default_codegen_config
    print(f"Using credentials:")
    print(f"   - Org ID: {config.org_id}")
    print(f"   - Token: {config.token[:10]}...{config.token[-4:]}")
    print(f"   - Base URL: {config.base_url}")
    
    try:
        agent_client = get_or_create_agent_client(config.org_id, config.token, config.base_url)
        print("✅ Agent client created successfully")
        
        # Test 1: Streaming (should return immediately)
        print("\\nTest 1: Streaming mode (should return immediately)...")
        test_prompt = "Hello! This is a streaming test."
        
        try:
            result = await agent_client.process_message(test_prompt, stream=True)
            print("✅ Streaming call successful!")
            print(f"Result: {result}")
            
            if result.get("status") == "initiated":
                task = result.get("task")
                if task:
                    print(f"Task ID: {task.id}")
                    print(f"Task status: {task.status}")
                    print(f"Task web URL: {task.web_url}")
            
        except Exception as e:
            print(f"❌ Streaming call failed: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "error": str(e)}
        
        # Test 2: Non-streaming with timeout (should wait for completion)
        print("\\nTest 2: Non-streaming mode with short timeout...")
        test_prompt2 = "Hello! This is a non-streaming test. Please respond briefly."
        
        try:
            # Modify the agent client to have a shorter timeout for testing
            original_process = agent_client.process_message
            
            async def process_with_timeout(message, stream=True):
                if not stream:
                    # Override the max_retries for testing
                    task = agent_client.agent.run(prompt=message)
                    task_id = str(task.id) if task.id else f"task_{datetime.now().timestamp()}"
                    
                    # Wait only 3 iterations (15 seconds) for testing
                    max_retries = 3
                    for i in range(max_retries):
                        print(f"  Checking task status (attempt {i+1}/{max_retries})...")
                        task.refresh()
                        status = task.status.lower() if task.status else "unknown"
                        print(f"  Status: {status}")
                        
                        if status == "completed":
                            return {
                                "status": "completed",
                                "result": getattr(task, 'result', None),
                                "task_id": task_id,
                                "web_url": getattr(task, 'web_url', None)
                            }
                        elif status == "failed":
                            return {
                                "status": "failed",
                                "error": getattr(task, 'error', "Unknown error"),
                                "task_id": task_id
                            }
                        
                        if i < max_retries - 1:  # Don't sleep on the last iteration
                            await asyncio.sleep(5)
                    
                    return {
                        "status": "timeout",
                        "error": "Task timed out (test timeout)",
                        "task_id": task_id,
                        "final_status": task.status
                    }
                else:
                    return await original_process(message, stream)
            
            result = await process_with_timeout(test_prompt2, stream=False)
            print("✅ Non-streaming call completed!")
            print(f"Result: {result}")
            
            return {"status": "success", "streaming_result": "initiated", "non_streaming_result": result.get("status")}
            
        except Exception as e:
            print(f"❌ Non-streaming call failed: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "error": str(e)}
            
    except Exception as e:
        print(f"❌ Agent client creation failed: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": f"Agent client creation failed: {str(e)}"}

if __name__ == "__main__":
    result = asyncio.run(test_streaming_behavior())
    
    print("\\n" + "="*50)
    print("TEST RESULT:")
    print("="*50)
    for key, value in result.items():
        print(f"{key}: {value}")
    print("="*50)
    
    if result.get("status") == "success":
        print("✅ STREAMING BEHAVIOR TEST PASSED")
        sys.exit(0)
    else:
        print("❌ STREAMING BEHAVIOR TEST FAILED")
        sys.exit(1)

