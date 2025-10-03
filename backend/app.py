#!/usr/bin/env python3
"""
NGL - Next Gen LULA Backend
Modular backend using new parser architecture with database support
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import time
import traceback
from parsers import get_parser
from database import init_db, SessionLocal
from models import User, Parser, LogFile, Analysis, AnalysisResult
from auth import token_required, log_audit
from auth_routes import auth_bp
from admin_routes import admin_bp
from datetime import datetime, timedelta
import hashlib

app = Flask(__name__)
CORS(app)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(admin_bp, url_prefix='/api/admin')

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

def calculate_file_hash(filepath):
    """Calculate SHA256 hash of file"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


@app.route('/api/upload', methods=['POST'])
@token_required
def upload_file(current_user, db):
    """Upload and process log file synchronously (requires authentication)"""
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

        # Check storage quota
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Seek back to start
        file_size_mb = file_size / (1024 * 1024)

        if current_user.storage_used_mb + file_size_mb > current_user.storage_quota_mb:
            return jsonify({'error': 'Storage quota exceeded'}), 400

        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = int(time.time())
        stored_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], stored_filename)
        file.save(filepath)

        # Calculate file hash
        file_hash = calculate_file_hash(filepath)

        # Create log file record
        log_file = LogFile(
            user_id=current_user.id,
            original_filename=filename,
            stored_filename=stored_filename,
            file_path=filepath,
            file_size_bytes=file_size,
            file_hash=file_hash,
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

        app.logger.info(f"Processing {filename} in {parse_mode} mode for user {current_user.username}")

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

            # Log audit
            log_audit(db, current_user.id, 'upload_and_parse', 'analysis', analysis.id, {
                'filename': filename,
                'parse_mode': parse_mode,
                'processing_time': processing_time
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

        except Exception as parse_error:
            # Update analysis status
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
        return jsonify({'error': f'Upload error: {str(e)}'}), 500


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
                'filename': a.log_file.original_filename if a.log_file else None,
                'status': a.status,
                'created_at': a.created_at.isoformat(),
                'completed_at': a.completed_at.isoformat() if a.completed_at else None,
                'processing_time_seconds': a.processing_time_seconds,
                'error_message': a.error_message
            } for a in analyses]
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get analyses: {str(e)}'}), 500


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
                'filename': analysis.log_file.original_filename if analysis.log_file else None,
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
        return jsonify({'error': f'Failed to get analysis: {str(e)}'}), 500


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
