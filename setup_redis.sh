#!/bin/bash
# Redis Setup Script for Fikiri Solutions

echo "🔧 Setting up Redis for Fikiri Solutions..."

# Check if Redis is already installed
if command -v redis-server &> /dev/null; then
    echo "✅ Redis is already installed"
else
    echo "📦 Installing Redis..."
    if command -v brew &> /dev/null; then
        brew install redis
    else
        echo "❌ Homebrew not found. Please install Redis manually:"
        echo "   https://redis.io/docs/getting-started/installation/"
        exit 1
    fi
fi

# Start Redis service
echo "🚀 Starting Redis service..."
if command -v brew &> /dev/null; then
    brew services start redis
else
    redis-server --daemonize yes
fi

# Wait a moment for Redis to start
sleep 2

# Test Redis connection
echo "🧪 Testing Redis connection..."
if redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis is running successfully!"
    echo "📊 Redis info:"
    redis-cli info server | grep redis_version
else
    echo "❌ Redis connection failed"
    echo "💡 Try running: brew services restart redis"
    exit 1
fi

echo ""
echo "🎉 Redis setup complete!"
echo "💡 To stop Redis: brew services stop redis"
echo "💡 To restart Redis: brew services restart redis"
