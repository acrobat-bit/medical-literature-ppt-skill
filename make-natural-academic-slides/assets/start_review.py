#!/usr/bin/env python3
"""Serve only this review bundle on a free loopback port."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import webbrowser
import hashlib
import json
import urllib.request

ROOT_ID = hashlib.sha256(str(Path(__file__).resolve().parent).encode()).hexdigest()

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/__medical_review_health':
            body=json.dumps({'app':'medical-slide-review','root_id':ROOT_ID}).encode()
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()
    def list_directory(self, path):
        self.send_error(404)
    def log_message(self, *args):
        pass
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        super().end_headers()

if __name__ == '__main__':
    root=Path(__file__).resolve().parent
    if not (root/'index.html').is_file():
        raise SystemExit('请将启动器与 index.html 放在同一文件夹。')
    hint=root/'.review-port'
    port=41000+int(ROOT_ID[:6],16)%18000
    try:
        saved=int(hint.read_text())
        if 1024<=saved<=65535:port=saved
    except (OSError,ValueError):
        pass
    try:
        server=ThreadingHTTPServer(('127.0.0.1',port),partial(Handler,directory=str(root)))
    except OSError:
        try:
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            health=json.loads(opener.open(f'http://127.0.0.1:{port}/__medical_review_health',timeout=1).read(2000))
            if health.get('app')=='medical-slide-review' and health.get('root_id')==ROOT_ID:
                url=f'http://127.0.0.1:{port}/'
                print(url,flush=True)
                print('此审阅台已在运行，继续使用原地址。',flush=True)
                if '--no-open' not in sys.argv:webbrowser.open(url)
                raise SystemExit(0)
        except (OSError,ValueError):
            pass
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(root)))
        print('原端口被占用，已换用新地址；如需恢复旧意见，请导入 JSON 备份。',flush=True)
    try:
        hint.write_text(str(server.server_port))
    except OSError:
        print('启动地址记录失败；结束审阅前请导出 JSON 备份。',flush=True)
    with server:
        url=f'http://127.0.0.1:{server.server_port}/'
        print(url,flush=True)
        print('审阅台只在本机运行，无需联网。关闭此窗口或按 Ctrl+C 停止。',flush=True)
        if '--no-open' not in sys.argv:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
