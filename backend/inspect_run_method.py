#!/usr/bin/env python3
"""
Inspect the Agent.run method to understand its signature
"""

import sys
import os
import inspect

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from codegen import Agent
from api import default_codegen_config

def inspect_run_method():
    """Inspect Agent.run method signature and documentation"""
    print("Inspecting Agent.run method...")
    
    config = default_codegen_config
    agent = Agent(
        org_id=config.org_id,
        token=config.token,
        base_url=config.base_url
    )
    
    run_method = agent.run
    
    print(f"Method: {run_method}")
    print(f"Method type: {type(run_method)}")
    
    # Get method signature
    try:
        signature = inspect.signature(run_method)
        print(f"\n📋 METHOD SIGNATURE:")
        print(f"  {run_method.__name__}{signature}")
        
        print(f"\n📋 PARAMETERS:")
        for param_name, param in signature.parameters.items():
            print(f"  - {param_name}: {param}")
            
    except Exception as e:
        print(f"Error getting signature: {e}")
    
    # Get method documentation
    try:
        doc = run_method.__doc__
        if doc:
            print(f"\n📋 DOCUMENTATION:")
            print(f"  {doc}")
        else:
            print(f"\n📋 DOCUMENTATION: None")
    except Exception as e:
        print(f"Error getting documentation: {e}")
    
    # Try to get the source code
    try:
        source = inspect.getsource(run_method)
        print(f"\n📋 SOURCE CODE:")
        print(source)
    except Exception as e:
        print(f"Error getting source: {e}")

if __name__ == "__main__":
    inspect_run_method()

