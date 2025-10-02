#!/usr/bin/env python3
"""
Modular backend using new parser architecture
No dependency on lula2.py
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import time
import traceback
from parsers import get_parser

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
]

def allowed_file(filename):
    """Check if file extension is allowed"""
    return filename.endswith('.tar.bz2') or filename.endswith('.bz2') or filename.endswith('.tar.gz') or filename.endswith('.gz')

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '3.0.0',
        'mode': 'modular',
        'features': ['modular-parsers', 'no-lula2-dependency']
    })

@app.route('/api/parse-modes', methods=['GET'])
def get_parse_modes():
    """Get available parsing modes"""
    return jsonify(PARSE_MODES)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload and process log file synchronously"""
    start_time = time.time()

    try:
        # Validate file upload
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Please upload .tar.bz2, .bz2, .tar.gz, or .gz files'}), 400

        # Get parameters
        parse_mode = request.form.get('parse_mode', 'known')
        timezone = request.form.get('timezone', 'US/Eastern')
        begin_date = request.form.get('begin_date', '')
        end_date = request.form.get('end_date', '')

        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = int(time.time())
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{timestamp}_{filename}")
        file.save(filepath)

        app.logger.info(f"Processing {filename} in {parse_mode} mode")

        try:
            # Get appropriate parser
            parser = get_parser(parse_mode)

            # Process the file
            result = parser.process(
                archive_path=filepath,
                timezone=timezone,
                begin_date=begin_date if begin_date else None,
                end_date=end_date if end_date else None
            )

            processing_time = time.time() - start_time

            # Clean up uploaded file
            try:
                os.remove(filepath)
            except:
                pass

            # Return results
            return jsonify({
                'success': True,
                'output': result['raw_output'],
                'parsed_data': result['parsed_data'],
                'parse_mode': parse_mode,
                'filename': filename,
                'processing_time': round(processing_time, 2),
                'error': None
            })

        except Exception as parse_error:
            # Clean up on error
            try:
                os.remove(filepath)
            except:
                pass

            app.logger.error(f"Parse error: {str(parse_error)}\n{traceback.format_exc()}")

            return jsonify({
                'success': False,
                'error': f'Parse error: {str(parse_error)}',
                'output': '',
                'parsed_data': None,
                'parse_mode': parse_mode,
                'filename': filename
            }), 500

    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Upload error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
