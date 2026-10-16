"""Local-only HTTP interface. No third-party packages or external calls."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .store import Store

STATIC = Path(__file__).resolve().parents[1] / "static"


def handler(store):
    class App(BaseHTTPRequestHandler):
        def send_json(self, obj, status=200):
            raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def read_json(self):
            size = int(self.headers.get("Content-Length", "0"))
            if size > 10000:
                raise ValueError("request too large")
            return json.loads(self.rfile.read(size) or b"{}")

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/":
                raw = (STATIC / "index.html").read_bytes()
                kind = "text/html; charset=utf-8"
            elif path == "/app.js":
                raw = (STATIC / "app.js").read_bytes()
                kind = "text/javascript; charset=utf-8"
            elif path == "/style.css":
                raw = (STATIC / "style.css").read_bytes()
                kind = "text/css; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            path = urlparse(self.path).path
            try:
                data = self.read_json()
                if path == "/api/start":
                    sid = store.start(data.get("seed"))
                    result = dict(session_id=sid, **store.current(sid))
                else:
                    sid = data.get("session_id", "")
                    if path == "/api/current":
                        result = store.current(sid)
                    elif path == "/api/baseline":
                        result = store.submit_baseline(sid, data)
                    elif path == "/api/judgment":
                        result = store.submit_judgment(sid, data)
                    elif path == "/api/final":
                        result = store.submit_final(sid, data)
                    elif path == "/api/diagnosis":
                        result = store.submit_diagnosis(sid, data)
                    elif path == "/api/transfer":
                        result = store.submit_transfer(sid, data)
                    elif path == "/api/results":
                        result = store.results(sid)
                    else:
                        self.send_error(404)
                        return
                self.send_json(result)
            except (KeyError, ValueError, TypeError, IndexError) as exc:
                self.send_json({"error": str(exc)}, 400)

    return App


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", default="var/trustprobe.sqlite3")
    args = parser.parse_args()
    store = Store(args.db)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler(store))
    print(f"TrustProbe en http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
