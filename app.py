from flask import Flask, request, send_from_directory, send_file, session, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from zipfile import ZipFile
import os
import re
import time
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

app = Flask(__name__)
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
    password = generate_password_hash(request.form['password'])
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (regno, password_hash) VALUES (%s, %s)", (regno, password))
        conn.commit()
        return jsonify(success=True)
    except mysql.connector.IntegrityError:
        return jsonify(error="Registration number exists"), 409
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
        return jsonify(success=True)
    return jsonify(error="Invalid credentials"), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))
    
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
            cursor.execute(
                "INSERT INTO uploads (user_id, filename, project_folder) VALUES (%s, %s, %s)",
                (session['user_id'], filename, project_name)
            )
            conn.commit()
            cursor.close()

            project_url = f"/projects/{regno}/{project_name}/"
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

        return jsonify(success=True)
        
    except Exception as e:
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
        SELECT id, filename, project_folder, upload_time 
        FROM uploads 
        WHERE user_id = %s 
        ORDER BY upload_time DESC
    """, (session['user_id'],))
    uploads = cursor.fetchall()
    cursor.close()
    conn.close()
    
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
@app.route('/upload')
def upload_page():
    check_valid_session()
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return send_from_directory(VIEWS_DIR, 'upload.html')

# Add redirects for authenticated users
@app.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('upload_page'))
    return send_from_directory(VIEWS_DIR, 'login.html')

@app.route('/register')
def register_page():
    if 'user_id' in session:
        return redirect(url_for('upload_page'))
    return send_from_directory(VIEWS_DIR, 'register.html')

@app.route('/home')
def home():
    return send_from_directory(VIEWS_DIR, 'home.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        session.clear()
        return redirect(url_for('login_page'))
    return send_from_directory(VIEWS_DIR, 'dashboard.html')

# Serve Projects
@app.route('/projects/<path:subpath>')
def serve_projects(subpath):
    return send_from_directory(PROJECTS_DIR, subpath)

@app.route('/projects/<regno>/<project>/')
def serve_project_index(regno, project):
    index_path = os.path.join(PROJECTS_DIR, regno, project, 'index.html')
    if os.path.exists(index_path):
        return send_file(index_path)
    else:
        return "index.html not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=True)