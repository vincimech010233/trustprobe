import json
import math
import sqlite3
import time
import uuid
from pathlib import Path

from .core import CATEGORIES, load_items, select_trials, score_trial, metrics, public_trial


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, seed INTEGER NOT NULL, trials TEXT NOT NULL,
              cursor INTEGER NOT NULL DEFAULT 0, phase TEXT NOT NULL DEFAULT 'baseline', served_at REAL NOT NULL,
              created_at REAL NOT NULL, schema_version INTEGER NOT NULL DEFAULT 2);
            CREATE TABLE IF NOT EXISTS attempts(session_id TEXT NOT NULL, position INTEGER NOT NULL,
              item_id TEXT NOT NULL, variant TEXT NOT NULL,
              condition TEXT CHECK(condition IN ('ai_correct','ai_incorrect','no_ai_control')),
              baseline_value TEXT, baseline_unit TEXT, pre_ai_confidence INTEGER,
              baseline_seconds REAL, judgment TEXT, confidence INTEGER, ai_judgment_confidence INTEGER,
              final_value TEXT, final_unit TEXT, post_ai_confidence INTEGER, final_reason TEXT, final_seconds REAL,
              category TEXT, correction_value TEXT, correction_unit TEXT, explanation TEXT,
              judgment_seconds REAL, diagnosis_seconds REAL, transfer_value TEXT, transfer_unit TEXT, transfer_seconds REAL,
              PRIMARY KEY(session_id, position));
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
              position INTEGER, kind TEXT NOT NULL, payload TEXT NOT NULL, at REAL NOT NULL);
            """)
            existing_sessions = {r["name"] for r in db.execute("PRAGMA table_info(sessions)")}
            if "schema_version" not in existing_sessions:
                db.execute("ALTER TABLE sessions ADD COLUMN schema_version INTEGER NOT NULL DEFAULT 1")
            existing_attempts = {r["name"] for r in db.execute("PRAGMA table_info(attempts)")}
            additions = {"condition": "TEXT", "pre_ai_confidence": "INTEGER", "ai_judgment_confidence": "INTEGER",
                         "final_value": "TEXT", "final_unit": "TEXT", "post_ai_confidence": "INTEGER",
                         "final_reason": "TEXT", "final_seconds": "REAL", "diagnosis_seconds": "REAL"}
            for name, kind in additions.items():
                if name not in existing_attempts:
                    db.execute(f"ALTER TABLE attempts ADD COLUMN {name} {kind}")
            db.execute("UPDATE attempts SET ai_judgment_confidence=confidence WHERE ai_judgment_confidence IS NULL AND confidence IS NOT NULL")
            db.execute("UPDATE attempts SET condition=CASE variant WHEN 'correct' THEN 'ai_correct' ELSE 'ai_incorrect' END WHERE condition IS NULL")

    def db(self):
        con = sqlite3.connect(self.path, timeout=5)
        con.row_factory = sqlite3.Row
        return con

    def start(self, seed=None):
        seed = int(seed if seed is not None else int.from_bytes(uuid.uuid4().bytes[:4], "big"))
        trials = select_trials(load_items(), seed)
        sid = uuid.uuid4().hex
        now = time.time()
        with self.db() as db:
            db.execute("INSERT INTO sessions(id,seed,trials,served_at,created_at,schema_version) VALUES(?,?,?,?,?,2)",
                       (sid, seed, json.dumps(trials), now, now))
            self._event(db, sid, None, "session_started", {"seed": seed, "item_count": len(trials)})
        return sid

    @staticmethod
    def _event(db, sid, pos, kind, payload):
        db.execute("INSERT INTO events(session_id,position,kind,payload,at) VALUES(?,?,?,?,?)",
                   (sid, pos, kind, json.dumps(payload, ensure_ascii=False), time.time()))

    @staticmethod
    def _answer(data, confidence_key):
        value = str(data.get("value") or "")[:100].strip()
        unit = str(data.get("unit") or "")[:50].strip()
        if bool(value) != bool(unit):
            raise ValueError("value and unit must both be present or both blank")
        raw = data.get(confidence_key)
        if not value:
            if raw not in (None, ""):
                raise ValueError("confidence requires an answer")
            return value, unit, None
        try:
            if not math.isfinite(float(value.replace(",", "."))):
                raise ValueError("value must be a finite number")
        except ValueError:
            raise ValueError("value must be a finite number")
        try:
            confidence = int(raw)
        except (TypeError, ValueError):
            raise ValueError(f"{confidence_key} must be 0–100")
        if not 0 <= confidence <= 100:
            raise ValueError(f"{confidence_key} must be 0–100")
        return value, unit, confidence

    @staticmethod
    def _active(db, sid, phase):
        session = db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
        if session is None:
            raise KeyError("session")
        if session["schema_version"] != 2:
            raise ValueError("legacy incomplete session; start a new session")
        if session["phase"] != phase:
            raise ValueError("wrong phase")
        return session

    def current(self, sid):
        with self.db() as db:
            session = db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
            if session is None:
                raise KeyError("session")
            trials = json.loads(session["trials"])
            pos = session["cursor"]
            if pos >= len(trials):
                return dict(phase="done", position=pos, total=len(trials), metrics=self.results(sid))
            if session["schema_version"] != 2:
                return dict(phase="legacy_incomplete", position=pos, total=len(trials))
            item_id, variant = trials[pos]
            item = next(x for x in load_items() if x["id"] == item_id)
            result = dict(phase=session["phase"], position=pos, total=len(trials))
            if session["phase"] == "baseline":
                result["baseline"] = dict(id=item_id, area=item["area"], concept=item["concept"], prompt=item["prompt"])
            elif session["phase"] in ("judgment", "final", "diagnosis"):
                result["trial"] = public_trial(item, variant)
            else:
                result["transfer"] = dict(prompt=item["transfer"]["prompt"], id=item_id)
            return result

    def submit_baseline(self, sid, data):
        value, unit, pre_confidence = self._answer(data, "pre_ai_confidence")
        with self.db() as db:
            session = self._active(db, sid, "baseline")
            pos = session["cursor"]
            item_id, variant = json.loads(session["trials"])[pos]
            condition = "ai_correct" if variant == "correct" else "ai_incorrect"
            seconds = max(0, time.time() - session["served_at"])
            db.execute("INSERT INTO attempts(session_id,position,item_id,variant,condition,baseline_value,baseline_unit,pre_ai_confidence,baseline_seconds) VALUES(?,?,?,?,?,?,?,?,?)",
                       (sid, pos, item_id, variant, condition, value, unit, pre_confidence, seconds))
            self._event(db, sid, pos, "baseline_submitted", dict(value=value, unit=unit, pre_ai_confidence=pre_confidence, seconds=seconds))
            db.execute("UPDATE sessions SET phase='judgment',served_at=? WHERE id=?", (time.time(), sid))
        return self.current(sid)

    def submit_judgment(self, sid, data):
        judgment = data.get("judgment")
        try:
            confidence = int(data.get("ai_judgment_confidence"))
        except (TypeError, ValueError):
            raise ValueError("ai_judgment_confidence must be 0–100")
        if judgment not in ("correct", "incorrect", "unsure") or not 0 <= confidence <= 100:
            raise ValueError("invalid judgment or ai_judgment_confidence")
        with self.db() as db:
            session = self._active(db, sid, "judgment")
            pos = session["cursor"]
            seconds = max(0, time.time() - session["served_at"])
            db.execute("UPDATE attempts SET judgment=?,ai_judgment_confidence=?,judgment_seconds=? WHERE session_id=? AND position=?",
                       (judgment, confidence, seconds, sid, pos))
            self._event(db, sid, pos, "judgment_submitted", dict(judgment=judgment, ai_judgment_confidence=confidence, seconds=seconds))
            db.execute("UPDATE sessions SET phase='final',served_at=? WHERE id=?", (time.time(), sid))
        return self.current(sid)

    def submit_final(self, sid, data):
        value, unit, post_confidence = self._answer(data, "post_ai_confidence")
        reason = str(data.get("reason") or "")[:2000]
        with self.db() as db:
            session = self._active(db, sid, "final")
            pos = session["cursor"]
            seconds = max(0, time.time() - session["served_at"])
            db.execute("UPDATE attempts SET final_value=?,final_unit=?,post_ai_confidence=?,final_reason=?,final_seconds=? WHERE session_id=? AND position=?",
                       (value, unit, post_confidence, reason, seconds, sid, pos))
            self._event(db, sid, pos, "final_submitted", dict(value=value, unit=unit, post_ai_confidence=post_confidence, reason=reason, seconds=seconds))
            db.execute("UPDATE sessions SET phase='diagnosis',served_at=? WHERE id=?", (time.time(), sid))
        return self.current(sid)

    def submit_diagnosis(self, sid, data):
        category = data.get("category", "no_se")
        if category not in CATEGORIES:
            raise ValueError("invalid category")
        correction_value = str(data.get("correction_value") or "")[:100]
        correction_unit = str(data.get("correction_unit") or "")[:50]
        explanation = str(data.get("explanation") or "")[:2000]
        with self.db() as db:
            session = self._active(db, sid, "diagnosis")
            pos = session["cursor"]
            seconds = max(0, time.time() - session["served_at"])
            db.execute("UPDATE attempts SET category=?,correction_value=?,correction_unit=?,explanation=?,diagnosis_seconds=? WHERE session_id=? AND position=?",
                       (category, correction_value, correction_unit, explanation, seconds, sid, pos))
            self._event(db, sid, pos, "diagnosis_submitted", dict(category=category, correction_value=correction_value,
                correction_unit=correction_unit, explanation=explanation, seconds=seconds))
            db.execute("UPDATE sessions SET phase='transfer',served_at=? WHERE id=?", (time.time(), sid))
        return self.current(sid)

    def submit_transfer(self, sid, data):
        value = str(data.get("value", ""))[:100]
        unit = str(data.get("unit", ""))[:50]
        with self.db() as db:
            session = self._active(db, sid, "transfer")
            pos = session["cursor"]
            seconds = max(0, time.time() - session["served_at"])
            db.execute("UPDATE attempts SET transfer_value=?,transfer_unit=?,transfer_seconds=? WHERE session_id=? AND position=?",
                       (value, unit, seconds, sid, pos))
            self._event(db, sid, pos, "transfer_submitted", dict(value=value, unit=unit, seconds=seconds))
            db.execute("UPDATE sessions SET cursor=cursor+1,phase='baseline',served_at=? WHERE id=?", (time.time(), sid))
        return self.current(sid)

    def results(self, sid):
        with self.db() as db:
            session = db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
            if session is None:
                raise KeyError("session")
            if session["cursor"] < len(json.loads(session["trials"])):
                raise ValueError("session incomplete")
            rows = db.execute("SELECT * FROM attempts WHERE session_id=? ORDER BY position", (sid,)).fetchall()
        items = {x["id"]: x for x in load_items()}
        scores = [score_trial(items[r["item_id"]], r["variant"], r["judgment"], r["ai_judgment_confidence"],
                              r["category"], r["correction_value"], r["correction_unit"],
                              r["transfer_value"], r["transfer_unit"], r["baseline_value"], r["baseline_unit"],
                              r["final_value"], r["final_unit"], r["pre_ai_confidence"], r["post_ai_confidence"],
                              r["condition"]) for r in rows]
        return dict(summary=metrics(scores), trials=[dict(item_id=r["item_id"], area=items[r["item_id"]]["area"],
            variant=r["variant"],
            baseline_value=r["baseline_value"], baseline_unit=r["baseline_unit"],
            final_value=r["final_value"], final_unit=r["final_unit"], final_reason=r["final_reason"],
            baseline_seconds=r["baseline_seconds"], judgment_seconds=r["judgment_seconds"],
            final_seconds=r["final_seconds"], diagnosis_seconds=r["diagnosis_seconds"],
            transfer_seconds=r["transfer_seconds"], **s)
            for r, s in zip(rows, scores)])
