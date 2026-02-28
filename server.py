#!/usr/bin/env python3
"""
Dashboard server with live data refresh endpoint.
Serves dashboard.html and provides /api/refresh to pull new data.

Usage:
    python3 server.py              # serve on port 8888
    python3 server.py 9000         # serve on custom port
"""

import http.server
import json
import os
import subprocess
import sys
import threading
import time
from urllib.parse import urlparse

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Lock to prevent concurrent refreshes
_refresh_lock = threading.Lock()


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler with /api/refresh endpoint."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SCRIPT_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/refresh":
            self._handle_refresh()
        elif parsed.path == "/api/status":
            self._handle_status()
        else:
            super().do_GET()

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json_response(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _handle_status(self):
        """Return current data freshness."""
        files = {
            "ad_insights": os.path.join(SCRIPT_DIR, "ad_insights.json"),
            "daily_insights": os.path.join(SCRIPT_DIR, "daily_insights.json"),
            "adset_insights": os.path.join(SCRIPT_DIR, "adset_insights.json"),
            "ventas": os.path.join(SCRIPT_DIR, "ventas_2026.csv"),
            "resumen": os.path.join(SCRIPT_DIR, "resumen_gsheet.csv"),
            "dashboard": os.path.join(SCRIPT_DIR, "dashboard.html"),
        }
        status = {}
        for name, path in files.items():
            if os.path.exists(path):
                mtime = os.path.getmtime(path)
                age_min = (time.time() - mtime) / 60
                status[name] = {
                    "exists": True,
                    "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime)),
                    "age_minutes": round(age_min, 1),
                    "size_kb": round(os.path.getsize(path) / 1024, 1),
                }
            else:
                status[name] = {"exists": False}
        self._json_response(200, status)

    def _handle_refresh(self):
        """Refresh all data sources and rebuild dashboard."""
        if not _refresh_lock.acquire(blocking=False):
            self._json_response(409, {
                "ok": False,
                "error": "Refresh already in progress. Please wait."
            })
            return

        try:
            log = []
            overall_ok = True

            # Step 1: Refresh Google Sheets
            log.append("=== Google Sheets ===")
            try:
                result = subprocess.run(
                    [sys.executable, os.path.join(SCRIPT_DIR, "sync_ventas.py"), "--force"],
                    capture_output=True, text=True, timeout=30, cwd=SCRIPT_DIR
                )
                log.append(result.stdout.strip())
                if result.returncode != 0:
                    log.append(f"⚠️ stderr: {result.stderr.strip()}")
                    overall_ok = False
                else:
                    log.append("✅ Google Sheets refreshed")
            except Exception as e:
                log.append(f"❌ Google Sheets error: {e}")
                overall_ok = False

            # Step 2: Refresh Meta Ads
            log.append("")
            log.append("=== Meta Ads API ===")
            try:
                result = subprocess.run(
                    [sys.executable, os.path.join(SCRIPT_DIR, "refresh_meta.py")],
                    capture_output=True, text=True, timeout=120, cwd=SCRIPT_DIR
                )
                log.append(result.stdout.strip())
                if result.returncode != 0:
                    log.append(f"⚠️ stderr: {result.stderr.strip()}")
                    # Don't fail overall if Meta fails - could be token issue
                    # Data files may still be usable from last successful fetch
            except Exception as e:
                log.append(f"❌ Meta Ads error: {e}")

            # Step 3: Rebuild dashboard
            log.append("")
            log.append("=== Rebuilding Dashboard ===")
            try:
                result = subprocess.run(
                    [sys.executable, os.path.join(SCRIPT_DIR, "build_dashboard.py")],
                    capture_output=True, text=True, timeout=120, cwd=SCRIPT_DIR
                )
                log.append(result.stdout.strip())
                if result.returncode != 0:
                    log.append(f"⚠️ stderr: {result.stderr.strip()}")
                    overall_ok = False
                else:
                    log.append("✅ Dashboard rebuilt!")
            except Exception as e:
                log.append(f"❌ Build error: {e}")
                overall_ok = False

            self._json_response(200, {
                "ok": overall_ok,
                "log": "\n".join(log),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            })
        finally:
            _refresh_lock.release()

    def log_message(self, format, *args):
        # Suppress access logs for static files, show API calls
        if "/api/" in (args[0] if args else ""):
            super().log_message(format, *args)


def main():
    handler = DashboardHandler
    with http.server.ThreadingHTTPServer(("", PORT), handler) as httpd:
        print(f"🚀 Dashboard server running at http://localhost:{PORT}")
        print(f"   Dashboard:  http://localhost:{PORT}/dashboard.html")
        print(f"   Refresh:    http://localhost:{PORT}/api/refresh")
        print(f"   Status:     http://localhost:{PORT}/api/status")
        print(f"   Serving:    {SCRIPT_DIR}")
        print()
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
            httpd.shutdown()


if __name__ == "__main__":
    main()
