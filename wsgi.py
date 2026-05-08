"""
Gunicorn WSGI entry point.

Gevent monkey-patching MUST run before any other import that touches `ssl`,
`socket`, `threading`, or `time`. If we let `app.py` import flask / requests /
stripe first, those modules cache references to the unpatched stdlib objects
and we get `RecursionError: maximum recursion depth exceeded` deep inside
`ssl.SSLSocket.read()` on every outbound HTTPS call (Google OAuth, Stripe, ...).

The render start command must reference `wsgi:wsgi_app` (not `app:wsgi_app`)
so this module loads first. Local `python app.py` stays unpatched, which is
fine because the dev server uses Werkzeug threads, not gevent.
"""

import os

if os.getenv("FIKIRI_SKIP_GEVENT_PATCH", "").lower() not in {"1", "true", "yes"}:
    from gevent import monkey

    monkey.patch_all()

from app import wsgi_app  # noqa: E402

application = wsgi_app
