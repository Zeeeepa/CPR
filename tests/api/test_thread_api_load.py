#!/usr/bin/env python3
"""
Load Test Script for Thread Management API
This script performs a load test of the thread management API:
1. Create multiple threads concurrently
2. Send multiple messages to each thread concurrently
3. Monitor response times and success rates
"""

import requests
import json
import time
import argparse
import os
import sys
import threading
import concurrent.futures
import statistics
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

class ThreadAPILoadTester:
    def __init__(self, org_id, token, base_url='default', backend_url='http://localhost:8002'):
        self.org_id = org_id
        self.token = token
        self.base_url = base_url
        self.backend_url = backend_url
        
        # Headers for API requests
        self.headers = {
            'Content-Type': 'application/json',
            'X-Organization-ID': self.org_id,
            'X-Token': self.token,
            'X-Base-URL': self.base_url
        }
        
        # Stats tracking
        self.response_times = {
            'create_thread': [],
            'send_message': [],
            'get_message': [],
            'list_threads': [],
            'list_messages': []
        }
        
        self.success_counts = {
            'create_thread': 0,
            'send_message': 0,
            'get_message': 0,
            'list_threads': 0,
            'list_messages': 0
        }
        
        self.failure_counts = {
            'create_thread': 0,
            'send_message': 0,
            'get_message': 0,
            'list_threads': 0,
            'list_messages': 0
        }
        
        # Thread-safe collections for test data
        self.lock = threading.Lock()
        self.threads = []
        self.messages = []
        
        logger.info(f"Initialized ThreadAPILoadTester with org_id: {org_id}, backend_url: {backend_url}")
    
    def create_thread(self, thread_num):
        """Create a new thread and measure response time"""
        name = f"Load Test Thread {thread_num} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        start_time = time.time()
        success = False
        
        try:
            response = requests.post(
                f"{self.backend_url}/api/v1/threads",
                headers=self.headers,
                json={"name": name}
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                thread_data = response.json()
                
                with self.lock:
                    self.threads.append(thread_data)
                    self.response_times['create_thread'].append(elapsed)
                    self.success_counts['create_thread'] += 1
                
                logger.info(f"Created thread {thread_num} in {elapsed:.3f}s: {thread_data.get('thread_id')}")
                success = True
                return thread_data
            else:
                logger.error(f"Failed to create thread {thread_num}: {response.status_code} - {response.text}")
                
                with self.lock:
                    self.failure_counts['create_thread'] += 1
                
                return None
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Exception creating thread {thread_num}: {str(e)}")
            
            with self.lock:
                self.failure_counts['create_thread'] += 1
            
            return None
    
    def send_message(self, thread_id, message_num):
        """Send a message to a thread and measure response time"""
        content = f"Load test message {message_num} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.backend_url}/api/v1/threads/{thread_id}/messages",
                headers=self.headers,
                json={"content": content, "thread_id": thread_id}
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                message_data = response.json()
                
                with self.lock:
                    self.messages.append(message_data)
                    self.response_times['send_message'].append(elapsed)
                    self.success_counts['send_message'] += 1
                
                logger.info(f"Sent message {message_num} to thread {thread_id} in {elapsed:.3f}s: {message_data.get('message_id')}")
                return message_data
            else:
                logger.error(f"Failed to send message {message_num} to thread {thread_id}: {response.status_code} - {response.text}")
                
                with self.lock:
                    self.failure_counts['send_message'] += 1
                
                return None
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Exception sending message {message_num} to thread {thread_id}: {str(e)}")
            
            with self.lock:
                self.failure_counts['send_message'] += 1
            
            return None
    
    def get_message(self, thread_id, message_id, attempt=0):
        """Get a message and measure response time"""
        start_time = time.time()
        
        try:
            response = requests.get(
                f"{self.backend_url}/api/v1/threads/{thread_id}/messages/{message_id}",
                headers=self.headers
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                message_data = response.json()
                
                with self.lock:
                    self.response_times['get_message'].append(elapsed)
                    self.success_counts['get_message'] += 1
                
                if attempt % 5 == 0:  # Log only every 5th attempt to reduce noise
                    logger.info(f"Got message {message_id} from thread {thread_id} in {elapsed:.3f}s: status={message_data.get('status')}")
                
                return message_data
            else:
                logger.error(f"Failed to get message {message_id} from thread {thread_id}: {response.status_code} - {response.text}")
                
                with self.lock:
                    self.failure_counts['get_message'] += 1
                
                return None
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Exception getting message {message_id} from thread {thread_id}: {str(e)}")
            
            with self.lock:
                self.failure_counts['get_message'] += 1
            
            return None
    
    def list_threads(self):
        """List all threads and measure response time"""
        start_time = time.time()
        
        try:
            response = requests.get(
                f"{self.backend_url}/api/v1/threads",
                headers=self.headers
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                threads_data = response.json()
                
                with self.lock:
                    self.response_times['list_threads'].append(elapsed)
                    self.success_counts['list_threads'] += 1
                
                logger.info(f"Listed {len(threads_data.get('threads', []))} threads in {elapsed:.3f}s")
                return threads_data.get('threads', [])
            else:
                logger.error(f"Failed to list threads: {response.status_code} - {response.text}")
                
                with self.lock:
                    self.failure_counts['list_threads'] += 1
                
                return []
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Exception listing threads: {str(e)}")
            
            with self.lock:
                self.failure_counts['list_threads'] += 1
            
            return []
    
    def list_messages(self, thread_id):
        """List all messages in a thread and measure response time"""
        start_time = time.time()
        
        try:
            response = requests.get(
                f"{self.backend_url}/api/v1/threads/{thread_id}/messages",
                headers=self.headers
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                messages_data = response.json()
                
                with self.lock:
                    self.response_times['list_messages'].append(elapsed)
                    self.success_counts['list_messages'] += 1
                
                logger.info(f"Listed {len(messages_data.get('messages', []))} messages in thread {thread_id} in {elapsed:.3f}s")
                return messages_data.get('messages', [])
            else:
                logger.error(f"Failed to list messages in thread {thread_id}: {response.status_code} - {response.text}")
                
                with self.lock:
                    self.failure_counts['list_messages'] += 1
                
                return []
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Exception listing messages in thread {thread_id}: {str(e)}")
            
            with self.lock:
                self.failure_counts['list_messages'] += 1
            
            return []
    
    def wait_for_message_completion(self, thread_id, message_id, max_attempts=30, delay=2):
        """Poll for message completion"""
        for attempt in range(max_attempts):
            message_data = self.get_message(thread_id, message_id, attempt)
            if not message_data:
                time.sleep(delay)
                continue
            
            status = message_data.get('status')
            
            # Check if message is completed or failed
            if status in ['completed', 'failed', 'timeout']:
                return message_data
            
            # Wait before checking again
            time.sleep(delay)
        
        logger.warning(f"Message {message_id} did not complete within the expected time")
        return None
    
    def create_threads_concurrent(self, num_threads, max_workers=5):
        """Create multiple threads concurrently"""
        logger.info(f"Creating {num_threads} threads concurrently with {max_workers} workers")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.create_thread, i) for i in range(num_threads)]
            
            # Wait for all threads to be created
            concurrent.futures.wait(futures)
            
            # Get results
            created_threads = [future.result() for future in futures if future.result() is not None]
            
            logger.info(f"Successfully created {len(created_threads)} threads out of {num_threads}")
            return created_threads
    
    def send_messages_concurrent(self, thread_ids, messages_per_thread, max_workers=5):
        """Send multiple messages to multiple threads concurrently"""
        logger.info(f"Sending {messages_per_thread} messages to {len(thread_ids)} threads concurrently with {max_workers} workers")
        
        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for thread_id in thread_ids:
                for i in range(messages_per_thread):
                    futures.append(executor.submit(self.send_message, thread_id, i))
            
            # Wait for all messages to be sent
            concurrent.futures.wait(futures)
            
            # Get results
            sent_messages = [future.result() for future in futures if future.result() is not None]
            
            logger.info(f"Successfully sent {len(sent_messages)} messages out of {len(thread_ids) * messages_per_thread}")
            return sent_messages
    
    def wait_for_messages_concurrent(self, messages, max_workers=5):
        """Wait for multiple messages to complete concurrently"""
        logger.info(f"Waiting for {len(messages)} messages to complete concurrently with {max_workers} workers")
        
        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for message in messages:
                thread_id = message.get('thread_id')
                message_id = message.get('message_id')
                futures.append(executor.submit(self.wait_for_message_completion, thread_id, message_id))
            
            # Wait for all messages to complete
            concurrent.futures.wait(futures)
            
            # Get results
            completed_messages = [future.result() for future in futures if future.result() is not None]
            
            logger.info(f"Successfully completed {len(completed_messages)} messages out of {len(messages)}")
            return completed_messages
    
    def print_stats(self):
        """Print statistics from the load test"""
        logger.info("\n=== Load Test Statistics ===")
        
        for operation in self.response_times:
            times = self.response_times[operation]
            successes = self.success_counts[operation]
            failures = self.failure_counts[operation]
            total = successes + failures
            
            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                median_time = statistics.median(times)
                p95_time = sorted(times)[int(len(times) * 0.95)] if len(times) >= 20 else max_time
                
                logger.info(f"{operation}:")
                logger.info(f"  Requests: {total} (Success: {successes}, Failure: {failures})")
                logger.info(f"  Success Rate: {(successes / total * 100) if total > 0 else 0:.2f}%")
                logger.info(f"  Response Times (seconds):")
                logger.info(f"    Avg: {avg_time:.3f}")
                logger.info(f"    Min: {min_time:.3f}")
                logger.info(f"    Max: {max_time:.3f}")
                logger.info(f"    Median: {median_time:.3f}")
                logger.info(f"    P95: {p95_time:.3f}")
            else:
                logger.info(f"{operation}: No data")
    
    def run_load_test(self, num_threads=5, messages_per_thread=3, max_workers=5):
        """Run a load test of the Thread API"""
        start_time = time.time()
        logger.info(f"=== Starting Load Test with {num_threads} threads, {messages_per_thread} messages per thread ===")
        
        # Step 1: Create threads concurrently
        logger.info("\n=== Step 1: Creating Threads Concurrently ===")
        created_threads = self.create_threads_concurrent(num_threads, max_workers)
        thread_ids = [thread.get('thread_id') for thread in created_threads]
        
        if not thread_ids:
            logger.error("Failed to create any threads, aborting test")
            return False
        
        # Step 2: List threads to verify creation
        logger.info("\n=== Step 2: Listing All Threads ===")
        self.list_threads()
        
        # Step 3: Send messages to threads concurrently
        logger.info("\n=== Step 3: Sending Messages Concurrently ===")
        sent_messages = self.send_messages_concurrent(thread_ids, messages_per_thread, max_workers)
        
        if not sent_messages:
            logger.error("Failed to send any messages, aborting test")
            return False
        
        # Step 4: Wait for message responses concurrently
        logger.info("\n=== Step 4: Waiting for Message Responses Concurrently ===")
        completed_messages = self.wait_for_messages_concurrent(sent_messages, max_workers)
        
        # Step 5: List messages in threads
        logger.info("\n=== Step 5: Listing Messages in Threads ===")
        for thread_id in thread_ids[:min(3, len(thread_ids))]:  # List messages for first 3 threads only
            self.list_messages(thread_id)
        
        # Print statistics
        elapsed = time.time() - start_time
        logger.info(f"\n=== Load Test Completed in {elapsed:.2f} seconds ===")
        logger.info(f"Created {len(created_threads)} threads out of {num_threads}")
        logger.info(f"Sent {len(sent_messages)} messages out of {num_threads * messages_per_thread}")
        logger.info(f"Completed {len(completed_messages)} messages out of {len(sent_messages)}")
        
        self.print_stats()
        
        return True

def main():
    parser = argparse.ArgumentParser(description='Load Test for Thread Management API')
    parser.add_argument('--org_id', type=str, default=os.getenv('CODEGEN_ORG_ID'),
                        help='Organization ID')
    parser.add_argument('--token', type=str, default=os.getenv('CODEGEN_TOKEN'),
                        help='API token')
    parser.add_argument('--base_url', type=str, default='default',
                        help='Base URL')
    parser.add_argument('--backend_url', type=str, default='http://localhost:8002',
                        help='Backend URL')
    parser.add_argument('--num_threads', type=int, default=5,
                        help='Number of threads to create')
    parser.add_argument('--messages_per_thread', type=int, default=3,
                        help='Number of messages to send per thread')
    parser.add_argument('--max_workers', type=int, default=5,
                        help='Maximum number of concurrent workers')
    
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
    logger.info(f"Number of threads: {args.num_threads}")
    logger.info(f"Messages per thread: {args.messages_per_thread}")
    logger.info(f"Max workers: {args.max_workers}")
    
    # Create tester and run load test
    tester = ThreadAPILoadTester(
        org_id=args.org_id,
        token=args.token,
        base_url=args.base_url,
        backend_url=args.backend_url
    )
    
    success = tester.run_load_test(
        num_threads=args.num_threads,
        messages_per_thread=args.messages_per_thread,
        max_workers=args.max_workers
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

