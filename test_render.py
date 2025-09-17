#!/usr/bin/env python3
"""
Minimal test for Render deployment
"""

from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        'status': 'working',
        'message': 'Render deployment test successful!',
        'port': os.environ.get('PORT', '8081'),
        'environment': os.environ.get('RENDER', 'local')
    })

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': '2025-09-17T08:40:00Z',
        'version': '1.0.0',
        'render': True
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8081))
    app.run(host='0.0.0.0', port=port, debug=True)
