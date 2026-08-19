"""
rankf_o.py -- A faithful, from-scratch reimplementation of RankF_O.

RankF_O is one of the two ranking engines from:
    Rahman, Chanumolu, Rafi, Shi, Lam. "Ranking Relevant Tests for
    Order-Dependent Flaky Tests." (the RankF paper)

Given an order-dependent (OD) test and a set of *test-order execution
observations* (i.e. "in this order, with these tests running before it, the OD
test PASSED/FAILED"), RankF_O scores every other test in the suite by how
likely it is to be the "OD-relevant test" (the polluter for a victim, or the
state-setter for a brittle) -- WITHOUT needing to run anything. It's pure
arithmetic over data you already have from a detection tool like iDFlakies.

This module has no third-party dependencies (pure Python stdlib) and is
independent of any particular project -- see run_on_http_request.py for how
it's applied to our own real Phase 2 data.

---------------------------------------------------------------------------
THE FIVE SCORING HEURISTICS (Section III-B of the paper)
---------------------------------------------------------------------------
For a processed test-order, let `order` = the list of tests that ran BEFORE
the OD test (nearest-last), and let n = len(order) (this plays the role of
the paper's `indexOf(ot)`, the OD test's position in the order).
For a candidate test `gt` sitting at 1-based position `p` within `order`
(so p=n means gt is the very last test before the OD test, i.e. distance 1):

    Plus One (+1)          : score += 1                         for every gt
    #Methods (#M)           : score += 1 / n                     for every gt
    Distance (D)             : score += 1 / (n - p + 1)           for every gt
    Combined (+1, D)        : Plus One score, Distance breaks ties
    Combined (#M, D)         : #Methods score, Distance breaks ties

If the OD test FAILED in that order, the increment goes to the test's
POSITIVE class score (evidence it's OD-relevant). If the OD test PASSED, the
increment goes to its NEGATIVE class score (evidence it's NOT OD-relevant).

---------------------------------------------------------------------------
THE THREE RANKING STRATEGIES (Section III-C)
---------------------------------------------------------------------------
    positive  : sort by positive score, descending  (most failures-before first)
    negative  : sort by negative score, ascending   (fewest passes-before first)
    combined  : sort by (positive - negative), descending

The paper found "combined" works best for RankF_O (Section VI), which is why
run_on_http_request.py uses it as the headline result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

HEURISTICS = (
    "plus_one",
    "num_methods",
    "distance",
    "combined_plus_one_distance",
    "combined_num_methods_distance",
)
STRATEGIES = ("positive", "negative", "combined")


@dataclass
class Observation:
    """One test-order execution observation for a given OD test.

    `order` = tests that ran BEFORE the OD test, nearest-last.
    `result` = "PASS" if the OD test passed in this order, anything else
               (e.g. "ERROR"/"FAILURE") is treated as a failing order.
    """

    order: list[str]
    result: str

    @property
    def failed(self) -> bool:
        return self.result != "PASS"


@dataclass
class CandidateScore:
    test: str
    positive: float = 0.0
    negative: float = 0.0
    positive_tiebreak: float = 0.0
    negative_tiebreak: float = 0.0
    rank: int | None = None


def _increment_and_tiebreak(heuristic: str, n: int, position_1based: int) -> tuple[float, float]:
    """Return (score_increment, distance_tiebreak) for one candidate test."""
    distance = n - position_1based + 1  # 1 = adjacent to the OD test, n = first test in the order
    if heuristic == "plus_one":
        return 1.0, 0.0
    if heuristic == "num_methods":
        return (1.0 / n if n else 0.0), 0.0
    if heuristic == "distance":
        return 1.0 / distance, 0.0
    if heuristic == "combined_plus_one_distance":
        return 1.0, 1.0 / distance
    if heuristic == "combined_num_methods_distance":
        return (1.0 / n if n else 0.0), 1.0 / distance
    raise ValueError(f"unknown heuristic: {heuristic}")


def score_candidates(
    observations: Iterable[Observation], heuristic: str
) -> dict[str, CandidateScore]:
    """Compute positive/negative scores for every test seen in `observations`."""
    scores: dict[str, CandidateScore] = {}
    for obs in observations:
        n = len(obs.order)
        for i, test in enumerate(obs.order):
            pos_1based = i + 1
            inc, tie = _increment_and_tiebreak(heuristic, n, pos_1based)
            cs = scores.setdefault(test, CandidateScore(test=test))
            if obs.failed:
                cs.positive += inc
                cs.positive_tiebreak += tie
            else:
                cs.negative += inc
                cs.negative_tiebreak += tie
    return scores


def rank_candidates(
    all_candidates: Iterable[str],
    scores: dict[str, CandidateScore],
    strategy: str,
) -> list[CandidateScore]:
    """Rank every candidate test (even ones with a zero score) by `strategy`."""
    rows = [scores.get(t, CandidateScore(test=t)) for t in all_candidates]

    if strategy == "positive":
        rows.sort(key=lambda r: (-r.positive, -r.positive_tiebreak, r.test))
    elif strategy == "negative":
        rows.sort(key=lambda r: (r.negative, r.negative_tiebreak, r.test))
    elif strategy == "combined":
        rows.sort(
            key=lambda r: (
                -(r.positive - r.negative),
                -(r.positive_tiebreak - r.negative_tiebreak),
                r.test,
            )
        )
    else:
        raise ValueError(f"unknown strategy: {strategy}")

    for i, r in enumerate(rows, start=1):
        r.rank = i
    return rows


def rank(
    all_candidates: Iterable[str],
    observations: Iterable[Observation],
    heuristic: str = "plus_one",
    strategy: str = "combined",
) -> list[CandidateScore]:
    """Convenience one-shot: score then rank. Defaults match the paper's best combo."""
    observations = list(observations)
    scores = score_candidates(observations, heuristic)
    return rank_candidates(all_candidates, scores, strategy)
