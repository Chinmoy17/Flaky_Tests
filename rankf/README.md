# RankF_O reimplementation

A from-scratch, dependency-free Python reimplementation of **RankF_O**, one of the two ranking
engines from Rahman et al.'s *"Ranking Relevant Tests for Order-Dependent Flaky Tests"* (RankF) paper.

## Why reimplement instead of running the official artifact?

- **RankF_L** (the other engine) fine-tunes a BigBird LLM and needs a GPU — not feasible here.
- The official artifact (`sites.google.com/view/ranking-od-relevant-tests`) was unreachable via
  automated fetch (blocked by Google's bot detection), and no public GitHub mirror was found under
  the obvious research-group orgs.
- **RankF_O itself is just arithmetic** over test-order execution data — simple enough to reimplement
  faithfully from the paper's own formulas (Section III-B/III-C), and doing so is arguably a *deeper*
  demonstration of understanding the technique than running someone else's black box.

## Files

| File | Purpose |
|------|---------|
| `rankf_o.py` | The algorithm: 5 scoring heuristics + 3 ranking strategies (pure stdlib, no deps). |
| `run_on_http_request.py` | Applies it to **our own real Phase 2 data** (iDFlakies' detect() output on `kevinsawicki/http-request`) for all 28 OD tests. |

## Run it

```powershell
python rankf/run_on_http_request.py
```

Reads from `results/idflakies/http-request/dtfixingtools/` (already committed from Phase 2) and
writes to `results/rankf/http-request/{rankings.json,summary.csv}`.

## The algorithm, in brief

For an OD test, given several **observations** — each a `(order, result)` pair where `order` is the
list of tests that ran *before* it and `result` is PASS or FAIL — score every test that appears in
`order`:

- **Plus One (+1)**: `score += 1` per occurrence.
- **#Methods (#M)**: `score += 1/len(order)` (test-orders with fewer preceding tests count more).
- **Distance (D)**: `score += 1/distance_to_od_test` (closer tests count more).
- **Combined (+1, D)** / **Combined (#M, D)**: primary heuristic + Distance as a tiebreaker.

A **failing** order contributes to a candidate's *positive* score (evidence it's OD-relevant); a
**passing** order contributes to its *negative* score. Three strategies then rank all candidates:
`positive` (descending), `negative` (ascending), `combined` (positive − negative, descending) — the
paper found `combined` works best for RankF_O, which is why `run_on_http_request.py` uses it as the
headline result.

## Honest limitation

We do **not** have verified ground-truth "this is the actual polluter" labels for this project —
`idflakies:minimize`/iFixFlakies required building the tool from source, which we skipped (see
[results/idflakies/http-request/findings.md](../results/idflakies/http-request/findings.md)). So we
can demonstrate the ranking mechanism, its speed, and sanity-check it by hand against the real source
code (see [results/rankf/http-request/findings.md](../results/rankf/http-request/findings.md)) — but
we cannot claim to reproduce the paper's exact "rank of the true OD-relevant test" accuracy metric for
this project.
