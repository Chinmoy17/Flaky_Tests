# Flaky_Tests — tool exploration

Hands-on exploration of the flaky-test tooling referenced by Prof. Shanto Rahman, run reproducibly
in Docker (no local Java toolchain required). Companion reading notes for the three papers
(**RankF**, **FlakeSync**, **TSVD4J**) are in [`Papers/Paper-Notes.md`](Papers/Paper-Notes.md).

## Tool runs

| Tool | Purpose | Status | Findings |
|------|---------|--------|----------|
| **NonDex** | Detect *implementation-dependent* (ID) flaky tests via legal shuffling of under-determined Java APIs | ✅ Done | [gson](results/nondex/gson/findings.md) · [fastjson2](results/nondex/fastjson2/findings.md) |
| **iDFlakies** | Detect *order-dependent* (OD) flaky tests via many random test-orders | ✅ Done | [http-request](results/idflakies/http-request/findings.md) |
| **RankF (RankF_O reimplementation)** | Rank OD-relevant tests (find the polluter/state-setter) from test-order data | ✅ Done | [http-request](results/rankf/http-request/findings.md) |

## Highlight so far
- **NonDex 2.2.1** on two IDoFT projects → reproduced **18 catalogued ID flaky tests**:
  - **`google/gson`** (`e685705b`) — 12 tests → [findings](results/nondex/gson/findings.md)
  - **`alibaba/fastjson2`** (`450d9fe5`) — 6 tests → [findings](results/nondex/fastjson2/findings.md)
  - All fail only when NonDex legally permutes `HashMap`/`HashSet` iteration and reflection field order.
- **iDFlakies 2.0.0** on `kevinsawicki/http-request` (`2d62a3e9`, iDFlakies' own README example) →
  **28/28 catalogued OD flaky tests reproduced (100% match)** →
  [findings](results/idflakies/http-request/findings.md). These tests' pass/fail outcome depends on
  which other tests ran before them (shared static state), unlike NonDex's within-run API shuffling.
- **RankF_O** (reimplemented from the paper's formulas — RankF_L needs a GPU we don't have) applied
  to our own real iDFlakies data → ranked candidate polluters for all 28 OD tests in **269ms total**
  → [findings](results/rankf/http-request/findings.md). Its #1 suspect, `customConnectionFactory`,
  checks out against the actual source: it mutates a static field (`HttpRequest.setConnectionFactory`)
  shared by every other test.

## Reproduce (Docker Compose — one command)
From the repo root:
```
docker compose --profile gson         up   # NonDex on google/gson            -> 12 ID tests
docker compose --profile fastjson2    up   # NonDex on alibaba/fastjson2       ->  6 ID tests
docker compose --profile http-request up   # iDFlakies on kevinsawicki/http-request -> 28 OD tests
```
Results land in `results/<tool>/<project>/`. A non-zero exit from the NonDex profiles is **expected**
— that is how NonDex signals it found flaky tests (iDFlakies exits 0 either way). See
[docker/nondex/README.md](docker/nondex/README.md) and [docker/idflakies/README.md](docker/idflakies/README.md)
for the plain `docker build` / `docker run` equivalents and how to add new targets.

RankF_O needs no Docker/Java at all — it's pure Python over data the iDFlakies run above already
produced:
```
python rankf/run_on_http_request.py
```
See [rankf/README.md](rankf/README.md) for how the reimplementation works.

> NonDex 2.2.1 needs **JDK 9+** (JDK 8 fails with `Unrecognized option: --add-exports`), which is why
> the image is JDK 11. `http-request`'s `pom.xml` hardcodes an obsolete Java 1.5 compiler level that
> modern JDKs reject; the iDFlakies runner patches it to 1.8 automatically (see its findings.md).

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
