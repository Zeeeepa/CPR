#!/usr/bin/env python3
"""
Test the correct Agent API using the run method
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from codegen import Agent
from api import default_codegen_config

async def test_correct_api():
    """Test the correct Agent API"""
    print("Testing correct Agent API...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    config = default_codegen_config
    print(f"Using credentials:")
    print(f"   - Org ID: {config.org_id}")
    print(f"   - Token: {config.token[:10]}...{config.token[-4:]}")
    print(f"   - Base URL: {config.base_url}")
    
    try:
        agent = Agent(
            org_id=config.org_id,
            token=config.token,
            base_url=config.base_url
        )
        print("✅ Agent created successfully")
        
        # Test with the correct API
        print("Testing agent.run() method...")
        test_prompt = "Hello! This is a test. Please respond with 'SDK test successful'."
        
        try:
            # This should be synchronous based on the signature
            task = agent.run(test_prompt)
            print("✅ agent.run() call successful!")
            print(f"Task type: {type(task)}")
            
            # Inspect the task object
            print("\\nInspecting AgentTask object...")
            print(f"Task attributes:")
            for attr_name in dir(task):
                if not attr_name.startswith('_'):
                    try:
                        attr = getattr(task, attr_name)
                        if callable(attr):
                            print(f"  - {attr_name}() - method")
                        else:
                            print(f"  - {attr_name}: {type(attr)} = {attr}")
                    except Exception as e:
                        print(f"  - {attr_name}: Error accessing - {e}")
            
            return {"status": "success", "task": str(task)}
            
        except Exception as e:
            print(f"❌ agent.run() failed: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "error": str(e)}
            
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": f"Agent creation failed: {str(e)}"}

if __name__ == "__main__":
    result = asyncio.run(test_correct_api())
    
    print("\\n" + "="*50)
    print("TEST RESULT:")
    print("="*50)
    for key, value in result.items():
        print(f"{key}: {value}")
    print("="*50)
    
    if result.get("status") == "success":
        print("✅ CORRECT API TEST PASSED")
        sys.exit(0)
    else:
        print("❌ CORRECT API TEST FAILED")
        sys.exit(1)

