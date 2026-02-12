#!/usr/bin/env python3
"""
Redis Usage Monitor
Monitor Redis memory, keys, and usage patterns
"""

import logging
from typing import Dict, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

def get_redis_usage_stats() -> Optional[Dict[str, Any]]:
    """Get comprehensive Redis usage statistics"""
    try:
        from core.redis_connection_helper import get_redis_client
        client = get_redis_client()
        
        if not client:
            return None
        
        # Get memory info
        info = client.info('memory')
        stats = client.info('stats')
        
        # Count keys by prefix
        all_keys = client.keys('fikiri:*')
        prefix_counts = defaultdict(int)
        keys_with_ttl = 0
        keys_without_ttl = 0
        
        for key in all_keys:
            # Extract prefix (second part after fikiri:)
            parts = key.split(':')
            if len(parts) >= 2:
                prefix = parts[1]
                prefix_counts[prefix] += 1
            
            # Check TTL
            ttl = client.ttl(key)
            if ttl > 0:
                keys_with_ttl += 1
            elif ttl == -1:
                keys_without_ttl += 1
        
        # Calculate usage percentages (for Upstash free tier)
        used_memory_bytes = info.get('used_memory', 0)
        used_memory_mb = used_memory_bytes / (1024 * 1024)
        storage_percent = (used_memory_mb / 256) * 100  # 256 MB limit
        
        # Estimate commands (rough - actual tracking needed)
        total_commands = stats.get('total_commands_processed', 0)
        commands_percent = (total_commands / 500000) * 100  # 500k limit
        
        return {
            'memory': {
                'used_bytes': used_memory_bytes,
                'used_mb': round(used_memory_mb, 2),
                'used_human': info.get('used_memory_human', 'N/A'),
                'limit_mb': 256,
                'usage_percent': round(storage_percent, 2),
                'status': '✅ Excellent' if storage_percent < 10 else '⚠️ Monitor' if storage_percent < 50 else '❌ High'
            },
            'keys': {
                'total': client.dbsize(),
                'with_ttl': keys_with_ttl,
                'without_ttl': keys_without_ttl,
                'by_prefix': dict(prefix_counts)
            },
            'commands': {
                'total_processed': total_commands,
                'limit': 500000,
                'usage_percent': round(commands_percent, 2),
                'status': '✅ Excellent' if commands_percent < 10 else '⚠️ Monitor' if commands_percent < 50 else '❌ High'
            },
            'connection': {
                'connected_clients': info.get('connected_clients', 0),
                'uptime_seconds': info.get('uptime_in_seconds', 0)
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Redis usage stats failed: {e}")
        return None


def log_redis_usage_report():
    """Log a formatted Redis usage report (use logger for production)."""
    stats = get_redis_usage_stats()
    if not stats:
        logger.warning("Redis not available or connection failed")
        return
    mem = stats['memory']
    keys = stats['keys']
    cmd = stats['commands']
    conn = stats['connection']
    logger.info(
        "Redis usage: storage %s MB/%s MB (%s%%), keys total=%s with_ttl=%s without_ttl=%s, "
        "commands %s/%s (%s%%), clients=%s uptime_h=%s",
        mem['used_mb'], mem['limit_mb'], mem['usage_percent'],
        keys['total'], keys['with_ttl'], keys['without_ttl'],
        cmd['total_processed'], cmd['limit'], cmd['usage_percent'],
        conn['connected_clients'], conn['uptime_seconds'] // 3600,
    )
    if keys['without_ttl'] > 0:
        logger.warning("%s keys have no expiration", keys['without_ttl'])
    for prefix, count in sorted(keys['by_prefix'].items(), key=lambda x: x[1], reverse=True):
        logger.debug("Redis prefix %s: %s", prefix, count)


def print_redis_usage_report():
    """Print a formatted Redis usage report (CLI only, e.g. python -m core.redis_monitor)."""
    stats = get_redis_usage_stats()
    if not stats:
        print("❌ Redis not available or connection failed")
        return
    mem = stats['memory']
    keys = stats['keys']
    cmd = stats['commands']
    conn = stats['connection']
    print("\n" + "="*60)
    print("REDIS USAGE REPORT")
    print("="*60)
    print(f"\n📦 STORAGE\n   Used: {mem['used_mb']} MB / {mem['limit_mb']} MB ({mem['usage_percent']}%)")
    print(f"   Status: {mem['status']}")
    print(f"\n🔑 KEYS\n   Total: {keys['total']}\n   With TTL: {keys['with_ttl']}\n   Without TTL: {keys['without_ttl']}")
    if keys['without_ttl'] > 0:
        print(f"   ⚠️  Warning: {keys['without_ttl']} keys have no expiration!")
    print("   By Prefix:")
    for prefix, count in sorted(keys['by_prefix'].items(), key=lambda x: x[1], reverse=True):
        print(f"      {prefix}: {count}")
    print(f"\n⚡ COMMANDS\n   Processed: {cmd['total_processed']:,} / {cmd['limit']:,} ({cmd['usage_percent']}%)")
    print(f"   Status: {cmd['status']}")
    print(f"\n🔌 CONNECTION\n   Connected clients: {conn['connected_clients']}\n   Uptime: {conn['uptime_seconds'] // 3600} hours")
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    print_redis_usage_report()






