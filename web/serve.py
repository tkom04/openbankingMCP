#!/usr/bin/env python3
"""
Simple HTTP server to serve the Finance Autopilot web app.
Run with: python serve.py
Then open: http://localhost:8000
"""

import http.server
import socketserver
import webbrowser
import os
from pathlib import Path

PORT = 8000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def main():
    # Change to the web directory
    web_dir = Path(__file__).parent
    os.chdir(web_dir)

    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"🚀 Finance Autopilot server running at http://localhost:{PORT}")
        print("📁 Serving files from:", web_dir)
        print("🔄 Press Ctrl+C to stop")

        # Try to open browser automatically
        try:
            webbrowser.open(f'http://localhost:{PORT}')
        except:
            pass

        httpd.serve_forever()

if __name__ == "__main__":
    main()
