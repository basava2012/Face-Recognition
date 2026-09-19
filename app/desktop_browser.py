"""
Simple desktop launcher that starts the Flask server in a background thread
and opens the default system browser to the app URL. This avoids pywebview
and heavy native dependencies.

Run:
& "B:/Face detection/.venv/Scripts/python.exe" app/desktop_browser.py
"""
import threading
import time
import webbrowser
import os
import importlib.util

# Load Flask app module by path to avoid package import errors (when 'app' is not a package)
app_py = os.path.join(os.path.dirname(__file__), 'app.py')
spec = importlib.util.spec_from_file_location('flask_app_module', app_py)
flask_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flask_mod)
flask_app = getattr(flask_mod, 'app')


def run_server():
    flask_app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(1.0)
    url = 'http://127.0.0.1:5000'
    webbrowser.open(url)
    print(f'Opened browser at {url}. Flask server is running.')
    try:
        # keep the script alive while server thread runs
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Shutting down.')
