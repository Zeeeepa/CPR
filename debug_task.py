#!/usr/bin/env python3

import os
import time
from codegen import Agent

# Set up the agent
agent = Agent(
    token=os.getenv("CODEGEN_TOKEN", "sk-ce027fa7-3c8d-4beb-8c86-ed8ae982ac99"),
    org_id=os.getenv("CODEGEN_ORG_ID", "323")
)

print("Creating task...")
task = agent.run(prompt="hello world")
print(f"Task created: {task.id}")
print(f"Initial status: {task.status}")
print(f"Web URL: {getattr(task, 'web_url', 'None')}")

# Monitor the task for a few iterations
for i in range(10):
    print(f"\n--- Iteration {i+1} ---")
    task.refresh()
    print(f"Status: {task.status}")
    print(f"Has result: {hasattr(task, 'result') and task.result is not None}")
    print(f"Has output: {hasattr(task, 'output') and task.output is not None}")
    print(f"Has web_url: {hasattr(task, 'web_url') and task.web_url is not None}")
    
    if hasattr(task, 'web_url') and task.web_url:
        print(f"Web URL: {task.web_url}")
    
    # Print all available attributes
    print("All task attributes:")
    for attr in dir(task):
        if not attr.startswith('_'):
            try:
                value = getattr(task, attr)
                if not callable(value):
                    print(f"  {attr}: {value}")
            except:
                pass
    
    time.sleep(5)
