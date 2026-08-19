"""
run_on_http_request.py -- Apply our RankF_O reimplementation to REAL data from
Phase 2 (iDFlakies detect() run on kevinsawicki/http-request).

For every one of the 28 OD tests iDFlakies found, this script:
  1. Loads every distinct (test-order, PASS/FAIL) observation iDFlakies
     recorded for it across its 10 detection rounds.
  2. Runs RankF_O (five heuristics x three strategies) to rank all other
     ~162 tests in the suite by likelihood of being the OD-relevant test
     (the polluter/state-setter).
  3. Times how long ranking takes (RankF_O's whole point: near-instant).

Output:
  results/rankf/http-request/rankings.json  -- full per-test rankings + timing
  results/rankf/http-request/summary.csv    -- one row per OD test: top candidate + time

Run with:  python rankf/run_on_http_request.py
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

from rankf_o import HEURISTICS, STRATEGIES, Observation, rank

REPO_ROOT = Path(__file__).resolve().parents[1]
DT_DIR = REPO_ROOT / "results" / "idflakies" / "http-request" / "dtfixingtools"
ROUNDS_DIR = DT_DIR / "detection-results" / "random-class-method"
ORIGINAL_ORDER = DT_DIR / "original-order"
OUT_DIR = REPO_ROOT / "results" / "rankf" / "http-request"


def load_all_test_names() -> list[str]:
    return [
        line.strip() for line in ORIGINAL_ORDER.read_text().splitlines() if line.strip()
    ]


def load_observations_for_all_tests() -> dict[str, list[Observation]]:
    """Scan every round*.json and collect deduped (order, result) observations
    per OD test name. Returns {test_name: [Observation, ...]}."""
    per_test: dict[str, dict[tuple, str]] = {}  # test -> {order_tuple: result} (dedupe)
    for f in sorted(ROUNDS_DIR.glob("round*.json")):
        data = json.loads(f.read_text())
        for entry in data.get("unfilteredTests", {}).get("dts", []):
            name = entry["name"]
            for kind in ("intended", "revealed"):
                o = entry.get(kind)
                if not o:
                    continue
                order_tuple = tuple(o["order"])
                per_test.setdefault(name, {})[order_tuple] = o["result"]

    return {
        name: [Observation(order=list(order), result=result) for order, result in orders.items()]
        for name, orders in per_test.items()
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_tests = load_all_test_names()
    observations_by_test = load_observations_for_all_tests()

    od_tests = sorted(observations_by_test.keys())
    print(f"Loaded {len(all_tests)} total tests; {len(od_tests)} have OD observations.")

    full_report: dict[str, dict] = {}
    summary_rows: list[dict] = []

    for od_test in od_tests:
        observations = observations_by_test[od_test]
        candidates = [t for t in all_tests if t != od_test]
        n_fail = sum(1 for o in observations if o.failed)
        n_pass = len(observations) - n_fail

        per_heuristic: dict[str, list] = {}
        t0 = time.perf_counter()
        for heuristic in HEURISTICS:
            for strategy in STRATEGIES:
                ranked = rank(candidates, observations, heuristic=heuristic, strategy=strategy)
                key = f"{heuristic}__{strategy}"
                per_heuristic[key] = [
                    {"rank": r.rank, "test": r.test, "positive": r.positive, "negative": r.negative}
                    for r in ranked[:10]
                ]
        elapsed_ms = (time.perf_counter() - t0) * 1000

        headline = per_heuristic["plus_one__combined"]
        full_report[od_test] = {
            "num_observations": len(observations),
            "num_failing_orders": n_fail,
            "num_passing_orders": n_pass,
            "ranking_time_ms_all_15_combos": round(elapsed_ms, 3),
            "top10_by_combo": per_heuristic,
        }
        summary_rows.append(
            {
                "od_test": od_test.rsplit(".", 1)[-1],
                "num_failing_orders": n_fail,
                "num_passing_orders": n_pass,
                "top1_candidate": headline[0]["test"].rsplit(".", 1)[-1] if headline else "",
                "ranking_time_ms": round(elapsed_ms, 3),
            }
        )

    (OUT_DIR / "rankings.json").write_text(json.dumps(full_report, indent=2))
    with (OUT_DIR / "summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    total_time = sum(r["ranking_time_ms"] for r in summary_rows)
    print(f"Ranked OD-relevant-test candidates for {len(od_tests)} OD tests.")
    print(f"Total time for ALL {len(od_tests)} tests x 15 heuristic/strategy combos: {total_time:.1f} ms")
    print(f"Wrote {OUT_DIR / 'rankings.json'} and {OUT_DIR / 'summary.csv'}")


if __name__ == "__main__":
    main()
