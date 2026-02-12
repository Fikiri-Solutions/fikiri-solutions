"""
Gmail Integration Module
"""
from .gmail_client import gmail_client, GmailClient
from .utils import MinimalGmailService

__all__ = [
    "gmail_client",
    "GmailClient",
    "MinimalGmailService"
]

