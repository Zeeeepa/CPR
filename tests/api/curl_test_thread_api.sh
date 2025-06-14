#!/bin/bash
# Script to test the Thread Management API using curl

# Load environment variables from .env file if it exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Set default values
ORG_ID=${CODEGEN_ORG_ID:-"your_org_id"}
TOKEN=${CODEGEN_TOKEN:-"your_token"}
BASE_URL=${CODEGEN_BASE_URL:-"default"}
BACKEND_URL=${BACKEND_URL:-"http://localhost:8002"}

# Check if required variables are set
if [ "$ORG_ID" = "your_org_id" ] || [ "$TOKEN" = "your_token" ]; then
  echo "Error: Organization ID and token are required."
  echo "Set them in .env file or export them as environment variables."
  exit 1
fi

# Common headers for all requests
HEADERS=(
  -H "Content-Type: application/json"
  -H "X-Organization-ID: $ORG_ID"
  -H "X-Token: $TOKEN"
  -H "X-Base-URL: $BASE_URL"
)

echo "=== Starting Thread API Test ==="
echo

# Step 1: Create a thread
echo "=== Creating Thread ==="
THREAD_RESPONSE=$(curl -s "${BACKEND_URL}/api/v1/threads/" \
  "${HEADERS[@]}" \
  -d "{\"name\": \"Curl Test Thread $(date +"%Y-%m-%d %H:%M:%S")\"}" \
  -X POST)

echo "Response: $THREAD_RESPONSE"
THREAD_ID=$(echo $THREAD_RESPONSE | jq -r '.thread_id')

if [ -z "$THREAD_ID" ] || [ "$THREAD_ID" = "null" ]; then
  echo "Error: Failed to create thread"
  exit 1
fi

echo "Thread created with ID: $THREAD_ID"
echo

# Step 2: Send a message to the thread
echo "=== Sending Message ==="
MESSAGE="Hello from curl test script! $(date +"%Y-%m-%d %H:%M:%S")"
MESSAGE_RESPONSE=$(curl -s "${BACKEND_URL}/api/v1/threads/${THREAD_ID}/messages" \
  "${HEADERS[@]}" \
  -d "{\"content\": \"$MESSAGE\", \"thread_id\": \"$THREAD_ID\"}" \
  -X POST)

echo "Response: $MESSAGE_RESPONSE"
MESSAGE_ID=$(echo $MESSAGE_RESPONSE | jq -r '.message_id')

if [ -z "$MESSAGE_ID" ] || [ "$MESSAGE_ID" = "null" ]; then
  echo "Error: Failed to send message"
  exit 1
fi

echo "Message sent with ID: $MESSAGE_ID"
echo

# Step 3: Poll for message response
echo "=== Polling for Response ==="
MAX_ATTEMPTS=30
for ((i=1; i<=MAX_ATTEMPTS; i++)); do
  echo "Checking message status (attempt $i/$MAX_ATTEMPTS)..."
  
  STATUS_RESPONSE=$(curl -s "${BACKEND_URL}/api/v1/threads/${THREAD_ID}/messages/${MESSAGE_ID}" \
    "${HEADERS[@]}")
  
  echo "Status response: $STATUS_RESPONSE"
  STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
  
  # Check if message is completed
  if [ "$STATUS" = "completed" ]; then
    echo
    echo "=== Message Completed ==="
    CONTENT=$(echo $STATUS_RESPONSE | jq -r '.content')
    COMPLETED_AT=$(echo $STATUS_RESPONSE | jq -r '.completed_at')
    echo "Response content: $CONTENT"
    echo "Completed at: $COMPLETED_AT"
    break
  fi
  
  # Check if message failed
  if [ "$STATUS" = "failed" ] || [ "$STATUS" = "timeout" ]; then
    echo
    echo "=== Message Failed ==="
    ERROR=$(echo $STATUS_RESPONSE | jq -r '.content')
    echo "Error: $ERROR"
    break
  fi
  
  # Wait before checking again
  sleep 2
done

if [ $i -gt $MAX_ATTEMPTS ]; then
  echo
  echo "=== Polling Timeout ==="
  echo "Message did not complete within the expected time."
fi

# Step 4: List all messages in the thread
echo
echo "=== Listing All Messages ==="
MESSAGES_RESPONSE=$(curl -s "${BACKEND_URL}/api/v1/threads/${THREAD_ID}/messages" \
  "${HEADERS[@]}")

echo "Messages response: $MESSAGES_RESPONSE"
MESSAGE_COUNT=$(echo $MESSAGES_RESPONSE | jq '.messages | length')
echo "Found $MESSAGE_COUNT messages in thread"

echo
echo "=== Test Complete ==="
echo "Thread ID: $THREAD_ID"
echo "Message ID: $MESSAGE_ID"
echo
echo "You can now check the UI to see if the thread and message are displayed correctly."
