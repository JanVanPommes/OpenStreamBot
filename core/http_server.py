import http.server
import socketserver
import threading
import functools
import os
import sys

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

class SimpleWebServer(threading.Thread):
    def __init__(self, port=8000):
        super().__init__()
        self.port = port
        self.daemon = True
        self.httpd = None

    def run(self):
        # Determine root directory containing interface/dashboard.html
        root_dir = os.getcwd()
        if not os.path.exists(os.path.join(root_dir, "interface", "dashboard.html")):
            # Fallback 1: PyInstaller internal temp dir (_MEIPASS)
            meipass = getattr(sys, '_MEIPASS', None)
            if meipass and os.path.exists(os.path.join(meipass, "interface", "dashboard.html")):
                root_dir = meipass
            else:
                # Fallback 2: Executable location
                exe_dir = os.path.dirname(os.path.abspath(sys.executable))
                if os.path.exists(os.path.join(exe_dir, "interface", "dashboard.html")):
                    root_dir = exe_dir
                else:
                    # Fallback 3: Package location relative to this file
                    file_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    if os.path.exists(os.path.join(file_dir, "interface", "dashboard.html")):
                        root_dir = file_dir

        Handler = functools.partial(NoCacheHandler, directory=root_dir)

        try:
            with ReusableTCPServer(("", self.port), Handler) as httpd:
                self.httpd = httpd
                print(f"[System] Web Server läuft ({root_dir}): http://localhost:{self.port}/interface/dashboard.html")
                httpd.serve_forever()
        except OSError as e:
            print(f"[System] Fehler: Port {self.port} ist belegt. Web Server konnte nicht starten.")

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()

