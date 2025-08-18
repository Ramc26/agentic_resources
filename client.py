import httpx
import json
import threading
import time
from urllib.parse import urljoin, urlparse, parse_qs

SERVER_BASE_URL = "http://127.0.0.1:8000"
SERVER_SSE_URL = urljoin(SERVER_BASE_URL, "/mcp/sse")

SESSION_STATE = {"id": None, "post_url": None}
SESSION_READY = threading.Event()

def listen_for_events(response):
    """
    Listens for and manually parses SSE messages from the httpx stream.
    """
    print("Listener thread started. Waiting for session ID...")
    try:
        current_event = {}
        for line in response.iter_lines():
            if not line:
                # An empty line signifies the end of an event
                if 'event' in current_event and 'data' in current_event:
                    if current_event['event'] in ('mcp-session-id', 'session-id', 'mcp_session_id'):
                        session_id = current_event['data']
                        print(f"Session ID received: {session_id}")
                        SESSION_STATE["id"] = session_id
                        # Do not set ready yet; prefer endpoint which includes post URL
                    elif current_event['event'] == 'endpoint':
                        relative_uri = current_event['data']  # e.g., /mcp/message?session_id=...
                        absolute_url = urljoin(SERVER_BASE_URL, relative_uri)
                        print(f"Endpoint received: {absolute_url}")
                        # Extract session_id from query string
                        parsed = urlparse(absolute_url)
                        q = parse_qs(parsed.query)
                        session_id_list = q.get('session_id', [])
                        if session_id_list:
                            SESSION_STATE["id"] = session_id_list[0]
                            print(f"Session ID parsed from endpoint: {SESSION_STATE['id']}")
                        SESSION_STATE["post_url"] = absolute_url
                        SESSION_READY.set()
                    elif current_event['event'] == 'message':
                        print("\n--- Response Received ---")
                        parsed_data = json.loads(current_event['data'])
                        print(json.dumps(parsed_data, indent=2))
                        print("-------------------------")
                current_event = {}
                continue

            if line.startswith('event:'):
                current_event['event'] = line[len('event: '):].strip()
            elif line.startswith('data:'):
                current_event['data'] = line[len('data: '):].strip()
    except Exception as e:
        print(f"\nListener thread error: {e}")

def send_mcp_request(client, method: str, params: dict = {}, session_id: str = None):
    """Sends a JSON-RPC request using the httpx client."""
    payload = {
        "jsonrpc": "2.0",
        "id": int(time.time()),
        "method": method,
        "params": params,
    }
    try:
        post_url = SESSION_STATE.get("post_url")
        if not post_url:
            print("No POST URL available yet.")
            return
        resp = client.post(post_url, json=payload, timeout=5, follow_redirects=True)
        print(f"POST {post_url} -> {resp.status_code}")
    except httpx.RequestError as e:
        print(f"Could not send request. Is the server running? Error: {e}")
        exit()

def send_mcp_notification(client, method: str, params: dict | None = None):
    payload = {
        "jsonrpc": "2.0",
        "method": method,
    }
    if params is not None:
        payload["params"] = params
    try:
        post_url = SESSION_STATE.get("post_url")
        if not post_url:
            print("No POST URL available yet.")
            return
        resp = client.post(post_url, json=payload, timeout=5, follow_redirects=True)
        print(f"POST(notify) {post_url} -> {resp.status_code}")
    except httpx.RequestError as e:
        print(f"Could not send notification. Is the server running? Error: {e}")
        exit()

def main():
    with httpx.Client() as client:
        try:
            headers = {"Accept": "text/event-stream", "Cache-Control": "no-cache", "Connection": "keep-alive"}
            with client.stream("GET", SERVER_SSE_URL, headers=headers, timeout=20) as response:
                print(f"SSE GET {SERVER_SSE_URL} -> {response.status_code}")
                for k, v in response.headers.items():
                    if k.lower() in ("content-type", "cache-control"):
                        print(f"Header {k}: {v}")
                listener = threading.Thread(target=listen_for_events, args=(response,), daemon=True)
                listener.start()

                print("Waiting for server to provide a session ID...")
                ready = SESSION_READY.wait(timeout=5)

                if not ready or not SESSION_STATE["id"]:
                    print("\nError: Did not receive a session ID. Exiting.")
                    return

                session_id = SESSION_STATE["id"]

                print("\n>>> Initializing MCP session...")
                send_mcp_request(
                    client,
                    "initialize",
                    {
                        "protocolVersion": 1,
                        "clientInfo": {"name": "agentic-resources-client", "version": "0.1.0"},
                        "capabilities": {},
                    },
                )
                time.sleep(0.5)

                print("\n>>> Sending notifications/initialized...")
                send_mcp_notification(client, "notifications/initialized")
                time.sleep(0.5)

                print("\n>>> Sending request to list files...")
                send_mcp_request(client, "resources/read", {"uri": "resource://files/list"}, session_id)
                time.sleep(1)

                print("\n>>> Sending request to greeting resource...")
                send_mcp_request(client, "resources/read", {"uri": "resource://greeting"}, session_id)
                time.sleep(1)

                print("\n>>> Sending request to read 'project_notes.txt'...")
                send_mcp_request(client, "resources/read", {"uri": "file:///project_notes.txt"}, session_id)
                time.sleep(1)

                print("\n>>> Sending request to fetch image bytes 'img.jpg' (if present)...")
                send_mcp_request(client, "resources/read", {"uri": "images://img.jpg"}, session_id)

                print("\nClient has finished sending requests. Waiting for responses...")
                time.sleep(3)

        except httpx.ConnectError as e:
            print(f"Connection failed. Is the server running at {SERVER_SSE_URL}? Error: {e}")

if __name__ == "__main__":
    main()