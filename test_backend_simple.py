#!/usr/bin/env python3
"""
Simple backend test to diagnose Render deployment issues
"""

from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        'status': 'working',
        'message': 'Backend is running!',
        'port': os.environ.get('PORT', '8081')
    })

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': '2025-09-17T08:40:00Z',
        'version': '1.0.0'
    })

@app.route('/api/test')
def test():
    return jsonify({
        'message': 'Test endpoint working!',
        'environment': os.environ.get('FLASK_ENV', 'development')
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8081))
    app.run(host='0.0.0.0', port=port, debug=True)
