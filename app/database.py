import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'attendance.db')

def init_db():
    """Initialize the database with required tables"""
    if not os.path.exists(os.path.dirname(DB_PATH)):
        os.makedirs(os.path.dirname(DB_PATH))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_number TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            session_date DATE NOT NULL,
            check_in_time TIMESTAMP,
            check_out_time TIMESTAMP,
            duration_minutes INTEGER,
            attendance_status TEXT DEFAULT 'ABSENT',
            marked_by TEXT,
            FOREIGN KEY (student_id) REFERENCES students(id),
            UNIQUE(student_id, session_date)
        )
    ''')
    
    # Face encodings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS face_encodings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            encoding BLOB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    ''')
    
    conn.commit()
    conn.close()

    # Ensure attendance table has a 'subject' column (default 'General') for subject-wise tracking
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info('attendance')")
    cols = [r[1] for r in cursor.fetchall()]
    if 'subject' not in cols:
        try:
            cursor.execute("ALTER TABLE attendance ADD COLUMN subject TEXT DEFAULT 'General'")
        except Exception:
            pass
    conn.commit()
    conn.close()

def add_student(roll_number, name, email=''):
    """Add a new student"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO students (roll_number, name, email) VALUES (?, ?, ?)',
                      (roll_number, name, email))
        conn.commit()
        student_id = cursor.lastrowid
        conn.close()
        return student_id, True
    except sqlite3.IntegrityError:
        conn.close()
        return None, False

def get_all_students():
    """Get all students"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, roll_number, name, email FROM students ORDER BY roll_number')
    students = cursor.fetchall()
    conn.close()
    return students

def get_student_by_id(student_id):
    """Get student by ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, roll_number, name, email FROM students WHERE id = ?', (student_id,))
    student = cursor.fetchone()
    conn.close()
    return student

def mark_attendance_auto(student_id, session_date, min_minutes: int = 45):
    """Mark attendance as PRESENT when a student's duration meets the threshold.
    min_minutes defaults to 45, but can be overridden per session.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, check_in_time, duration_minutes FROM attendance 
        WHERE student_id = ? AND session_date = ?
    ''', (student_id, session_date))
    
    record = cursor.fetchone()
    
    if record:
        attendance_id, check_in_time, duration = record
        if duration and duration >= int(min_minutes):
            cursor.execute('''
                UPDATE attendance SET attendance_status = 'PRESENT' 
                WHERE id = ?
            ''', (attendance_id,))
            conn.commit()
            conn.close()
            return True
    
    conn.close()
    return False

def mark_attendance_manual(student_id, session_date, status='PRESENT', marked_by='teacher', subject=None):
    """Manually mark attendance (records subject if provided)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO attendance 
            (student_id, session_date, check_in_time, attendance_status, marked_by, subject)
            VALUES (?, ?, datetime('now'), ?, ?, ?)
        ''', (student_id, session_date, status, marked_by, subject or 'General'))
        conn.commit()
    finally:
        conn.close()
    return True

def get_attendance_record(student_id, session_date):
    """Get attendance record for a student on a specific date"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, check_in_time, check_out_time, duration_minutes, attendance_status 
        FROM attendance 
        WHERE student_id = ? AND session_date = ?
    ''', (student_id, session_date))
    
    record = cursor.fetchone()
    conn.close()
    return record

def check_in_student(student_id, session_date, subject=None):
    """Record student check-in, storing subject if given"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO attendance 
        (student_id, session_date, check_in_time, subject)
        VALUES (?, ?, datetime('now'), ?)
    ''', (student_id, session_date, subject or 'General'))
    conn.commit()
    conn.close()

def check_out_student(student_id, session_date):
    """Record student check-out and calculate duration"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get check-in time
    cursor.execute('''
        SELECT check_in_time FROM attendance 
        WHERE student_id = ? AND session_date = ?
    ''', (student_id, session_date))
    
    result = cursor.fetchone()
    if result and result[0]:
        cursor.execute('''
            UPDATE attendance 
            SET check_out_time = datetime('now'),
                duration_minutes = CAST((julianday('now') - julianday(check_in_time)) * 24 * 60 AS INTEGER)
            WHERE student_id = ? AND session_date = ?
        ''', (student_id, session_date))
        
        conn.commit()
    
    conn.close()

def get_attendance_report(session_date):
    """Get attendance report for a specific date"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.id, s.roll_number, s.name, 
               COALESCE(a.attendance_status, 'ABSENT') as status,
               a.check_in_time, a.duration_minutes
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id AND a.session_date = ?
        ORDER BY s.roll_number
    ''', (session_date,))
    
    report = cursor.fetchall()
    conn.close()
    return report

def update_student(student_id, roll_number=None, name=None, email=None):
    """Update student details. Returns (True, message) or (False, message) on error."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Build dynamic update
        fields = []
        params = []
        if roll_number is not None:
            fields.append('roll_number = ?')
            params.append(roll_number)
        if name is not None:
            fields.append('name = ?')
            params.append(name)
        if email is not None:
            fields.append('email = ?')
            params.append(email)
        if not fields:
            conn.close()
            return False, 'No fields to update'
        params.append(student_id)
        sql = f"UPDATE students SET {', '.join(fields)} WHERE id = ?"
        cursor.execute(sql, params)
        conn.commit()
        conn.close()
        return True, 'Updated successfully'
    except sqlite3.IntegrityError:
        conn.close()
        return False, 'Roll number already exists'

def get_student_subjects(student_id):
    """Return a list of distinct subjects for which the student has attendance records"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT COALESCE(subject, 'General') FROM attendance WHERE student_id = ? ORDER BY 1
    ''', (student_id,))
    rows = [r[0] for r in cursor.fetchall()]
    conn.close()
    return rows


def get_student_attendance_by_subject(student_id, subject=None):
    """Return attendance records for a student filtered by subject (or all if None)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if subject:
        cursor.execute('''
            SELECT session_date, attendance_status, check_in_time, check_out_time, duration_minutes
            FROM attendance
            WHERE student_id = ? AND COALESCE(subject, 'General') = ?
            ORDER BY session_date DESC
        ''', (student_id, subject))
    else:
        cursor.execute('''
            SELECT session_date, attendance_status, check_in_time, check_out_time, duration_minutes, COALESCE(subject, 'General')
            FROM attendance
            WHERE student_id = ?
            ORDER BY session_date DESC
        ''', (student_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows
