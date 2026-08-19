# RankF_O run — `kevinsawicki/http-request` (Phase 3)

Applying a from-scratch reimplementation of **RankF_O** (Rahman et al., RankF paper) to our own real
Phase 2 data — no third-party artifact, no GPU, pure Python.

## Setup
| Item | Value |
|------|-------|
| Engine | RankF_O reimplementation ([rankf/rankf_o.py](../../../rankf/rankf_o.py)) |
| Input data | Our own [iDFlakies Phase 2 run](../../idflakies/http-request/findings.md) on this project |
| Candidates ranked | All 163 tests in the `lib` module (minus the OD test itself) |
| OD tests processed | All **28** tests iDFlakies detected |
| Heuristic / strategy shown | `plus_one` / `combined` (the paper's best-performing combo for RankF_O) |
| Date | 2026-08-19 |

## Why RankF_O and not RankF_L
RankF_L requires fine-tuning a BigBird LLM on a GPU (per the paper, an RTX A5000). RankF_O only needs
test-order execution data — exactly what iDFlakies already gave us in Phase 2 — so it's the only
engine feasible to run here.

## The data, concretely
For each OD test, we scanned all 10 of iDFlakies' `round*.json` detection files and collected every
**distinct** `(order, result)` observation it recorded — `order` = the tests that ran before it,
`result` = whether it passed or failed in that order. Example for `basicProxyAuthentication`:

| Observations | Passing orders | Failing orders |
|---|---|---|
| 8 distinct | 1 (19 tests before it) | 7 (ranging 29–148 tests before it) |

This is real, genuinely observed data — not synthetic.

## Result: ranking speed
```
Total time to rank ALL 28 OD tests x all 15 heuristic/strategy combinations: 268.9 ms
```
i.e. **under 10ms per OD test** to produce a full ranking of ~162 candidates. Compare this to the
`idflakies:minimize` delta-debugging baseline: the RankF paper's own evaluation table lists **this
same project** (their row M19) at **~17.8s (delta-debugging) to ~66.8s (one-by-one)** *per test* to
find a polluter. RankF_O is roughly **1,000–5,000x faster** here, entirely consistent with the paper's
core claim.

## Result: the ranking itself — a clear, verifiable pattern

Full per-test results: [`rankings.json`](rankings.json) (top-10 candidates per test, all 15
heuristic/strategy combos) and [`summary.csv`](summary.csv) (one row per OD test).

**Striking finding:** the single test `customConnectionFactory` is ranked **#1 (or tied #1) for
11 of the 28 OD tests** — e.g.:

| OD test | Top-1 candidate | positive score | negative score |
|---|---|---|---|
| `basicProxyAuthentication` | `customConnectionFactory` | 7.00 | 0.00 |
| `singleVerifier` | `customConnectionFactory` (tied) | 4.00 | 0.00 |
| `getWithMappedQueryParams` | `customConnectionFactory` | — | — |
| `postWithMappedQueryParams` | `customConnectionFactory` | — | — |
| *(7 more, see summary.csv)* | `customConnectionFactory` | — | — |

For `basicProxyAuthentication`: `customConnectionFactory` appeared in **all 7 failing orders** and
**0 of the 1 passing order** — a maximally clean positive/negative split.

## Manual sanity check against the real source code

We cloned the project at the pinned SHA and inspected `HttpRequestTest.java`:

```java
public void customConnectionFactory() throws Exception {
    ConnectionFactory factory = new ConnectionFactory() {
        public HttpURLConnection create(URL otherUrl) throws IOException {
            return (HttpURLConnection) new URL(url).openConnection();  // hijacks ALL future requests
        }
    };
    HttpRequest.setConnectionFactory(factory);   // <-- mutates a STATIC field on HttpRequest!
    int code = get("http://not/a/real/url").code();
    assertEquals(200, code);
}
```

`HttpRequest.setConnectionFactory(...)` sets a **static field** on the `HttpRequest` class — global,
shared state. Once `customConnectionFactory` runs, *every other test* that makes a normal HTTP request
afterward gets silently rerouted through the hijacked factory, breaking it. This is a textbook
**polluter** in RankF's own terminology (from the RankF paper: *"the test that 'pollutes' the shared
state in the failing test-order of a victim is a polluter"*).

We also spotted a companion test, `nullConnectionFactory`, which calls
`HttpRequest.setConnectionFactory(null)` — plausibly a **cleaner/reset** that explains why the many
victim tests pass when a test resetting this static field runs before them instead.

**RankF_O found this using only pass/fail-per-order data — zero code analysis** — and it points at
exactly the mechanism a source-code read confirms. That is a genuinely encouraging (if informal)
validation of the technique.

## Honest limitations
- We do **not** have verified ground-truth "this is the actual polluter" labels for this project.
  `idflakies:minimize`/iFixFlakies (which would compute this) requires building the tool from source
  (never published beyond `2.0.0` on Maven Central) — we deliberately skipped that detour. So we
  cannot report the paper's precise "rank of the true OD-relevant test" accuracy metric here.
- The manual source-code check above is a **plausibility check on 2 tests**, not a systematic
  validation across all 28 — but the "appears in 7/7 failing orders, 0/1 passing order" signal, plus
  the static-field mechanism it points to, is strong informal evidence RankF_O is working correctly.

## Files in this folder
- `rankings.json` — full output: per OD test, top-10 candidates for all 5 heuristics × 3 strategies,
  plus observation counts and ranking time.
- `summary.csv` — one row per OD test: observation counts, top-1 candidate, ranking time.
