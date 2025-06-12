#!/usr/bin/env python3
"""
Test complete task lifecycle and status changes
"""

import asyncio
import sys
import os
import time
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import get_or_create_agent_client, default_codegen_config

async def test_task_lifecycle():
    """Test complete task lifecycle with status monitoring"""
    print("=== TASK LIFECYCLE VALIDATION ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    config = default_codegen_config
    print(f"Using credentials:")
    print(f"   - Org ID: {config.org_id}")
    print(f"   - Base URL: {config.base_url}")
    
    try:
        # Create agent client
        agent_client = get_or_create_agent_client(config.org_id, config.token, config.base_url)
        print("✅ Agent client created successfully")
        
        # Test 1: Create a simple task and monitor its lifecycle
        print("\n" + "="*60)
        print("TEST 1: Simple Task Lifecycle")
        print("="*60)
        
        simple_prompt = "Hello! Please respond with exactly: 'Task completed successfully. Current time is [current time]'"
        print(f"Creating task with prompt: {simple_prompt}")
        
        # Create task in streaming mode (immediate return)
        result = await agent_client.process_message(simple_prompt, stream=True)
        
        if result.get("status") != "initiated":
            print(f"❌ Task creation failed: {result}")
            return {"status": "error", "error": "Task creation failed"}
        
        task = result.get("task")
        task_id = result.get("task_id")
        
        print(f"✅ Task created successfully:")
        print(f"   - Task ID: {task_id}")
        print(f"   - Initial Status: {task.status}")
        print(f"   - Web URL: {task.web_url}")
        
        # Monitor task status changes
        print(f"\n📊 Monitoring task status changes...")
        status_history = []
        max_monitoring_time = 120  # 2 minutes
        check_interval = 10  # 10 seconds
        max_checks = max_monitoring_time // check_interval
        
        for check_num in range(max_checks):
            try:
                task.refresh()
                current_status = task.status
                current_time = datetime.now().isoformat()
                
                status_entry = {
                    "check": check_num + 1,
                    "time": current_time,
                    "status": current_status,
                    "result_available": hasattr(task, 'result') and task.result is not None
                }
                status_history.append(status_entry)
                
                print(f"   Check {check_num + 1:2d}: {current_status:12s} | Result: {'Yes' if status_entry['result_available'] else 'No':3s} | {current_time}")
                
                # Check for completion
                if current_status.lower() in ['completed', 'failed', 'cancelled']:
                    print(f"\n🎯 Task reached final status: {current_status}")
                    
                    if current_status.lower() == 'completed':
                        result_content = getattr(task, 'result', None)
                        print(f"📄 Task Result:")
                        if result_content:
                            print(f"   {result_content}")
                        else:
                            print("   No result content available")
                    elif current_status.lower() == 'failed':
                        error_content = getattr(task, 'error', 'Unknown error')
                        print(f"❌ Task Error: {error_content}")
                    
                    break
                
                # Wait before next check
                if check_num < max_checks - 1:
                    await asyncio.sleep(check_interval)
                    
            except Exception as e:
                print(f"❌ Error during status check {check_num + 1}: {e}")
                break
        
        # Test 2: Test different prompt types
        print("\n" + "="*60)
        print("TEST 2: Different Prompt Types")
        print("="*60)
        
        test_prompts = [
            {
                "name": "Quick Response",
                "prompt": "Say 'Hello World' and nothing else.",
                "expected_duration": "short"
            },
            {
                "name": "Code Generation",
                "prompt": "Write a simple Python function that adds two numbers.",
                "expected_duration": "medium"
            },
            {
                "name": "Analysis Task",
                "prompt": "Explain the benefits of using async/await in Python.",
                "expected_duration": "medium"
            }
        ]
        
        prompt_results = []
        
        for i, test_case in enumerate(test_prompts, 1):
            print(f"\nTest 2.{i}: {test_case['name']}")
            print(f"Prompt: {test_case['prompt']}")
            
            try:
                # Create task
                result = await agent_client.process_message(test_case['prompt'], stream=True)
                
                if result.get("status") == "initiated":
                    task = result.get("task")
                    task_id = result.get("task_id")
                    
                    print(f"✅ Task {task_id} created")
                    
                    # Quick status check (don't wait for completion)
                    await asyncio.sleep(2)
                    task.refresh()
                    
                    prompt_results.append({
                        "name": test_case['name'],
                        "task_id": task_id,
                        "initial_status": task.status,
                        "web_url": task.web_url
                    })
                    
                    print(f"   Status after 2s: {task.status}")
                    print(f"   Web URL: {task.web_url}")
                else:
                    print(f"❌ Task creation failed: {result}")
                    
            except Exception as e:
                print(f"❌ Error in test case {i}: {e}")
        
        # Test 3: Error handling
        print("\n" + "="*60)
        print("TEST 3: Error Handling")
        print("="*60)
        
        # Test with potentially problematic prompt
        error_prompt = "This is a test prompt that might cause issues: " + "x" * 1000  # Very long prompt
        print(f"Testing error handling with long prompt ({len(error_prompt)} chars)")
        
        try:
            result = await agent_client.process_message(error_prompt, stream=True)
            print(f"Result: {result.get('status')}")
            
            if result.get("status") == "initiated":
                task = result.get("task")
                print(f"✅ Long prompt handled successfully, task ID: {task.id}")
            else:
                print(f"⚠️ Long prompt result: {result}")
                
        except Exception as e:
            print(f"❌ Error handling test failed: {e}")
        
        # Summary
        print("\n" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)
        
        print(f"📊 Status History for Task {task_id}:")
        for entry in status_history:
            print(f"   {entry['check']:2d}. {entry['time']} | {entry['status']:12s} | Result: {'✓' if entry['result_available'] else '✗'}")
        
        print(f"\n📋 Created Tasks:")
        for result in prompt_results:
            print(f"   - {result['name']:15s} | ID: {result['task_id']:8s} | Status: {result['initial_status']:10s}")
        
        return {
            "status": "success",
            "main_task_id": task_id,
            "final_status": status_history[-1]['status'] if status_history else "unknown",
            "status_changes": len(set(entry['status'] for entry in status_history)),
            "additional_tasks": len(prompt_results),
            "total_checks": len(status_history)
        }
        
    except Exception as e:
        print(f"❌ Lifecycle test failed: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    result = asyncio.run(test_task_lifecycle())
    
    print("\n" + "="*60)
    print("FINAL TEST RESULT")
    print("="*60)
    for key, value in result.items():
        print(f"{key}: {value}")
    print("="*60)
    
    if result.get("status") == "success":
        print("✅ TASK LIFECYCLE VALIDATION PASSED")
        sys.exit(0)
    else:
        print("❌ TASK LIFECYCLE VALIDATION FAILED")
        sys.exit(1)

