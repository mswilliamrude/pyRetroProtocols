import requests
import sseclient
import threading
import json
import time

url = "http://10.0.10.4:8080/sse"
messages_url = None

def sse_thread():
    global messages_url
    response = requests.get(url, stream=True)
    client = sseclient.SSEClient(response)
    for event in client.events():
        print(f"Event: {event.event}")
        if event.event == "endpoint":
            messages_url = "http://10.0.10.4:8080" + event.data
            print(f"Got post URL: {messages_url}")
        elif event.event == "message":
            print(f"Data: {event.data}")

t = threading.Thread(target=sse_thread)
t.daemon = True
t.start()
time.sleep(2)

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
requests.post(messages_url, json=req)
time.sleep(1)

# Send tools/list
req = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
}
requests.post(messages_url, json=req)
time.sleep(2)
