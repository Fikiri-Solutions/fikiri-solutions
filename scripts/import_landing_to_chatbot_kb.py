#!/usr/bin/env python3
"""
Bulk-import landing content into the chatbot knowledge base.
Uses POST /api/chatbot/knowledge/import/bulk with X-API-Key.

Usage:
  python scripts/import_landing_to_chatbot_kb.py [path/to/documents.json]
  python scripts/import_landing_to_chatbot_kb.py

Default JSON path: scripts/chatbot_kb_landing_documents.json

Env:
  CHATBOT_KB_API_KEY or API_KEY  – API key for X-API-Key header (required).
  API_BASE_URL                    – Base URL of the backend (default http://localhost:5000).
"""

import json
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import requests
except ImportError:
    print("Install requests: pip install requests", file=sys.stderr)
    sys.exit(1)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    default_json = os.path.join(script_dir, "chatbot_kb_landing_documents.json")

    json_path = sys.argv[1] if len(sys.argv) > 1 else default_json
    if not os.path.isfile(json_path):
        print(f"File not found: {json_path}", file=sys.stderr)
        sys.exit(2)

    api_key = os.environ.get("CHATBOT_KB_API_KEY") or os.environ.get("API_KEY")
    if not api_key:
        try:
            sys.path.insert(0, project_root)
            os.environ.setdefault("FLASK_ENV", "development")
            from core.api_key_manager import api_key_manager
            from core.database_optimization import db_optimizer
            row = db_optimizer.execute_query("SELECT id FROM users LIMIT 1")
            if row:
                user_id = row[0]["id"] if hasattr(row[0], "keys") else row[0][0]
                result = api_key_manager.generate_api_key(
                    user_id=user_id,
                    name="KB import (script)",
                    description="One-time key for landing KB import",
                    tenant_id=str(user_id),
                    scopes=["chatbot:query"],
                )
                api_key = result["api_key"]
                print(f"Using one-time API key (user_id={user_id}): {api_key[:12]}...")
            else:
                print("No user in database. Create an account first or set CHATBOT_KB_API_KEY in .env", file=sys.stderr)
                sys.exit(3)
        except Exception as e:
            print(f"Set CHATBOT_KB_API_KEY or API_KEY in .env. (Auto-create failed: {e})", file=sys.stderr)
            sys.exit(3)

    base_url = (os.environ.get("API_BASE_URL") or "http://localhost:5000").rstrip("/")
    url = f"{base_url}/api/chatbot/knowledge/import/bulk"

    with open(json_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if "documents" not in payload:
        print("JSON must contain a 'documents' array.", file=sys.stderr)
        sys.exit(4)

    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }

    print(f"POST {url} ({len(payload['documents'])} documents)...")
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=60)
        r.raise_for_status()
        data = r.json()
        imported = data.get("imported", 0)
        total = data.get("total", 0)
        print(f"Imported {imported}/{total} documents.")
        results = data.get("results", [])
        for res in results:
            if res.get("success"):
                print(f"  [{res.get('index')}] doc_id={res.get('document_id')}")
            else:
                print(f"  [{res.get('index')}] FAILED: {res.get('error', 'unknown')}")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}", file=sys.stderr)
        if hasattr(e, "response") and e.response is not None and e.response.text:
            print(e.response.text[:500], file=sys.stderr)
        sys.exit(5)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON response: {e}", file=sys.stderr)
        sys.exit(6)


if __name__ == "__main__":
    main()
