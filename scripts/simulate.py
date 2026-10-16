"""Synthetic software validation. No human observations are generated."""
import json
import tempfile
from pathlib import Path

from trustprobe.core import load_items, metrics
from trustprobe.store import Store

ROOT = Path(__file__).resolve().parents[1]
PROFILES = (
    "alto_resiste_ia_erronea", "alto_adopta_ia_erronea",
    "bajo_adopta_ia_correcta", "bajo_ignora_ia_correcta", "mixto_calibrado",
)


def response(profile, position, item, variant):
    correct, wrong = item["correct"], item["wrong"][0]
    truth = variant == "correct"
    if profile == "alto_resiste_ia_erronea":
        baseline, final = correct, correct
        judgment = "correct" if truth else "incorrect"
    elif profile == "alto_adopta_ia_erronea":
        baseline, final = correct, correct if truth else wrong
        judgment = "correct"
    elif profile == "bajo_adopta_ia_correcta":
        baseline, final = wrong, correct if truth else wrong
        judgment = "correct"
    elif profile == "bajo_ignora_ia_correcta":
        baseline, final = wrong, wrong
        judgment = "incorrect" if truth else "correct"
    else:
        baseline = correct if position % 2 == 0 else wrong
        final = (correct if truth else baseline) if position % 3 else (wrong if not truth else baseline)
        judgment = ("correct" if truth else "incorrect") if position % 3 else "unsure"
    pre_confidence = 90 if baseline is correct else 35
    post_confidence = 90 if final is correct else 40
    baseline_data = dict(value=str(baseline["value"]), unit=baseline["unit"], pre_ai_confidence=pre_confidence)
    judgment_data = dict(judgment=judgment, ai_judgment_confidence=80 if judgment != "unsure" else 30)
    final_data = dict(value=str(final["value"]), unit=final["unit"], post_ai_confidence=post_confidence,
                      reason="Respuesta sintética predefinida.")
    diagnosis_data = dict(category=wrong["category"] if judgment == "incorrect" and not truth else "no_se",
                          correction_value=str(correct["value"]) if judgment == "incorrect" and not truth else "",
                          correction_unit=correct["unit"] if judgment == "incorrect" and not truth else "",
                          explanation="Diagnóstico sintético predefinido.")
    parallel = item["transfer"] if final is correct else dict(value=item["transfer"]["value"] + max(10, abs(item["transfer"]["value"]) * .2), unit=item["transfer"]["unit"])
    parallel_data = dict(value=str(parallel["value"]), unit=parallel["unit"])
    return baseline_data, judgment_data, final_data, diagnosis_data, parallel_data


def run_profile(store, profile, seeds=range(20)):
    collected = []
    items = {x["id"]: x for x in load_items()}
    for seed in seeds:
        sid = store.start(seed)
        for position in range(7):
            with store.db() as db:
                row = db.execute("SELECT trials FROM sessions WHERE id=?", (sid,)).fetchone()
            item_id, variant = json.loads(row["trials"])[position]
            baseline, judgment, final, diagnosis, parallel = response(profile, position, items[item_id], variant)
            store.submit_baseline(sid, baseline)
            store.submit_judgment(sid, judgment)
            store.submit_final(sid, final)
            store.submit_diagnosis(sid, diagnosis)
            store.submit_transfer(sid, parallel)
        collected.extend(store.results(sid)["trials"])
    return metrics(collected)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp) / "simulation.sqlite3")
        output = {p: run_profile(store, p) for p in PROFILES}
    target = ROOT / "results"
    target.mkdir(exist_ok=True)
    (target / "synthetic-validation.json").write_text(json.dumps({"label": "synthetic validation", "seeds": list(range(20)), "profiles": output}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    names = ("n", "complete_pair_n", "correct_to_incorrect_n", "incorrect_to_correct_n", "correct_to_correct_n", "incorrect_to_incorrect_n", "observed_answer_switch_rate", "wrong_ai_adoption_rate", "correct_ai_adoption_rate", "rair", "rair_eligible_n", "rsr", "rsr_eligible_n", "mean_confidence_change", "parallel_item_accuracy")
    rows = ["# Synthetic validation", "", "Perfiles programados, 20 sesiones × 7 ítems cada uno. No son datos de estudiantes ni evidencia causal.", "", "| Perfil | " + " | ".join(names) + " |", "|---|" + "---:|" * len(names)]
    for p, m in output.items():
        rows.append("| " + p + " | " + " | ".join(f"{m[k]:.3f}" if isinstance(m[k], float) else str(m[k]) if m[k] is not None else "n/a" for k in names) + " |")
    rows += ["", "RAIR/RSR son adaptaciones estrictas que excluyen terceras respuestas. Las transiciones B→F son observadas en perfiles programados; no demuestran influencia causal ni validez educativa."]
    (target / "synthetic-validation.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
