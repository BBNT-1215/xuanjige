#!/usr/bin/env python3
"""
玄机阁 Dashboard Web服务器

提供看板的Web界面和REST API。

启动:
  python3 dashboard/server.py [--host 127.0.0.1] [--port 7892]
"""
import json
import pathlib
import sys
import os
import datetime
import http.server
import socketserver
import urllib.parse

_BASE = pathlib.Path(os.environ.get('HERMESTRIX_HOME',
           pathlib.Path(__file__).resolve().parent.parent))
DATA_DIR = _BASE / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)
TASKS_FILE = DATA_DIR / 'tasks.json'
REGISTRY_FILE = _BASE / 'agents' / 'registry.json'

STATIC_DIR = pathlib.Path(__file__).parent / 'static'
STATIC_DIR.mkdir(exist_ok=True)

PORT = 7892
HOST = '127.0.0.1'

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(pathlib.Path(__file__).parent), **kwargs)

    def do_GET(self):
        if self.path == '/api/tasks':
            self.send_json(self._get_tasks())
        elif self.path == '/api/registry':
            self.send_json(self._get_registry())
        elif self.path == '/api/stats':
            self.send_json(self._get_stats())
        elif self.path.startswith('/pixel'):
            self.path = '/pixel/index.html'
            super().do_GET()
        elif self.path == '/' or self.path == '/index.html':
            self.path = '/index.html'
            super().do_GET()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith('/api/'):
            self.send_error(404)
            return
        self.send_error(405)

    def _get_tasks(self):
        if not TASKS_FILE.exists():
            return []
        try:
            return json.loads(TASKS_FILE.read_text(encoding='utf-8'))
        except:
            return []

    def _get_registry(self):
        if not REGISTRY_FILE.exists():
            return {"roles": []}
        try:
            return json.loads(REGISTRY_FILE.read_text(encoding='utf-8'))
        except:
            return {"roles": []}

    def _get_stats(self):
        tasks = self._get_tasks()
        return {
            'total': len(tasks),
            'by_state': {s: len([t for t in tasks if t.get('state') == s])
                        for s in ['Taizi','Zhongshu','Menxia','Assigned','Doing','Review','Done','Blocked','Pending','Cancelled']},
            'updated_at': datetime.datetime.now().isoformat()
        }

    def send_json(self, data):
        response = json.dumps(data, ensure_ascii=False, indent=2)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', len(response.encode('utf-8')))
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))

    def log_message(self, format, *args):
        pass  # 静默日志

def main():
    global PORT, HOST
    for i, a in enumerate(sys.argv):
        if a == '--port' and i+1 < len(sys.argv):
            PORT = int(sys.argv[i+1])
        if a == '--host' and i+1 < len(sys.argv):
            HOST = sys.argv[i+1]

    with socketserver.TCPServer((HOST, PORT), Handler) as httpd:
        print(f"\n\n⚔️ 玄机阁 Dashboard")
        print(f"   http://{HOST}:{PORT}")
        print(f"   看板: http://{HOST}:{PORT}/index.html")
        print(f"\n   按 Ctrl+C 停止\n\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n已停止")

if __name__ == '__main__':
    main()
