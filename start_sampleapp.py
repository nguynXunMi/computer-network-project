#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement". Please see the LICENSE
# file that should have been included as part of this package.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#


"""
start_sampleapp
~~~~~~~~~~~~~~~~~

This module provides a sample RESTful web application using the WeApRous framework.

It defines basic route handlers and launches a TCP-based backend server to serve
HTTP requests. The application includes a login endpoint and a greeting endpoint,
and can be configured via command-line arguments.
"""
# Quick overview
# - This file can act as both a tracker (port 8000) and a peer (any other port).
# - When a peer starts, it automatically registers to the tracker at <server-ip>:8000
#   and periodically syncs the peer list (every SYNC_INTERVAL seconds).
# - The simple UI is served from www/index.html. It polls the backend to show
#   messages, channel list, and peers.



import argparse
import os
import time
import threading


from daemon.weaprous import WeApRous
from urllib import parse, request as url_request

PORT = 8000  # Default port
SYNC_INTERVAL = 2  # seconds between background tracker syncs
AUTO_TRACKER = 1

# Note: auto-connect to tracker is enabled by default in the __main__ section.
# There is no need for an AUTO_TRACKER env flag anymore.
app = WeApRous()
# In-memory storage for peers and messages
peers = []

# Optional centralized tracker registry (used if this node is chosen as tracker)
tracker_registry = []  # list of 'ip:port' strings

# Channel-based storage
channels = {
    "general": {
        "members": [],
        "messages": []
    }
}
# Active channel for this peer's UI (simple global state per process)
active_channel = "general"
# Username/identity for this peer
current_user = "Anonymous"
# ---- Helpers ----
def normalize_peer(addr: str) -> str:
    try:
        if not addr:
            return ''
        a = addr.strip()
        if a.startswith('http://'):
            a = a[7:]
        if a.startswith('https://'):
            a = a[8:]
        a = a.strip('/')
        host_port = a.split('/')[0]
        host, sep, port = host_port.partition(':')
        if host in ('localhost', '127.0.0.1', '::1'):
            host = '127.0.0.1'
        if not sep:  # no port provided
            return host
        return f"{host}:{port}"
    except Exception:
        return addr or ''

def _auto_register_and_sync(tracker, me):
    """Periodically register this peer to tracker and sync peers (best-effort, background)."""
    while True:
        try:
            me_norm = normalize_peer(me)
            tracker_norm = normalize_peer(tracker)
            # 1. Register self (skip if this node IS the tracker)
            if me_norm != tracker_norm:
                data = parse.urlencode({'peer': me_norm}).encode()
                req = url_request.Request(f"http://{tracker_norm}/register", data=data, method='POST')
                with url_request.urlopen(req, timeout=5):
                    pass
            # 2. Sync peer list from tracker
            with url_request.urlopen(f"http://{tracker_norm}/tracker-peers", timeout=5) as r:
                import json as _json
                remote = _json.loads(r.read().decode('utf-8') or '[]')

            added = 0
            # Normalize and add new peers
            current_peers_set = set(normalize_peer(p) for p in peers)
            for p_addr in remote:
                normalized_p = normalize_peer(p_addr)
                if normalized_p and normalized_p != me_norm and normalized_p not in current_peers_set:
                    peers.append(normalized_p)
                    added += 1
        except Exception as e:
            print(f"[AutoSync] Failed to connect or sync with tracker {tracker}: {e}")

        # Wait for the next cycle
        time.sleep(SYNC_INTERVAL)

@app.route('/login', methods=['POST'])
def login(headers="guest", body="anonymous"):
    """
    Handle user login via POST request.

    This route simulates a login process and prints the provided headers and body
    to the console.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body or login payload.
    """
    print ("[SampleApp] Logging in {} to {}".format(headers, body))

@app.route('/index.html', methods=['GET'])
def root(headers=None, body=None):
    print("[DEBUG] / called")

    cookie_header = ""
    if headers and isinstance(headers, dict):
        for k, v in headers.items():
            if k.lower() == "cookie":
                cookie_header = v
                break

    authorized = "auth=true" in cookie_header

    if authorized:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(base_dir, "www", "index.html")

        try:
            with open(html_path, "r", encoding="utf-8") as f:
                html = f.read()
            # Inject dynamic placeholders for the UI
            html = html.replace("{{PEER_PORT}}", str(app.port))
            peer_ip = getattr(app, 'server_ip', '127.0.0.1')
            peer_addr = f"{peer_ip}:{app.port}"
            tracker_addr = f"{peer_ip}:8000"
            html = html.replace("{{PEER_ADDR}}", peer_addr)
            html = html.replace("{{TRACKER_ADDR}}", tracker_addr)
        except FileNotFoundError:
            html = "<h1>Index page not found</h1>"

        return (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html\r\n"
            f"Content-Length: {len(html)}\r\n"
            "Connection: close\r\n"
            "\r\n"
            f"{html}"
        )

    # Missing / invalid cookie → 401 Unauthorized
    else:
        unauthorized_html = (
            "<h1>401 Unauthorized</h1>"
            "<p>You must log in first.</p>"
        )
        return (
            "HTTP/1.1 401 Unauthorized\r\n"
            "Content-Type: text/html\r\n"
            f"Content-Length: {len(unauthorized_html)}\r\n"
            "Connection: close\r\n"
            "\r\n"
            f"{unauthorized_html}"
        )

@app.route('/add-peer', methods=['POST'])
def add_peer(headers, body):
    """Add a new peer (one-way). No symmetric call, no sync here to avoid loops."""
    try:
        parsed = parse.parse_qs(body)
        raw = parsed.get('peer', [''])[0].strip()
        peer_address = normalize_peer(raw)
        me_host = normalize_peer(headers.get('host', '').strip() or f"127.0.0.1:{app.port}")

        if not peer_address or peer_address == me_host:
            return "HTTP/1.1 200 OK\r\n\r\n"

        if peer_address not in peers:
            peers.append(peer_address)
            print(f"[ChatApp] Added peer: {peer_address}")

        return "HTTP/1.1 200 OK\r\n\r\n"
    except Exception as e:
        print(f"[ChatApp] Error adding peer: {e}")
        return "HTTP/1.1 400 Bad Request\r\n\r\n"

@app.route('/create-channel', methods=['POST'])
def create_channel(headers, body):
    """Create channel locally, auto-join creator, optionally broadcast to peers.
    Use 'nobroadcast=1' in body to suppress rebroadcast (prevents loops)."""
    global active_channel
    try:
        parsed = parse.parse_qs(body)
        name = parsed.get('channel', [''])[0].strip()
        nobc = parsed.get('nobroadcast', ['0'])[0] in ('1', 'true', 'yes')
        if not name:
            return "HTTP/1.1 400 Bad Request\r\n\r\n"

        # 1) Ensure channel exists locally
        if name not in channels:
            channels[name] = {"members": [], "messages": []}

        # 2) For originator: auto-join + set active. For broadcast recipients: just create the channel (no join, no switch)
        peer_id = f"peer:{app.port}"
        if not nobc:
            if peer_id not in channels[name]["members"]:
                channels[name]["members"].append(peer_id)
            active_channel = name

        # 3) Broadcast to all peers (only from originator)
        if not nobc:
            try:
                data = parse.urlencode({'channel': name, 'nobroadcast': '1'}).encode()
                for p in sorted(set(peers)):
                    try:
                        req = url_request.Request(f"http://{p}/create-channel", data=data, method='POST')
                        with url_request.urlopen(req, timeout=4):
                            pass
                    except Exception as be:
                        print(f"[ChatApp] Broadcast create-channel to {p} failed: {be}")
            except Exception as e2:
                print(f"[ChatApp] Broadcast error: {e2}")

        return "HTTP/1.1 200 OK\r\n\r\n"
    except Exception as e:
        return "HTTP/1.1 500 Internal Server Error\r\n\r\n"

@app.route('/join-channel', methods=['POST'])
def join_channel(headers, body):
    """Join a channel and set it active"""
    global active_channel
    try:
        parsed = parse.parse_qs(body)
        name = parsed.get('channel', [''])[0].strip()
        if not name:
            return "HTTP/1.1 400 Bad Request\r\n\r\n"
        if name not in channels:
            channels[name] = {"members": [], "messages": []}
        peer_id = f"peer:{app.port}"
        if peer_id not in channels[name]["members"]:
            channels[name]["members"].append(peer_id)
        active_channel = name
        return "HTTP/1.1 200 OK\r\n\r\n"
    except Exception as e:
        print(f"[ChatApp] Error joining channel: {e}")
        return "HTTP/1.1 500 Internal Server Error\r\n\r\n"

@app.route('/set-active-channel', methods=['POST'])
def set_active_channel(headers, body):
    """Set the active channel without changing membership"""
    global active_channel
    try:
        parsed = parse.parse_qs(body)
        name = parsed.get('channel', [''])[0].strip()
        if not name:
            return "HTTP/1.1 400 Bad Request\r\n\r\n"
        if name not in channels:
            channels[name] = {"members": [], "messages": []}
        active_channel = name
        return "HTTP/1.1 200 OK\r\n\r\n"
    except Exception as e:
        print(f"[ChatApp] Error setting active channel: {e}")
        return "HTTP/1.1 500 Internal Server Error\r\n\r\n"

@app.route('/list-channels', methods=['GET'])
def list_channels(headers, body):
    """Return channel list with membership and active flags"""
    import json
    peer_id = f"peer:{app.port}"
    data = []
    for name, entry in channels.items():
        data.append({
            "name": name,
            "joined": peer_id in entry.get("members", []),
            "active": name == active_channel
        })
    response_body = json.dumps(data)
    return (
        f"HTTP/1.1 200 OK\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(response_body)}\r\n"
        f"\r\n"
        f"{response_body}"
    )

@app.route('/set-username', methods=['POST'])
def set_username(headers, body):
    """Set display username for this peer."""
    global current_user
    try:
        parsed = parse.parse_qs(body)
        name = parsed.get('username', [''])[0].strip()
        if not name:
            return "HTTP/1.1 400 Bad Request\r\n\r\n"
        current_user = name
        return "HTTP/1.1 200 OK\r\n\r\n"
    except Exception as e:
        print(f"[ChatApp] Error setting username: {e}")
        return "HTTP/1.1 500 Internal Server Error\r\n\r\n"

@app.route('/whoami', methods=['GET'])
def whoami(headers, body):
    """Return current username of this peer."""
    import json
    response_body = json.dumps({"user": current_user})
    return (
        f"HTTP/1.1 200 OK\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(response_body)}\r\n\r\n{response_body}"
    )

# ================= Tracker (Centralized) APIs =================
@app.route('/register', methods=['POST'])
def tracker_register(headers, body):
    """Tracker endpoint: register a peer 'ip:port'"""
    try:
        parsed = parse.parse_qs(body)
        peer = parsed.get('peer', [''])[0].strip()
        if not peer:
            return "HTTP/1.1 400 Bad Request\r\n\r\n"
        if peer not in tracker_registry:
            tracker_registry.append(peer)
        return "HTTP/1.1 200 OK\r\n\r\n"
    except Exception as e:
        print(f"[Tracker] Error register: {e}")
        return "HTTP/1.1 500 Internal Server Error\r\n\r\n"


@app.route('/tracker-peers', methods=['GET'])
def tracker_peers(headers, body):
    """Tracker endpoint: return registered peers"""
    import json
    response_body = json.dumps(tracker_registry)
    return (
        f"HTTP/1.1 200 OK\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(response_body)}\r\n\r\n{response_body}"
    )


@app.route('/sync-from-tracker', methods=['POST'])
def sync_from_tracker(headers, body):
    """Client endpoint: fetch peers from a tracker and merge into local peers list."""
    try:
        parsed = parse.parse_qs(body)
        tracker = parsed.get('tracker', [''])[0].strip()  # ip:port
        if not tracker:
            return "HTTP/1.1 400 Bad Request\r\n\r\n"
        # Fetch peers
        url = f"http://{tracker}/tracker-peers"
        with url_request.urlopen(url, timeout=5) as r:
            import json
            remote_list = json.loads(r.read().decode('utf-8') or '[]')
        # Merge (normalized + unique)
        added = 0
        me_host = f"{app.server_ip}:{app.port}"
        for p in remote_list:
            n = normalize_peer(p)
            if n and n not in peers and n != me_host:
                peers.append(n)
                added += 1
        return "HTTP/1.1 200 OK\r\n\r\n"
    except Exception as e:
        print(f"[Client] Error syncing peers: {e}")
        return "HTTP/1.1 500 Internal Server Error\r\n\r\n"


@app.route('/register-to-tracker', methods=['POST'])
def register_to_tracker(headers, body):
    """Client endpoint: register this peer to a tracker."""
    try:
        parsed = parse.parse_qs(body)
        tracker = parsed.get('tracker', [''])[0].strip()
        me = parsed.get('me', [''])[0].strip()
        if not tracker:
            return "HTTP/1.1 400 Bad Request\r\n\r\n"
        if not me:
            # Fallback to injected server ip/port
            me = f"{app.server_ip}:{app.port}"
        if not me:
            return "HTTP/1.1 400 Bad Request\r\n\r\n"
        data = parse.urlencode({'peer': me}).encode()
        req = url_request.Request(f"http://{tracker}/register", data=data, method='POST')
        with url_request.urlopen(req, timeout=5):
            pass
        return "HTTP/1.1 200 OK\r\n\r\n"
    except Exception as e:
        print(f"[Client] Error registering to tracker: {e}")
        return "HTTP/1.1 500 Internal Server Error\r\n\r\n"

@app.route('/send-message', methods=['POST'])
def send_message(_, body):
    """
    Send a message to all known peers (channel-aware).
    """
    global active_channel
    try:
        parsed_body = parse.parse_qs(body)
        message_text = parsed_body.get('message', [''])[0]
        # Allow channel override in request, fallback to current active channel
        channel = parsed_body.get('channel', [active_channel])[0] or active_channel

        if not channel:
            channel = "general"
        if channel not in channels:
            # Auto-create channel if not exists
            channels[channel] = {"members": [], "messages": []}

        if message_text:
            # Add message to local channel
            local_msg = f"{current_user}: {message_text}"
            channels[channel]["messages"].append(local_msg)
            # Broadcast to other peers with channel context
            for peer in sorted(set(peers)):
                # Retry sending up to 3 times with short backoff
                data = parse.urlencode({
                    'message': message_text,
                    'channel': channel,
                    'user': current_user,
                }).encode()
                for attempt in range(3):
                    try:
                        req = url_request.Request(f"http://{peer}/receive-message", data=data, method='POST')
                        with url_request.urlopen(req, timeout=5) as response:
                            if response.status == 200:
                                break
                            else:
                                print(f"[ChatApp] Error sending to peer {peer}: Status {response.status} (attempt {attempt+1})")
                        time.sleep(0.4 * (attempt + 1))
                    except Exception as e:
                        if attempt == 2:
                            print(f"[ChatApp] Could not send message to peer {peer}: {e}")
                        else:
                            time.sleep(0.4 * (attempt + 1))

    except Exception as e:
        print(f"[ChatApp] Error sending message: {e}")

# ----- Direct peer communication (no tracker in path) -----
@app.route('/send-peer', methods=['POST'])
def send_peer(_, body):
    """Send a message directly to a single peer address (ip:port)."""
    try:
        parsed = parse.parse_qs(body)
        target = normalize_peer(parsed.get('peer', [''])[0])
        message_text = parsed.get('message', [''])[0]
        channel = parsed.get('channel', [active_channel])[0] or active_channel or 'general'
        if not target or not message_text:
            return "HTTP/1.1 400 Bad Request\r\n\r\n"
        # Ensure local channel exists and store local copy for the sender as well
        if channel not in channels:
            channels[channel] = {"members": [], "messages": []}
        channels[channel]["messages"].append(f"{current_user}: {message_text}")
        # Deliver directly to the peer
        data = parse.urlencode({'message': message_text, 'channel': channel, 'user': current_user}).encode()
        req = url_request.Request(f"http://{target}/receive-message", data=data, method='POST')
        with url_request.urlopen(req, timeout=5):
            pass
        return "HTTP/1.1 200 OK\r\n\r\n"
    except Exception as e:
        print(f"[ChatApp] Error send-peer: {e}")
        return "HTTP/1.1 500 Internal Server Error\r\n\r\n"

@app.route('/receive-message', methods=['POST'])
def receive_message(_, body):
    """
    Receive a message from another peer (channel-aware).
    """
    try:
        parsed_body = parse.parse_qs(body)
        message_text = parsed_body.get('message', [''])[0]
        channel = parsed_body.get('channel', ['general'])[0] or 'general'
        user = parsed_body.get('user', ['Peer'])[0] or 'Peer'

        if channel not in channels:
            channels[channel] = {"members": [], "messages": []}

        if message_text:
            incoming_msg = f"{user}: {message_text}"
            channels[channel]["messages"].append(incoming_msg)
    except Exception as e:
        print(f"[ChatApp] Error receiving message: {e}")
        return "HTTP/1.1 400 Bad Request\r\n\r\n"

    return "HTTP/1.1 200 OK\r\n\r\n"

@app.route('/get-messages', methods=['GET'])
def get_messages(headers, body):
    """
    Return the list of messages for the active channel as JSON.
    """
    import json
    # Use active channel for this peer's UI
    msgs = channels.get(active_channel, {"messages": []}).get("messages", [])
    response_body = json.dumps(msgs)
    return (
        f"HTTP/1.1 200 OK\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(response_body)}\r\n"
        f"\r\n"
        f"{response_body}"
    )


@app.route('/get-peers', methods=['GET'])
def get_peers(headers, body):
    """
    Return the list of peers as JSON (unique + sorted for stable UI).
    On tracker node (port 8000), show the tracker registry instead for clarity.
    """
    import json
    if int(app.port) == 8000:
        data = sorted(set(tracker_registry))
    else:
        data = sorted(set(peers))
    response_body = json.dumps(data)
    return (
        f"HTTP/1.1 200 OK\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(response_body)}\r\n"
        f"\r\n"
        f"{response_body}"
    )

if __name__ == "__main__":
    # Parse command-line arguments to configure server IP and port
    parser = argparse.ArgumentParser(prog='Backend', description='', epilog='Beckend daemon')
    parser.add_argument('--server-ip', default='127.0.0.1', help='The IP address this peer will run on.')
    parser.add_argument('--server-port', type=int, default=PORT)

    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    # Store server ip/port for later injection
    app.server_ip = ip
    app.port = port
    # Set a default username to identify this peer
    try:
        current_user = f"peer:{port}"
    except Exception:
        pass
    app.prepare_address(ip, port)
    # Auto-connect to tracker is enabled by default for non-tracker peers.
    if AUTO_TRACKER == 1:
        try:
            if int(port) != 8000:
                me = f"{ip}:{port}"  # Use the actual IP for registration
                tracker_addr = f"{ip}:8000"
                t = threading.Thread(target=_auto_register_and_sync, args=(tracker_addr, me), daemon=True)
                t.start()
        except Exception as _e:
            print(f"[AutoSync] could not start background sync: {_e}")

    app.run()