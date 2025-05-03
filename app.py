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
import mysql.connector
from flask_session import Session

# Configuration
PORT = 7777
ALLOWED_HOST = 'gces2.duckdns.org'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, 'projects')
TEMP_DIR = os.path.join(BASE_DIR, 'temp')
VIEWS_DIR = os.path.join(BASE_DIR, 'views')

# MySQL Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'server-84k$',
    'database': 'ziphost'
}

app = Flask(__name__,
            template_folder='views',
            static_folder='views',
            static_url_path='/views')
# Add session lifetime configuration
app.config['PERMANENT_SESSION'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = TEMP_DIR
Session(app)

os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

def get_db():
    return mysql.connector.connect(**DB_CONFIG)                                                                                                                                                                                                                                                                                                                                                             
# Auth Routes
@app.route('/register', methods=['POST'])
def register():
    regno = request.form['regno']
    dob = request.form['dob']
    password = request.form['password']
    
    # Validate REGNO format
    if not regno.startswith('8301') or len(regno) != 12 or not regno.isdigit():
        return jsonify(error="Invalid registration number format"), 400
    
    # Validate date format
    try:
        datetime.datetime.strptime(dob, '%Y-%m-%d')
    except ValueError:
        return jsonify(error="Invalid date format (use YYYY-MM-DD)"), 400
    
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Check valid REGNO/DOB combination
        cursor.execute("""
            SELECT regno 
            FROM valid_registrations 
            WHERE regno = %s AND dob = %s
        """, (regno, dob))
        valid = cursor.fetchone()
        
        if not valid:
            return jsonify(error="Invalid registration number or date of birth"), 401

        # Rest of registration logic...

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
        
    except mysql.connector.Error as e:
        return jsonify(error="Database error"), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    regno = request.form['regno']
    password = request.form['password']
    
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE regno = %s", (regno,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session['regno'] = regno
        session['is_admin'] = user.get('is_admin', False)  # Add admin status to session
        log_activity(user['id'], 'login', description=f"User logged in", request=request)
        return jsonify(success=True)
    return jsonify(error="Invalid credentials"), 401

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
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Check admin status
        cursor.execute("SELECT is_admin FROM users WHERE id = %s", (session['user_id'],))
        user = cursor.fetchone()
        
        if not user:
            return jsonify(error="User not found"), 404

        # Base query
        query = """
            SELECT al.*, u.regno 
            FROM activity_logs al
            JOIN users u ON al.user_id = u.id
        """
        params = []

        # Add where clause for non-admins
        if not user.get('is_admin', False):
            query += " WHERE al.user_id = %s"
            params.append(session['user_id'])

        query += " ORDER BY al.created_at DESC LIMIT 10"

        cursor.execute(query, params)
        logs = cursor.fetchall()

        return jsonify(logs=logs)

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
        cursor = conn.cursor(dictionary=True)
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
            cursor = conn.cursor()
            project_url = f"/projects/{regno}/{project_name}/"
            cursor.execute(
                "INSERT INTO uploads (user_id, filename, project_folder,link) VALUES (%s, %s, %s,%s)",
                (session['user_id'], filename, project_name,f"http://{request.host}{project_url}")
            )
            conn.commit()
            cursor.close()


            log_activity(
            session['user_id'],
            'upload',
            table_affected='uploads',
            record_id=cursor.lastrowid,
            description=f"Uploaded project: {project_name}",
            request=request)

            return jsonify(
                success=True,
                url=project_url,
                viewUrl=f"http://{request.host}{project_url}",
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
        cursor = conn.cursor(dictionary=True)
        
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
    cursor = conn.cursor(dictionary=True)
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
        cursor = conn.cursor(dictionary=True)
        
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
    cursor = conn.cursor(dictionary=True)
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=True)