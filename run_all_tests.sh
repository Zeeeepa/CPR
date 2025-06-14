#!/bin/bash
# Script to run all thread API tests

# Load environment variables from .env file if it exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Check if required variables are set
if [ -z "$CODEGEN_ORG_ID" ] || [ -z "$CODEGEN_TOKEN" ]; then
  echo "Error: CODEGEN_ORG_ID and CODEGEN_TOKEN environment variables are required."
  echo "Please set them in .env file or export them before running this script."
  exit 1
fi

# Set default backend URL
BACKEND_URL=${BACKEND_URL:-"http://localhost:8002"}

# Print test configuration
echo "=== Thread API Test Configuration ==="
echo "Organization ID: $CODEGEN_ORG_ID"
echo "Token: ${CODEGEN_TOKEN:0:10}..."
echo "Backend URL: $BACKEND_URL"
echo

# Function to check if backend is running
check_backend() {
  echo "Checking if backend is running at $BACKEND_URL..."
  if curl -s "$BACKEND_URL/docs" > /dev/null; then
    echo "Backend is running."
    return 0
  else
    echo "Backend is not running at $BACKEND_URL."
    echo "Please start the backend server before running tests."
    return 1
  fi
}

# Check if backend is running
if ! check_backend; then
  echo "Would you like to start the backend server? (y/n)"
  read -r response
  if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "Starting backend server in a new terminal..."
    # Start backend server in a new terminal
    if command -v gnome-terminal &> /dev/null; then
      gnome-terminal -- bash -c "cd $(pwd) && python -m uvicorn backend.api:app --host 0.0.0.0 --port 8002 --reload"
    elif command -v xterm &> /dev/null; then
      xterm -e "cd $(pwd) && python -m uvicorn backend.api:app --host 0.0.0.0 --port 8002 --reload" &
    else
      echo "Could not find a suitable terminal emulator. Please start the backend server manually."
      exit 1
    fi
    
    # Wait for backend to start
    echo "Waiting for backend to start..."
    for i in {1..10}; do
      if check_backend; then
        break
      fi
      sleep 2
    done
    
    if ! check_backend; then
      echo "Backend did not start within the expected time. Please check for errors."
      exit 1
    fi
  else
    echo "Exiting. Please start the backend server before running tests."
    exit 1
  fi
fi

# Run basic test
echo
echo "=== Running Basic Thread API Test ==="
./test_thread_api.py --org_id "$CODEGEN_ORG_ID" --token "$CODEGEN_TOKEN" --backend_url "$BACKEND_URL"
BASIC_TEST_RESULT=$?

# Run full test
echo
echo "=== Running Full Thread API Test ==="
./test_thread_api_full.py --org_id "$CODEGEN_ORG_ID" --token "$CODEGEN_TOKEN" --backend_url "$BACKEND_URL"
FULL_TEST_RESULT=$?

# Run load test with smaller parameters
echo
echo "=== Running Load Thread API Test ==="
./test_thread_api_load.py --org_id "$CODEGEN_ORG_ID" --token "$CODEGEN_TOKEN" --backend_url "$BACKEND_URL" --num_threads 3 --messages_per_thread 2 --max_workers 3
LOAD_TEST_RESULT=$?

# Run curl test
echo
echo "=== Running Curl Thread API Test ==="
./curl_test_thread_api.sh
CURL_TEST_RESULT=$?

# Print summary
echo
echo "=== Test Summary ==="
echo "Basic Test: $([ $BASIC_TEST_RESULT -eq 0 ] && echo "PASSED" || echo "FAILED")"
echo "Full Test: $([ $FULL_TEST_RESULT -eq 0 ] && echo "PASSED" || echo "FAILED")"
echo "Load Test: $([ $LOAD_TEST_RESULT -eq 0 ] && echo "PASSED" || echo "FAILED")"
echo "Curl Test: $([ $CURL_TEST_RESULT -eq 0 ] && echo "PASSED" || echo "FAILED")"

# Check if all tests passed
if [ $BASIC_TEST_RESULT -eq 0 ] && [ $FULL_TEST_RESULT -eq 0 ] && [ $LOAD_TEST_RESULT -eq 0 ] && [ $CURL_TEST_RESULT -eq 0 ]; then
  echo
  echo "🎉 All tests passed! The Thread API is working correctly."
  exit 0
else
  echo
  echo "❌ Some tests failed. Please check the output for details."
  exit 1
fi

