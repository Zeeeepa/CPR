#!/usr/bin/env python3
"""
Deep inspection of task attributes and result handling
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import get_or_create_agent_client, default_codegen_config

async def inspect_task_attributes():
    """Deep inspection of task attributes"""
    print("=== TASK ATTRIBUTES INSPECTION ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    config = default_codegen_config
    agent_client = get_or_create_agent_client(config.org_id, config.token, config.base_url)
    print("✅ Agent client ready")
    
    # Create a simple task
    prompt = "Please respond with: 'This is a test response for attribute inspection'"
    print(f"Creating task with prompt: {prompt}")
    
    result = await agent_client.process_message(prompt, stream=True)
    
    if result.get("status") != "initiated":
        print(f"❌ Task creation failed: {result}")
        return
    
    task = result.get("task")
    task_id = result.get("task_id")
    
    print(f"✅ Task {task_id} created")
    
    # Initial inspection
    print(f"\n📋 INITIAL TASK INSPECTION:")
    print(f"   Task Type: {type(task)}")
    print(f"   Task ID: {task.id}")
    print(f"   Task Status: {task.status}")
    print(f"   Web URL: {task.web_url}")
    
    # List all attributes
    print(f"\n📋 ALL TASK ATTRIBUTES:")
    for attr_name in dir(task):
        if not attr_name.startswith('_'):
            try:
                attr_value = getattr(task, attr_name)
                if callable(attr_value):
                    print(f"   {attr_name}() - method")
                else:
                    attr_str = str(attr_value)
                    if len(attr_str) > 100:
                        attr_str = attr_str[:100] + "..."
                    print(f"   {attr_name}: {type(attr_value).__name__} = {attr_str}")
            except Exception as e:
                print(f"   {attr_name}: Error accessing - {e}")
    
    # Wait for completion and monitor all attributes
    print(f"\n📊 MONITORING ATTRIBUTE CHANGES:")
    max_checks = 15
    check_interval = 5
    
    for check in range(max_checks):
        await asyncio.sleep(check_interval)
        
        try:
            task.refresh()
            print(f"\n   Check {check + 1}: {task.status}")
            
            # Check all attributes that might contain results
            result_attrs = ['result', 'output', 'response', 'content', 'data', 'message']
            
            for attr in result_attrs:
                if hasattr(task, attr):
                    value = getattr(task, attr)
                    if value is not None:
                        value_str = str(value)
                        if len(value_str) > 200:
                            value_str = value_str[:200] + "..."
                        print(f"     {attr}: {type(value).__name__} = {value_str}")
                    else:
                        print(f"     {attr}: None")
            
            # Check if task has completed
            if task.status.lower() in ['complete', 'completed']:
                print(f"\n🎯 TASK COMPLETED - FINAL INSPECTION:")
                
                # Try to access the underlying task data
                if hasattr(task, '__dict__'):
                    print(f"   Task __dict__:")
                    for key, value in task.__dict__.items():
                        if not key.startswith('_'):
                            value_str = str(value)
                            if len(value_str) > 200:
                                value_str = value_str[:200] + "..."
                            print(f"     {key}: {type(value).__name__} = {value_str}")
                
                # Try different ways to access result
                result_methods = [
                    ('task.result', lambda: getattr(task, 'result', None)),
                    ('task.output', lambda: getattr(task, 'output', None)),
                    ('task.response', lambda: getattr(task, 'response', None)),
                    ('task.get_result()', lambda: task.get_result() if hasattr(task, 'get_result') else None),
                    ('task.fetch_result()', lambda: task.fetch_result() if hasattr(task, 'fetch_result') else None),
                ]
                
                print(f"\n🔍 TRYING DIFFERENT RESULT ACCESS METHODS:")
                for method_name, method_func in result_methods:
                    try:
                        result_value = method_func()
                        if result_value is not None:
                            result_str = str(result_value)
                            if len(result_str) > 300:
                                result_str = result_str[:300] + "..."
                            print(f"   ✅ {method_name}: {type(result_value).__name__} = {result_str}")
                        else:
                            print(f"   ❌ {method_name}: None")
                    except Exception as e:
                        print(f"   ❌ {method_name}: Error - {e}")
                
                break
                
        except Exception as e:
            print(f"   ❌ Error during check {check + 1}: {e}")
    
    # Final summary
    print(f"\n{'='*60}")
    print("TASK ATTRIBUTES SUMMARY")
    print(f"{'='*60}")
    print(f"Task ID: {task_id}")
    print(f"Final Status: {task.status}")
    print(f"Web URL: {task.web_url}")
    
    return {
        "status": "success",
        "task_id": task_id,
        "final_status": task.status,
        "web_url": task.web_url
    }

if __name__ == "__main__":
    result = asyncio.run(inspect_task_attributes())
    
    print(f"\n{'='*60}")
    print("INSPECTION RESULT")
    print(f"{'='*60}")
    for key, value in result.items():
        print(f"{key}: {value}")
    print(f"{'='*60}")
    
    if result.get("status") == "success":
        print("✅ TASK ATTRIBUTES INSPECTION COMPLETED")
        sys.exit(0)
    else:
        print("❌ TASK ATTRIBUTES INSPECTION FAILED")
        sys.exit(1)

