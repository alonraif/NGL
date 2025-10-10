#!/usr/bin/env python3
"""
NGL - Next Gen LULA Backend
Modular backend using new parser architecture with database support
"""
from flask import Flask, request, jsonify, send_file, redirect
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import time
import traceback
import signal
import redis
import threading
import requests
import tempfile
from parsers import get_parser
from parsers.base import CancellationException
from database import init_db, SessionLocal
from models import User, Parser, LogFile, Analysis, AnalysisResult, SSLConfiguration
from auth import token_required, log_audit
from auth_routes import auth_bp
from admin_routes import admin_bp
from datetime import datetime, timedelta
from config import Config
import hashlib
import magic
from rate_limiter import limiter
from storage_service import StorageFactory
from werkzeug.middleware.proxy_fix import ProxyFix
import json

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

# Prefer HTTPS URLs when generating external links
app.config['PREFERRED_URL_SCHEME'] = 'https'
# Restrict CORS to configured origins only
CORS(app, origins=Config.CORS_ORIGINS, supports_credentials=True)

# Initialize rate limiter with app
limiter.init_app(app)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(admin_bp, url_prefix='/api/admin')

# Initialize Redis client
redis_client = redis.from_url(Config.REDIS_URL, decode_responses=True)

# Global dictionary to track active parsers for in-process cancellation
# Key: f"user_id:analysis_id", Value: parser instance
active_parsers = {}
parsers_lock = threading.Lock()  # Thread-safe access to active_parsers

UPLOAD_FOLDER = '/app/uploads'
TEMP_FOLDER = '/app/temp'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max

# HTTPS enforcement controls
HTTP_TO_HTTPS_REDIRECT_CODE = int(os.getenv('HTTPS_REDIRECT_STATUS', '308'))
FORCE_DISABLE_HTTPS = os.getenv('FORCE_DISABLE_HTTPS_ENFORCEMENT', 'false').lower() == 'true'

SSL_STATE_PATH = os.getenv('SSL_STATE_PATH', '/etc/nginx/runtime/ssl_state.json')
SSL_CACHE_TTL = int(os.getenv('SSL_STATE_CACHE_TTL', '5'))
_ssl_enforce_cache = {
    'value': False,
    'checked_at': 0.0
}


def _read_ssl_state_file():
    try:
        with open(SSL_STATE_PATH, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
            return bool(data.get('enforce_https'))
    except Exception:
        return None


def is_https_enforced(force_refresh: bool = False) -> bool:
    """Return whether HTTPS enforcement is currently active."""
    if FORCE_DISABLE_HTTPS:
        return False
    now = time.time()
    if force_refresh or (now - _ssl_enforce_cache['checked_at'] > SSL_CACHE_TTL):
        state = _read_ssl_state_file()
        if state is None:
            db = SessionLocal()
            try:
                ssl_config = db.query(SSLConfiguration).first()
                state = bool(ssl_config and ssl_config.enforce_https)
            except Exception:
                state = False
            finally:
                db.close()
        _ssl_enforce_cache['value'] = bool(state)
        _ssl_enforce_cache['checked_at'] = now
    return bool(_ssl_enforce_cache['value'])


@app.before_request
def redirect_to_https():
    """Force HTTPS when enforcement is enabled."""
    if FORCE_DISABLE_HTTPS:
        return
    if request.path.startswith('/.well-known/acme-challenge/'):
        # Allow ACME HTTP-01 challenges to pass through
        return

    if request.is_secure or request.headers.get('X-Forwarded-Proto', '').lower() == 'https':
        return

    if is_https_enforced():
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=HTTP_TO_HTTPS_REDIRECT_CODE)


@app.after_request
def add_hsts_header(response):
    """Add HSTS header when HTTPS is enforced."""
    if not FORCE_DISABLE_HTTPS and is_https_enforced():
        response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
    else:
        # Explicitly expire any cached HSTS policy when enforcement is off
        response.headers.setdefault('Strict-Transport-Security', 'max-age=0')
    return response

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


def validate_file_type(filepath):
    """Validate file is actually a compressed archive using magic bytes"""
    try:
        mime = magic.from_file(filepath, mime=True)
        allowed_mimes = [
            'application/x-bzip2',
            'application/x-gzip',
            'application/gzip',
            'application/x-tar',
            'application/x-compressed-tar'
        ]
        return mime in allowed_mimes
    except Exception as e:
        app.logger.error(f"File type validation error: {str(e)}")
        return False

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    db = SessionLocal()
    try:
        # Check database connection
        db.execute('SELECT 1')
        db_status = 'connected'
    except:
        db_status = 'disconnected'
    finally:
        db.close()

    return jsonify({
        'status': 'healthy',
        'version': '4.0.0',
        'mode': 'modular-with-database',
        'features': ['modular-parsers', 'database', 'authentication', 'user-management'],
        'database': db_status
    })

@app.route('/api/parse-modes', methods=['GET'])
@token_required
def get_parse_modes(current_user, db):
    """Get available parsing modes (requires authentication)"""
    # Get user's available parsers
    available_modes = []

    for mode in PARSE_MODES:
        # Check if parser is enabled and available
        parser = db.query(Parser).filter(Parser.parser_key == mode['value']).first()

        if parser:
            # Admin can see all enabled parsers
            if current_user.is_admin():
                if parser.is_enabled:
                    available_modes.append(mode)
            # Regular users see only available, non-admin parsers
            else:
                if parser.is_enabled and parser.is_available_to_users and not parser.is_admin_only:
                    available_modes.append(mode)
        else:
            # Parser not in DB yet - available to all by default
            available_modes.append(mode)

    return jsonify(available_modes)


@app.route('/api/download-progress', methods=['GET'])
@token_required
def get_download_progress(current_user, db):
    """Get current download progress for URL uploads"""
    try:
        progress_key = f"download_progress:{current_user.id}"
        progress_data = redis_client.get(progress_key)

        if not progress_data:
            return jsonify({'downloading': False}), 200

        # Parse progress data: "downloaded:total:percent"
        parts = progress_data.split(':')
        if len(parts) >= 3:
            downloaded = int(parts[0])
            total = int(parts[1]) if parts[1] != 'None' else None
            percent = float(parts[2])

            return jsonify({
                'downloading': True,
                'downloaded': downloaded,
                'total': total,
                'percent': percent
            }), 200
        else:
            return jsonify({'downloading': False}), 200

    except Exception as e:
        app.logger.error(f"Error getting download progress: {str(e)}")
        return jsonify({'downloading': False}), 200

def calculate_file_hash(filepath):
    """Calculate SHA256 hash of file"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


@app.route('/api/upload', methods=['POST'])
@limiter.limit("100 per hour")  # Increased for development/testing
@token_required
def upload_file(current_user, db):
    """Upload and process log file synchronously (requires authentication)"""
    start_time = time.time()

    try:
        # Check if this is a URL upload or file upload
        file_url = request.form.get('file_url', '').strip()

        if file_url:
            # URL-based upload
            # Clean the URL (remove backslashes, extra whitespace)
            file_url = file_url.replace('\\', '').strip()
            app.logger.info(f"URL-based upload requested: {file_url}")

            # Validate URL format
            if not file_url.startswith(('http://', 'https://')):
                app.logger.error(f"Invalid URL format: {file_url}")
                return jsonify({'error': 'Invalid URL. Must start with http:// or https://'}), 400

            # Extract filename from URL
            filename = file_url.split('/')[-1].split('?')[0]  # Remove query params
            app.logger.info(f"Extracted filename from URL: {filename}")
            if not filename or not allowed_file(filename):
                app.logger.error(f"Invalid filename extracted: {filename}")
                return jsonify({'error': 'URL must point to a valid log file (.tar.bz2, .bz2, .tar.gz, or .gz)'}), 400

            # Download file from URL with timeout and size limit
            try:
                app.logger.info(f"Downloading file from: {file_url}")
                response = requests.get(file_url, stream=True, timeout=300)  # 5 minute timeout
                response.raise_for_status()

                # Check content length if available
                content_length = response.headers.get('content-length')
                total_size = int(content_length) if content_length else None

                if total_size and total_size > app.config['MAX_CONTENT_LENGTH']:
                    return jsonify({'error': 'File too large. Maximum size is 500MB'}), 400

                # Create temporary file to store downloaded content
                temp_fd, temp_filepath = tempfile.mkstemp(suffix='.tmp', dir=TEMP_FOLDER)
                file_size = 0

                # Store progress in Redis for tracking
                progress_key = f"download_progress:{current_user.id}"

                try:
                    with os.fdopen(temp_fd, 'wb') as temp_file:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                temp_file.write(chunk)
                                file_size += len(chunk)

                                # Update progress in Redis
                                progress_percent = (file_size / total_size * 100) if total_size else 0
                                redis_client.setex(progress_key, 60, f"{file_size}:{total_size}:{progress_percent:.1f}")

                                # Check size during download
                                if file_size > app.config['MAX_CONTENT_LENGTH']:
                                    raise Exception('File size exceeds maximum allowed size')

                    # Clear progress
                    redis_client.delete(progress_key)
                    app.logger.info(f"Downloaded {file_size} bytes to {temp_filepath}")

                except Exception as e:
                    # Clean up temp file on download error
                    if os.path.exists(temp_filepath):
                        os.remove(temp_filepath)
                    raise e

            except requests.exceptions.Timeout:
                app.logger.error(f"Download timeout for URL: {file_url}")
                redis_client.delete(progress_key)
                return jsonify({'error': 'Download timeout. File took too long to download.'}), 408
            except requests.exceptions.HTTPError as e:
                app.logger.error(f"HTTP error downloading {file_url}: {e.response.status_code}")
                redis_client.delete(progress_key)

                # Provide helpful error messages based on status code
                if e.response.status_code == 403:
                    return jsonify({'error': 'Access denied. The URL requires authentication or the link has expired.'}), 403
                elif e.response.status_code == 404:
                    return jsonify({'error': 'File not found at the provided URL.'}), 404
                else:
                    return jsonify({'error': f'Failed to download file: HTTP {e.response.status_code}'}), 400
            except requests.exceptions.RequestException as e:
                app.logger.error(f"Request error downloading {file_url}: {str(e)}")
                redis_client.delete(progress_key)
                return jsonify({'error': f'Failed to download file: {str(e)}'}), 400
            except Exception as e:
                app.logger.error(f"Download error for {file_url}: {str(e)}")
                redis_client.delete(progress_key)
                return jsonify({'error': f'Download error: {str(e)}'}), 500

        else:
            # Traditional file upload
            if 'file' not in request.files:
                return jsonify({'error': 'No file or URL provided'}), 400

            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400

            if not allowed_file(file.filename):
                return jsonify({'error': 'Invalid file type. Please upload .tar.bz2, .bz2, .tar.gz, or .gz files'}), 400

            filename = secure_filename(file.filename)

        # Get parameters
        parse_mode = request.form.get('parse_mode', 'known')
        session_name = request.form.get('session_name', '').strip()
        zendesk_case = request.form.get('zendesk_case', '').strip()
        timezone = request.form.get('timezone', 'US/Eastern')
        begin_date = request.form.get('begin_date', '')
        end_date = request.form.get('end_date', '')

        # Validate required fields
        if not session_name:
            return jsonify({'error': 'Session name is required'}), 400

        # Handle file size and quota differently for URL vs file upload
        if file_url:
            # URL download - file_size and temp_filepath already set above
            file_size_mb = file_size / (1024 * 1024)
            # filename already extracted from URL
            # temp_filepath already created during download
        else:
            # File upload - get size and save
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Seek back to start
            file_size_mb = file_size / (1024 * 1024)

            # Save uploaded file temporarily for validation and parsing
            timestamp = int(time.time())
            stored_filename = f"{timestamp}_{filename}"
            temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], stored_filename)
            file.save(temp_filepath)

        # Check storage quota (applies to both URL and file uploads)
        if current_user.storage_used_mb + file_size_mb > current_user.storage_quota_mb:
            # Clean up temp file if URL download
            if file_url and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
            return jsonify({'error': 'Storage quota exceeded'}), 400

        # Generate stored filename if not already set (for URL uploads)
        if file_url:
            timestamp = int(time.time())
            stored_filename = f"{timestamp}_{secure_filename(filename)}"

        # Validate file type using magic bytes
        if not validate_file_type(temp_filepath):
            os.remove(temp_filepath)  # Clean up invalid file
            return jsonify({'error': 'Invalid file type. File must be a valid compressed archive.'}), 400

        # Calculate file hash
        file_hash = calculate_file_hash(temp_filepath)

        # Get storage service and save file
        try:
            storage_service = StorageFactory.get_storage_service()
            storage_type = storage_service.get_storage_type()

            # Save file to storage
            if storage_type == 's3':
                # Upload to S3, keep temp file for parsing
                with open(temp_filepath, 'rb') as f:
                    stored_path = storage_service.save_file(f, stored_filename)
                filepath = temp_filepath  # Use temp file for parsing
            else:
                # Local storage - file is already saved at temp_filepath
                stored_path = temp_filepath
                filepath = temp_filepath

        except Exception as storage_error:
            # If storage fails, clean up temp file and try local storage as fallback
            app.logger.error(f"Storage service failed: {str(storage_error)}, falling back to local storage")
            storage_type = 'local'
            filepath = temp_filepath
            stored_path = temp_filepath

        # Create log file record
        log_file = LogFile(
            user_id=current_user.id,
            original_filename=filename,
            stored_filename=stored_filename,
            file_path=stored_path,
            file_size_bytes=file_size,
            file_hash=file_hash,
            storage_type=storage_type,
            retention_days=int(os.getenv('UPLOAD_RETENTION_DAYS', '30'))
        )
        log_file.expires_at = datetime.utcnow() + timedelta(days=log_file.retention_days)
        db.add(log_file)
        db.flush()  # Get ID without committing

        # Create analysis record
        parser_obj = db.query(Parser).filter(Parser.parser_key == parse_mode).first()
        analysis = Analysis(
            user_id=current_user.id,
            log_file_id=log_file.id,
            parser_id=parser_obj.id if parser_obj else None,
            parse_mode=parse_mode,
            session_name=session_name,
            zendesk_case=zendesk_case if zendesk_case else None,
            timezone=timezone,
            begin_date=begin_date,
            end_date=end_date,
            status='running',
            started_at=datetime.utcnow(),
            retention_days=int(os.getenv('UPLOAD_RETENTION_DAYS', '30'))
        )
        analysis.expires_at = datetime.utcnow() + timedelta(days=analysis.retention_days)
        db.add(analysis)
        db.flush()

        # Commit immediately so analysis is visible to cancel endpoint
        db.commit()

        # Store user's current analysis ID in Redis (for cancellation)
        user_analysis_key = f"user:{current_user.id}:current_analysis"
        redis_client.setex(user_analysis_key, 3600, str(analysis.id))

        app.logger.info(f"Processing {filename} in {parse_mode} mode for user {current_user.username}")

        try:
            # Get appropriate parser
            parser = get_parser(parse_mode)

            # Register parser for in-process cancellation
            parser_key = f"{current_user.id}:{analysis.id}"
            with parsers_lock:
                active_parsers[parser_key] = parser

            try:
                # Process the file using standalone parser (in-process, no subprocess)
                result = parser.process(
                    archive_path=filepath,
                    timezone=timezone,
                    begin_date=begin_date if begin_date else None,
                    end_date=end_date if end_date else None
                )
            finally:
                # Always remove parser from active list
                with parsers_lock:
                    active_parsers.pop(parser_key, None)

            processing_time = time.time() - start_time

            # Update analysis status
            analysis.status = 'completed'
            analysis.completed_at = datetime.utcnow()
            analysis.processing_time_seconds = int(processing_time)

            # Save analysis results
            analysis_result = AnalysisResult(
                analysis_id=analysis.id,
                raw_output=result['raw_output'],
                parsed_data=result['parsed_data']
            )
            db.add(analysis_result)

            # Update user storage
            current_user.storage_used_mb += file_size_mb

            db.commit()

            # Clean up temporary file if using S3
            if storage_type == 's3' and os.path.exists(temp_filepath) and temp_filepath != stored_path:
                try:
                    os.remove(temp_filepath)
                    app.logger.info(f"Cleaned up temporary file: {temp_filepath}")
                except Exception as e:
                    app.logger.warning(f"Failed to clean up temp file {temp_filepath}: {str(e)}")

            # Clean up user's current analysis from Redis
            user_analysis_key = f"user:{current_user.id}:current_analysis"
            redis_client.delete(user_analysis_key)

            # Log audit
            log_audit(db, current_user.id, 'upload_and_parse', 'analysis', analysis.id, {
                'filename': filename,
                'parse_mode': parse_mode,
                'processing_time': processing_time,
                'storage_type': storage_type
            })

            # Return results
            return jsonify({
                'success': True,
                'output': result['raw_output'],
                'parsed_data': result['parsed_data'],
                'parse_mode': parse_mode,
                'filename': filename,
                'processing_time': round(processing_time, 2),
                'analysis_id': analysis.id,
                'log_file_id': log_file.id,
                'error': None
            })

        except CancellationException as cancel_error:
            # Parser was cancelled via in-process cancellation
            app.logger.info(f"Analysis {analysis.id} was cancelled by user (in-process)")

            # Clean up Redis keys
            user_analysis_key = f"user:{current_user.id}:current_analysis"
            redis_client.delete(user_analysis_key)

            # Analysis status already updated by cancel endpoint
            # Return cancellation response
            return jsonify({
                'success': False,
                'error': 'Analysis was cancelled by user'
            }), 499  # 499 = Client Closed Request

        except Exception as parse_error:

            # Update analysis status for other errors
            analysis.status = 'failed'
            analysis.completed_at = datetime.utcnow()
            analysis.error_message = str(parse_error)
            db.commit()

            app.logger.error(f"Parse error: {str(parse_error)}\n{traceback.format_exc()}")

            # Log audit
            log_audit(db, current_user.id, 'upload_and_parse', 'analysis', analysis.id, {
                'filename': filename,
                'parse_mode': parse_mode
            }, success=False, error_message=str(parse_error))

            return jsonify({
                'success': False,
                'error': f'Parse error: {str(parse_error)}',
                'output': '',
                'parsed_data': None,
                'parse_mode': parse_mode,
                'filename': filename,
                'analysis_id': analysis.id
            }), 500

    except Exception as e:
        db.rollback()
        app.logger.error(f"Upload error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'An error occurred during file upload. Please try again.'}), 500


@app.route('/api/cancel', methods=['POST'])
@token_required
def cancel_analysis(current_user, db):
    """Cancel the user's currently running analysis using in-process cancellation"""
    try:
        # Get user's current analysis ID from Redis
        user_analysis_key = f"user:{current_user.id}:current_analysis"
        analysis_id_str = redis_client.get(user_analysis_key)

        app.logger.info(f"Cancel request from user {current_user.username}, analysis: {analysis_id_str}")

        if not analysis_id_str:
            return jsonify({'message': 'No running analysis found for user'}), 200

        analysis_id = int(analysis_id_str)

        # Get analysis (must belong to user unless admin)
        query = db.query(Analysis).filter(Analysis.id == analysis_id)
        if not current_user.is_admin():
            query = query.filter(Analysis.user_id == current_user.id)

        analysis = query.first()
        if not analysis:
            # Clean up stale Redis entry
            app.logger.warning(f"Analysis {analysis_id} not found in database")
            redis_client.delete(user_analysis_key)
            return jsonify({'message': 'No running analysis found (stale entry cleaned)'}), 200

        # Check if analysis is running
        if analysis.status != 'running':
            redis_client.delete(user_analysis_key)
            return jsonify({'message': 'Analysis is not running'}), 200

        # Find active parser and cancel it (in-process cancellation)
        parser_key = f"{current_user.id}:{analysis_id}"
        with parsers_lock:
            parser = active_parsers.get(parser_key)

        if parser:
            # Cancel the parser (sets threading.Event, parser will check and stop)
            parser.cancel()
            app.logger.info(f"Sent cancellation signal to parser for analysis {analysis_id}")
        else:
            app.logger.info(f"Parser for analysis {analysis_id} not found (may have already completed)")

        # Update analysis status
        analysis.status = 'cancelled'
        analysis.completed_at = datetime.utcnow()
        analysis.error_message = 'Cancelled by user'
        db.commit()

        # Clean up Redis
        redis_client.delete(user_analysis_key)

        app.logger.info(f"Analysis {analysis_id} cancelled by user {current_user.username}")

        return jsonify({
            'success': True,
            'message': 'Analysis cancelled successfully'
        }), 200

    except Exception as e:
        db.rollback()
        app.logger.error(f"Cancel error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'An error occurred while cancelling analysis.'}), 500


@app.route('/api/analyses', methods=['GET'])
@token_required
def get_analyses(current_user, db):
    """Get user's analysis history"""
    try:
        # Get analyses for current user (not deleted)
        analyses = db.query(Analysis).filter(
            Analysis.user_id == current_user.id,
            Analysis.is_deleted == False
        ).order_by(Analysis.created_at.desc()).all()

        return jsonify({
            'analyses': [{
                'id': a.id,
                'parse_mode': a.parse_mode,
                'session_name': a.session_name,
                'zendesk_case': a.zendesk_case,
                'filename': a.log_file.original_filename if a.log_file else None,
                'storage_type': a.log_file.storage_type if a.log_file else 'local',
                'status': a.status,
                'created_at': a.created_at.isoformat(),
                'completed_at': a.completed_at.isoformat() if a.completed_at else None,
                'processing_time_seconds': a.processing_time_seconds,
                'error_message': a.error_message
            } for a in analyses]
        }), 200

    except Exception as e:
        app.logger.error(f'Failed to get analyses: {str(e)}')
        return jsonify({'error': 'An error occurred while retrieving analyses.'}), 500


@app.route('/api/analyses/<int:analysis_id>', methods=['GET'])
@token_required
def get_analysis(analysis_id, current_user, db):
    """Get specific analysis with results"""
    try:
        # Get analysis (must belong to user unless admin)
        query = db.query(Analysis).filter(Analysis.id == analysis_id)
        if not current_user.is_admin():
            query = query.filter(Analysis.user_id == current_user.id)

        analysis = query.first()
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404

        # Get results
        result = db.query(AnalysisResult).filter(AnalysisResult.analysis_id == analysis_id).first()

        return jsonify({
            'analysis': {
                'id': analysis.id,
                'parse_mode': analysis.parse_mode,
                'session_name': analysis.session_name,
                'zendesk_case': analysis.zendesk_case,
                'filename': analysis.log_file.original_filename if analysis.log_file else None,
                'storage_type': analysis.log_file.storage_type if analysis.log_file else 'local',
                'status': analysis.status,
                'created_at': analysis.created_at.isoformat(),
                'completed_at': analysis.completed_at.isoformat() if analysis.completed_at else None,
                'processing_time_seconds': analysis.processing_time_seconds,
                'error_message': analysis.error_message
            },
            'result': {
                'raw_output': result.raw_output if result else None,
                'parsed_data': result.parsed_data if result else None
            } if result else None
        }), 200

    except Exception as e:
        app.logger.error(f'Failed to get analysis {analysis_id}: {str(e)}')
        return jsonify({'error': 'An error occurred while retrieving analysis.'}), 500


@app.route('/api/analyses/<int:analysis_id>/download', methods=['GET'])
@token_required
def download_log_file(analysis_id, current_user, db):
    """Download the log file associated with an analysis"""
    try:
        # Get analysis (must belong to user unless admin)
        query = db.query(Analysis).filter(Analysis.id == analysis_id)
        if not current_user.is_admin():
            query = query.filter(Analysis.user_id == current_user.id)

        analysis = query.first()
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404

        # Get associated log file
        if not analysis.log_file:
            return jsonify({'error': 'Log file not found'}), 404

        log_file = analysis.log_file

        # Log the download
        log_audit(db, current_user.id, 'download_log_file', 'log_file', log_file.id, {
            'filename': log_file.original_filename,
            'analysis_id': analysis_id,
            'storage_type': log_file.storage_type
        })

        # Handle download based on storage type
        if log_file.storage_type == 's3':
            # Get S3 presigned URL and return it in JSON (avoid CORS issues with redirect)
            try:
                storage_service = StorageFactory.get_storage_service()
                if storage_service.get_storage_type() == 's3':
                    presigned_url = storage_service.get_file(log_file.file_path, log_file.original_filename)
                    if presigned_url:
                        # Return URL in JSON for client-side redirect (avoids CORS)
                        return jsonify({
                            'download_url': presigned_url,
                            'filename': log_file.original_filename,
                            'storage_type': 's3'
                        }), 200
                    else:
                        return jsonify({'error': 'Failed to generate download URL'}), 500
                else:
                    return jsonify({'error': 'S3 storage not available'}), 503
            except Exception as e:
                app.logger.error(f"S3 download error: {str(e)}")
                return jsonify({'error': 'Failed to generate download URL from S3'}), 500
        else:
            # Local storage - check if file exists and send
            if not os.path.exists(log_file.file_path):
                return jsonify({'error': 'Physical file not found'}), 404

            return send_file(
                log_file.file_path,
                as_attachment=True,
                download_name=log_file.original_filename
            )

    except Exception as e:
        app.logger.error(f'Failed to download file for analysis {analysis_id}: {str(e)}')
        return jsonify({'error': 'An error occurred while downloading file.'}), 500


@app.route('/api/analyses/search', methods=['GET'])
@token_required
def search_analyses(current_user, db):
    """Search analyses by session name or Zendesk case"""
    try:
        search_query = request.args.get('q', '').strip()

        if not search_query:
            return jsonify({'analyses': []}), 200

        # Search by session_name or zendesk_case (case-insensitive partial match)
        # Using string concatenation instead of f-string to prevent SQL injection
        search_pattern = '%' + search_query + '%'
        analyses = db.query(Analysis).filter(
            Analysis.user_id == current_user.id,
            Analysis.is_deleted == False,
            (Analysis.session_name.ilike(search_pattern) |
             Analysis.zendesk_case.ilike(search_pattern))
        ).order_by(Analysis.created_at.desc()).all()

        return jsonify({
            'analyses': [{
                'id': a.id,
                'parse_mode': a.parse_mode,
                'session_name': a.session_name,
                'zendesk_case': a.zendesk_case,
                'filename': a.log_file.original_filename if a.log_file else None,
                'storage_type': a.log_file.storage_type if a.log_file else 'local',
                'status': a.status,
                'created_at': a.created_at.isoformat(),
                'completed_at': a.completed_at.isoformat() if a.completed_at else None,
                'processing_time_seconds': a.processing_time_seconds,
                'error_message': a.error_message
            } for a in analyses]
        }), 200

    except Exception as e:
        app.logger.error(f'Failed to search analyses: {str(e)}')
        return jsonify({'error': 'An error occurred while searching analyses.'}), 500


def init_parsers_in_db():
    """Initialize parser records in database"""
    db = SessionLocal()
    try:
        for mode in PARSE_MODES:
            existing = db.query(Parser).filter(Parser.parser_key == mode['value']).first()
            if not existing:
                parser = Parser(
                    parser_key=mode['value'],
                    name=mode['label'],
                    description=mode.get('description', ''),
                    is_enabled=True,
                    is_available_to_users=True,
                    is_admin_only=False
                )
                db.add(parser)
        db.commit()
        print("Initialized parsers in database")
    except Exception as e:
        db.rollback()
        print(f"Error initializing parsers: {e}")
    finally:
        db.close()


if __name__ == '__main__':
    # Initialize database
    print("Initializing database...")
    init_db()
    init_parsers_in_db()
    print("Database initialized")

    app.run(host='0.0.0.0', port=5000, debug=True)
