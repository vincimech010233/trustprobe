# TrustProbe

**A local prototype for studying how students judge and revise physics answers after seeing simulated AI feedback.**

[Español](README.es.md)

TrustProbe records a learner's initial answer and confidence, their judgment of a prepared AI answer, and their final answer and confidence. It also records the learner's explanation and response to a parallel exercise. The prototype uses scripted responses; it does not call an AI model or an external service.

## Status

**Verified as a software prototype. Not validated as an educational measurement tool.** Its synthetic checks show how the software behaves under selected conditions. They do not show that TrustProbe changes learning, measures trust reliably, or works with real students.

## Run locally

Requires Python 3.10 or newer. The app uses the Python standard library.

```bash
python3 -m trustprobe.web --port 8765
```

Open <http://127.0.0.1:8765>. The local database is stored under `var/`. Do not enter personal information. The project has no accounts or external service connection.

## Verify

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
PYTHONPATH=. python3 scripts/simulate.py
python3 data/build_dataset.py  # regenerates data/exercises.json; review the diff
```

The sample exercises and generated validation results are synthetic. See [`results/`](results/) and the design and limitations notes in [`docs/`](docs/).

## Research and limits

TrustProbe can record answer changes before and after simulated feedback. That change alone does not prove the feedback caused the change. Testing with real learners, research ethics review, and evidence of measurement validity would be needed before using it for educational conclusions.

This repository contains the prototype, tests, synthetic exercises, and selected design notes. It does not claim educational effectiveness or market demand.
