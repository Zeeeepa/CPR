#!/usr/bin/env python3
"""
Test actual result content and response quality
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import get_or_create_agent_client, default_codegen_config

async def test_result_content():
    """Test actual result content from completed tasks"""
    print("=== RESULT CONTENT VALIDATION ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    config = default_codegen_config
    agent_client = get_or_create_agent_client(config.org_id, config.token, config.base_url)
    print("✅ Agent client ready")
    
    test_cases = [
        {
            "name": "Simple Response",
            "prompt": "Please respond with exactly: 'Hello from Codegen API test'",
            "expected_keywords": ["Hello", "Codegen", "API", "test"]
        },
        {
            "name": "JSON Response",
            "prompt": "Return a JSON object with keys 'status', 'message', and 'timestamp'. Set status to 'success'.",
            "expected_keywords": ["status", "success", "message", "timestamp"]
        },
        {
            "name": "Code Generation",
            "prompt": "Write a Python function called 'calculate_sum' that takes two parameters and returns their sum.",
            "expected_keywords": ["def", "calculate_sum", "return", "sum"]
        },
        {
            "name": "Explanation",
            "prompt": "Explain in 2 sentences what REST API means.",
            "expected_keywords": ["REST", "API", "HTTP"]
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"TEST {i}: {test_case['name']}")
        print(f"{'='*60}")
        print(f"Prompt: {test_case['prompt']}")
        
        try:
            # Create task
            result = await agent_client.process_message(test_case['prompt'], stream=True)
            
            if result.get("status") != "initiated":
                print(f"❌ Task creation failed: {result}")
                continue
            
            task = result.get("task")
            task_id = result.get("task_id")
            
            print(f"✅ Task {task_id} created")
            print(f"📊 Monitoring completion...")
            
            # Wait for completion with detailed monitoring
            max_wait_time = 60  # 1 minute
            check_interval = 5   # 5 seconds
            max_checks = max_wait_time // check_interval
            
            task_result = None
            final_status = None
            
            for check in range(max_checks):
                await asyncio.sleep(check_interval)
                task.refresh()
                current_status = task.status
                
                print(f"   Check {check + 1:2d}: {current_status}")
                
                if current_status.lower() in ['complete', 'completed']:
                    final_status = current_status
                    task_result = getattr(task, 'result', None)
                    print(f"✅ Task completed!")
                    break
                elif current_status.lower() in ['failed', 'cancelled']:
                    final_status = current_status
                    error_msg = getattr(task, 'error', 'Unknown error')
                    print(f"❌ Task failed: {error_msg}")
                    break
            
            if final_status and final_status.lower() in ['complete', 'completed']:
                print(f"\n📄 RESULT CONTENT:")
                print(f"   Type: {type(task_result)}")
                print(f"   Length: {len(str(task_result)) if task_result else 0} characters")
                
                if task_result:
                    # Display result content
                    result_str = str(task_result)
                    if len(result_str) > 500:
                        print(f"   Content (first 500 chars): {result_str[:500]}...")
                    else:
                        print(f"   Content: {result_str}")
                    
                    # Check for expected keywords
                    found_keywords = []
                    missing_keywords = []
                    
                    for keyword in test_case['expected_keywords']:
                        if keyword.lower() in result_str.lower():
                            found_keywords.append(keyword)
                        else:
                            missing_keywords.append(keyword)
                    
                    print(f"\n🔍 KEYWORD ANALYSIS:")
                    print(f"   Found: {found_keywords}")
                    if missing_keywords:
                        print(f"   Missing: {missing_keywords}")
                    
                    quality_score = len(found_keywords) / len(test_case['expected_keywords'])
                    print(f"   Quality Score: {quality_score:.2f} ({len(found_keywords)}/{len(test_case['expected_keywords'])})")
                    
                    results.append({
                        "name": test_case['name'],
                        "task_id": task_id,
                        "status": "completed",
                        "result_length": len(result_str),
                        "quality_score": quality_score,
                        "found_keywords": found_keywords,
                        "missing_keywords": missing_keywords,
                        "web_url": task.web_url
                    })
                else:
                    print(f"⚠️ Task completed but no result content available")
                    results.append({
                        "name": test_case['name'],
                        "task_id": task_id,
                        "status": "completed_no_result",
                        "result_length": 0,
                        "quality_score": 0,
                        "web_url": task.web_url
                    })
            else:
                print(f"⚠️ Task did not complete within {max_wait_time} seconds")
                results.append({
                    "name": test_case['name'],
                    "task_id": task_id,
                    "status": final_status or "timeout",
                    "result_length": 0,
                    "quality_score": 0,
                    "web_url": task.web_url
                })
                
        except Exception as e:
            print(f"❌ Error in test case {i}: {e}")
            results.append({
                "name": test_case['name'],
                "status": "error",
                "error": str(e)
            })
    
    # Summary
    print(f"\n{'='*60}")
    print("RESULT CONTENT SUMMARY")
    print(f"{'='*60}")
    
    completed_tasks = [r for r in results if r.get('status') == 'completed']
    avg_quality = sum(r.get('quality_score', 0) for r in completed_tasks) / len(completed_tasks) if completed_tasks else 0
    
    print(f"📊 STATISTICS:")
    print(f"   Total Tests: {len(test_cases)}")
    print(f"   Completed: {len(completed_tasks)}")
    print(f"   Average Quality Score: {avg_quality:.2f}")
    
    print(f"\n📋 DETAILED RESULTS:")
    for result in results:
        status_emoji = "✅" if result.get('status') == 'completed' else "❌"
        quality = result.get('quality_score', 0)
        print(f"   {status_emoji} {result['name']:20s} | Score: {quality:.2f} | Status: {result.get('status', 'unknown')}")
        if result.get('web_url'):
            print(f"      URL: {result['web_url']}")
    
    return {
        "status": "success",
        "total_tests": len(test_cases),
        "completed_tasks": len(completed_tasks),
        "average_quality": avg_quality,
        "results": results
    }

if __name__ == "__main__":
    result = asyncio.run(test_result_content())
    
    print(f"\n{'='*60}")
    print("FINAL VALIDATION RESULT")
    print(f"{'='*60}")
    for key, value in result.items():
        if key != 'results':  # Don't print the detailed results again
            print(f"{key}: {value}")
    print(f"{'='*60}")
    
    if result.get("status") == "success" and result.get("completed_tasks", 0) > 0:
        print("✅ RESULT CONTENT VALIDATION PASSED")
        sys.exit(0)
    else:
        print("❌ RESULT CONTENT VALIDATION FAILED")
        sys.exit(1)

