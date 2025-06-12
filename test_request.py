import requests
import json
import sseclient
import time

def test_stream():
    url = "http://localhost:8890/api/v1/run-task"
    headers = {
        "Content-Type": "application/json",
    }
    data = {
        "prompt": "Hello!",
        "stream": True
    }
    
    try:
        print("Sending request...")
        response = requests.post(url, headers=headers, json=data, stream=True, timeout=5)
        print(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return
            
        client = sseclient.SSEClient(response)
        
        print("\nStreaming response:")
        start_time = time.time()
        for event in client.events():
            print(f"\nEvent data: {event.data}")
            if event.data == "[DONE]":
                print("\nStream completed")
                break
            try:
                data = json.loads(event.data)
                print(f"Status: {data.get('status')}, Task ID: {data.get('task_id')}")
                if "result" in data:
                    print(f"Result: {data.get('result')}")
                if "error" in data:
                    print(f"Error: {data.get('error')}")
            except json.JSONDecodeError as e:
                print(f"Could not parse event data: {e}")
                
            # Break if taking too long
            if time.time() - start_time > 30:
                print("\nTimeout after 30 seconds")
                break
                
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    test_stream()

