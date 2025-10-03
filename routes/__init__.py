#!/usr/bin/env python3
"""
Routes Package
Centralized routing for Fikiri Solutions
"""

from .auth import auth_bp
from .business import business_bp
from .test import test_bp
from .user import user_bp
from .monitoring import monitoring_bp

__all__ = [
    'auth_bp',
    'business_bp', 
    'test_bp',
    'user_bp',
    'monitoring_bp'
]
