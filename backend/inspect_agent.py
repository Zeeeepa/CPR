#!/usr/bin/env python3
"""
Inspect the Agent object to see what methods are available
"""

import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from codegen import Agent
from api import default_codegen_config

def inspect_agent():
    """Inspect Agent object methods and attributes"""
    print("Inspecting Codegen Agent object...")
    
    config = default_codegen_config
    agent = Agent(
        org_id=config.org_id,
        token=config.token,
        base_url=config.base_url
    )
    
    print(f"Agent type: {type(agent)}")
    print(f"Agent module: {agent.__class__.__module__}")
    
    print("\nAvailable methods and attributes:")
    methods = []
    attributes = []
    
    for attr_name in dir(agent):
        if not attr_name.startswith('_'):
            attr = getattr(agent, attr_name)
            if callable(attr):
                methods.append(attr_name)
            else:
                attributes.append(attr_name)
    
    print("\n📋 METHODS:")
    for method in sorted(methods):
        print(f"  - {method}")
    
    print("\n📋 ATTRIBUTES:")
    for attr in sorted(attributes):
        try:
            value = getattr(agent, attr)
            print(f"  - {attr}: {type(value)} = {value}")
        except Exception as e:
            print(f"  - {attr}: Error accessing - {e}")
    
    # Check for common method names
    print("\n🔍 CHECKING COMMON METHOD NAMES:")
    common_methods = [
        'process_message', 'send_message', 'chat', 'run', 'execute',
        'create_task', 'start_task', 'process', 'handle_message'
    ]
    
    for method_name in common_methods:
        if hasattr(agent, method_name):
            method = getattr(agent, method_name)
            if callable(method):
                print(f"  ✅ {method_name} - {method}")
            else:
                print(f"  ❓ {method_name} - Not callable: {method}")
        else:
            print(f"  ❌ {method_name} - Not found")

if __name__ == "__main__":
    inspect_agent()

