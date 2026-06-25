import sys, os, threading, socket, webbrowser, atexit
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

LOCK_FILE = os.path.join(BASE_DIR, ".safenet.lock")
SERVER_PID = os.getpid()

def check_single_instance():
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE) as f:
            try:
                pid = int(f.read().strip())
                import psutil
                if psutil.pid_exists(pid):
                    print("  SafeNet is already running.")
                    print("  Open: http://127.0.0.1:5000")
                    sys.exit(0)
            except Exception:
                pass
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    atexit.register(lambda: os.path.exists(LOCK_FILE) and os.remove(LOCK_FILE))

check_single_instance()

from webapp.app import create_app
import updater

app = create_app()

def startup_update_check():
    try:
        update = updater.check_for_update()
        if update:
            from webapp.routes import UPDATE_STATUS
            UPDATE_STATUS["available"] = True
            UPDATE_STATUS["version"] = update["version"]
    except Exception:
        pass

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

if __name__ == "__main__":
    threading.Thread(target=startup_update_check, daemon=True).start()
    host = "0.0.0.0"
    port = 5000
    local_ip = get_local_ip()
    url = f"http://127.0.0.1:{port}"
    print()
    print("=" * 54)
    print("   SafeNet - Family Online Safety Platform")
    print("=" * 54)
    print(f"   >>>  {url}  <<<")
    print(f"   >>>  http://{local_ip}:{port}  <<<")
    print("=" * 54)
    print("   Admin login: admin@safenet.local / admin123")
    print("   Close this window to stop the server.")
    print("=" * 54)
    print()
    webbrowser.open(url, new=2)
    try:
        from waitress import serve
        serve(app, host=host, port=port, threads=8)
    except ImportError:
        try:
            import gunicorn.app.wsgiapp
            gunicorn.app.wsgiapp.WSGIApplication(
                app_module="run:app", use_reloader=False,
                bind=f"{host}:{port}", workers=4
            ).run()
        except ImportError:
            app.run(host=host, port=port, debug=False)
