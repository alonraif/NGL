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
import multiprocessing
from queue import Empty
from parsers import get_parser
from parsers.base import CancellationException
from database import init_db, SessionLocal
from models import User, Parser, LogFile, Analysis, AnalysisResult, SSLConfiguration, Bookmark
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
from archive_filter import ArchiveFilter

app = Flask(__name__)
# Trust 2 proxies in the chain (e.g., CDN + nginx)
# This will properly extract the real client IP from X-Forwarded-For
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=2, x_proto=1, x_host=1, x_port=1)

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


class ProcessParserHandle:
    """Wrapper that provides a cancel() API for multiprocessing processes."""

    def __init__(self, process: multiprocessing.Process):
        self.process = process

    def cancel(self):
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=1)
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
    {'value': 'sessions', 'label': '⭐ Sessions (Recommended First)', 'description': 'Analyze streaming sessions - Run this first, then drill down into specific sessions', 'recommended': True},
    {'value': 'known', 'label': 'Known Errors (Default)', 'description': 'Small set of known errors and events'},
    {'value': 'error', 'label': 'All Errors', 'description': 'Any line containing ERROR'},
    {'value': 'v', 'label': 'Verbose', 'description': 'Include more common errors'},
    {'value': 'all', 'label': 'All Lines', 'description': 'Return all log lines'},
    {'value': 'bw', 'label': 'Bandwidth', 'description': 'Stream bandwidth in CSV format'},
    {'value': 'md-bw', 'label': 'Modem Bandwidth', 'description': 'Modem bandwidth in CSV format'},
    {'value': 'md-db-bw', 'label': 'Data Bridge Bandwidth', 'description': 'Data bridge modem bandwidth'},
    {'value': 'md', 'label': 'Modem Statistics', 'description': 'Detailed modem statistics'},
    {'value': 'id', 'label': 'Device IDs', 'description': 'Boss ID of device and server'},
    {'value': 'memory', 'label': 'Memory Usage', 'description': 'Memory consumption data'},
    {'value': 'grading', 'label': 'Modem Grading', 'description': 'Service level transitions'},
    {'value': 'cpu', 'label': 'CPU Usage', 'description': 'CPU utilization by component'},
    {'value': 'debug', 'label': 'Debug Logs', 'description': 'Debug-level logging output'},
    {'value': 'ffmpeg', 'label': 'FFmpeg Logs', 'description': 'FFmpeg video encoding logs'},
    {'value': 'ffmpegv', 'label': 'FFmpeg Verbose', 'description': 'FFmpeg verbose output'},
    {'value': 'ffmpega', 'label': 'FFmpeg Audio', 'description': 'FFmpeg audio-related logs'},
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
                # Pre-filter archive by time range if dates are specified
                filtered_filepath = filepath
                if begin_date and end_date:
                    try:
                        app.logger.info(f"Pre-filtering archive by time range: {begin_date} to {end_date}")

                        # Parse date strings to datetime objects
                        # Assuming dates are in format: YYYY-MM-DD HH:MM:SS or similar
                        from dateutil import parser as date_parser
                        start_dt = date_parser.parse(begin_date)
                        end_dt = date_parser.parse(end_date)

                        # Apply archive filtering
                        archive_filter = ArchiveFilter(filepath)
                        filtered_filepath = archive_filter.filter_by_time_range(
                            start_time=start_dt,
                            end_time=end_dt,
                            buffer_hours=1  # Keep 1 hour before/after for safety
                        )

                        if filtered_filepath != filepath:
                            app.logger.info(f"Archive filtered successfully. Using: {filtered_filepath}")
                        else:
                            app.logger.info("Archive filtering skipped (not worth overhead)")

                    except Exception as filter_error:
                        app.logger.warning(f"Archive filtering failed: {filter_error}. Using original archive.")
                        filtered_filepath = filepath

                # Process the file using standalone parser (in-process, no subprocess)
                result = parser.process(
                    archive_path=filtered_filepath,
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

            # Clean up filtered temp file if it was created
            if filtered_filepath != filepath and os.path.exists(filtered_filepath):
                try:
                    os.remove(filtered_filepath)
                    app.logger.info(f"Cleaned up filtered archive: {filtered_filepath}")
                except Exception as e:
                    app.logger.warning(f"Failed to clean up filtered archive {filtered_filepath}: {str(e)}")

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

        # Log cancellation
        log_audit(db, current_user.id, 'cancel_analysis', 'analysis', analysis_id, {
            'session_name': analysis.session_name,
            'parse_mode': analysis.parse_mode
        })

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
    """Get user's analysis history with multi-field filtering (includes own analyses + bookmarked analyses)"""
    try:
        # Get filter parameters (same as /api/analyses/all)
        session_name = request.args.get('session_name', '').strip()
        zendesk_case = request.args.get('zendesk_case', '').strip()
        filename = request.args.get('filename', '').strip()
        analysis_id = request.args.get('analysis_id', '').strip()
        status = request.args.get('status', '').strip()
        parser_mode = request.args.get('parser_mode', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()

        from sqlalchemy.orm import joinedload
        from sqlalchemy import or_
        from datetime import datetime, timedelta

        # Get bookmarked analysis IDs for this user
        bookmarked_ids = db.query(Bookmark.analysis_id).filter(
            Bookmark.user_id == current_user.id
        ).all()
        bookmarked_ids = [b[0] for b in bookmarked_ids]

        # Base query: user's own analyses OR bookmarked analyses (not deleted)
        query = db.query(Analysis).outerjoin(
            LogFile, Analysis.log_file_id == LogFile.id
        ).options(
            joinedload(Analysis.log_file)
        ).filter(
            or_(
                Analysis.user_id == current_user.id,
                Analysis.id.in_(bookmarked_ids) if bookmarked_ids else False
            ),
            Analysis.is_deleted == False
        )

        # Apply filters (same logic as /api/analyses/all)
        if session_name:
            query = query.filter(Analysis.session_name.ilike(f'%{session_name}%'))

        if zendesk_case:
            query = query.filter(Analysis.zendesk_case.ilike(f'%{zendesk_case}%'))

        if filename:
            query = query.filter(LogFile.original_filename.ilike(f'%{filename}%'))

        if analysis_id:
            if analysis_id.isdigit():
                query = query.filter(Analysis.id == int(analysis_id))
            else:
                query = query.filter(Analysis.session_name.ilike(f'%{analysis_id}%'))

        if status:
            query = query.filter(Analysis.status == status.lower())

        if parser_mode:
            query = query.filter(Analysis.parse_mode == parser_mode)

        if date_from:
            try:
                date_from_obj = datetime.fromisoformat(date_from)
                query = query.filter(Analysis.created_at >= date_from_obj)
            except ValueError:
                app.logger.warning(f'Invalid date_from format: {date_from}')

        if date_to:
            try:
                date_to_obj = datetime.fromisoformat(date_to)
                date_to_end = date_to_obj + timedelta(days=1)
                query = query.filter(Analysis.created_at < date_to_end)
            except ValueError:
                app.logger.warning(f'Invalid date_to format: {date_to}')

        # Get results
        analyses = query.order_by(Analysis.created_at.desc()).all()

        # Build response with ownership and bookmark information
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
                'error_message': a.error_message,
                'is_drill_down': a.is_drill_down,
                'parent_analysis_id': a.parent_analysis_id,
                'is_own': a.user_id == current_user.id,
                'owner_username': a.user.username if a.user else None
            } for a in analyses]
        }), 200

    except Exception as e:
        app.logger.error(f'Failed to get analyses: {str(e)}')
        return jsonify({'error': 'An error occurred while retrieving analyses.'}), 500


@app.route('/api/analyses/all', methods=['GET'])
@token_required
def get_all_analyses(current_user, db):
    """Get all analyses from all users (shared view) with multi-field filtering"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))

        # Get filter parameters
        session_name = request.args.get('session_name', '').strip()
        owner = request.args.get('owner', '').strip()
        zendesk_case = request.args.get('zendesk_case', '').strip()
        filename = request.args.get('filename', '').strip()
        analysis_id = request.args.get('analysis_id', '').strip()
        status = request.args.get('status', '').strip()
        parser_mode = request.args.get('parser_mode', '').strip()
        date_from = request.args.get('date_from', '').strip()  # ISO format: 2025-10-01
        date_to = request.args.get('date_to', '').strip()

        # Base query: all non-deleted analyses with user relationship loaded
        from sqlalchemy.orm import joinedload
        from datetime import datetime

        # Always join User and LogFile for potential filtering
        query = db.query(Analysis).join(
            User, Analysis.user_id == User.id
        ).outerjoin(
            LogFile, Analysis.log_file_id == LogFile.id
        ).options(
            joinedload(Analysis.user),
            joinedload(Analysis.log_file)
        ).filter(Analysis.is_deleted == False)

        # Apply filters (AND logic - all filters must match)
        if session_name:
            query = query.filter(Analysis.session_name.ilike(f'%{session_name}%'))

        if owner:
            query = query.filter(User.username.ilike(f'%{owner}%'))

        if zendesk_case:
            query = query.filter(Analysis.zendesk_case.ilike(f'%{zendesk_case}%'))

        if filename:
            query = query.filter(LogFile.original_filename.ilike(f'%{filename}%'))

        if analysis_id:
            if analysis_id.isdigit():
                query = query.filter(Analysis.id == int(analysis_id))
            else:
                # If not a number, search in session name as fallback
                query = query.filter(Analysis.session_name.ilike(f'%{analysis_id}%'))

        if status:
            query = query.filter(Analysis.status == status.lower())

        if parser_mode:
            query = query.filter(Analysis.parse_mode == parser_mode)

        if date_from:
            try:
                date_from_obj = datetime.fromisoformat(date_from)
                query = query.filter(Analysis.created_at >= date_from_obj)
            except ValueError:
                app.logger.warning(f'Invalid date_from format: {date_from}')

        if date_to:
            try:
                # Add 1 day to include the entire end date
                date_to_obj = datetime.fromisoformat(date_to)
                from datetime import timedelta
                date_to_end = date_to_obj + timedelta(days=1)
                query = query.filter(Analysis.created_at < date_to_end)
            except ValueError:
                app.logger.warning(f'Invalid date_to format: {date_to}')

        # Get total count before pagination
        total_count = query.count()

        # Apply pagination
        analyses = query.order_by(Analysis.created_at.desc())\
            .offset((page - 1) * per_page)\
            .limit(per_page)\
            .all()

        # Get current user's bookmarks
        bookmarks = {b.analysis_id for b in db.query(Bookmark).filter(Bookmark.user_id == current_user.id).all()}

        # Build response with user info
        analyses_data = []
        for a in analyses:
            try:
                analysis_data = {
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
                    'error_message': a.error_message,
                    'is_drill_down': a.is_drill_down,
                    'parent_analysis_id': a.parent_analysis_id,
                    # Additional fields for shared view
                    'owner_username': a.user.username if a.user else 'Unknown',
                    'owner_id': a.user_id,
                    'is_own': a.user_id == current_user.id,
                    'is_bookmarked': a.id in bookmarks
                }
                analyses_data.append(analysis_data)
            except Exception as item_error:
                app.logger.error(f'Error serializing analysis {a.id}: {str(item_error)}')
                continue

        # Build active filters dict for logging and audit
        active_filters = {k: v for k, v in {
            'session_name': session_name, 'owner': owner, 'zendesk_case': zendesk_case,
            'filename': filename, 'analysis_id': analysis_id, 'status': status,
            'parser_mode': parser_mode, 'date_from': date_from, 'date_to': date_to
        }.items() if v}

        # Log filter usage if any filters active
        if active_filters:
            log_audit(db, current_user.id, 'filter_analyses', 'analysis', None, {
                'filters': active_filters,
                'results_count': total_count,
                'page': page
            })
            app.logger.info(f'Returning {len(analyses_data)} analyses for /api/analyses/all (total: {total_count}, page: {page}, filters: {active_filters})')
        else:
            app.logger.info(f'Returning {len(analyses_data)} analyses for /api/analyses/all (total: {total_count}, page: {page}, no filters)')

        return jsonify({
            'analyses': analyses_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        }), 200

    except Exception as e:
        app.logger.error(f'Failed to get all analyses: {str(e)}')
        return jsonify({'error': 'An error occurred while retrieving analyses.'}), 500


@app.route('/api/bookmarks', methods=['GET'])
@token_required
def get_bookmarks(current_user, db):
    """Get current user's bookmarked analyses"""
    try:
        bookmarks = db.query(Bookmark).filter(
            Bookmark.user_id == current_user.id
        ).order_by(Bookmark.created_at.desc()).all()

        return jsonify({
            'bookmarks': [b.analysis_id for b in bookmarks]
        }), 200

    except Exception as e:
        app.logger.error(f'Failed to get bookmarks: {str(e)}')
        return jsonify({'error': 'An error occurred while retrieving bookmarks.'}), 500


@app.route('/api/bookmarks/<int:analysis_id>', methods=['POST'])
@token_required
def add_bookmark(analysis_id, current_user, db):
    """Add a bookmark for an analysis"""
    try:
        # Check if analysis exists
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404

        # Check if already bookmarked
        existing = db.query(Bookmark).filter(
            Bookmark.user_id == current_user.id,
            Bookmark.analysis_id == analysis_id
        ).first()

        if existing:
            return jsonify({'message': 'Already bookmarked'}), 200

        # Create bookmark
        bookmark = Bookmark(
            user_id=current_user.id,
            analysis_id=analysis_id
        )
        db.add(bookmark)
        db.commit()

        # Log audit
        log_audit(db, current_user.id, 'bookmark_analysis', 'analysis', analysis_id, {
            'session_name': analysis.session_name,
            'owner_username': analysis.user.username
        })

        return jsonify({
            'success': True,
            'message': 'Bookmark added successfully'
        }), 201

    except Exception as e:
        db.rollback()
        app.logger.error(f'Failed to add bookmark: {str(e)}')
        return jsonify({'error': 'An error occurred while adding bookmark.'}), 500


@app.route('/api/bookmarks/<int:analysis_id>', methods=['DELETE'])
@token_required
def remove_bookmark(analysis_id, current_user, db):
    """Remove a bookmark"""
    try:
        # Find and delete bookmark
        bookmark = db.query(Bookmark).filter(
            Bookmark.user_id == current_user.id,
            Bookmark.analysis_id == analysis_id
        ).first()

        if not bookmark:
            return jsonify({'message': 'Bookmark not found'}), 404

        # Get analysis info for audit log
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()

        db.delete(bookmark)
        db.commit()

        # Log audit
        if analysis:
            log_audit(db, current_user.id, 'remove_bookmark', 'analysis', analysis_id, {
                'session_name': analysis.session_name,
                'owner_username': analysis.user.username
            })

        return jsonify({
            'success': True,
            'message': 'Bookmark removed successfully'
        }), 200

    except Exception as e:
        db.rollback()
        app.logger.error(f'Failed to remove bookmark: {str(e)}')
        return jsonify({'error': 'An error occurred while removing bookmark.'}), 500


def _parser_worker(result_queue, analysis_id, parse_mode, archive_path, timezone, begin_date, end_date):
    """Run a parser in a separate process and push the outcome to the parent."""
    job_start = time.time()
    filtered_filepath = None
    try:
        # Pre-filter archive by time range if dates are specified
        filtered_archive_path = archive_path
        if begin_date and end_date:
            try:
                app.logger.info(f"Worker {analysis_id}: Pre-filtering archive by time range: {begin_date} to {end_date}")

                # Parse date strings to datetime objects
                from dateutil import parser as date_parser
                start_dt = date_parser.parse(begin_date)
                end_dt = date_parser.parse(end_date)

                # Apply archive filtering
                archive_filter = ArchiveFilter(archive_path)
                filtered_archive_path = archive_filter.filter_by_time_range(
                    start_time=start_dt,
                    end_time=end_dt,
                    buffer_hours=1  # Keep 1 hour before/after for safety
                )

                if filtered_archive_path != archive_path:
                    filtered_filepath = filtered_archive_path
                    app.logger.info(f"Worker {analysis_id}: Archive filtered successfully. Using: {filtered_archive_path}")
                else:
                    app.logger.info(f"Worker {analysis_id}: Archive filtering skipped (not worth overhead)")

            except Exception as filter_error:
                app.logger.warning(f"Worker {analysis_id}: Archive filtering failed: {filter_error}. Using original archive.")
                filtered_archive_path = archive_path

        parser = get_parser(parse_mode)
        result = parser.process(
            archive_path=filtered_archive_path,
            timezone=timezone,
            begin_date=begin_date,
            end_date=end_date
        )

        # Clean up filtered temp file if it was created
        if filtered_filepath and os.path.exists(filtered_filepath):
            try:
                os.remove(filtered_filepath)
                app.logger.info(f"Worker {analysis_id}: Cleaned up filtered archive: {filtered_filepath}")
            except Exception as e:
                app.logger.warning(f"Worker {analysis_id}: Failed to clean up filtered archive: {e}")

        result_queue.put({
            'analysis_id': analysis_id,
            'parse_mode': parse_mode,
            'status': 'completed',
            'result': result,
            'duration': time.time() - job_start
        })
    except CancellationException:
        # Clean up filtered temp file on cancellation
        if filtered_filepath and os.path.exists(filtered_filepath):
            try:
                os.remove(filtered_filepath)
            except Exception:
                pass

        result_queue.put({
            'analysis_id': analysis_id,
            'parse_mode': parse_mode,
            'status': 'cancelled',
            'error': 'Analysis cancelled by user',
            'duration': time.time() - job_start
        })
    except Exception as exc:
        # Clean up filtered temp file on error
        if filtered_filepath and os.path.exists(filtered_filepath):
            try:
                os.remove(filtered_filepath)
            except Exception:
                pass

        result_queue.put({
            'analysis_id': analysis_id,
            'parse_mode': parse_mode,
            'status': 'failed',
            'error': str(exc),
            'traceback': traceback.format_exc(),
            'duration': time.time() - job_start
        })

def _process_drilldown_async(analysis_jobs, filepath, timezone, session_start, session_end, user_id, username, parent_analysis_id, session_name, zendesk_case, storage_type):
    """Run drill-down analyses in background processes and update results asynchronously."""
    ctx = multiprocessing.get_context('spawn')
    result_queue = ctx.Queue()
    job_map = {}
    pending_ids = set()
    outcomes_by_id = {}
    db_session = SessionLocal()
    successes = []
    failures = []

    try:
        analysis_ids = [job['analysis_id'] for job in analysis_jobs]
        if not analysis_ids:
            app.logger.info('No drill-down analyses requested; nothing to process.')
            return

        analyses = db_session.query(Analysis).filter(Analysis.id.in_(analysis_ids)).all()
        analysis_by_id = {analysis.id: analysis for analysis in analyses}
        if not analysis_by_id:
            app.logger.warning('Drill-down worker could not find analyses for IDs: %s', analysis_ids)
            return

        for job in analysis_jobs:
            analysis = analysis_by_id.get(job['analysis_id'])
            if not analysis:
                continue

            parse_mode = job['parse_mode']
            job_archive_path = filepath
            try:
                unique_name = f"{analysis.id}_{os.path.basename(filepath)}"
                job_archive_path = os.path.join(TEMP_FOLDER, unique_name)
                if os.path.exists(job_archive_path):
                    if os.path.islink(job_archive_path):
                        os.unlink(job_archive_path)
                    else:
                        os.remove(job_archive_path)
                os.symlink(filepath, job_archive_path)
            except Exception:
                job_archive_path = filepath

            process = ctx.Process(
                target=_parser_worker,
                args=(
                    result_queue,
                    analysis.id,
                    parse_mode,
                    job_archive_path,
                    timezone,
                    session_start,
                    session_end
                )
            )
            process.start()

            parser_key = f"{user_id}:{analysis.id}"
            with parsers_lock:
                active_parsers[parser_key] = ProcessParserHandle(process)

            job_map[analysis.id] = {
                'analysis': analysis,
                'parse_mode': parse_mode,
                'process': process,
                'parser_key': parser_key,
                'archive_path': job_archive_path
            }
            pending_ids.add(analysis.id)

            app.logger.info(
                f"Processing drill-down analysis {analysis.id} (PID {process.pid}) in {parse_mode} mode for user {username}"
            )

        while pending_ids:
            try:
                outcome = result_queue.get(timeout=0.5)
                if outcome:
                    analysis_id = outcome.get('analysis_id')
                    if analysis_id in pending_ids:
                        outcomes_by_id[analysis_id] = outcome
                        pending_ids.remove(analysis_id)
            except Empty:
                pass
            except Exception as queue_error:
                app.logger.warning(f'Drill-down worker queue error: {queue_error}')

            for analysis_id in list(pending_ids):
                process = job_map[analysis_id]['process']
                if process.is_alive():
                    continue

                exit_code = process.exitcode
                if exit_code in (-signal.SIGTERM, -signal.SIGKILL):
                    status = 'cancelled'
                    error_message = 'Analysis cancelled by user'
                elif exit_code == 0:
                    status = 'failed'
                    error_message = 'Parser process exited without returning a result'
                else:
                    status = 'failed'
                    error_message = f'Parser process exited with code {exit_code}'

                outcomes_by_id[analysis_id] = {
                    'analysis_id': analysis_id,
                    'parse_mode': job_map[analysis_id]['parse_mode'],
                    'status': status,
                    'error': error_message,
                    'duration': 0
                }
                pending_ids.remove(analysis_id)

            if pending_ids:
                time.sleep(0.05)

        for analysis_id, job_info in job_map.items():
            process = job_info['process']
            try:
                process.join()
            except Exception:
                pass
            try:
                process.close()
            except Exception:
                pass

            with parsers_lock:
                active_parsers.pop(job_info['parser_key'], None)

            outcome = outcomes_by_id.get(analysis_id, {
                'analysis_id': analysis_id,
                'parse_mode': job_info['parse_mode'],
                'status': 'failed',
                'error': 'Unknown error',
                'duration': 0
            })

            analysis = job_info['analysis']
            duration = outcome.get('duration', 0)
            analysis.completed_at = datetime.utcnow()
            analysis.processing_time_seconds = int(duration)
            status = outcome.get('status')

            try:
                if status == 'completed':
                    result = outcome['result']
                    analysis.status = 'completed'
                    analysis.error_message = None

                    analysis_result = AnalysisResult(
                        analysis_id=analysis.id,
                        raw_output=result['raw_output'],
                        parsed_data=result['parsed_data']
                    )
                    db_session.add(analysis_result)

                    successes.append({
                        'parse_mode': job_info['parse_mode'],
                        'analysis_id': analysis.id,
                        'processing_time': round(duration, 2)
                    })

                    app.logger.info(f"Drill-down analysis {analysis.id} completed successfully")
                elif status == 'cancelled':
                    analysis.status = 'cancelled'
                    error_message = outcome.get('error', 'Analysis cancelled by user')
                    analysis.error_message = error_message
                    failures.append({
                        'parse_mode': job_info['parse_mode'],
                        'error': error_message,
                        'status': 'cancelled'
                    })
                    app.logger.info(f"Drill-down analysis {analysis.id} was cancelled")
                else:
                    analysis.status = 'failed'
                    error_message = outcome.get('error', 'Unknown error')
                    analysis.error_message = error_message
                    failures.append({
                        'parse_mode': job_info['parse_mode'],
                        'error': error_message,
                        'status': 'failed'
                    })
                    trace = outcome.get('traceback')
                    if trace:
                        app.logger.error(f"Drill-down analysis {analysis.id} failed: {error_message}\n{trace}")
                    else:
                        app.logger.error(f"Drill-down analysis {analysis.id} failed: {error_message}")

                db_session.commit()
            except Exception as commit_error:
                db_session.rollback()
                app.logger.error(
                    f"Failed to finalize drill-down analysis {analysis_id}: {commit_error}\n{traceback.format_exc()}"
                )

        try:
            log_audit(db_session, user_id, 'session_drill_down', 'analysis', parent_analysis_id, {
                'session_start': session_start,
                'session_end': session_end,
                'parse_modes': [job['parse_mode'] for job in analysis_jobs],
                'successful': len(successes),
                'failed': len(failures),
                'session_name': session_name,
                'zendesk_case': zendesk_case
            })
            db_session.commit()
        except Exception as audit_error:
            db_session.rollback()
            app.logger.error(f"Failed to log drill-down audit record: {audit_error}")

    except Exception as exc:
        db_session.rollback()
        app.logger.error(f"Drill-down background worker error: {exc}\n{traceback.format_exc()}")
    finally:
        try:
            result_queue.close()
            result_queue.join_thread()
        except Exception:
            pass

        for job_info in job_map.values():
            archive_path = job_info.get('archive_path')
            if archive_path and archive_path != filepath:
                try:
                    if os.path.islink(archive_path):
                        os.unlink(archive_path)
                    elif archive_path.startswith(TEMP_FOLDER) and os.path.exists(archive_path):
                        os.remove(archive_path)
                except Exception:
                    pass

        if storage_type == 's3' and os.path.exists(filepath):
            try:
                os.remove(filepath)
                app.logger.info(f"Cleaned up temporary file: {filepath}")
            except Exception as cleanup_error:
                app.logger.warning(f"Failed to clean up temp file {filepath}: {cleanup_error}")

        db_session.close()
@app.route('/api/analyses/<int:analysis_id>', methods=['GET'])
@token_required
def get_analysis(analysis_id, current_user, db):
    """Get specific analysis with results (any authenticated user can view)"""
    try:
        # Get analysis (any authenticated user can view)
        analysis = db.query(Analysis).filter(
            Analysis.id == analysis_id,
            Analysis.is_deleted == False
        ).first()

        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404

        # Log viewing analysis result (include owner info if viewing others' analysis)
        is_viewing_own = analysis.user_id == current_user.id
        log_audit(db, current_user.id, 'view_analysis', 'analysis', analysis_id, {
            'session_name': analysis.session_name,
            'parse_mode': analysis.parse_mode,
            'is_viewing_own': is_viewing_own,
            'owner_username': analysis.user.username if not is_viewing_own else None
        })

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
                'error_message': analysis.error_message,
                'is_drill_down': analysis.is_drill_down,
                'parent_analysis_id': analysis.parent_analysis_id,
                'timezone': analysis.timezone,
                'begin_date': analysis.begin_date,
                'end_date': analysis.end_date,
                'log_file_id': analysis.log_file_id
            },
            'result': {
                'raw_output': result.raw_output if result else None,
                'parsed_data': result.parsed_data if result else None
            } if result else None
        }), 200

    except Exception as e:
        app.logger.error(f'Failed to get analysis {analysis_id}: {str(e)}')
        return jsonify({'error': 'An error occurred while retrieving analysis.'}), 500


def _parser_worker(result_queue, analysis_id, parse_mode, archive_path, timezone, begin_date, end_date):
    """Run a parser in a separate process and push the outcome to the parent."""
    job_start = time.time()
    filtered_filepath = None
    try:
        # Pre-filter archive by time range if dates are specified
        filtered_archive_path = archive_path
        if begin_date and end_date:
            try:
                app.logger.info(f"Worker {analysis_id}: Pre-filtering archive by time range: {begin_date} to {end_date}")

                # Parse date strings to datetime objects
                from dateutil import parser as date_parser
                start_dt = date_parser.parse(begin_date)
                end_dt = date_parser.parse(end_date)

                # Apply archive filtering
                archive_filter = ArchiveFilter(archive_path)
                filtered_archive_path = archive_filter.filter_by_time_range(
                    start_time=start_dt,
                    end_time=end_dt,
                    buffer_hours=1  # Keep 1 hour before/after for safety
                )

                if filtered_archive_path != archive_path:
                    filtered_filepath = filtered_archive_path
                    app.logger.info(f"Worker {analysis_id}: Archive filtered successfully. Using: {filtered_archive_path}")
                else:
                    app.logger.info(f"Worker {analysis_id}: Archive filtering skipped (not worth overhead)")

            except Exception as filter_error:
                app.logger.warning(f"Worker {analysis_id}: Archive filtering failed: {filter_error}. Using original archive.")
                filtered_archive_path = archive_path

        parser = get_parser(parse_mode)
        result = parser.process(
            archive_path=filtered_archive_path,
            timezone=timezone,
            begin_date=begin_date,
            end_date=end_date
        )

        # Clean up filtered temp file if it was created
        if filtered_filepath and os.path.exists(filtered_filepath):
            try:
                os.remove(filtered_filepath)
                app.logger.info(f"Worker {analysis_id}: Cleaned up filtered archive: {filtered_filepath}")
            except Exception as e:
                app.logger.warning(f"Worker {analysis_id}: Failed to clean up filtered archive: {e}")

        result_queue.put({
            'analysis_id': analysis_id,
            'parse_mode': parse_mode,
            'status': 'completed',
            'result': result,
            'duration': time.time() - job_start
        })
    except CancellationException:
        # Clean up filtered temp file on cancellation
        if filtered_filepath and os.path.exists(filtered_filepath):
            try:
                os.remove(filtered_filepath)
            except Exception:
                pass

        result_queue.put({
            'analysis_id': analysis_id,
            'parse_mode': parse_mode,
            'status': 'cancelled',
            'error': 'Analysis cancelled by user',
            'duration': time.time() - job_start
        })
    except Exception as exc:
        # Clean up filtered temp file on error
        if filtered_filepath and os.path.exists(filtered_filepath):
            try:
                os.remove(filtered_filepath)
            except Exception:
                pass

        result_queue.put({
            'analysis_id': analysis_id,
            'parse_mode': parse_mode,
            'status': 'failed',
            'error': str(exc),
            'traceback': traceback.format_exc(),
            'duration': time.time() - job_start
        })


@app.route('/api/analyses/from-session', methods=['POST'])
@token_required
def create_analysis_from_session(current_user, db):
    """Create new analysis from existing session time range (drill-down)."""
    try:
        data = request.get_json()

        required_fields = ['parent_analysis_id', 'log_file_id', 'session_start', 'parse_modes']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'})

        parent_analysis_id = data['parent_analysis_id']
        log_file_id = data['log_file_id']
        session_start = data['session_start']
        session_end = data.get('session_end')
        parse_modes = data['parse_modes']
        timezone = data.get('timezone', 'UTC')
        session_name = data.get('session_name', '')
        zendesk_case = data.get('zendesk_case', '')

        if not isinstance(parse_modes, list) or not parse_modes:
            return jsonify({'error': 'parse_modes must be a non-empty list'}), 400

        if not session_end:
            return jsonify({'error': 'session_end is required for incomplete sessions'}), 400

        app.logger.info(
            "Drill-down request parent_analysis_id=%s log_file_id=%s modes=%s",
            parent_analysis_id,
            log_file_id,
            parse_modes,
        )

        parent_query = db.query(Analysis).filter(Analysis.id == parent_analysis_id)
        if not current_user.is_admin():
            parent_query = parent_query.filter(Analysis.user_id == current_user.id)
        parent_analysis = parent_query.first()
        if not parent_analysis:
            return jsonify({'error': 'Parent analysis not found'}), 404

        log_file_query = db.query(LogFile).filter(LogFile.id == log_file_id)
        if not current_user.is_admin():
            log_file_query = log_file_query.filter(LogFile.user_id == current_user.id)
        log_file = log_file_query.first()
        if not log_file:
            return jsonify({'error': 'Log file not found'}), 404
        if log_file.is_deleted:
            return jsonify({'error': 'Log file has been deleted'}), 410

        storage_service = StorageFactory.get_storage_service()
        if log_file.storage_type == 's3':
            temp_fd, filepath = tempfile.mkstemp(suffix='.tmp', dir=TEMP_FOLDER)
            os.close(temp_fd)
            try:
                if hasattr(storage_service, 's3_client'):
                    storage_service.s3_client.download_file(
                        storage_service.config.bucket_name,
                        log_file.stored_filename,
                        filepath
                    )
                    app.logger.info("Downloaded S3 file %s to %s", log_file.stored_filename, filepath)
                else:
                    raise Exception("S3 storage not properly configured")
            except Exception as err:
                app.logger.error("Failed to download file from S3: %s", err)
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({'error': 'Failed to retrieve log file from storage'}), 500
        else:
            filepath = log_file.file_path

        if not os.path.exists(filepath):
            return jsonify({'error': 'Log file not found on disk'}), 404

        analysis_jobs = []
        for parse_mode in parse_modes:
            parser_obj = db.query(Parser).filter(Parser.parser_key == parse_mode).first()
            analysis = Analysis(
                user_id=current_user.id,
                log_file_id=log_file.id,
                parser_id=parser_obj.id if parser_obj else None,
                parse_mode=parse_mode,
                session_name=session_name if session_name else parent_analysis.session_name,
                zendesk_case=zendesk_case if zendesk_case else parent_analysis.zendesk_case,
                timezone=timezone,
                begin_date=session_start,
                end_date=session_end,
                status='running',
                started_at=datetime.utcnow(),
                retention_days=int(os.getenv('UPLOAD_RETENTION_DAYS', '30')),
                parent_analysis_id=parent_analysis_id,
                is_drill_down=True
            )
            analysis.expires_at = datetime.utcnow() + timedelta(days=analysis.retention_days)
            db.add(analysis)
            db.flush()

            analysis_jobs.append({
                'analysis_id': analysis.id,
                'parse_mode': parse_mode
            })

        db.commit()

        log_audit(db, current_user.id, 'session_drill_down', 'analysis', parent_analysis_id, {
            'session_start': session_start,
            'session_end': session_end,
            'parse_modes': parse_modes,
            'status': 'started'
        })

        processing_thread = threading.Thread(
            target=_process_drilldown_async,
            args=(
                analysis_jobs,
                filepath,
                timezone,
                session_start,
                session_end,
                current_user.id,
                current_user.username,
                parent_analysis_id,
                session_name,
                zendesk_case,
                log_file.storage_type
            ),
            daemon=True
        )
        processing_thread.start()

        return jsonify({
            'success': True,
            'message': 'Drill-down analyses started',
            'analysis_ids': [job['analysis_id'] for job in analysis_jobs],
            'analyses': analysis_jobs,
            'parent_analysis_id': parent_analysis_id
        }), 202

    except Exception as err:
        db.rollback()
        app.logger.error("Drill-down analysis error: %s\n%s", err, traceback.format_exc())
        return jsonify({'error': 'An error occurred during drill-down analysis. Please try again.'}), 500


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

        # Log search query
        log_audit(db, current_user.id, 'search_analyses', 'analysis', None, {
            'query': search_query,
            'results_count': len(analyses)
        })

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
                'error_message': a.error_message,
                'is_drill_down': a.is_drill_down,
                'parent_analysis_id': a.parent_analysis_id
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
