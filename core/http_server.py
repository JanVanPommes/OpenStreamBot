import http.server
import socketserver
import threading
import functools

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

class SimpleWebServer(threading.Thread):
    def __init__(self, port=8000):
        super().__init__()
        self.port = port
        self.daemon = True
        self.httpd = None

    def run(self):
        # Serve current directory
        Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=".")
        
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
