from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash
import cv2
import os
from datetime import datetime, timedelta
import json
from database import (
    init_db, add_student, get_all_students, get_student_by_id, update_student,
    mark_attendance_auto, mark_attendance_manual, get_attendance_record,
    check_in_student, check_out_student, get_attendance_report,
    get_student_subjects, get_student_attendance_by_subject
)
from face_recognition_module import (
    get_student_encoding, recognize_faces, load_all_encodings,
    save_student_face
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
# Secret key for session management (change in production or set FLASK_SECRET env var)
app.secret_key = os.environ.get('FLASK_SECRET', 'super-secret-change-me')

# Initialize database
init_db()

# Global variables for video stream
recognized_students = {}
session_students = {}
# Active auto-mark threshold (seconds) for current session; set by start-session
AUTO_MARK_SECONDS_ACTIVE = None

# Auto-mark threshold in minutes (can be overridden with env var)
AUTO_MARK_MINUTES = int(os.environ.get('AUTO_MARK_MINUTES', '45'))


@app.before_request
def api_require_auth_json():
    """For API routes, return JSON 401 when not authenticated instead of redirecting
    to the login page (which causes the client-side JSON.parse error).
    """
    # only enforce for API endpoints
    if request.path.startswith('/api/'):
        # allow health and whoami to be callable without login
        if request.path in ('/api/health', '/api/whoami'):
            return None
        if not session.get('user'):
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401

@app.route('/')
def index():
    """Home page (requires login)"""
    if not session.get('user'):
        return redirect(url_for('login'))
    return render_template('index.html')

# Top-level login choice page
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Top-level login choice page. Accepts POST from the choice form and redirects
    to either admin or student login to avoid a 405 Method Not Allowed error.
    """
    if request.method == 'POST':
        # Look for a field that indicates which login the user chose.
        login_type = (
            request.form.get('login_type') or
            request.form.get('role') or
            request.form.get('user_type')
        )

        # Some forms use submit buttons named 'admin' or 'student'
        if not login_type:
            if 'admin' in request.form:
                login_type = 'admin'
            elif 'student' in request.form:
                login_type = 'student'

        if login_type == 'admin':
            return redirect(url_for('admin_login'))
        if login_type == 'student':
            return redirect(url_for('student_login'))

        flash('Please choose Admin or Student login', 'error')

    return render_template('login.html')

# Admin login
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
        ADMIN_PASS = os.environ.get('ADMIN_PASS', 'admin@123')

        if username == ADMIN_USER and password == ADMIN_PASS:
            session['user'] = username
            session['role'] = 'admin'
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
            return render_template('admin_login.html')

    return render_template('admin_login.html')

# Student login (by roll number)
@app.route('/student-login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        roll_number = request.form.get('roll_number', '').strip()
        # find student by roll_number
        students = get_all_students()
        matched = [s for s in students if s[1] == roll_number]
        if matched:
            student = matched[0]
            session['user'] = student[2]
            session['role'] = 'student'
            session['student_id'] = student[0]
            return redirect(url_for('student_dashboard'))
        else:
            flash('Roll number not found', 'error')
            return render_template('student_login.html')

    return render_template('student_login.html')

@app.route('/student')
def student_dashboard():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    return render_template('student_dashboard.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('role', None)
    session.pop('student_id', None)
    return redirect(url_for('login'))

# Student info endpoint
@app.route('/api/students/<int:student_id>', methods=['GET'])
def api_get_student(student_id):
    student = get_student_by_id(student_id)
    if not student:
        return jsonify({'success': False, 'message': 'Student not found'}), 404
    return jsonify({'success': True, 'student': {'id': student[0], 'roll_number': student[1], 'name': student[2], 'email': student[3]}})

# List face images for a student
@app.route('/api/students/<int:student_id>/faces', methods=['GET'])
def api_get_student_faces(student_id):
    folder = os.path.join(app.root_path, 'student_faces', str(student_id))
    images = []
    if os.path.isdir(folder):
        for f in os.listdir(folder):
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                images.append(url_for('static', filename=f'../student_faces/{student_id}/{f}'))
    return jsonify({'success': True, 'images': images})

@app.route('/api/students', methods=['GET'])
def get_students():
    """Get all students"""
    students = get_all_students()
    student_list = [
        {'id': s[0], 'roll_number': s[1], 'name': s[2], 'email': s[3]}
        for s in students
    ]
    return jsonify(student_list)

@app.route('/api/students', methods=['POST'])
def add_new_student():
    """Add a new student"""
    data = request.json
    roll_number = data.get('roll_number', '').strip()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    
    if not roll_number or not name:
        return jsonify({'success': False, 'message': 'Roll number and name are required'}), 400
    
    student_id, success = add_student(roll_number, name, email)
    
    if success:
        # If client requested live webcam capture for better attendance detection,
        # attempt to capture face images using the local webcam.
        if data.get('capture_from_webcam'):
            try:
                # import locally to avoid requiring webcam for normal runs
                from face_recognition_module import capture_face_from_webcam
                captured = capture_face_from_webcam(student_id, num_images=3)
                if captured:
                    return jsonify({'success': True, 'student_id': student_id, 'message': 'Student added and face captured successfully'})
                else:
                    # Student added but webcam capture did not yield enough faces
                    return jsonify({'success': False, 'student_id': student_id, 'message': 'Student added but failed to capture adequate face images from webcam'}), 400
            except Exception as e:
                # If webcam capture fails, inform the client but keep the student record
                return jsonify({'success': True, 'student_id': student_id, 'message': f'Student added but webcam capture failed: {str(e)}'})
        # Default response when not capturing from webcam
        return jsonify({'success': True, 'student_id': student_id, 'message': 'Student added successfully'})
    else:
        return jsonify({'success': False, 'message': 'Roll number already exists'}), 400

# Upload face for student (used by admin or student dashboard)
@app.route('/api/students/<int:student_id>/face', methods=['POST'])
def upload_student_face(student_id):
    """Upload and register a student's face"""
    # Only admin or the same student can upload
    if session.get('role') not in ('admin', 'student'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    if session.get('role') == 'student' and session.get('student_id') != student_id:
        return jsonify({'success': False, 'message': 'Students can only register their own face'}), 403

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    # Save the uploaded file
    temp_path = os.path.join(app.root_path, 'temp_image.jpg')
    file.save(temp_path)
    
    try:
        success, message = save_student_face(student_id, temp_path)
        if success:
            return jsonify({'success': True, 'message': 'Face registered successfully'})
        else:
            return jsonify({'success': False, 'message': message}), 400
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.route('/api/attendance/start-session', methods=['POST'])
def start_session():
    """Start attendance session"""
    global session_students, recognized_students, AUTO_MARK_SECONDS_ACTIVE
    
    data = request.json
    session_date = data.get('session_date', datetime.now().strftime('%Y-%m-%d'))
    duration_minutes = data.get('duration_minutes')
    subject = data.get('subject') or 'General'
    
    session_students = {}
    recognized_students = {}
    try:
        if duration_minutes is not None:
            AUTO_MARK_SECONDS_ACTIVE = int(duration_minutes) * 60
        else:
            AUTO_MARK_SECONDS_ACTIVE = AUTO_MARK_MINUTES * 60
    except Exception:
        AUTO_MARK_SECONDS_ACTIVE = AUTO_MARK_MINUTES * 60
    
    # store active subject for this session in a global (simple approach)
    session_subject = subject
    app.config['CURRENT_SESSION_SUBJECT'] = session_subject
    
    return jsonify({
        'success': True,
        'message': 'Session started',
        'session_date': session_date,
        'auto_mark_seconds': AUTO_MARK_SECONDS_ACTIVE,
        'subject': session_subject
    })

@app.route('/api/attendance/recognize', methods=['POST'])
def recognize_attendance():
    import traceback
    global recognized_students, session_students
    try:
        if 'frame' not in request.files:
            return jsonify({'success': False, 'message': 'No frame provided'}), 400

        file = request.files['frame']
        session_date = request.form.get('session_date', datetime.now().strftime('%Y-%m-%d'))

        # Read the frame
        import io
        from PIL import Image
        import numpy as np

        try:
            image = Image.open(io.BytesIO(file.read())).convert('RGB')
            frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error processing image: {str(e)}'}), 400

        # Get all students and their encodings
        students = get_all_students()
        known_encodings, student_ids = load_all_encodings(students)

        if not known_encodings:
            return jsonify({
                'success': True,
                'recognized': [],
                'message': 'No registered faces'
            })

        # Recognize faces in the frame
        results = recognize_faces(frame, known_encodings, student_ids)

        detected_students = []
        now_iso = datetime.now().isoformat()

        for student_id, confidence, location in results:
            # If this is the first time we've seen this student in the session, check them in
            if student_id not in session_students:
                # pass session subject to check-in so attendance row contains subject
                check_in_student(student_id, session_date, subject=app.config.get('CURRENT_SESSION_SUBJECT'))
                session_students[student_id] = {
                    'first_detected': now_iso,
                    'last_seen': now_iso,
                    'session_date': session_date,
                    'auto_marked': False
                }
            else:
                # update last seen time
                session_students[student_id]['last_seen'] = now_iso
            # track globally when the student was last seen (for UI total)
            recognized_students[student_id] = now_iso

            student = get_student_by_id(student_id)
            if student:
                detected_students.append({
                    'id': student_id,
                    'roll_number': student[1],
                    'name': student[2],
                    'confidence': round(confidence * 100, 2)
                })

        # Auto-mark students who have been present for configured minutes
        try:
            threshold_seconds = AUTO_MARK_SECONDS_ACTIVE or (AUTO_MARK_MINUTES * 60)
            for sid, info in list(session_students.items()):
                if not info.get('auto_marked'):
                    first_dt = datetime.fromisoformat(info['first_detected'])
                    if (datetime.now() - first_dt).total_seconds() >= threshold_seconds:
                        # mark as present automatically
                        mark_attendance_auto(sid, session_date, int(threshold_seconds/60))
                        session_students[sid]['auto_marked'] = True
        except Exception as e:
            # log but continue
            print('Auto-mark error:', str(e))

        return jsonify({
            'success': True,
            'recognized': detected_students,
            'total_recognized': len(recognized_students)
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/attendance/manual-mark', methods=['POST'])
def manual_mark_attendance():
    """Manually mark attendance for one or multiple students"""
    data = request.json or {}
    student_ids = data.get('student_ids')
    student_id = data.get('student_id')
    session_date = data.get('session_date') or datetime.now().strftime('%Y-%m-%d')
    status = data.get('status', 'PRESENT')
    subject = data.get('subject') or app.config.get('CURRENT_SESSION_SUBJECT') or 'General'
    
    target_ids = []
    if student_ids and isinstance(student_ids, list):
        target_ids = [sid for sid in student_ids if sid]
    elif student_id:
        target_ids = [student_id]
        
    if not target_ids:
        return jsonify({'success': False, 'message': 'Student ID(s) required'}), 400
    
    try:
        for sid in target_ids:
            mark_attendance_manual(sid, session_date, status, 'teacher', subject=subject)
        return jsonify({'success': True, 'message': f'Attendance marked as {status} for {len(target_ids)} student(s)'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/attendance/report', methods=['GET'])
def get_report():
    """Get attendance report for a date"""
    session_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        report = get_attendance_report(session_date)
        report_list = [
            {
                'id': r[0],
                'roll_number': r[1],
                'name': r[2],
                'status': r[3],
                'check_in_time': r[4],
                'duration_minutes': r[5]
            }
            for r in report
        ]
        return jsonify({'success': True, 'report': report_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/attendance/<int:student_id>/<session_date>', methods=['GET'])
def get_attendance_details(student_id, session_date):
    """Get attendance details for a student"""
    try:
        record = get_attendance_record(student_id, session_date)
        if record:
            return jsonify({
                'success': True,
                'check_in_time': record[1],
                'check_out_time': record[2],
                'duration_minutes': record[3],
                'status': record[4]
            })
        else:
            return jsonify({'success': False, 'message': 'No record found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

@app.route('/api/whoami', methods=['GET'])
def whoami():
    """Return current logged in user and role"""
    return jsonify({
        'logged_in': bool(session.get('user')),
        'user': session.get('user'),
        'role': session.get('role'),
        'student_id': session.get('student_id')
    })

@app.route('/api/attendance/complete-session', methods=['POST'])
def complete_session():
    """Mark listed students as present for the session_date. Only admin or teacher can call."""
    if session.get('role') not in ('admin',):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    data = request.json
    session_date = data.get('session_date', datetime.now().strftime('%Y-%m-%d'))
    student_ids = data.get('student_ids', [])
    try:
        subject = data.get('subject') or app.config.get('CURRENT_SESSION_SUBJECT') or 'General'
        for sid in student_ids:
            mark_attendance_manual(sid, session_date, 'PRESENT', 'system', subject=subject)
        return jsonify({'success': True, 'marked': len(student_ids)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Finalize a session: checkout recognized students, mark PRESENT for those meeting threshold,
# and return present/absent lists for the date
@app.route('/api/attendance/stop-session', methods=['POST'])
def stop_session_api():
    global session_students
    data = request.json or {}
    session_date = data.get('session_date', datetime.now().strftime('%Y-%m-%d'))
    try:
        # checkout all students seen in this session to capture duration
        for sid in list(session_students.keys()):
            try:
                check_out_student(sid, session_date)
            except Exception:
                pass
        # ensure those meeting threshold are marked PRESENT
        threshold_minutes = int((AUTO_MARK_SECONDS_ACTIVE or (AUTO_MARK_MINUTES * 60)) / 60)
        for sid in list(session_students.keys()):
            try:
                mark_attendance_auto(sid, session_date, threshold_minutes)
            except Exception:
                pass
        # Build present/absent lists from report
        report = get_attendance_report(session_date)
        present = []
        absent = []
        for r in report:
            item = {'id': r[0], 'roll_number': r[1], 'name': r[2]}
            if r[3] == 'PRESENT':
                present.append(item)
            else:
                absent.append(item)
        # clear session memory
        session_students = {}
        return jsonify({'success': True, 'present': present, 'absent': absent})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Serve student face images (files stored under app/student_faces/<id>/filename)
@app.route('/student_faces/<int:student_id>/<path:filename>')
def serve_student_face(student_id, filename):
    folder = os.path.join(app.root_path, 'student_faces', str(student_id))
    file_path = os.path.join(folder, filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    return ('', 404)

@app.route('/api/students/<int:student_id>', methods=['PUT'])
def edit_student(student_id):
    """Admin-only: edit student details (roll_number, name, email)"""
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    data = request.json or {}
    roll_number = data.get('roll_number')
    name = data.get('name')
    email = data.get('email')

    success, message = update_student(student_id, roll_number=roll_number, name=name, email=email)
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message}), 400

@app.route('/api/students/<int:student_id>/faces', methods=['DELETE'])
def delete_student_face(student_id):
    """Admin-only: delete a stored face image file for a student"""
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    data = request.json or {}
    filename = data.get('filename')
    if not filename:
        return jsonify({'success': False, 'message': 'filename required'}), 400
    folder = os.path.join(app.root_path, 'student_faces', str(student_id))
    file_path = os.path.join(folder, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return jsonify({'success': True, 'message': 'File deleted'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    return jsonify({'success': False, 'message': 'File not found'}), 404

@app.route('/api/students/<int:student_id>/subjects', methods=['GET'])
def api_get_student_subjects(student_id):
    try:
        subjects = get_student_subjects(student_id)
        return jsonify({'success': True, 'subjects': subjects})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/students/<int:student_id>/attendance', methods=['GET'])
def api_get_student_attendance(student_id):
    subject = request.args.get('subject')
    try:
        records = get_student_attendance_by_subject(student_id, subject)
        # normalize to JSON
        if subject:
            data = [
                {'session_date': r[0], 'status': r[1], 'check_in': r[2], 'check_out': r[3], 'duration_minutes': r[4]}
                for r in records
            ]
        else:
            data = [
                {'session_date': r[0], 'status': r[1], 'check_in': r[2], 'check_out': r[3], 'duration_minutes': r[4], 'subject': r[5]}
                for r in records
            ]
        return jsonify({'success': True, 'records': data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
