from flask import Flask, request, send_from_directory,send_file, session, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from zipfile import ZipFile
import os
import shutil

from flask_session import Session

# Configuration
PORT = 7777
ALLOWED_HOST = 'gces2.duckdns.org'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, 'projects')
TEMP_DIR = os.path.join(BASE_DIR, 'temp')
PUBLIC_DIR = os.path.join(BASE_DIR, 'public')
VIEWS_DIR = os.path.join(BASE_DIR, 'views')

# Setup
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = TEMP_DIR
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Domain restriction middleware
@app.before_request
def restrict_domain():
    pass
    # if request.host.split(':')[0] != ALLOWED_HOST:
    #     return jsonify({'error': 'Forbidden access. Invalid domain.'}), 403

# Serve static files
@app.route('/projects/<path:subpath>')
def serve_project(subpath):
    return send_from_directory(PROJECTS_DIR, subpath)

@app.route('/')
def home():
    return send_from_directory(VIEWS_DIR, 'index.html')

@app.route('/projects/<regno>/<project>/')
def serve_project_index(regno, project):
    index_path = os.path.join(PROJECTS_DIR, regno, project, 'index.html')
    if os.path.exists(index_path):
        return send_file(index_path)
    else:
        return "index.html not found", 404

# Upload route
@app.route('/upload', methods=['POST'])
def upload_zip():
    if 'zipfile' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['zipfile']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not file.filename.endswith('.zip'):
        return jsonify({'error': 'Only ZIP files allowed'}), 400

    filename = secure_filename(file.filename)
    temp_zip_path = os.path.join(TEMP_DIR, filename)
    file.save(temp_zip_path)

    try:
        with ZipFile(temp_zip_path, 'r') as zip_ref:
            for entry in zip_ref.namelist():
                if any(x in entry for x in ['..', '.env', 'node_modules', 'package.json']) or os.path.isabs(entry):
                    raise Exception(f'Forbidden file detected: {entry}')
            
            regno = session.get('regno', 'anonymous')
            folder_name = os.path.splitext(filename)[0]
            extract_path = os.path.join(PROJECTS_DIR, regno)
            os.makedirs(extract_path, exist_ok=True)
            zip_ref.extractall(extract_path)

        os.remove(temp_zip_path)
        final_url = f'/projects/{regno}/{folder_name}'

        print(f"✅ Project uploaded: http://{ALLOWED_HOST}:{PORT}{final_url}")
        return jsonify({'success': True, 'url': final_url, 'viewUrl': final_url})

    except Exception as e:
        os.remove(temp_zip_path)
        return jsonify({'error': str(e)}), 400

# View endpoint for index.html
@app.route('/view/<regno>')
def view_project(regno):
    index_path = os.path.join(PROJECTS_DIR, regno, 'index.html')
    if not os.path.exists(index_path):
        return 'Project not found', 404
    return send_from_directory(os.path.join(PROJECTS_DIR, regno), 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
