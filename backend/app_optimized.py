#!/usr/bin/env python3
"""
Optimized Flask backend with async processing and progress updates
"""
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import sys
import subprocess
import json
import re
from datetime import datetime
import tempfile
import shutil
import threading
import time
import uuid
from collections import OrderedDict

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = '/app/uploads'
TEMP_FOLDER = '/app/temp'
ALLOWED_EXTENSIONS = {'bz2', 'tar'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max

# Job storage (in production, use Redis or database)
jobs = OrderedDict()
MAX_JOBS = 100  # Keep last 100 jobs in memory

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

def update_job_status(job_id, status, progress=None, message=None, result=None, error=None):
    """Update job status thread-safely"""
    if job_id in jobs:
        jobs[job_id]['status'] = status
        jobs[job_id]['updated_at'] = datetime.now().isoformat()
        if progress is not None:
            jobs[job_id]['progress'] = progress
        if message is not None:
            jobs[job_id]['message'] = message
        if result is not None:
            jobs[job_id]['result'] = result
        if error is not None:
            jobs[job_id]['error'] = error

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

            # Extract session type
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

            # Extract session ID if present
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

def process_log_async(job_id, filepath, parse_mode, timezone, begin_date, end_date, filename):
    """Process log file in background thread"""
    try:
        update_job_status(job_id, 'processing', 10, 'Building command...')

        # Build command
        cmd = ['python3', '/app/lula2.py', filepath, '-p', parse_mode, '-t', timezone]

        if begin_date:
            cmd.extend(['-b', begin_date])
        if end_date:
            cmd.extend(['-e', end_date])

        update_job_status(job_id, 'processing', 30, f'Executing lula2.py in {parse_mode} mode...')

        # Execute lula2.py
        start_time = time.time()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # Increased to 10 minutes
        )

        processing_time = time.time() - start_time

        update_job_status(job_id, 'processing', 70, 'Parsing output...')

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

        update_job_status(job_id, 'processing', 90, 'Cleaning up...')

        # Clean up uploaded file
        try:
            os.remove(filepath)
        except:
            pass

        # Store result
        result_data = {
            'success': True,
            'output': output,
            'error': error if error else None,
            'parsed_data': parsed_data,
            'parse_mode': parse_mode,
            'filename': filename,
            'processing_time': round(processing_time, 2)
        }

        update_job_status(job_id, 'completed', 100, 'Analysis complete!', result=result_data)

    except subprocess.TimeoutExpired:
        update_job_status(job_id, 'failed', error='Processing timeout (>10 minutes)')
    except Exception as e:
        update_job_status(job_id, 'failed', error=str(e))

@app.route('/api/parse-modes', methods=['GET'])
def get_parse_modes():
    """Get available parsing modes"""
    return jsonify(PARSE_MODES)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload and start async processing"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Please upload .tar.bz2 files'}), 400

    parse_mode = request.form.get('parse_mode', 'known')
    timezone = request.form.get('timezone', 'US/Eastern')
    begin_date = request.form.get('begin_date', '')
    end_date = request.form.get('end_date', '')

    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Create job
        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            'id': job_id,
            'status': 'queued',
            'progress': 0,
            'message': 'Upload complete, queued for processing...',
            'filename': filename,
            'parse_mode': parse_mode,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'result': None,
            'error': None
        }

        # Limit jobs in memory
        if len(jobs) > MAX_JOBS:
            jobs.popitem(last=False)

        # Start background processing
        thread = threading.Thread(
            target=process_log_async,
            args=(job_id, filepath, parse_mode, timezone, begin_date, end_date, filename)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'File uploaded successfully. Processing started.'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/job/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get job status"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404

    return jsonify(jobs[job_id])

@app.route('/api/job/<job_id>/stream', methods=['GET'])
def stream_job_progress(job_id):
    """Stream job progress using Server-Sent Events"""
    def generate():
        if job_id not in jobs:
            yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
            return

        while True:
            job = jobs.get(job_id)
            if not job:
                break

            yield f"data: {json.dumps(job)}\n\n"

            if job['status'] in ['completed', 'failed']:
                break

            time.sleep(0.5)  # Poll every 500ms

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List all jobs"""
    return jsonify(list(jobs.values()))

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '2.0.0',
        'features': ['async-processing', 'progress-streaming', 'improved-performance']
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
