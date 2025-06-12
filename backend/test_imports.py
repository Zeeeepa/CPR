#!/usr/bin/env python3
"""
Test imports step by step to isolate the hanging issue
"""

import sys
import os

print("Step 1: Basic imports...")
import logging
import asyncio
from datetime import datetime
print("✅ Basic imports successful")

print("Step 2: Adding backend to path...")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
print("✅ Path added")

print("Step 3: Testing Codegen import...")
try:
    from codegen import Agent
    print("✅ Codegen Agent import successful")
except Exception as e:
    print(f"❌ Codegen Agent import failed: {e}")
    sys.exit(1)

print("Step 4: Testing API imports...")
try:
    from api import default_codegen_config, generate_request_id
    print("✅ API imports successful")
except Exception as e:
    print(f"❌ API imports failed: {e}")
    sys.exit(1)

print("Step 5: Testing configuration...")
try:
    config = default_codegen_config
    print(f"✅ Configuration loaded:")
    print(f"   - Org ID: {config.org_id[:8] + '...' if config.org_id else 'None'}")
    print(f"   - Token: {'***' + config.token[-4:] if config.token else 'None'}")
    print(f"   - Base URL: {config.base_url}")
except Exception as e:
    print(f"❌ Configuration failed: {e}")
    sys.exit(1)

print("Step 6: Testing Agent creation...")
try:
    agent = Agent(
        org_id=config.org_id,
        token=config.token,
        base_url=config.base_url
    )
    print("✅ Agent creation successful")
    print(f"   - Agent type: {type(agent)}")
except Exception as e:
    print(f"❌ Agent creation failed: {e}")
    sys.exit(1)

print("\n🎉 All imports and basic initialization successful!")
print("The hanging issue is likely in the process_message call or network communication.")

