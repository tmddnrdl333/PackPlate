"""Project 3 M0: does the daily meal planner (P3 M2) work for restricted students?

Plan: docs/p3-m0-planner-eval.md. It calls the planner the API uses
(backend/app/services/planner.py), so backend/ goes on the import path, as in
the original team's eval/ and eval_loop2/. It reuses eval_loop2's snapshot
reader and person simulator rather than copying them, so both evals turn
snapshot rows into dishes and draw restrictions the same way.
"""

import sys
from pathlib import Path

_BACKEND = str(Path(__file__).resolve().parent.parent / "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)
