import json
import os
import sys
import subprocess
import tempfile
import shutil
import zipfile
import threading
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(BASE_DIR, "version.json")

try:
    from urllib.request import urlopen, Request
    from urllib.error import URLError
except ImportError:
    from urllib2 import urlopen, Request, URLError


def get_local_version():
    try:
        with open(VERSION_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"version": "0.0.0", "github_repo": "", "update_url": ""}


def set_local_version(ver):
    try:
        data = get_local_version()
        data["version"] = ver
        with open(VERSION_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def parse_version(v):
    parts = re.split(r"[^0-9]", v)
    nums = []
    for p in parts:
        try:
            nums.append(int(p))
        except ValueError:
            break
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:3])


def check_for_update():
    info = get_local_version()
    url = info.get("update_url", "")
    if not url:
        return None
    try:
        req = Request(url, headers={"User-Agent": "SafeNet-Updater/1.0", "Accept": "application/json"})
        resp = urlopen(req, timeout=10)
        data = json.loads(resp.read().decode("utf-8"))
        latest = data.get("tag_name", data.get("name", "")).lstrip("v")
        current = info.get("version", "0.0.0")
        if parse_version(latest) > parse_version(current):
            download_url = None
            assets = data.get("assets", [])
            for a in assets:
                name = a.get("name", "")
                if name.endswith(".zip") and "safenet" in name.lower():
                    download_url = a.get("browser_download_url")
                    break
            if not download_url:
                for a in assets:
                    name = a.get("name", "")
                    if name.endswith(".zip"):
                        download_url = a.get("browser_download_url")
                        break
            return {
                "version": latest,
                "download_url": download_url,
                "release_url": data.get("html_url", ""),
                "changelog": data.get("body", "No details available."),
                "published": data.get("published_at", ""),
            }
    except Exception:
        pass
    return None


def download_update(download_url, dest_dir):
    try:
        req = Request(download_url, headers={"User-Agent": "SafeNet-Updater/1.0"})
        resp = urlopen(req, timeout=120)
        zip_path = os.path.join(dest_dir, "safenet_update.zip")
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 65536
        with open(zip_path, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
        return zip_path
    except Exception:
        return None


def apply_update(zip_path, app_dir):
    try:
        extract_dir = tempfile.mkdtemp(prefix="safenet_update_")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)
        extracted_items = os.listdir(extract_dir)
        if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_dir, extracted_items[0])):
            extract_dir = os.path.join(extract_dir, extracted_items[0])
        excluded = {"safety.db", "version.json", "config.json"}
        for item in os.listdir(extract_dir):
            if item in excluded:
                continue
            src = os.path.join(extract_dir, item)
            dst = os.path.join(app_dir, item)
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        shutil.rmtree(os.path.dirname(extract_dir) if len(os.listdir(os.path.dirname(extract_dir))) > 0 else extract_dir,
                      ignore_errors=True)
        return True
    except Exception:
        return False


def restart_app(wait=3):
    if getattr(sys, "frozen", False):
        exe = sys.executable
        subprocess.Popen([exe], cwd=os.path.dirname(exe))
    else:
        script = os.path.join(BASE_DIR, "run.py")
        subprocess.Popen([sys.executable, script], cwd=BASE_DIR)


def run_update_background(callback=None):
    def worker():
        update = check_for_update()
        if update and update.get("download_url"):
            temp_dir = tempfile.mkdtemp(prefix="safenet_dl_")
            zip_path = download_update(update["download_url"], temp_dir)
            if zip_path and apply_update(zip_path, BASE_DIR):
                set_local_version(update["version"])
                if callback:
                    callback(True, update)
                return
            if callback:
                callback(False, None)
        elif callback:
            callback(False, None)

    threading.Thread(target=worker, daemon=True).start()
    return True


def run_update_apply(callback=None):
    run_update_background(callback)


if __name__ == "__main__":
    print("Checking for updates...")
    update = check_for_update()
    if update:
        print(f"Update found: v{update['version']}")
        print(f"Download URL: {update['download_url']}")
        print(f"Changelog: {update['changelog'][:200]}")
        temp_dir = tempfile.mkdtemp(prefix="safenet_dl_")
        zip_path = download_update(update["download_url"], temp_dir)
        if zip_path:
            print("Downloaded. Applying...")
            if apply_update(zip_path, BASE_DIR):
                set_local_version(update["version"])
                print("Update applied successfully!")
            else:
                print("Failed to apply update.")
        else:
            print("Failed to download update.")
    else:
        print("No update available.")
