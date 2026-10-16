import json
import math
import random
from pathlib import Path

DATASET = Path(__file__).resolve().parents[1] / "data" / "exercises.json"
CATEGORIES = ("formula", "relacion_invertida", "signo", "unidades", "conservacion", "supuesto_invalido", "ninguno", "no_se")
CONDITIONS = ("ai_correct", "ai_incorrect", "no_ai_control")


def load_items(path=DATASET):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def select_trials(items, seed):
    """One per area, four incorrect and three correct, stable for a seed."""
    rng = random.Random(seed)
    areas = sorted({x["area"] for x in items})
    chosen = [rng.choice([x for x in items if x["area"] == a]) for a in areas]
    rng.shuffle(chosen)
    wrong_positions = set(rng.sample(range(len(chosen)), 4))
    return [(x["id"], "wrong" if i in wrong_positions else "correct") for i, x in enumerate(chosen)]


def numeric_score(value, unit, expected, expected_unit):
    try:
        n = float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return False
    return math.isfinite(n) and math.isclose(n, expected, rel_tol=0.01, abs_tol=0.01) and str(unit).strip() == expected_unit


def usable_answer(value, unit):
    if not str(value or "").strip() or not str(unit or "").strip():
        return False
    try:
        return math.isfinite(float(str(value).replace(",", ".")))
    except (ValueError, TypeError):
        return False


def answers_match(value, unit, reference_value, reference_unit):
    if not usable_answer(value, unit) or not usable_answer(reference_value, reference_unit):
        return False
    return numeric_score(value, unit, float(str(reference_value).replace(",", ".")), str(reference_unit).strip())


def score_trial(item, variant, judgment, confidence, category, correction_value,
                correction_unit, transfer_value, transfer_unit, baseline_value="", baseline_unit="",
                final_value="", final_unit="", pre_ai_confidence=None, post_ai_confidence=None,
                condition=None):
    condition = condition or ("ai_correct" if variant == "correct" else "ai_incorrect")
    if condition not in CONDITIONS:
        raise ValueError("invalid condition")
    truth = None if condition == "no_ai_control" else condition == "ai_correct"
    decision_correct = ((judgment == "correct") == truth if judgment != "unsure" else False) if truth is not None else None
    correction = (truth is False and judgment == "incorrect" and category == item["wrong"][0]["category"]
                  and numeric_score(correction_value, correction_unit, item["correct"]["value"], item["correct"]["unit"]))
    transfer = numeric_score(transfer_value, transfer_unit, item["transfer"]["value"], item["transfer"]["unit"])
    baseline_missing = not usable_answer(baseline_value, baseline_unit)
    final_missing = not usable_answer(final_value, final_unit)
    baseline = None if baseline_missing else numeric_score(baseline_value, baseline_unit, item["correct"]["value"], item["correct"]["unit"])
    final = None if final_missing else numeric_score(final_value, final_unit, item["correct"]["value"], item["correct"]["unit"])
    ai_answer = item["correct"] if truth is True else item["wrong"][0] if truth is False else None
    baseline_matches_ai = answers_match(baseline_value, baseline_unit, ai_answer["value"], ai_answer["unit"]) if ai_answer and not baseline_missing else None
    matches_baseline = answers_match(final_value, final_unit, baseline_value, baseline_unit) if not (baseline_missing or final_missing) else None
    matches_ai = answers_match(final_value, final_unit, ai_answer["value"], ai_answer["unit"]) if ai_answer and not final_missing else None
    transition = ("correct" if baseline else "incorrect") + "_to_" + ("correct" if final else "incorrect") if baseline is not None and final is not None else "unclassified_missing"
    return dict(decision_correct=decision_correct, abstained=judgment == "unsure",
                false_rejection=truth is True and judgment == "incorrect",
                correction_correct=correction,
                parallel_item_correct=transfer, baseline_correct=baseline,
                final_correct=final, baseline_missing=baseline_missing, final_missing=final_missing,
                truth_correct=truth, condition=condition, confidence=confidence,
                pre_ai_confidence=pre_ai_confidence, post_ai_confidence=post_ai_confidence,
                confidence_change=(post_ai_confidence - pre_ai_confidence) if pre_ai_confidence is not None and post_ai_confidence is not None else None,
                judgment=judgment, transition=transition,
                baseline_matches_ai=baseline_matches_ai,
                final_matches_baseline=matches_baseline, final_matches_ai=matches_ai,
                observed_answer_switch=(not matches_baseline) if matches_baseline is not None else None)


def metrics(scores):
    n = len(scores)
    if not n:
        return {}
    wrong = [s for s in scores if s["truth_correct"] is False]
    right = [s for s in scores if s["truth_correct"] is True]
    corrected = [s for s in wrong if s["correction_correct"]]
    advised = wrong + right
    committed = [s for s in scores if s["decision_correct"] is not None and not s["abstained"]]
    initial_success_wrong_ai = [s for s in wrong if s["baseline_correct"]]
    initial_error_right_ai = [s for s in right if s["baseline_correct"] is False]
    complete = [s for s in scores if s["baseline_correct"] is not None and s["final_correct"] is not None]
    final_observed = [s for s in scores if s["final_correct"] is not None]
    initial_correct = [s for s in complete if s["baseline_correct"]]
    initial_incorrect = [s for s in complete if not s["baseline_correct"]]
    wrong_ai_final = [s for s in wrong if s["baseline_matches_ai"] is False and s["final_matches_ai"] is not None]
    right_ai_final = [s for s in right if s["baseline_matches_ai"] is False and s["final_matches_ai"] is not None]
    positive_advice = [s for s in initial_error_right_ai if s["final_matches_ai"] is not None and s["final_matches_baseline"] is not None]
    negative_advice = [s for s in initial_success_wrong_ai if s["final_matches_ai"] is not None and s["final_matches_baseline"] is not None]
    rair_eligible = [s for s in positive_advice if s["final_matches_ai"] or s["final_matches_baseline"]]
    rsr_eligible = [s for s in negative_advice if s["final_matches_ai"] or s["final_matches_baseline"]]
    switches = [s for s in complete if s["observed_answer_switch"] is not None]
    confidence_pairs = [s for s in scores if s["confidence_change"] is not None]
    def rate(rows, predicate):
        return sum(predicate(s) for s in rows) / len(rows) if rows else None
    # Confidence is certainty that one's committed decision is right.
    return dict(n=n, decision_accuracy=sum(s["decision_correct"] for s in advised) / len(advised) if advised else None,
                abstention_rate=sum(s["abstained"] for s in advised) / len(advised) if advised else None,
                error_detection_rate=sum(s["decision_correct"] for s in wrong) / len(wrong) if wrong else None,
                false_rejection_rate=sum(s["false_rejection"] for s in right) / len(right) if right else None,
                brier=sum((s["confidence"] / 100 - int(s["decision_correct"])) ** 2 for s in committed) / len(committed) if committed else None,
                confidence_gap=sum(s["confidence"] / 100 - int(s["decision_correct"]) for s in committed) / len(committed) if committed else None,
                correction_score=sum(s["correction_correct"] for s in wrong) / len(wrong) if wrong else None,
                parallel_item_accuracy=sum(s["parallel_item_correct"] for s in scores) / n,
                parallel_item_after_correction_accuracy=sum(s["parallel_item_correct"] for s in corrected) / len(corrected) if corrected else None,
                physics_knowledge_score=sum(s["baseline_correct"] is True for s in scores) / n,
                final_answer_accuracy=rate(final_observed, lambda s: s["final_correct"] is True),
                final_observed_n=len(final_observed),
                # Observable appraisal signals, not final-answer switching or causal AI effects.
                harmful_endorsement_signal=sum(s["judgment"] == "correct" for s in initial_success_wrong_ai) / len(initial_success_wrong_ai) if initial_success_wrong_ai else None,
                resistance_appraisal_signal=sum(s["judgment"] == "incorrect" for s in initial_success_wrong_ai) / len(initial_success_wrong_ai) if initial_success_wrong_ai else None,
                correct_advice_recognition_signal=sum(s["judgment"] == "correct" for s in initial_error_right_ai) / len(initial_error_right_ai) if initial_error_right_ai else None,
                complete_pair_n=len(complete), missing_pair_n=n-len(complete),
                correct_to_incorrect_n=sum(s["transition"] == "correct_to_incorrect" for s in complete),
                incorrect_to_correct_n=sum(s["transition"] == "incorrect_to_correct" for s in complete),
                correct_to_correct_n=sum(s["transition"] == "correct_to_correct" for s in complete),
                incorrect_to_incorrect_n=sum(s["transition"] == "incorrect_to_incorrect" for s in complete),
                correct_to_incorrect_rate=rate(complete, lambda s: s["transition"] == "correct_to_incorrect"),
                incorrect_to_correct_rate=rate(complete, lambda s: s["transition"] == "incorrect_to_correct"),
                correct_to_correct_rate=rate(complete, lambda s: s["transition"] == "correct_to_correct"),
                incorrect_to_incorrect_rate=rate(complete, lambda s: s["transition"] == "incorrect_to_incorrect"),
                correct_to_incorrect_rate_given_initial_correct=rate(initial_correct, lambda s: s["final_correct"] is False),
                incorrect_to_correct_rate_given_initial_incorrect=rate(initial_incorrect, lambda s: s["final_correct"] is True),
                observed_answer_switch_rate=rate(switches, lambda s: s["observed_answer_switch"]),
                wrong_ai_adoption_rate=rate(wrong_ai_final, lambda s: s["final_matches_ai"]),
                correct_ai_adoption_rate=rate(right_ai_final, lambda s: s["final_matches_ai"]),
                rair=rate(rair_eligible, lambda s: s["final_matches_ai"]),
                rair_eligible_n=len(rair_eligible), rair_third_or_missing_n=len(initial_error_right_ai)-len(rair_eligible),
                rsr=rate(rsr_eligible, lambda s: s["final_matches_baseline"]),
                rsr_eligible_n=len(rsr_eligible), rsr_third_or_missing_n=len(initial_success_wrong_ai)-len(rsr_eligible),
                mean_confidence_change=sum(s["confidence_change"] for s in confidence_pairs) / len(confidence_pairs) if confidence_pairs else None)


def public_trial(item, variant):
    if variant == "correct":
        response = item["correct"]["explanation"]
    else:
        response = item["wrong"][0]["text"]
    return dict(id=item["id"], area=item["area"], concept=item["concept"],
                difficulty=item["difficulty"], prompt=item["prompt"], ai_response=response,
                categories=CATEGORIES)
