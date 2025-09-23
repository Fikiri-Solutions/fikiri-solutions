#!/usr/bin/env python3
"""
Test the monitoring fix
"""

import os
import time

# Set Redis environment variables
os.environ['REDIS_URL'] = 'redis://default:fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H@redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com:19575'
os.environ['REDIS_HOST'] = 'redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com'
os.environ['REDIS_PORT'] = '19575'
os.environ['REDIS_PASSWORD'] = 'fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H'
os.environ['REDIS_DB'] = '0'

print("🔧 Environment variables set")
print("🔍 Testing performance monitor...")

# Import the performance monitor
from core.performance_monitor import performance_monitor

print("✅ Performance monitor imported successfully")
print("⏳ Waiting 35 seconds to see if monitoring errors occur...")

# Wait for the monitoring thread to run (it runs every 30 seconds)
time.sleep(35)

print("✅ Test completed - no monitoring errors should have appeared above")
