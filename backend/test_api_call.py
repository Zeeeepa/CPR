#!/usr/bin/env python3
"""
Test API call with timeout to identify the hanging issue
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from codegen import Agent
from api import default_codegen_config

async def test_api_call_with_timeout():
    """Test API call with timeout"""
    print("Starting API call test with timeout...")
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
        
        # Test with a very short timeout
        print("Testing API call with 10 second timeout...")
        test_prompt = "Hello! This is a test."
        
        try:
            result = await asyncio.wait_for(
                agent.process_message(test_prompt, stream=False),
                timeout=10.0
            )
            print("✅ API call successful!")
            print(f"Result: {result}")
            return {"status": "success", "result": result}
            
        except asyncio.TimeoutError:
            print("❌ API call timed out after 10 seconds")
            return {"status": "timeout", "error": "API call timed out"}
            
        except Exception as e:
            print(f"❌ API call failed: {e}")
            return {"status": "error", "error": str(e)}
            
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        return {"status": "error", "error": f"Agent creation failed: {str(e)}"}

if __name__ == "__main__":
    result = asyncio.run(test_api_call_with_timeout())
    
    print("\n" + "="*50)
    print("TEST RESULT:")
    print("="*50)
    for key, value in result.items():
        print(f"{key}: {value}")
    print("="*50)
    
    if result.get("status") == "success":
        print("✅ API CALL TEST PASSED")
        sys.exit(0)
    else:
        print("❌ API CALL TEST FAILED")
        sys.exit(1)

