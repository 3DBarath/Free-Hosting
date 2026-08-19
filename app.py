from flask import Flask, request,render_template, send_from_directory, send_file, session, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from zipfile import ZipFile
import os
import re
import time
import datetime
from datetime import timedelta
import shutil
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from flask_session import Session
from dotenv import load_dotenv

load_dotenv()

# Configuration
PORT = 7777
ALLOWED_HOST = 'freehosting.gces.net.in'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, 'projects')
TEMP_DIR = os.path.join(BASE_DIR, 'temp')
VIEWS_DIR = os.path.join(BASE_DIR, 'views')

# PostgreSQL Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'user': os.getenv('DB_USER', 'MessReduction'),
    'password': os.getenv('DB_PASSWORD'),
    'dbname': os.getenv('DB_NAME', 'ziphost')
}

# Hostel student-verification API (used at registration to validate
# registerNo + password against the real student database).
STUDENT_VERIFY_API_URL = os.getenv('STUDENT_VERIFY_API_URL', 'https://hostel-api.gces.net.in/api/auth/verify-details')
STUDENT_VERIFY_API_KEY = os.getenv('STUDENT_VERIFY_API_KEY')

app = Flask(__name__,
            template_folder='views',
            static_folder='views',
            static_url_path='/views')
# Add session lifetime configuration
app.config['PERMANENT_SESSION'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-insecure-key')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = TEMP_DIR
Session(app)

os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

def get_db():
    return psycopg2.connect(**DB_CONFIG)

def verify_student(regno, password):
    """Verify registerNo + password against the hostel student DB.

    Returns True (valid), False (invalid), or None (verification service
    unavailable).
    """
    try:
        resp = requests.post(
            STUDENT_VERIFY_API_URL,
            json={'registerNo': regno, 'password': password},
            headers={'X-API-Key': STUDENT_VERIFY_API_KEY},
            timeout=10
        )
        text = resp.text.strip().lower()
        if text == 'true':
            return True
        try:
            return bool(resp.json().get('success'))
        except Exception:
            return False
    except requests.RequestException as e:
        app.logger.error(f"Student verification error: {str(e)}")
        return None

# Auth Routes
@app.route('/register', methods=['POST'])
def register():
    regno = request.form['regno']
    password = request.form['password']

    # Validate REGNO format
    if not regno.startswith('8301') or len(regno) != 12 or not regno.isdigit():
        return jsonify(error="Invalid registration number format"), 400

    # Verify registerNo + password against the hostel student database
    verified = verify_student(regno, password)
    if verified is None:
        return jsonify(error="Verification service unavailable, please try again"), 503
    if not verified:
        return jsonify(error="Invalid registration number or password"), 401

    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Check if already registered
        cursor.execute("SELECT id FROM users WHERE regno = %s", (regno,))
        if cursor.fetchone():
            return jsonify(error="Registration number already exists"), 409
        hashed_password = generate_password_hash(password)
        # Create user
        cursor.execute("""
            INSERT INTO users (regno, password_hash)
            VALUES (%s, %s)
        """, (regno, hashed_password))
        conn.commit()

        return jsonify(success=True)

    except psycopg2.Error as e:
        return jsonify(error="Database error"), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    regno = request.form['regno']
    password = request.form['password']

    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM users WHERE regno = %s", (regno,))
    user = cursor.fetchone()

    try:
        if user and check_password_hash(user['password_hash'], password):
            # Known user, stored password matches.
            session['user_id'] = user['id']
            session['regno'] = regno
            session['is_admin'] = user.get('is_admin', False)
            log_activity(user['id'], 'login', description=f"User logged in", request=request)
            return jsonify(success=True)

        if not user:
            # Unknown user: verify against the hostel DB and auto-create on
            # success, so a first login doubles as registration.
            verified = verify_student(regno, password)
            if verified is None:
                return jsonify(error="Verification service unavailable, please try again"), 503
            if verified:
                hashed_password = generate_password_hash(password)
                # Guard against a concurrent registration racing this insert.
                try:
                    cursor.execute(
                        "INSERT INTO users (regno, password_hash) VALUES (%s, %s) RETURNING id",
                        (regno, hashed_password)
                    )
                    new_id = cursor.fetchone()['id']
                except Exception:
                    cursor.rollback()
                    cursor.execute("SELECT id FROM users WHERE regno = %s", (regno,))
                    new_id = user = cursor.fetchone()
                    if not new_id:
                        return jsonify(error="Invalid credentials"), 401
                    new_id = new_id['id']
                conn.commit()
                session['user_id'] = new_id
                session['regno'] = regno
                session['is_admin'] = False
                log_activity(new_id, 'login', description="User auto-created on first login", request=request)
                return jsonify(success=True, created=True)

        # Known user but wrong password, or unknown user failed verification.
        return jsonify(error="Invalid credentials"), 401
    finally:
        cursor.close()
        conn.close()

@app.route('/logout')
def logout():
    log_activity(session['user_id'], 'logout', description="User logged out", request=request)
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/api/activity-logs')
def get_activity_logs():
    if 'user_id' not in session:
        return jsonify(error="Unauthorized"), 401
    
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Get parameters
        page = request.args.get('page', 1, type=int)
        action_type = request.args.get('action_type', 'all')
        regno_filter = request.args.get('regno', '')
        per_page = 10
        offset = (page - 1) * per_page

        # Check admin status
        cursor.execute("SELECT is_admin FROM users WHERE id = %s", (session['user_id'],))
        user = cursor.fetchone()
        if not user:
            return jsonify(error="User not found"), 404
            
        is_admin = user.get('is_admin', False)

        # Build base query
        query = """
            SELECT al.*, u.regno, COUNT(*) OVER() AS total_count
            FROM activity_logs al
            JOIN users u ON al.user_id = u.id
        """
        where_clauses = []
        params = []

        # Apply filters
        if not is_admin:
            where_clauses.append("al.user_id = %s")
            params.append(session['user_id'])
        
        if action_type != 'all':
            where_clauses.append("al.action_type = %s")
            params.append(action_type)
            
        if regno_filter and is_admin:
            where_clauses.append("u.regno LIKE %s")
            params.append(f"%{regno_filter}%")

        # Add WHERE clause if needed
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        # Add sorting and pagination
        query += " ORDER BY al.created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])

        # Execute query
        cursor.execute(query, params)
        logs = cursor.fetchall()

        # Get total results from the window function column
        total = logs[0]['total_count'] if logs else 0
        has_more = (page * per_page) < total

        return jsonify(
            logs=logs,
            has_more=has_more,
            is_admin=is_admin
        )

    except Exception as e:
        app.logger.error(f"Activity log error: {str(e)}")
        return jsonify(error="Server error"), 500
    finally:
        cursor.close()
        conn.close()
        
def log_activity(user_id, action_type, table_affected=None, record_id=None, description=None, request=None):
    """Log user activity to the database"""
    try:
        app.logger.info(f"Attempting to log activity: {action_type} for user {user_id}")
        
        ip_address = request.remote_addr if request else None
        user_agent = request.headers.get('User-Agent') if request else None
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO activity_logs 
            (user_id, action_type, table_affected, record_id, description, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id, 
            action_type, 
            table_affected, 
            record_id, 
            description, 
            ip_address, 
            user_agent
        ))
        conn.commit()
        cursor.close()
        app.logger.info(f"Successfully logged activity: {action_type} for user {user_id}")
        
    except Exception as e:
        app.logger.error(f"Failed to log activity: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()
            
@app.route('/upload', methods=['POST'])
def upload_zip():
    if 'user_id' not in session or 'regno' not in session:
        return jsonify(error="Session expired. Please login again"), 401

    try:
        # Verify user exists
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id FROM users WHERE id = %s", (session['user_id'],))
        user = cursor.fetchone()
        cursor.close()
        
        if not user:
            session.clear()
            return jsonify(error="User not found. Please login again"), 401

        # Get project name from form data
        project_name = request.form.get('projectName')
        if not project_name:
            return jsonify(error="Project name required"), 400

        # Validate project name format
        if not re.match(r'^[\w-]{3,50}$', project_name):
            return jsonify(error="Invalid project name (3-50 chars, letters/numbers/-/_ only)"), 400

        # Check name availability
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM uploads WHERE user_id = %s AND filename = %s",
            (session['user_id'], f"{project_name}.zip")
        )
        if cursor.fetchone():
            return jsonify(error="Project name already exists"), 409
        cursor.close()

        # Process file upload
        if 'zipfile' not in request.files:
            return jsonify(error="No file uploaded"), 400
            
        file = request.files['zipfile']
        if not file.filename.endswith('.zip'):
            return jsonify(error="Only ZIP files allowed"), 400

        # Generate unique folder name
        regno = session['regno']
        timestamp = int(time.time())
        extract_path = os.path.join(PROJECTS_DIR,regno,project_name)

        # Save and process ZIP file
        # Save and rename ZIP to project_name.zip
        original_name = secure_filename(file.filename)
        filename = secure_filename(f"{project_name}.zip")
        temp_path = os.path.join(TEMP_DIR, filename)
        file.save(temp_path)

        try:
            with ZipFile(temp_path, 'r') as zip_ref:
                # Security checks
                for entry in zip_ref.namelist():
                    if any(x in entry for x in ['..', '.env', 'node_modules']):
                        raise ValueError(f"Forbidden file: {entry}")
                
                # Extract to unique folder
                os.makedirs(extract_path, exist_ok=True)
                # Flatten ZIP extraction: remove top-level folder if present
                for member in zip_ref.namelist():
                    member_path = os.path.normpath(member)

                    if any(x in member_path for x in ['..', '.env', 'node_modules']):
                        raise ValueError(f"Forbidden file: {member_path}")

                    if member_path.endswith('/'):
                        continue  # Skip folders, they'll be created with files

                    # Remove top folder if exists (flatten)
                    parts = member_path.split(os.sep)
                    if len(parts) > 1:
                        stripped_path = os.path.join(*parts[1:])
                    else:
                        stripped_path = parts[0]

                    # Full target path
                    target_file_path = os.path.join(extract_path, stripped_path)
                    os.makedirs(os.path.dirname(target_file_path), exist_ok=True)

                    with zip_ref.open(member) as source, open(target_file_path, 'wb') as target:
                        shutil.copyfileobj(source, target)


            # Store in database
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            project_url = f"/projects/{regno}/{project_name}/"
            cursor.execute(
                "INSERT INTO uploads (user_id, filename, project_folder,link) VALUES (%s, %s, %s,%s) RETURNING id",
                (session['user_id'], filename, project_name,f"https://{request.host}{project_url}")
            )
            new_id = cursor.fetchone()['id']
            conn.commit()
            cursor.close()


            log_activity(
            session['user_id'],
            'upload',
            table_affected='uploads',
            record_id=new_id,
            description=f"Uploaded project: {project_name}",
            request=request)

            return jsonify(
                success=True,
                url=project_url,
                viewUrl=f"https://{request.host}{project_url}",
            )

        except Exception as e:
            # Cleanup on error
            if os.path.exists(extract_path):
                shutil.rmtree(extract_path)
            raise e

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        log_activity(
            session.get('user_id'),
            'upload',
            description=f"Upload failed: {str(e)}",
            request=request
        )
        return jsonify(error=str(e)), 500
    finally:
        conn.close()
# Add to your Flask app
@app.route('/api/delete-project/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    if 'user_id' not in session:
        return jsonify(error="Unauthorized"), 401

    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verify ownership
        cursor.execute("""
            SELECT project_folder 
            FROM uploads 
            WHERE id = %s AND user_id = %s
        """, (project_id, session['user_id']))
        project = cursor.fetchone()
        
        if not project:
            return jsonify(error="Project not found"), 404

        # Delete from database
        cursor.execute("DELETE FROM uploads WHERE id = %s", (project_id,))
        conn.commit()
        
                # Delete files
        target_path = os.path.join(PROJECTS_DIR, project['project_folder'])
        if os.path.exists(target_path):
            shutil.rmtree(target_path)
        log_activity(
            session['user_id'],
            'delete',
            table_affected='uploads',
            record_id=project_id,
            description=f"Deleted project: {project['project_folder']}",
            request=request
        )
        return jsonify(success=True)
        
    except Exception as e:
        log_activity(
            session.get('user_id'),
            'delete',
            description=f"Delete failed for project {project_id}: {str(e)}",
            request=request
        )
        return jsonify(error=str(e)), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/cleanup/<path:folder>', methods=['POST'])
def cleanup_files(folder):
    if 'user_id' not in session:
        return jsonify(error="Unauthorized"), 401

    try:
        target_path = os.path.join(PROJECTS_DIR,session.get('regno'), folder)
        if os.path.exists(target_path):
            shutil.rmtree(target_path)
        return jsonify(success=True)
    except Exception as e:
        return jsonify(error=str(e)), 500
@app.route('/get_regno')
def get_regno():
    try:
        if 'regno' not in session:
            return jsonify(error="Unauthorized"), 401
        return jsonify(regno=session['regno'])
    except Exception as e:
        app.logger.error(f'Regno fetch error: {str(e)}')
        return jsonify(error="Server error"), 500
    
# Dashboard API
@app.route('/api/dashboard')
def dashboard_data():
    if 'user_id' not in session:
        return jsonify(error="Unauthorized"), 401
    
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT id, filename, project_folder, upload_time, is_pinned
        FROM uploads 
        WHERE user_id = %s 
        ORDER BY is_pinned DESC, upload_time DESC
    """, (session['user_id'],))
    uploads = cursor.fetchall()
    cursor.close()
    conn.close()
    for upload in uploads:
        upload['is_pinned'] = bool(upload['is_pinned'])
    return jsonify(uploads=uploads)

@app.route('/api/check-name')
def check_name():
    if 'user_id' not in session:
        return jsonify(error="Unauthorized"), 401
    
    project_name = request.args.get('name')
    if not project_name:
        return jsonify(error="Name parameter required"), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM uploads WHERE user_id = %s AND filename = %s",
        (session['user_id'], project_name + '.zip')
    )
    exists = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return jsonify(available=not bool(exists))

@app.route('/get_base_url')
def get_base_url():
    return jsonify(base_url=request.host_url)
@app.route('/api/toggle-pin/<int:project_id>', methods=['POST'])
def toggle_pin(project_id):
    if 'user_id' not in session:
        return jsonify(error="Unauthorized"), 401

    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get current pin state
        cursor.execute("""
            SELECT is_pinned FROM uploads 
            WHERE id = %s AND user_id = %s
        """, (project_id, session['user_id']))
        project = cursor.fetchone()
        
        if not project:
            return jsonify(error="Project not found"), 404

        new_state = not project['is_pinned']
        
        # Update pin state
        cursor.execute("""
            UPDATE uploads 
            SET is_pinned = %s 
            WHERE id = %s
        """, (new_state, project_id))
        conn.commit()
        
        log_activity(
            session['user_id'],
            'pin' if new_state else 'unpin',
            description=f"{'Pinned' if new_state else 'Unpinned'} project",
            request=request
        )
        
        return jsonify(success=True, newState=new_state)
        
    except Exception as e:
        return jsonify(error=str(e)), 500
    finally:
        cursor.close()
        conn.close()
@app.before_request
def check_valid_session():
    # Skip validation for public routes
# Allow unauthenticated access to public routes
    if request.path.startswith('/projects/') or request.path in ['/login', '/register', '/home', '/']:
        return

    
    # Check both user_id and regno exist
    if 'user_id' not in session or 'regno' not in session:
        return redirect(url_for('login_page'))
    
    # Verify user exists in database
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT id FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not user:
        session.clear()
        return redirect(url_for('login_page'))

# HTML Routes
# Update home route to redirect to login
@app.route('/')
def index():
    return redirect(url_for('home'))
@app.route('/deploy')
def upload_page():
    check_valid_session()
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('upload.html')

# Add redirects for authenticated users
@app.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register')
def register_page():
    if 'user_id' in session:
        return redirect(url_for('upload_page'))
    return render_template('register.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.before_request
def force_https():
    # TLS is terminated by the Cloudflare tunnel, which forwards plain HTTP
    # to the origin and sets X-Forwarded-Proto. Only enforce https when the
    # proxy reports the client-facing scheme as http. Direct connections to
    # the origin (e.g. localhost dev) have no forwarded header and are served
    # as-is, so local testing doesn't get redirected into a dead https: loop.
    forwarded = request.headers.get('X-Forwarded-Proto')
    if forwarded == 'http':
        return redirect(request.url.replace("http://", "https://", 1))
@app.route('/dash')
def dash():
    return render_template("dashboard.html")

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        session.clear()
        return redirect(url_for('login_page'))
    return render_template('dashboard.html')

# Serve Projects
@app.route('/projects/<path:subpath>')
def serve_projects(subpath):
    # return render_template(subpath)
    return send_from_directory(PROJECTS_DIR,subpath)

@app.route('/projects/<regno>/<project>/')
def serve_project_index(regno, project):
    index_path = os.path.join(PROJECTS_DIR, regno, project, 'index.html')
    if os.path.exists(index_path):
        return send_file(index_path)
    else:
        return "index.html not found", 404

@app.errorhandler(Exception)
def handle_error(e):
    # The frontend always does response.json(); make sure server errors return
    # JSON rather than an HTML error page that breaks the client's parser.
    from werkzeug.exceptions import HTTPException
    app.logger.error(f"Unhandled error: {type(e).__name__}: {e}")
    if isinstance(e, HTTPException):
        return jsonify(error=e.description), e.code
    return jsonify(error="Server error"), 500

if __name__ == '__main__':
    # TLS is terminated at the Cloudflare tunnel edge, so the app runs plain
    # HTTP on this port. Use no_proxy/ProxyFix if running behind a reverse proxy.
    app.run(host='0.0.0.0', port=PORT, debug=True)