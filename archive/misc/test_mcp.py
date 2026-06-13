import requests
import sseclient
import threading
import json
import time

url = "http://10.0.10.4:8080/sse"

def sse_thread():
    response = requests.get(url, stream=True)
    client = sseclient.SSEClient(response)
    for event in client.events():
        print(f"Event: {event.event}")
        print(f"Data: {event.data}")
        if event.event == "endpoint":
            post_url = "http://10.0.10.4:8080" + event.data
            print(f"Got post URL: {post_url}")
            
            # Send initialize
            req = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0"}
                }
            }
            print("Sending initialize...")
            res = requests.post(post_url, json=req)
            print(f"Init response status: {res.status_code}")
            print(f"Init response body: {res.text}")

t = threading.Thread(target=sse_thread)
t.daemon = True
t.start()
time.sleep(5)
