import http.server
import socketserver
import os
import webbrowser

PORT = 8080
DIRECTORY = os.path.join(os.path.dirname(__file__), "frontend")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

if __name__ == "__main__":
    print("[*] Booting Atlas UI Frontend...")
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"[*] Serving Atlas AI Interface at http://localhost:{PORT}")
        webbrowser.open(f"http://localhost:{PORT}")
        httpd.serve_forever()
