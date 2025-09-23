#!/bin/bash
# Fikiri Solutions - Run with Virtual Environment
# This script ensures the app runs with the correct virtual environment

cd "$(dirname "$0")"

# Activate virtual environment
source venv_local/bin/activate

# Check if virtual environment is active
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment activated: $VIRTUAL_ENV"
else
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

# Set Redis Cloud environment variables
echo "🔧 Setting up Redis Cloud configuration..."
export REDIS_URL="redis://default:fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H@redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com:19575"
export REDIS_HOST="redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com"
export REDIS_PORT="19575"
export REDIS_PASSWORD="fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H"
export REDIS_DB="0"
echo "✅ Redis Cloud environment variables configured"

# Check if required packages are installed
echo "🔍 Checking required packages..."
python -c "import flask_jwt_extended; print('✅ flask-jwt-extended installed')" || {
    echo "❌ flask-jwt-extended not found. Installing..."
    pip install flask-jwt-extended>=4.5.0
}

python -c "import stripe; print('✅ stripe installed')" || {
    echo "❌ stripe not found. Installing..."
    pip install stripe
}

python -c "import sqlalchemy; print('✅ sqlalchemy installed')" || {
    echo "❌ sqlalchemy not found. Installing..."
    pip install sqlalchemy
}

# Run the application
echo "🚀 Starting Fikiri Solutions..."
python app.py
