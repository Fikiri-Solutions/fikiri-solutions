#!/usr/bin/env python3
"""
Redis CLI Alternative for Fikiri Solutions
Interactive Redis client using Python
"""

import redis
import json
import sys
from datetime import datetime

class FikiriRedisCLI:
    def __init__(self):
        self.redis_url = 'redis://default:fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H@redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com:19575'
        self.r = redis.from_url(self.redis_url, decode_responses=True)
        
    def connect(self):
        """Test connection to Redis"""
        try:
            result = self.r.ping()
            print(f"✅ Connected to Redis Cloud: {result}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def info(self):
        """Get Redis server information"""
        try:
            info = self.r.info()
            print("📊 Redis Server Information:")
            print(f"   Version: {info.get('redis_version', 'Unknown')}")
            print(f"   Memory: {info.get('used_memory_human', 'Unknown')}")
            print(f"   Connected clients: {info.get('connected_clients', 'Unknown')}")
            print(f"   Uptime: {info.get('uptime_in_seconds', 'Unknown')} seconds")
            return True
        except Exception as e:
            print(f"❌ Info failed: {e}")
            return False
    
    def set(self, key, value):
        """Set a key-value pair"""
        try:
            self.r.set(key, value)
            print(f"✅ Set {key} = {value}")
            return True
        except Exception as e:
            print(f"❌ Set failed: {e}")
            return False
    
    def get(self, key):
        """Get value by key"""
        try:
            value = self.r.get(key)
            if value:
                print(f"✅ {key} = {value}")
            else:
                print(f"❌ Key {key} not found")
            return value
        except Exception as e:
            print(f"❌ Get failed: {e}")
            return None
    
    def delete(self, key):
        """Delete a key"""
        try:
            result = self.r.delete(key)
            if result:
                print(f"✅ Deleted {key}")
            else:
                print(f"❌ Key {key} not found")
            return result
        except Exception as e:
            print(f"❌ Delete failed: {e}")
            return False
    
    def keys(self, pattern="*"):
        """List keys matching pattern"""
        try:
            keys = self.r.keys(pattern)
            if keys:
                print(f"🔑 Keys matching '{pattern}':")
                for key in keys:
                    print(f"   {key}")
            else:
                print(f"❌ No keys found matching '{pattern}'")
            return keys
        except Exception as e:
            print(f"❌ Keys failed: {e}")
            return []
    
    def hset(self, key, field, value):
        """Set hash field"""
        try:
            self.r.hset(key, field, value)
            print(f"✅ Hash {key}.{field} = {value}")
            return True
        except Exception as e:
            print(f"❌ Hash set failed: {e}")
            return False
    
    def hget(self, key, field):
        """Get hash field value"""
        try:
            value = self.r.hget(key, field)
            if value:
                print(f"✅ {key}.{field} = {value}")
            else:
                print(f"❌ Hash field {key}.{field} not found")
            return value
        except Exception as e:
            print(f"❌ Hash get failed: {e}")
            return None
    
    def hgetall(self, key):
        """Get all hash fields"""
        try:
            fields = self.r.hgetall(key)
            if fields:
                print(f"📋 Hash {key}:")
                for field, value in fields.items():
                    print(f"   {field}: {value}")
            else:
                print(f"❌ Hash {key} not found")
            return fields
        except Exception as e:
            print(f"❌ Hash getall failed: {e}")
            return {}
    
    def json_set(self, key, path, value):
        """Set JSON value"""
        try:
            if isinstance(value, str):
                value = json.loads(value)
            self.r.json().set(key, path, value)
            print(f"✅ JSON {key}{path} = {value}")
            return True
        except Exception as e:
            print(f"❌ JSON set failed: {e}")
            return False
    
    def json_get(self, key, path="$"):
        """Get JSON value"""
        try:
            value = self.r.json().get(key, path)
            if value:
                print(f"✅ JSON {key}{path} = {value}")
            else:
                print(f"❌ JSON {key}{path} not found")
            return value
        except Exception as e:
            print(f"❌ JSON get failed: {e}")
            return None
    
    def test_fikiri_data(self):
        """Test Fikiri-specific data operations"""
        print("\n🧪 Testing Fikiri Data Operations...")
        print("=" * 50)
        
        # Test user data
        user_data = {
            'name': 'Test User',
            'email': 'test@fikirisolutions.com',
            'industry': 'landscaping',
            'created_at': datetime.now().isoformat()
        }
        
        # Store as JSON
        self.json_set('fikiri:user:test', '$', user_data)
        
        # Store as Hash
        self.hset('fikiri:user:hash', 'name', 'Hash User')
        self.hset('fikiri:user:hash', 'email', 'hash@fikirisolutions.com')
        
        # Store as String
        self.set('fikiri:test:string', 'Hello Fikiri!')
        
        # Retrieve data
        print("\n📊 Retrieving test data...")
        self.json_get('fikiri:user:test')
        self.hgetall('fikiri:user:hash')
        self.get('fikiri:test:string')
        
        # List all Fikiri keys
        print("\n🔑 All Fikiri keys:")
        self.keys('fikiri:*')
        
        # Cleanup
        print("\n🧹 Cleaning up test data...")
        self.delete('fikiri:user:test')
        self.delete('fikiri:user:hash')
        self.delete('fikiri:test:string')
        
        print("✅ Fikiri data operations completed!")
    
    def interactive_mode(self):
        """Interactive Redis CLI mode"""
        print("🚀 Fikiri Redis CLI - Interactive Mode")
        print("=" * 50)
        print("Commands:")
        print("  SET <key> <value>     - Set key-value pair")
        print("  GET <key>             - Get value by key")
        print("  DEL <key>             - Delete key")
        print("  KEYS [pattern]        - List keys (default: *)")
        print("  HSET <key> <field> <value> - Set hash field")
        print("  HGET <key> <field>    - Get hash field")
        print("  HGETALL <key>         - Get all hash fields")
        print("  JSON_SET <key> <path> <value> - Set JSON value")
        print("  JSON_GET <key> [path] - Get JSON value")
        print("  INFO                  - Show Redis info")
        print("  TEST                  - Run Fikiri data tests")
        print("  QUIT                  - Exit")
        print("=" * 50)
        
        while True:
            try:
                command = input("\nredis> ").strip().split()
                if not command:
                    continue
                
                cmd = command[0].upper()
                
                if cmd == 'QUIT':
                    print("👋 Goodbye!")
                    break
                elif cmd == 'SET' and len(command) >= 3:
                    self.set(command[1], ' '.join(command[2:]))
                elif cmd == 'GET' and len(command) >= 2:
                    self.get(command[1])
                elif cmd == 'DEL' and len(command) >= 2:
                    self.delete(command[1])
                elif cmd == 'KEYS':
                    pattern = command[1] if len(command) >= 2 else '*'
                    self.keys(pattern)
                elif cmd == 'HSET' and len(command) >= 4:
                    self.hset(command[1], command[2], ' '.join(command[3:]))
                elif cmd == 'HGET' and len(command) >= 3:
                    self.hget(command[1], command[2])
                elif cmd == 'HGETALL' and len(command) >= 2:
                    self.hgetall(command[1])
                elif cmd == 'JSON_SET' and len(command) >= 4:
                    self.json_set(command[1], command[2], ' '.join(command[3:]))
                elif cmd == 'JSON_GET' and len(command) >= 2:
                    path = command[2] if len(command) >= 3 else '$'
                    self.json_get(command[1], path)
                elif cmd == 'INFO':
                    self.info()
                elif cmd == 'TEST':
                    self.test_fikiri_data()
                else:
                    print("❌ Invalid command. Type 'QUIT' to exit.")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

def main():
    """Main function"""
    cli = FikiriRedisCLI()
    
    if not cli.connect():
        sys.exit(1)
    
    if len(sys.argv) > 1:
        # Command line mode
        command = ' '.join(sys.argv[1:])
        if command.upper() == 'PING':
            cli.connect()
        elif command.upper() == 'INFO':
            cli.info()
        elif command.upper() == 'TEST':
            cli.test_fikiri_data()
        else:
            print("❌ Unknown command. Use: ping, info, test, or interactive mode")
    else:
        # Interactive mode
        cli.interactive_mode()

if __name__ == "__main__":
    main()
