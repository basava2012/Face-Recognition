import pytest
import os
import sys

# Ensure app directory is on path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))

from app import app
from database import init_db, add_student, get_all_students

@pytest.fixture
def client():
    """Create a Flask test client for automated tests"""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client

def test_health_check_endpoint(client):
    """Test /health and /api/health return 200 and healthy status"""
    res1 = client.get('/health')
    assert res1.status_code == 200
    assert res1.get_json() == {'status': 'healthy'}

    res2 = client.get('/api/health')
    assert res2.status_code == 200
    assert res2.get_json() == {'status': 'healthy'}

def test_login_page_renders(client):
    """Test /login page renders successfully"""
    res = client.get('/login')
    assert res.status_code == 200
    assert b'Login' in res.data or b'login' in res.data

def test_unauthenticated_api_access(client):
    """Test protected API endpoints reject unauthenticated requests"""
    res = client.get('/api/students')
    assert res.status_code == 401
    assert res.get_json() == {'success': False, 'message': 'Unauthorized'}

def test_admin_login_flow(client):
    """Test admin login authentication"""
    res = client.post('/admin-login', data={
        'username': 'admin',
        'password': 'admin@123'
    }, follow_redirects=True)
    assert res.status_code == 200

def test_database_student_operations(client):
    """Test database helper functions for student management"""
    roll_num = f"TEST_{os.urandom(4).hex()}"
    student_id, success = add_student(roll_num, "Test Student", "test@example.com")
    assert success is True
    assert student_id is not None

    students = get_all_students()
    matched = [s for s in students if s[1] == roll_num]
    assert len(matched) == 1
    assert matched[0][2] == "Test Student"
