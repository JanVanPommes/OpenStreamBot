import http.server
import socketserver
import threading
import functools

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
        # Serve current directory without caching
        Handler = functools.partial(NoCacheHandler, directory=".")
        
        # Suppress default logging to keep console clean
        # Handler.log_message = lambda self, format, *args: None

        try:
            with ReusableTCPServer(("", self.port), Handler) as httpd:
                self.httpd = httpd
                print(f"[System] Web Server läuft: http://localhost:{self.port}/interface/dashboard.html")
                httpd.serve_forever()
        except OSError as e:
            print(f"[System] Fehler: Port {self.port} ist belegt. Web Server konnte nicht starten.")

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
