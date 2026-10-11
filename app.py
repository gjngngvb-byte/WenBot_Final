#!/usr/bin/env python3
"""
WenBot Backend API
Serves the frontend and provides endpoints to control the WenBot art generation process.
"""

import os
import subprocess
import json
import time
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)  # Enable CORS for all routes

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROBO_SCRIPT = os.path.join(BASE_DIR, 'robo.py')

# Store active processes and their logs
active_processes = {}
process_logs = {}

def run_robo_with_params(params, process_id):
    """Run robo.py with given parameters in a subprocess."""
    try:
        # Prepare environment with API keys and parameters
        env = os.environ.copy()

        # Override parameters if provided
        if 'width' in params:
            env['CLOUDFLARE_IMAGE_WIDTH'] = str(params['width'])
        if 'height' in params:
            env['CLOUDFLARE_IMAGE_HEIGHT'] = str(params['height'])
        if 'seed' in params:
            # Note: robo.py uses random seed internally, but we could modify it to accept seed
            # For now, we'll note that seed control would require modifying robo.py
            pass
        if 'attempts' in params:
            # This would require modifying robo.py's retry logic
            pass

        # Ensure required API keys are present (will fail gracefully if not)
        required_keys = ['GOOGLE_API_KEY', 'CLOUDFLARE_ACCOUNT_ID', 'CLOUDFLARE_API_TOKEN']
        missing_keys = [key for key in required_keys if not env.get(key)]
        if missing_keys:
            error_msg = f"Missing required environment variables: {', '.join(missing_keys)}"
            process_logs[process_id] = [{"timestamp": datetime.now().isoformat(), "level": "error", "message": error_msg}]
            active_processes[process_id] = {"status": "error", "error": error_msg}
            return

        # Build command to run robo.py
        cmd = ['python', ROBO_SCRIPT]

        # Create subprocess
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )

        active_processes[process_id] = {"status": "running", "pid": process.pid}
        process_logs[process_id] = []

        # Read output in real-time
        for line in process.stdout:
            if line:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "level": "info",
                    "message": line.strip()
                }
                process_logs[process_id].append(log_entry)

                # Keep only last 100 log entries to prevent memory issues
                if len(process_logs[process_id]) > 100:
                    process_logs[process_id] = process_logs[process_id][-100:]

        # Wait for process to complete
        process.wait()

        if process.returncode == 0:
            active_processes[process_id] = {"status": "completed"}
            # Add completion log
            process_logs[process_id].append({
                "timestamp": datetime.now().isoformat(),
                "level": "success",
                "message": "Art generation completed successfully!"
            })
        else:
            active_processes[process_id] = {"status": "error", "returncode": process.returncode}
            process_logs[process_id].append({
                "timestamp": datetime.now().isoformat(),
                "level": "error",
                "message": f"Process exited with code {process.returncode}"
            })

    except Exception as e:
        error_msg = f"Failed to run robo.py: {str(e)}"
        active_processes[process_id] = {"status": "error", "error": error_msg}
        process_logs[process_id].append({
            "timestamp": datetime.now().isoformat(),
            "level": "error",
            "message": error_msg
        })

@app.route('/')
def index():
    """Serve the main frontend page."""
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files (CSS, JS, images, etc.)."""
    return send_from_directory(BASE_DIR, filename)

@app.route('/api/generate', methods=['POST'])
def start_generation():
    """Start a new art generation process with given parameters."""
    try:
        data = request.get_json()

        # Generate unique process ID
        process_id = f"wenbot_{int(time.time() * 1000)}"

        # Validate parameters
        width = int(data.get('width', 1024))
        height = int(data.get('height', 1024))

        if width < 256 or width > 2048 or height < 256 or height > 2048:
            return jsonify({"error": "Image dimensions must be between 256 and 2048 pixels"}), 400

        # Start generation in background thread
        thread = threading.Thread(
            target=run_robo_with_params,
            args=({
                'width': width,
                'height': height,
                'seed': data.get('seed'),
                'attempts': int(data.get('attempts', 3))
            }, process_id)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            "process_id": process_id,
            "status": "started",
            "message": "Art generation started"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/status/<process_id>')
def get_status(process_id):
    """Get the status and logs of a generation process."""
    if process_id not in active_processes:
        return jsonify({"error": "Process not found"}), 404

    status_info = active_processes[process_id].copy()
    status_info["logs"] = process_logs.get(process_id, [])

    return jsonify(status_info)

@app.route('/api/art')
def get_current_art():
    """Get information about the currently generated art."""
    try:
        # Check if art files exist
        art_jpg = os.path.join(BASE_DIR, 'wen_art.jpg')
        art_txt = os.path.join(BASE_DIR, 'wen_art.txt')
        idea_txt = os.path.join(BASE_DIR, 'wen_art_idea.txt')

        response = {}

        if os.path.exists(art_jpg):
            response['image_url'] = '/wen_art.jpg?' + str(int(os.path.getmtime(art_jpg) * 1000))
            response['image_timestamp'] = os.path.getmtime(art_jpg)

        if os.path.exists(art_txt):
            with open(art_txt, 'r', encoding='utf-8') as f:
                response['legend'] = f.read().strip()

        if os.path.exists(idea_txt):
            with open(idea_txt, 'r', encoding='utf-8') as f:
                response['idea'] = f.read().strip()

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "robo_script_exists": os.path.exists(ROBO_SCRIPT)
    })

if __name__ == '__main__':
    print("Starting WenBot Backend...")
    print(f"Serving frontend from: {BASE_DIR}")
    print(f"Robo script: {ROBO_SCRIPT}")
    print("Access the interface at: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)