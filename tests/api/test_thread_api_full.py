#!/usr/bin/env python3
"""
Comprehensive Test Script for Thread Management API
This script performs a full test of the thread management API functionality:
1. Create multiple threads
2. List all threads
3. Send messages to threads
4. Retrieve message responses
5. Test error handling
"""

import requests
import json
import time
import argparse
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ThreadAPITester:
    def __init__(self, org_id, token, base_url='default', backend_url='http://localhost:8002'):
        self.org_id = org_id
        self.token = token
        self.base_url = base_url
        self.backend_url = backend_url
        self.threads = []
        self.messages = []
        
        # Headers for API requests
        self.headers = {
            'Content-Type': 'application/json',
            'X-Organization-ID': self.org_id,
            'X-Token': self.token,
            'X-Base-URL': self.base_url
        }
        
        logger.info(f"Initialized ThreadAPITester with org_id: {org_id}, backend_url: {backend_url}")
        
    def create_thread(self, name=None):
        """Create a new thread with optional name"""
        if name is None:
            name = f"Test Thread {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
        logger.info(f"Creating thread: {name}")
        
        try:
            response = requests.post(
                f"{self.backend_url}/api/v1/threads",
                headers=self.headers,
                json={"name": name}
            )
            
            if response.status_code != 200:
                logger.error(f"Error creating thread: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
            
            thread_data = response.json()
            thread_id = thread_data.get('thread_id')
            logger.info(f"Thread created with ID: {thread_id}")
            logger.info(f"Thread name: {thread_data.get('name')}")
            
            self.threads.append(thread_data)
            return thread_data
            
        except Exception as e:
            logger.error(f"Exception creating thread: {str(e)}")
            return None
    
    def list_threads(self):
        """List all threads"""
        logger.info("Listing all threads")
        
        try:
            response = requests.get(
                f"{self.backend_url}/api/v1/threads",
                headers=self.headers
            )
            
            if response.status_code != 200:
                logger.error(f"Error listing threads: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return []
            
            threads_data = response.json()
            thread_count = len(threads_data.get('threads', []))
            logger.info(f"Found {thread_count} threads")
            
            return threads_data.get('threads', [])
            
        except Exception as e:
            logger.error(f"Exception listing threads: {str(e)}")
            return []
    
    def get_thread(self, thread_id):
        """Get a specific thread"""
        logger.info(f"Getting thread: {thread_id}")
        
        try:
            response = requests.get(
                f"{self.backend_url}/api/v1/threads/{thread_id}",
                headers=self.headers
            )
            
            if response.status_code != 200:
                logger.error(f"Error getting thread: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
            
            thread_data = response.json()
            logger.info(f"Retrieved thread: {thread_data.get('name')}")
            
            return thread_data
            
        except Exception as e:
            logger.error(f"Exception getting thread: {str(e)}")
            return None
    
    def send_message(self, thread_id, content):
        """Send a message to a thread"""
        logger.info(f"Sending message to thread {thread_id}: {content}")
        
        try:
            response = requests.post(
                f"{self.backend_url}/api/v1/threads/{thread_id}/messages",
                headers=self.headers,
                json={"content": content, "thread_id": thread_id}
            )
            
            if response.status_code != 200:
                logger.error(f"Error sending message: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
            
            message_data = response.json()
            message_id = message_data.get('message_id')
            logger.info(f"Message sent with ID: {message_id}")
            
            self.messages.append(message_data)
            return message_data
            
        except Exception as e:
            logger.error(f"Exception sending message: {str(e)}")
            return None
    
    def get_message(self, thread_id, message_id):
        """Get a specific message"""
        logger.info(f"Getting message {message_id} from thread {thread_id}")
        
        try:
            response = requests.get(
                f"{self.backend_url}/api/v1/threads/{thread_id}/messages/{message_id}",
                headers=self.headers
            )
            
            if response.status_code != 200:
                logger.error(f"Error getting message: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
            
            message_data = response.json()
            logger.info(f"Message status: {message_data.get('status')}")
            
            return message_data
            
        except Exception as e:
            logger.error(f"Exception getting message: {str(e)}")
            return None
    
    def list_messages(self, thread_id):
        """List all messages in a thread"""
        logger.info(f"Listing messages for thread {thread_id}")
        
        try:
            response = requests.get(
                f"{self.backend_url}/api/v1/threads/{thread_id}/messages",
                headers=self.headers
            )
            
            if response.status_code != 200:
                logger.error(f"Error listing messages: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return []
            
            messages_data = response.json()
            message_count = len(messages_data.get('messages', []))
            logger.info(f"Found {message_count} messages in thread")
            
            return messages_data.get('messages', [])
            
        except Exception as e:
            logger.error(f"Exception listing messages: {str(e)}")
            return []
    
    def wait_for_message_completion(self, thread_id, message_id, max_attempts=30, delay=2):
        """Poll for message completion"""
        logger.info(f"Waiting for message {message_id} to complete")
        
        for attempt in range(max_attempts):
            logger.info(f"Checking message status (attempt {attempt+1}/{max_attempts})...")
            
            message_data = self.get_message(thread_id, message_id)
            if not message_data:
                time.sleep(delay)
                continue
            
            status = message_data.get('status')
            
            # Check if message is completed
            if status == 'completed':
                logger.info(f"Message completed: {message_data.get('content')}")
                return message_data
            
            # Check if message failed
            if status in ['failed', 'timeout']:
                logger.error(f"Message failed: {message_data.get('content')}")
                return message_data
            
            # Wait before checking again
            time.sleep(delay)
        
        logger.warning("Message did not complete within the expected time")
        return None
    
    def test_error_handling(self):
        """Test error handling scenarios"""
        logger.info("Testing error handling scenarios")
        
        # Test invalid thread ID
        logger.info("Testing invalid thread ID")
        response = requests.get(
            f"{self.backend_url}/api/v1/threads/invalid-thread-id",
            headers=self.headers
        )
        logger.info(f"Invalid thread ID response: {response.status_code}")
        
        # Test missing auth headers
        logger.info("Testing missing auth headers")
        response = requests.get(
            f"{self.backend_url}/api/v1/threads",
            headers={'Content-Type': 'application/json'}
        )
        logger.info(f"Missing auth headers response: {response.status_code}")
        
        # Test invalid message ID
        if self.threads:
            thread_id = self.threads[0].get('thread_id')
            logger.info(f"Testing invalid message ID in thread {thread_id}")
            response = requests.get(
                f"{self.backend_url}/api/v1/threads/{thread_id}/messages/invalid-message-id",
                headers=self.headers
            )
            logger.info(f"Invalid message ID response: {response.status_code}")
    
    def run_full_test(self):
        """Run a full test of the Thread API"""
        logger.info("=== Starting Full Thread API Test ===")
        
        # Step 1: Create multiple threads
        logger.info("\n=== Step 1: Creating Multiple Threads ===")
        thread1 = self.create_thread("Test Thread 1")
        thread2 = self.create_thread("Test Thread 2")
        
        if not thread1 or not thread2:
            logger.error("Failed to create test threads, aborting test")
            return False
        
        # Step 2: List all threads
        logger.info("\n=== Step 2: Listing All Threads ===")
        threads = self.list_threads()
        
        # Step 3: Send messages to threads
        logger.info("\n=== Step 3: Sending Messages to Threads ===")
        message1 = self.send_message(
            thread1.get('thread_id'),
            f"Hello from thread 1! {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        message2 = self.send_message(
            thread2.get('thread_id'),
            f"Hello from thread 2! {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        if not message1 or not message2:
            logger.error("Failed to send test messages, aborting test")
            return False
        
        # Step 4: Wait for message responses
        logger.info("\n=== Step 4: Waiting for Message Responses ===")
        response1 = self.wait_for_message_completion(
            thread1.get('thread_id'),
            message1.get('message_id')
        )
        
        response2 = self.wait_for_message_completion(
            thread2.get('thread_id'),
            message2.get('message_id')
        )
        
        # Step 5: List messages in threads
        logger.info("\n=== Step 5: Listing Messages in Threads ===")
        messages1 = self.list_messages(thread1.get('thread_id'))
        messages2 = self.list_messages(thread2.get('thread_id'))
        
        # Step 6: Test error handling
        logger.info("\n=== Step 6: Testing Error Handling ===")
        self.test_error_handling()
        
        logger.info("\n=== Full Test Complete ===")
        logger.info(f"Created {len(self.threads)} threads")
        logger.info(f"Sent {len(self.messages)} messages")
        
        return True

def main():
    parser = argparse.ArgumentParser(description='Full Test for Thread Management API')
    parser.add_argument('--org_id', type=str, default=os.getenv('CODEGEN_ORG_ID'),
                        help='Organization ID')
    parser.add_argument('--token', type=str, default=os.getenv('CODEGEN_TOKEN'),
                        help='API token')
    parser.add_argument('--base_url', type=str, default='default',
                        help='Base URL')
    parser.add_argument('--backend_url', type=str, default='http://localhost:8002',
                        help='Backend URL')
    
    args = parser.parse_args()
    
    # Validate required parameters
    if not args.org_id or not args.token:
        logger.error("Error: Organization ID and token are required.")
        logger.error("Set them as environment variables or provide them as arguments.")
        return 1
    
    # Print configuration
    logger.info(f"Organization ID: {args.org_id}")
    logger.info(f"Token: {args.token[:10]}..." if args.token else "Token: None")
    logger.info(f"Base URL: {args.base_url}")
    logger.info(f"Backend URL: {args.backend_url}")
    
    # Create tester and run full test
    tester = ThreadAPITester(
        org_id=args.org_id,
        token=args.token,
        base_url=args.base_url,
        backend_url=args.backend_url
    )
    
    success = tester.run_full_test()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

