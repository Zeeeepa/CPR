# Backend package initialization
# This file allows the backend directory to be treated as a Python package
# Add the current directory to the Python path to allow relative imports
import sys
import os

# Add the parent directory to sys.path to allow importing backend as a module
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

