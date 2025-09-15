#!/bin/bash

# 🚀 Fikiri Solutions - Local Development Script
# Quick restart cycle for every tweak

echo "🎯 Starting Fikiri Solutions Frontend Development..."

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Run this script from the frontend directory"
    exit 1
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Run type check
echo "🔍 Running TypeScript type check..."
npm run type-check

# Run linter
echo "🧹 Running ESLint..."
npm run lint

# Format code
echo "✨ Formatting code with Prettier..."
npm run format

# Start development server
echo "🚀 Starting development server..."
echo "📱 Open http://localhost:3000 in your browser"
echo "🔄 Hot reload enabled - changes will auto-refresh"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

npm run dev

