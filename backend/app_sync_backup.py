#!/usr/bin/env python3
"""
Fixed backend - simpler synchronous processing with better error handling
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import subprocess
import json
import re
from datetime import datetime
import time

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = '/app/uploads'
TEMP_FOLDER = '/app/temp'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max

PARSE_MODES = [
    {'value': 'known', 'label': 'Known Errors (Default)', 'description': 'Small set of known errors and events'},
    {'value': 'error', 'label': 'All Errors', 'description': 'Any line containing ERROR'},
    {'value': 'v', 'label': 'Verbose', 'description': 'Include more common errors'},
    {'value': 'all', 'label': 'All Lines', 'description': 'Return all log lines'},
    {'value': 'bw', 'label': 'Bandwidth', 'description': 'Stream bandwidth in CSV format'},
    {'value': 'md-bw', 'label': 'Modem Bandwidth', 'description': 'Modem bandwidth in CSV format'},
    {'value': 'md-db-bw', 'label': 'Data Bridge Bandwidth', 'description': 'Data bridge modem bandwidth'},
    {'value': 'md', 'label': 'Modem Statistics', 'description': 'Detailed modem statistics'},
    {'value': 'sessions', 'label': 'Sessions', 'description': 'Streaming session summaries'},
    {'value': 'id', 'label': 'Device IDs', 'description': 'Boss ID of device and server'},
    {'value': 'memory', 'label': 'Memory Usage', 'description': 'Memory consumption data'},
    {'value': 'grading', 'label': 'Modem Grading', 'description': 'Service level transitions'},
    {'value': 'cpu', 'label': 'CPU Usage', 'description': 'CPU idle/usage statistics'},
    {'value': 'modemevents', 'label': 'Modem Events', 'description': 'All modem connectivity events'},
    {'value': 'modemeventssorted', 'label': 'Modem Events Sorted', 'description': 'Connectivity events sorted by modem'},
    {'value': 'ffmpeg', 'label': 'FFmpeg Logs', 'description': 'FFmpeg processing logs'},
]

def allowed_file(filename):
    # Accept both .tar.bz2 and .bz2 files
    return filename.endswith('.tar.bz2') or filename.endswith('.bz2')

def parse_modem_statistics(output):
    """Parse modem statistics output into structured data"""
    modems = []
    lines = output.split('\n')
    current_modem = None

    for line in lines:
        if line.startswith('Modem '):
            if current_modem:
                modems.append(current_modem)
            modem_match = re.search(r'Modem (\d+)', line)
            if modem_match:
                current_modem = {'modem_id': modem_match.group(1), 'stats': {}}
        elif current_modem and '\t' in line:
            line = line.strip()
            if 'Potential Bandwidth' in line:
                match = re.search(r'\(L/H/A\): ([\d.]+) / ([\d.]+) / ([\d.]+)', line)
                if match:
                    current_modem['stats']['bandwidth'] = {
                        'low': float(match.group(1)),
                        'high': float(match.group(2)),
                        'avg': float(match.group(3))
                    }
            elif 'Percent Loss' in line:
                match = re.search(r'\(L/H/A\): ([\d.]+) / ([\d.]+) / ([\d.]+)', line)
                if match:
                    current_modem['stats']['loss'] = {
                        'low': float(match.group(1)),
                        'high': float(match.group(2)),
                        'avg': float(match.group(3))
                    }
            elif 'Extrapolated Up Delay' in line:
                match = re.search(r'\(L/H/A\): ([\d.]+) / ([\d.]+) / ([\d.]+)', line)
                if match:
                    current_modem['stats']['delay'] = {
                        'low': float(match.group(1)),
                        'high': float(match.group(2)),
                        'avg': float(match.group(3))
                    }

    if current_modem:
        modems.append(current_modem)

    return modems

def parse_sessions(output):
    """Parse session output into structured data"""
    sessions = []
    lines = output.split('\n')

    for line in lines:
        if 'Complete' in line or 'Start Only' in line or 'End Only' in line:
            session = {'raw': line}

            if 'Complete' in line:
                session['type'] = 'complete'
                times = re.search(r"-b '([^']+)' -e '([^']+)', (.+)", line)
                if times:
                    session['start'] = times.group(1)
                    session['end'] = times.group(2)
                    session['duration'] = times.group(3)
            elif 'Start Only' in line:
                session['type'] = 'start_only'
                times = re.search(r": (.+)", line)
                if times:
                    session['start'] = times.group(1)
            elif 'End Only' in line:
                session['type'] = 'end_only'
                times = re.search(r": (.+)", line)
                if times:
                    session['end'] = times.group(1)

            session_id = re.search(r'session id: ([^)]+)', line)
            if session_id:
                session['session_id'] = session_id.group(1)

            sessions.append(session)

    return sessions

def parse_bandwidth_csv(output):
    """Parse CSV bandwidth data"""
    lines = output.strip().split('\n')
    if len(lines) < 2:
        return []

    headers = [h.strip() for h in lines[0].split(',')]
    data = []

    for line in lines[1:]:
        if line.strip():
            values = [v.strip() for v in line.split(',')]
            if len(values) == len(headers):
                data.append(dict(zip(headers, values)))

    return data

@app.route('/api/parse-modes', methods=['GET'])
def get_parse_modes():
    """Get available parsing modes"""
    return jsonify(PARSE_MODES)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload and parse log file - SYNCHRONOUS"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Please upload .tar.bz2 or .bz2 files'}), 400

    parse_mode = request.form.get('parse_mode', 'known')
    timezone = request.form.get('timezone', 'US/Eastern')
    begin_date = request.form.get('begin_date', '')
    end_date = request.form.get('end_date', '')

    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = int(time.time())
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{timestamp}_{filename}")
        file.save(filepath)

        print(f"Processing {filename} in {parse_mode} mode...")

        # Build command
        cmd = ['python3', '/app/lula2.py', filepath, '-p', parse_mode, '-t', timezone]

        if begin_date:
            cmd.extend(['-b', begin_date])
        if end_date:
            cmd.extend(['-e', end_date])

        # Execute lula2.py with proper timeout
        print(f"Running: {' '.join(cmd)}")
        start_time = time.time()

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes
        )

        processing_time = time.time() - start_time
        print(f"Processing completed in {processing_time:.2f} seconds")

        output = result.stdout
        error = result.stderr

        # Parse output based on mode
        parsed_data = None
        if parse_mode == 'md':
            parsed_data = parse_modem_statistics(output)
        elif parse_mode == 'sessions':
            parsed_data = parse_sessions(output)
        elif parse_mode in ['bw', 'md-bw', 'md-db-bw']:
            parsed_data = parse_bandwidth_csv(output)

        # Clean up uploaded file
        try:
            os.remove(filepath)
        except:
            pass

        return jsonify({
            'success': True,
            'output': output,
            'error': error if error else None,
            'parsed_data': parsed_data,
            'parse_mode': parse_mode,
            'filename': filename,
            'processing_time': round(processing_time, 2)
        })

    except subprocess.TimeoutExpired:
        print(f"Processing timeout for {filename}")
        return jsonify({'error': 'Processing timeout (>10 minutes)'}), 408
    except Exception as e:
        print(f"Error processing {filename}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '2.1.0',
        'mode': 'synchronous',
        'features': ['reliable-processing', 'direct-response']
    })

if __name__ == '__main__':
    print("Starting LiveU Log Analyzer Backend v2.1.0 (Synchronous Mode)")
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
