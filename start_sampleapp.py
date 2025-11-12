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


import json
import socket
import argparse
import os
import time


from daemon.weaprous import WeApRous
from urllib import parse, request as url_request

PORT = 8000  # Default port

# In-memory storage for peers and messages
peers = []
messages = []

app = WeApRous()

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
    print("[DEBUG] /login called")
    try:
        data = json.loads(body)
        username = data.get("username")
        password = data.get("password")
    except Exception:
        return "HTTP/1.1 400 Bad Request\r\nContent-Type: text/plain\r\n\r\nInvalid request body format"

    # Check credentials
    if username == "admin" and password == "password":
        base_dir = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(base_dir, "www", "index.html")
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                html = f.read()
            # Inject the current peer's port into the HTML
            html = html.replace("{{PEER_PORT}}", str(app.port))
        except FileNotFoundError:
            html = "<h1>Index page not found</h1>"

        return (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html\r\n"
            "Set-Cookie: auth=true\r\n"
            f"Content-Length: {len(html)}\r\n"
            "Connection: close\r\n"
            "\r\n"
            f"{html}"
        )
    else:
        unauthorized_html = "<h1>401 Unauthorized</h1><p>Invalid credentials.</p>"
        return (
            "HTTP/1.1 401 Unauthorized\r\n"
            "Content-Type: text/html\r\n"
            f"Content-Length: {len(unauthorized_html)}\r\n"
            "\r\n"
            f"{unauthorized_html}"
        )

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
            # Inject the current peer's port into the HTML
            html = html.replace("{{PEER_PORT}}", str(app.port))
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
    """
    Add a new peer to the list.
    """
    try:
        # The body is url-encoded, e.g., "peer=127.0.0.1:8001"
        parsed_body = parse.parse_qs(body)
        peer_address = parsed_body.get('peer', [''])[0].strip()

        # Sanitize the peer address
        if peer_address.startswith("http://"):
            peer_address = peer_address[7:]
        if peer_address.startswith("https://"):
            peer_address = peer_address[8:]
        peer_address = peer_address.strip('/')

        if peer_address and peer_address not in peers:
            peers.append(peer_address)
            print(f"[ChatApp] Added peer: {peer_address}")
    except Exception as e:
        print(f"[ChatApp] Error adding peer: {e}")
        # A simple error response
        return "HTTP/1.1 400 Bad Request\r\n\r\n"

    # Redirect back to the main page to refresh the UI
    return "HTTP/1.1 302 Found\r\nLocation: /\r\n\r\n"


@app.route('/send-message', methods=['POST'])
def send_message(headers, body):
    """
    Send a message to all known peers.
    """
    try:
        parsed_body = parse.parse_qs(body)
        message_text = parsed_body.get('message', [''])[0]

        if message_text:
            # Add message to local list
            messages.append(f"Me: {message_text}")
            print(f"[ChatApp] Sending message: {message_text}")

            # Broadcast to other peers
            for peer in peers:
                # Retry sending up to 3 times with short backoff
                peer_message = f"Peer ({app.port}): {message_text}"
                data = parse.urlencode({'message': peer_message}).encode()
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
        return "HTTP/1.1 400 Bad Request\r\n\r\n"

    # Redirect back to the main page
    return "HTTP/1.1 302 Found\r\nLocation: /\r\n\r\n"


@app.route('/receive-message', methods=['POST'])
def receive_message(headers, body):
    """
    Receive a message from another peer.
    """
    try:
        parsed_body = parse.parse_qs(body)
        message_text = parsed_body.get('message', [''])[0]
        if message_text:
            messages.append(message_text)
            print(f"[ChatApp] Received message: {message_text}")
    except Exception as e:
        print(f"[ChatApp] Error receiving message: {e}")
        return "HTTP/1.1 400 Bad Request\r\n\r\n"

    return "HTTP/1.1 200 OK\r\n\r\n"

@app.route('/get-messages', methods=['GET'])
def get_messages(headers, body):
    """
    Return the list of messages as JSON.
    """
    import json
    response_body = json.dumps(messages)
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
    Return the list of peers as JSON.
    """
    import json
    response_body = json.dumps(peers)
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
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=PORT)

    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    # Store the port and prepare the address
    app.port = port
    app.prepare_address(ip, port)
    app.run()