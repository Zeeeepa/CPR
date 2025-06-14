#!/bin/bash

# Make the Python script executable
chmod +x ./create_thread.py

# Run the script with the provided message or a default one
if [ -z "$1" ]; then
  ./create_thread.py
else
  ./create_thread.py --message "$1"
fi

