"""
Simple desktop launcher using pywebview.
Starts the Flask app (from app/app.py) in a background thread and opens a native window
pointing to the local server.

Run with the project's Python environment:
"B:/Face detection/.venv311/Scripts/python.exe" app/desktop.py

Requires: pywebview (installed in the venv311)
"""
import threading
import time
import os
import importlib.util
import webview

# Load Flask app module by path to avoid package import issues
app_py = os.path.join(os.path.dirname(__file__), 'app.py')
spec = importlib.util.spec_from_file_location('flask_app_module', app_py)
flask_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flask_mod)
flask_app = getattr(flask_mod, 'app')


def run_server():
    # Run Flask without the reloader (reloader would spawn a second process)
    flask_app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Wait briefly for server to start
    time.sleep(1.0)

    # Open desktop window pointing to the local server
    webview.create_window('Face Recognition Attendance', 'http://127.0.0.1:5000', width=1200, height=800)
    webview.start()
