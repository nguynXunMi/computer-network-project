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

from daemon.weaprous import WeApRous

PORT = 8000  # Default port

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

@app.route('/', methods=['GET'])
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
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(base_dir, "www", "index.html")

        try:
            with open(html_path, "r", encoding="utf-8") as f:
                html = f.read()
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

@app.route('/hello', methods=['PUT'])
def hello(headers, body):
    """
    Handle greeting via PUT request.

    This route prints a greeting message to the console using the provided headers
    and body.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body or message payload.
    """
    print ("[SampleApp] ['PUT'] Hello in {} to {}".format(headers, body))

if __name__ == "__main__":
    # Parse command-line arguments to configure server IP and port
    parser = argparse.ArgumentParser(prog='Backend', description='', epilog='Beckend daemon')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=PORT)
 
    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    # Prepare and launch the RESTful application
    app.prepare_address(ip, port)
    app.run()