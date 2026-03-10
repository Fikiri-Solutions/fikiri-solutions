#!/usr/bin/env python3
"""
Obtain a Gmail refresh token for .env and contract tests.

Run this when you need GMAIL_REFRESH_TOKEN or GOOGLE_REFRESH_TOKEN in .env
(e.g. for provider contract tests or headless use). Uses the same OAuth
client as the app (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET) and the same
redirect URI (localhost:5000), so no Google Cloud Console change if the
app already has http://localhost:5000/api/oauth/gmail/callback.

Usage:
  1. Ensure .env has GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.
  2. Stop the main Fikiri app if it uses port 5000.
  3. From repo root: python scripts/obtain_gmail_refresh_token.py
  4. Browser opens; sign in with Google and approve.
  5. Copy the printed line into .env as GMAIL_REFRESH_TOKEN=...
"""

import os
import secrets
import sys
import threading
import time
from urllib.parse import urlencode

# Repo root on path and load .env before any app imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(REPO_ROOT, ".env"), override=True)
except ImportError:
    pass

PORT = 5000
REDIRECT_URI = f"http://localhost:{PORT}/api/oauth/gmail/callback"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

_refresh_token_result = None


if __name__ == "__main__":
    client_id = os.getenv("GOOGLE_CLIENT_ID") or os.getenv("GMAIL_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or os.getenv("GMAIL_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET in .env")
        sys.exit(1)

    from flask import Flask, request, redirect
    import requests
    from werkzeug.serving import make_server

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.urandom(24)
    state = secrets.token_urlsafe(24)

    @app.route("/api/oauth/gmail/start")
    def start():
        params = {
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": " ".join(SCOPES),
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return redirect(f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}")

    @app.route("/api/oauth/gmail/callback")
    def callback():
        global _refresh_token_result
        if request.args.get("state") != state:
            return "<p>Invalid state. Run the script again.</p>", 400
        code = request.args.get("code")
        if not code:
            return "<p>Authorization failed: missing code</p>", 400
        resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": REDIRECT_URI,
            },
            timeout=15,
        )
        data = resp.json()
        if "error" in data:
            return f"<p>Token error: {data.get('error_description', data['error'])}</p>", 400
        _refresh_token_result = data.get("refresh_token")
        if not _refresh_token_result:
            return (
                "<p>No refresh_token. Revoke app access at myaccount.google.com and try again.</p>",
                400,
            )
        return "<p><b>Success.</b> Close this tab and check the terminal.</p>"

    def run_server():
        srv = make_server("127.0.0.1", PORT, app, threaded=True)
        srv.serve_forever()

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    print("Open this URL in your browser (or it may open automatically):")
    print(f"  http://localhost:{PORT}/api/oauth/gmail/start")
    print()
    print("After you approve, return here for the refresh token.")
    print("Ensure nothing else is using port 5000.")
    print()

    import webbrowser
    webbrowser.open(f"http://localhost:{PORT}/api/oauth/gmail/start")

    print("Waiting for you to complete sign-in in the browser …")
    for _ in range(120):
        time.sleep(1)
        if _refresh_token_result:
            break
    else:
        print("Timed out. Run the script again.")
        sys.exit(1)
    print()
    print("Add this line to your .env file:")
    print(f"GMAIL_REFRESH_TOKEN={_refresh_token_result}")
    print()
    sys.exit(0)
