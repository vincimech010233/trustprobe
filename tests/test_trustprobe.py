import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from trustprobe.core import CONDITIONS, load_items, metrics, numeric_score, score_trial, select_trials
from trustprobe.store import Store
from scripts.simulate import PROFILES, run_profile


class CoreTests(unittest.TestCase):
    def test_bank(self):
        items = load_items()
        self.assertEqual(len(items), 21)
        self.assertEqual(len({x["id"] for x in items}), 21)
        self.assertEqual(len({x["area"] for x in items}), 7)
        for x in items:
            self.assertTrue(all(k in x for k in ("prompt", "correct", "wrong", "concept", "difficulty", "transfer", "solution")))
            self.assertTrue(x["correct"]["explanation"])
            self.assertTrue(x["wrong"][0]["text"])
            self.assertIn("value", x["wrong"][0])
            self.assertIn("unit", x["wrong"][0])
            self.assertFalse(numeric_score(str(x["wrong"][0]["value"]), x["wrong"][0]["unit"],
                                           x["correct"]["value"], x["correct"]["unit"]), x["id"])
            self.assertNotEqual(str(x["correct"]["value"]), x["wrong"][0]["text"])
            self.assertIsInstance(x["transfer"]["value"], (int, float))

    def test_physics_reference_calculations(self):
        # Independent formula checks for all displayed values and transfer keys.
        expected = {
            "K1": (120/2, 150/3), "K2": (2*5, 3*4), "K3": (.5*4*3**2, .5*2*4**2),
            "D1": (12/3, 20/5), "D2": ((10-4)/2, (20-8)/4), "D3": (.2*5*10, .3*4*10),
            "E1": (.5*2*3**2, .5*4*2**2), "E2": (3*10*4, 2*10*5), "E3": ((2*10*20)**.5, (2*10*5)**.5),
            "P1": (3*4, 5*2), "P2": (5*4, 6*3), "P3": ((2*6)/(2+1), (3*4)/(3+1)),
            "G1": (80/2**2, 90/3**2), "G2": (6*10, 8*10), "G3": (30/5, 40/8),
            "C1": (12/4, 20/5), "C2": (3+5, 4+6), "C3": (6*2, 10*3),
            "W1": (5*2, 4*3), "W2": (1/4, 1/2), "W3": (340*2/2, 300*3/2),
        }
        for item in load_items():
            correct, transfer = expected[item["id"]]
            self.assertAlmostEqual(item["correct"]["value"], correct, msg=item["id"])
            self.assertAlmostEqual(item["transfer"]["value"], transfer, msg=item["id"])

    def test_selection_reproducible_balanced(self):
        a = select_trials(load_items(), 42)
        self.assertEqual(a, select_trials(load_items(), 42))
        self.assertEqual(len(a), 7)
        self.assertEqual(sum(v == "wrong" for _, v in a), 4)
        self.assertEqual(len({next(x["area"] for x in load_items() if x["id"] == i) for i, _ in a}), 7)

    def test_numeric_and_scores(self):
        self.assertTrue(numeric_score("0,25", "s", .25, "s"))
        self.assertFalse(numeric_score("nan", "s", .25, "s"))
        self.assertFalse(numeric_score("0.25", "m", .25, "s"))
        x = load_items()[0]
        s = score_trial(x, "wrong", "incorrect", 80, x["wrong"][0]["category"],
                        str(x["correct"]["value"]), x["correct"]["unit"],
                        str(x["transfer"]["value"]), x["transfer"]["unit"])
        self.assertTrue(s["correction_correct"] and s["parallel_item_correct"])
        self.assertAlmostEqual(metrics([s])["brier"], .04)
        self.assertEqual(metrics([s])["parallel_item_after_correction_accuracy"], 1)

    def test_abstention_not_false_rejection(self):
        x = load_items()[0]
        s = score_trial(x, "correct", "unsure", 20, "no_se", "", "", "", "")
        self.assertEqual(metrics([s])["false_rejection_rate"], 0)
        self.assertEqual(metrics([s])["decision_accuracy"], 0)
        self.assertIsNone(metrics([s])["error_detection_rate"])
        self.assertIsNone(metrics([s])["brier"])
        self.assertEqual(metrics([s])["abstention_rate"], 1)
        self.assertIsNone(metrics([s])["parallel_item_after_correction_accuracy"])
        self.assertEqual(metrics([]), {})

    def test_appraisal_signals_are_conditional_and_not_switching(self):
        x = load_items()[0]
        v, u = str(x["correct"]["value"]), x["correct"]["unit"]
        def trial(ai, judgment, baseline_value=v, baseline_unit=u):
            return score_trial(x, ai, judgment, 50, "no_se", "", "", "", "",
                               baseline_value, baseline_unit)

        wrong_ai = [trial("wrong", "correct"), trial("wrong", "incorrect"),
                    trial("wrong", "unsure"), trial("wrong", "correct", "", "")]
        m = metrics(wrong_ai)
        self.assertAlmostEqual(m["harmful_endorsement_signal"], 1/3)
        self.assertAlmostEqual(m["resistance_appraisal_signal"], 1/3)
        self.assertIsNone(m["correct_advice_recognition_signal"])
        self.assertNotIn("harmful_ai_influence_rate", m)

        right_ai = [trial("correct", "correct", "-999", u),
                    trial("correct", "incorrect", "-999", u),
                    trial("correct", "correct", "", "")]
        m = metrics(right_ai)
        self.assertAlmostEqual(m["correct_advice_recognition_signal"], .5)
        self.assertIsNone(m["harmful_endorsement_signal"])
        self.assertIsNone(m["resistance_appraisal_signal"])

    def test_four_transitions_and_judgment_independence(self):
        x = load_items()[0]
        good, bad = x["correct"], x["wrong"][0]
        def trial(variant, j, b, f):
            return score_trial(x, variant, j, 70, "no_se", "", "", "", "",
                               str(b["value"]), b["unit"], str(f["value"]), f["unit"], 80, 60)
        rows = [trial("wrong", "incorrect", good, bad),  # rejects IA, still adopts its answer
                trial("correct", "incorrect", bad, good), # rejects IA, still improves
                trial("wrong", "correct", good, good),   # endorses IA, still retains own answer
                trial("correct", "correct", bad, bad)]
        self.assertEqual([r["transition"] for r in rows], [
            "correct_to_incorrect", "incorrect_to_correct",
            "correct_to_correct", "incorrect_to_incorrect"])
        self.assertTrue(rows[0]["final_matches_ai"])
        self.assertFalse(rows[0]["final_matches_baseline"])
        self.assertEqual(rows[0]["confidence_change"], -20)
        m = metrics(rows)
        self.assertEqual(m["complete_pair_n"], 4)
        for key in ("correct_to_incorrect_rate", "incorrect_to_correct_rate",
                    "correct_to_correct_rate", "incorrect_to_incorrect_rate"):
            self.assertEqual(m[key], .25)
        self.assertEqual(m["correct_to_incorrect_rate_given_initial_correct"], .5)
        self.assertEqual(m["incorrect_to_correct_rate_given_initial_incorrect"], .5)
        self.assertEqual(m["wrong_ai_adoption_rate"], .5)

    def test_strict_rair_rsr_exclude_third_answers_and_missing(self):
        x = load_items()[0]
        good, bad = x["correct"], x["wrong"][0]
        def trial(variant, b, f):
            return score_trial(x, variant, "unsure", 0, "no_se", "", "", "", "",
                               str(b["value"]), b["unit"], str(f["value"]) if f else "", f["unit"] if f else "")
        third = {"value": 9999, "unit": good["unit"]}
        rows = [trial("correct", bad, good), trial("correct", bad, bad), trial("correct", bad, third),
                trial("wrong", good, good), trial("wrong", good, bad), trial("wrong", good, None)]
        m = metrics(rows)
        self.assertEqual(m["rair"], .5)
        self.assertEqual(m["rsr"], .5)
        self.assertEqual(m["rair_eligible_n"], 2)
        self.assertEqual(m["rsr_eligible_n"], 2)
        self.assertEqual(m["rair_third_or_missing_n"], 1)
        self.assertEqual(m["rsr_third_or_missing_n"], 1)
        self.assertEqual(m["missing_pair_n"], 1)
        self.assertEqual(metrics([trial("correct", bad, third)])["rair"], None)
        self.assertEqual(metrics([trial("wrong", good, None)])["rsr"], None)

    def test_missing_and_future_control_condition(self):
        self.assertIn("no_ai_control", CONDITIONS)
        x = load_items()[0]
        missing = score_trial(x, "wrong", "unsure", 0, "no_se", "", "", "", "")
        self.assertEqual(missing["transition"], "unclassified_missing")
        self.assertIsNone(metrics([missing])["observed_answer_switch_rate"])
        self.assertEqual(metrics([missing])["missing_pair_n"], 1)
        good = x["correct"]
        control = score_trial(x, "wrong", "unsure", 0, "no_se", "", "", "", "",
                              str(good["value"]), good["unit"], str(good["value"]), good["unit"],
                              80, 80, "no_ai_control")
        self.assertIsNone(control["truth_correct"])
        self.assertIsNone(metrics([control])["decision_accuracy"])
        self.assertEqual(metrics([control])["correct_to_correct_rate"], 1)

    def test_persistent_error_can_be_own_ai_or_third_answer(self):
        x = load_items()[0]
        bad = x["wrong"][0]
        def trial(final_value):
            return score_trial(x, "wrong", "unsure", 0, "no_se", "", "", "", "",
                               "700", bad["unit"], str(final_value), bad["unit"])
        own = trial(700)
        ai = trial(bad["value"])
        third = trial(900)
        for row in (own, ai, third):
            self.assertEqual(row["transition"], "incorrect_to_incorrect")
        self.assertEqual([(r["final_matches_baseline"], r["final_matches_ai"]) for r in (own, ai, third)],
                         [(True, False), (False, True), (False, False)])
        self.assertEqual(metrics([own, ai, third])["wrong_ai_adoption_rate"], 1/3)
        confirmed = score_trial(x, "wrong", "correct", 50, "no_se", "", "", "", "",
                                str(bad["value"]), bad["unit"], str(bad["value"]), bad["unit"])
        self.assertIsNone(metrics([confirmed])["wrong_ai_adoption_rate"])


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "test.sqlite3")

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_session_and_events(self):
        sid = self.store.start(3)
        self.assertEqual(self.store.current(sid)["phase"], "baseline")
        with self.assertRaises(ValueError):
            self.store.results(sid)
        for _ in range(7):
            baseline = self.store.current(sid)
            self.assertNotIn("ai_response", baseline["baseline"])
            self.store.submit_baseline(sid, {"value": "0", "unit": "m", "pre_ai_confidence": 42})
            first = self.store.current(sid)
            self.assertNotIn("correct", first["trial"])
            self.assertNotIn("transfer", first)
            x = self.store.submit_judgment(sid, {"judgment": "unsure", "ai_judgment_confidence": 0})
            self.assertEqual(x["phase"], "final")
            self.assertEqual(self.store.submit_final(sid, {"value": "0", "unit": "m", "post_ai_confidence": 73, "reason": "prueba"})["phase"], "diagnosis")
            x = self.store.submit_diagnosis(sid, {"category": "no_se"})
            self.assertEqual(x["phase"], "transfer")
            with self.assertRaises(ValueError):
                self.store.submit_judgment(sid, {"judgment": "correct", "ai_judgment_confidence": 90})
            self.store.submit_transfer(sid, {"value": "0", "unit": "m"})
        result = self.store.results(sid)
        self.assertEqual(result["summary"]["n"], 7)
        with self.store.db() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM events WHERE session_id=?", (sid,)).fetchone()[0], 36)
            self.assertEqual(db.execute("SELECT count(*) FROM attempts WHERE condition IN ('ai_correct','ai_incorrect')", ()).fetchone()[0], 7)
        self.assertEqual(len(result["trials"]), 7)
        self.assertEqual(result["trials"][0]["pre_ai_confidence"], 42)
        self.assertEqual(result["trials"][0]["post_ai_confidence"], 73)
        self.assertEqual(result["trials"][0]["final_value"], "0")
        self.assertEqual(result["trials"][0]["final_reason"], "prueba")
        self.assertEqual(result["summary"]["complete_pair_n"], 7)

    def test_input_boundaries(self):
        sid = self.store.start(1)
        for confidence in (-1, 101, "nan", None):
            with self.assertRaises(ValueError):
                self.store.submit_baseline(sid, {"value": "0", "unit": "m", "pre_ai_confidence": confidence})
        with self.assertRaises(ValueError):
            self.store.submit_baseline(sid, {"value": "0", "pre_ai_confidence": 20})
        with self.assertRaises(ValueError):
            self.store.submit_baseline(sid, {"value": "nan", "unit": "m", "pre_ai_confidence": 20})
        self.store.submit_baseline(sid, {"value": "0", "unit": "m", "pre_ai_confidence": 20})
        for confidence in (-1, 101, "nan"):
            with self.assertRaises(ValueError):
                self.store.submit_judgment(sid, {"judgment": "correct", "ai_judgment_confidence": confidence})
        self.store.submit_judgment(sid, {"judgment": "incorrect", "ai_judgment_confidence": 55})
        for confidence in (-1, 101, "nan", None):
            with self.assertRaises(ValueError):
                self.store.submit_final(sid, {"value": "0", "unit": "m", "post_ai_confidence": confidence})
        self.assertEqual(self.store.submit_final(sid, {"value": "", "unit": "", "post_ai_confidence": ""})["phase"], "diagnosis")
        with self.store.db() as db:
            row = db.execute("SELECT pre_ai_confidence,ai_judgment_confidence,post_ai_confidence,final_value,condition FROM attempts WHERE session_id=?", (sid,)).fetchone()
        self.assertEqual((row["pre_ai_confidence"], row["ai_judgment_confidence"], row["post_ai_confidence"]), (20, 55, None))
        self.assertEqual(row["final_value"], "")
        self.assertIn(row["condition"], ("ai_correct", "ai_incorrect"))
        with self.store.db() as db:
            db.execute("UPDATE attempts SET condition='no_ai_control' WHERE session_id=?", (sid,))
            self.assertEqual(db.execute("SELECT condition FROM attempts WHERE session_id=?", (sid,)).fetchone()[0], "no_ai_control")
        with self.assertRaises(KeyError):
            self.store.current("missing")

    def test_legacy_schema_migrates_without_inventing_final_answer(self):
        path = Path(self.tmp.name) / "old.sqlite3"
        with sqlite3.connect(path) as db:
            db.executescript("""
            CREATE TABLE sessions(id TEXT PRIMARY KEY, seed INTEGER, trials TEXT, cursor INTEGER, phase TEXT, served_at REAL, created_at REAL);
            CREATE TABLE attempts(session_id TEXT, position INTEGER, item_id TEXT, variant TEXT,
              baseline_value TEXT, baseline_unit TEXT, baseline_seconds REAL, judgment TEXT, confidence INTEGER,
              category TEXT, correction_value TEXT, correction_unit TEXT, explanation TEXT,
              judgment_seconds REAL, transfer_value TEXT, transfer_unit TEXT, transfer_seconds REAL,
              PRIMARY KEY(session_id,position));
            """)
            db.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?,?)", ("old", 1, json.dumps([["K1", "wrong"]]), 0, "baseline", 0, 0))
            db.execute("INSERT INTO attempts(session_id,position,item_id,variant,confidence) VALUES(?,?,?,?,?)", ("old", 0, "K1", "wrong", 75))
        migrated = Store(path)
        self.assertEqual(migrated.current("old")["phase"], "legacy_incomplete")
        with migrated.db() as db:
            row = db.execute("SELECT ai_judgment_confidence,final_value,condition FROM attempts").fetchone()
            self.assertEqual((row["ai_judgment_confidence"], row["final_value"], row["condition"]), (75, None, "ai_incorrect"))
            db.execute("UPDATE sessions SET cursor=1 WHERE id='old'")
            db.execute("UPDATE attempts SET baseline_value='60',baseline_unit='km/h',judgment='incorrect',category='formula',transfer_value='50',transfer_unit='km/h' WHERE session_id='old'")
        summary = migrated.results("old")["summary"]
        self.assertEqual(summary["missing_pair_n"], 1)
        self.assertIsNone(summary["rsr"])

    def test_simulator_distinguishes(self):
        m = {p: run_profile(self.store, p, range(3)) for p in PROFILES}
        self.assertEqual(m["alto_resiste_ia_erronea"]["rsr"], 1)
        self.assertEqual(m["alto_adopta_ia_erronea"]["rsr"], 0)
        self.assertEqual(m["bajo_adopta_ia_correcta"]["rair"], 1)
        self.assertEqual(m["bajo_ignora_ia_correcta"]["rair"], 0)
        self.assertGreater(m["alto_adopta_ia_erronea"]["correct_to_incorrect_n"], 0)
        self.assertGreater(m["bajo_adopta_ia_correcta"]["incorrect_to_correct_n"], 0)


if __name__ == "__main__":
    unittest.main()
