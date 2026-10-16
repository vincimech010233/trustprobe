import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

from trustprobe.store import Store
from trustprobe.web import handler


class HttpJourney(unittest.TestCase):
    def test_local_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler(Store(Path(tmp) / "db.sqlite3")))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            root = f"http://127.0.0.1:{server.server_port}"

            def post(path, payload):
                body = json.dumps(payload).encode()
                req = Request(root + path, body, {"Content-Type": "application/json"})
                with urlopen(req, timeout=3) as response:
                    return json.load(response)

            try:
                with urlopen(root + "/", timeout=3) as response:
                    self.assertIn(b"TrustProbe", response.read())
                state = post("/api/start", {"seed": 17})
                sid = state.pop("session_id")
                for _ in range(7):
                    self.assertEqual(state["phase"], "baseline")
                    self.assertNotIn("ai_response", state["baseline"])
                    state = post("/api/baseline", {"session_id": sid, "value": "0", "unit": "m", "pre_ai_confidence": 25})
                    self.assertEqual(state["phase"], "judgment")
                    self.assertIn("ai_response", state["trial"])
                    self.assertNotIn("solution", state["trial"])
                    state = post("/api/judgment", {"session_id": sid, "judgment": "unsure", "ai_judgment_confidence": 0})
                    self.assertEqual(state["phase"], "final")
                    self.assertIn("ai_response", state["trial"])
                    state = post("/api/final", {"session_id": sid, "value": "0", "unit": "m",
                                                "post_ai_confidence": 60, "reason": "respuesta técnica"})
                    self.assertEqual(state["phase"], "diagnosis")
                    state = post("/api/diagnosis", {"session_id": sid, "category": "no_se", "explanation": "prueba técnica"})
                    self.assertEqual(state["phase"], "transfer")
                    state = post("/api/transfer", {"session_id": sid, "value": "0", "unit": "m"})
                self.assertEqual(state["phase"], "done")
                self.assertEqual(state["metrics"]["summary"]["n"], 7)
                self.assertEqual(post("/api/results", {"session_id": sid})["summary"]["decision_accuracy"], 0)
                self.assertEqual(state["metrics"]["trials"][0]["pre_ai_confidence"], 25)
                self.assertEqual(state["metrics"]["trials"][0]["post_ai_confidence"], 60)
                self.assertEqual(state["metrics"]["trials"][0]["final_value"], "0")
                self.assertEqual(state["metrics"]["trials"][0]["judgment"], "unsure")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
