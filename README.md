# Flaky_Tests — the story so far

# Flaky_Tests — the story so far

Hands-on work on **NonDex**, **iDFlakies**, and **RankF** — the tools and paper I found most
interesting — run reproducibly in Docker/Python, no local Java install needed. Reading notes on all
three papers, with a deep dive on **RankF**, are in [`Papers/Paper-Notes.md`](Papers/Paper-Notes.md).

For a structured what/why/how report with consolidated results tables, see
**[FINDINGS.md](FINDINGS.md)**. The chapters below tell the same story narratively.

## Chapter 1 — NonDex: tests that lie because Java never promised an order

The first thing to understand: a **flaky test** passes and fails on the exact same code — no changes,
different result. **NonDex** hunts a specific cause of this: code that secretly assumes an order Java
never actually guarantees, like the iteration order of a `HashMap`/`HashSet`, or the order
`Class.getDeclaredFields()` returns. It legally reshuffles those internals and re-runs the tests — if
a test breaks only when shuffled, it was relying on a lie.

I picked two real, IDoFT-catalogued targets and ran NonDex 2.2.1 against them in Docker:

- **`google/gson`** (`e685705b`) — 12 tests flip from PASS to FAIL under shuffling
- **`alibaba/fastjson2`** (`450d9fe5`) — 6 tests do the same

All 18 matched IDoFT's known list exactly. The clearest example: a test builds a `PriorityQueue` of
`[10, 20, 22]`, serializes it, and asserts the JSON is `[10,20,22]` — but a `PriorityQueue` never
promises that iteration order, so under NonDex's shuffling it comes out `[22,10,20]` instead, and the
hard-coded assertion breaks. → [gson findings](results/nondex/gson/findings.md) ·
[fastjson2 findings](results/nondex/fastjson2/findings.md)

**First real gotcha:** NonDex 2.2.1 needs JDK 9+; on JDK 8 it dies instantly with
`Unrecognized option: --add-exports`. Fixed by moving the Docker image to JDK 11.

## Chapter 2 — iDFlakies: tests that lie because of who ran before them

NonDex catches one kind of lie. There's a completely different one: a test that only fails because of
**which other tests ran before it** — shared static state, leftover files, a polluted singleton. That's
an **order-dependent (OD) flaky test**, and it needs a different tool: **iDFlakies**, which reruns a
project's *entire* suite in many random orders and watches for any test whose outcome flips.

I ran it on `kevinsawicki/http-request` (`2d62a3e9`) — fittingly, iDFlakies' own README example
project — across 10 random orders of its 163 tests. It found **28 order-dependent tests**, and for
each one it didn't just guess: it replayed the exact order that made the test fail and the exact order
that made it pass, confirming both reproduce on demand. All **28 matched IDoFT's catalogue — a perfect
100%.** → [findings](results/idflakies/http-request/findings.md)

I tried pushing one step further with `idflakies:minimize` (bundled iFixFlakies), which localizes the
*specific* polluting test via delta-debugging. It failed immediately — turns out **`2.0.0` (2022) is
the only version of the plugin ever published to Maven Central**; `minimize`/`fix` were added to the
tool's GitHub repo later and never released, so using them means building the tool itself from source.
I decided that detour wasn't worth it — which turned out to matter for the next chapter.

**Second gotcha:** this project's `pom.xml` hardcodes Java 1.5, which modern JDKs refuse to compile.
Patched automatically to 1.8 (a compiler-acceptance change only — doesn't touch behavior).

## Chapter 3 — RankF: finding the culprit without running anything

This is the paper I actually wanted to work with. **RankF**'s premise: once you know a test is
order-dependent, don't blindly rerun tests one-by-one or bisect your way to the culprit (what
`iDFlakies:minimize` tries to do) — **rank** every other test by *likelihood* of being the cause first,
using either a fine-tuned LLM (`RankF_L`) or lightweight test-order heuristics (`RankF_O`), then confirm
in ranked order. Much faster.

`RankF_L` needs a GPU to fine-tune BigBird — not available here. I tried to fetch the official
artifact site to at least try `RankF_O` as published, but Google Sites blocked the automated fetch
(bot detection) twice, and no GitHub mirror turned up in the obvious places. So I reimplemented
**RankF_O from scratch in pure Python**, straight from the paper's own formulas — arguably a better
test of actually understanding the technique than running someone else's black box anyway.

The satisfying part: I didn't need synthetic data. I fed it **the real test-order results iDFlakies
had just produced** in Chapter 2 — genuine (order, pass/fail) observations, no toy examples. It ranked
candidate culprits for all 28 OD tests, across 5 heuristics × 3 strategies, in **269 milliseconds
total**. One test, `customConnectionFactory`, came out ranked #1 (or tied #1) for **11 of the 28**
tests — a strikingly consistent signal. I cloned the actual source to check, and it wasn't a fluke:

```java
HttpRequest.setConnectionFactory(factory);   // mutates a STATIC field shared by every other test
```

RankF_O flagged the exact static-state mutation causing the pollution — using nothing but pass/fail
patterns, zero code analysis. → [findings](results/rankf/http-request/findings.md) ·
[how it works](rankf/README.md)

## What I'd want to work on

Of the three, **order-dependent flaky tests** is what pulled me in — specifically the gap between
*detecting* one (iDFlakies) and *explaining* one (RankF). Watching RankF_O nail the actual polluter
using only pass/fail patterns, with no understanding of the code at all, is what makes me want to dig
into how far that signal scales, and where it breaks (tests with more than one contributing culprit,
projects with much sparser test-order history, etc.).

## Reproduce it yourself
```
docker compose --profile gson         up   # NonDex on google/gson            -> 12 ID tests
docker compose --profile fastjson2    up   # NonDex on alibaba/fastjson2       ->  6 ID tests
docker compose --profile http-request up   # iDFlakies on kevinsawicki/http-request -> 28 OD tests
python rankf/run_on_http_request.py        # RankF_O over the iDFlakies data above (no Docker needed)
```
Results land in `results/<tool>/<project>/`. A non-zero exit from the NonDex profiles is **expected**
— that's how NonDex signals it found flaky tests. See [docker/nondex/README.md](docker/nondex/README.md),
[docker/idflakies/README.md](docker/idflakies/README.md), and [rankf/README.md](rankf/README.md) for
the plain `docker build`/`docker run` equivalents and how to point these at new targets.

## Repository layout
```
Papers/                 paper PDFs + Paper-Notes.md (RankF-focused notes)
docker/nondex/           Dockerfile + run-nondex.sh (the reproducible NonDex runner)
docker/idflakies/        Dockerfile + run-idflakies.sh (the reproducible iDFlakies runner)
docker-compose.yml       one-command targets (profiles: gson, fastjson2, http-request)
rankf/                   pure-Python RankF_O reimplementation (rankf_o.py + runner script)
results/nondex/          NonDex findings per project (findings.md + raw .nondex data + log)
results/idflakies/       iDFlakies findings per project (findings.md + raw dtfixingtools data + log)
results/rankf/           RankF_O findings per project (findings.md + rankings.json + summary.csv)
```

