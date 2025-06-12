#!/usr/bin/env python3
"""
Direct SDK test script - bypasses FastAPI to test core Codegen SDK functionality
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import get_or_create_agent_client, default_codegen_config, generate_request_id

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('sdk_test.log')
    ]
)
logger = logging.getLogger(__name__)

async def test_sdk_direct():
    """Test Codegen SDK directly without FastAPI wrapper"""
    request_id = generate_request_id()
    logger.info(f"[{request_id}] === DIRECT SDK TEST ===")
    
    try:
        # Use default configuration
        org_id = default_codegen_config.org_id
        token = default_codegen_config.token
        base_url = default_codegen_config.base_url
        
        logger.info(f"[{request_id}] Test credentials:")
        logger.info(f"[{request_id}]   - Org ID: {org_id[:8] + '...' if org_id else 'None'}")
        logger.info(f"[{request_id}]   - Token: {'***' + token[-4:] if token else 'None'}")
        logger.info(f"[{request_id}]   - Base URL: {base_url}")
        
        if not org_id or not token:
            logger.error(f"[{request_id}] Missing credentials")
            return {
                "status": "error",
                "error": "Missing org_id or token",
                "request_id": request_id
            }
        
        # Test 1: Agent client creation
        logger.info(f"[{request_id}] Test 1: Creating agent client...")
        try:
            agent_client = get_or_create_agent_client(org_id, token, base_url)
            logger.info(f"[{request_id}] ✅ Agent client created successfully")
            logger.info(f"[{request_id}] Agent client type: {type(agent_client)}")
        except Exception as e:
            logger.error(f"[{request_id}] ❌ Agent client creation failed: {e}")
            logger.exception(f"[{request_id}] Full traceback:")
            return {
                "status": "error",
                "error": f"Agent client creation failed: {str(e)}",
                "request_id": request_id,
                "failed_at": "agent_client_creation"
            }
        
        # Test 2: Simple non-streaming message
        logger.info(f"[{request_id}] Test 2: Testing simple message...")
        test_prompt = "Hello! This is a minimal test. Please respond with 'SDK test successful'."
        try:
            logger.info(f"[{request_id}] Calling process_message with prompt: {test_prompt}")
            result = await agent_client.process_message(test_prompt, stream=False)
            logger.info(f"[{request_id}] ✅ Message processed successfully")
            logger.info(f"[{request_id}] Result type: {type(result)}")
            logger.info(f"[{request_id}] Result: {result}")
            
            return {
                "status": "success",
                "message": "SDK test completed successfully",
                "request_id": request_id,
                "result": result,
                "tests_passed": ["agent_client_creation", "simple_message"]
            }
            
        except Exception as e:
            logger.error(f"[{request_id}] ❌ Message processing failed: {e}")
            logger.exception(f"[{request_id}] Full traceback:")
            return {
                "status": "error",
                "error": f"Message processing failed: {str(e)}",
                "request_id": request_id,
                "failed_at": "message_processing",
                "tests_passed": ["agent_client_creation"]
            }
            
    except Exception as e:
        logger.error(f"[{request_id}] ❌ Unexpected error in SDK test: {e}")
        logger.exception(f"[{request_id}] Full traceback:")
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
            "request_id": request_id,
            "failed_at": "unexpected"
        }

if __name__ == "__main__":
    print("Starting direct SDK test...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    result = asyncio.run(test_sdk_direct())
    
    print("\n" + "="*50)
    print("TEST RESULT:")
    print("="*50)
    for key, value in result.items():
        print(f"{key}: {value}")
    print("="*50)
    
    if result.get("status") == "success":
        print("✅ SDK TEST PASSED")
        sys.exit(0)
    else:
        print("❌ SDK TEST FAILED")
        sys.exit(1)

