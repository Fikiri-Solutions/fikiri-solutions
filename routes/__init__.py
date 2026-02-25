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
from .jobs import jobs_bp
from .expert_api import expert_bp
from .kpi_api import kpi_bp

__all__ = [
    'auth_bp',
    'business_bp', 
    'test_bp',
    'user_bp',
    'monitoring_bp',
    'jobs_bp',
    'expert_bp',
    'kpi_bp'
]
