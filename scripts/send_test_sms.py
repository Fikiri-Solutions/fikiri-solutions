#!/usr/bin/env python3
"""
Send a single test SMS using Twilio. Uses env vars; supports either:
  - Messaging Service: TWILIO_MESSAGING_SERVICE_SID set → send via service
  - Phone number: TWILIO_PHONE_NUMBER set (e.g. +18553894992) → send from that number

Required: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
One of: TWILIO_MESSAGING_SERVICE_SID or TWILIO_PHONE_NUMBER

Trial accounts: "To" must be a number you've verified in Twilio Console
(Phone Numbers > Manage > Verified Caller IDs).
"""
import os
import sys

def main():
    from dotenv import load_dotenv
    load_dotenv()

    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    to = os.environ.get("TWILIO_TEST_TO", "+13525755715").strip()
    if not to.startswith("+"):
        to = "+1" + "".join(c for c in to if c.isdigit())[-10:]

    if not account_sid or not auth_token:
        print("ERROR: Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env")
        sys.exit(1)

    messaging_sid = os.environ.get("TWILIO_MESSAGING_SERVICE_SID")
    from_number = os.environ.get("TWILIO_PHONE_NUMBER", "+18553894992").strip()

    from twilio.rest import Client
    client = Client(account_sid, auth_token)

    try:
        if messaging_sid:
            msg = client.messages.create(
                messaging_service_sid=messaging_sid,
                body="Fikiri test. Reply STOP to opt out. Msg & data rates may apply.",
                to=to,
            )
        else:
            msg = client.messages.create(
                from_=from_number,
                body="Fikiri test. Reply STOP to opt out. Msg & data rates may apply.",
                to=to,
            )
        print("OK sid=%s to=%s status=%s" % (msg.sid, to, msg.status))
    except Exception as e:
        print("Twilio error:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
