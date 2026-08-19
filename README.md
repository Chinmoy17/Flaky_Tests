# Flaky_Tests — tool exploration

Hands-on exploration of the flaky-test tooling referenced by Prof. Shanto Rahman, run reproducibly
in Docker (no local Java toolchain required). Companion reading notes for the three papers
(**RankF**, **FlakeSync**, **TSVD4J**) are in [`Papers/Paper-Notes.md`](Papers/Paper-Notes.md).

## Tool runs

| Tool | Purpose | Status | Findings |
|------|---------|--------|----------|
| **NonDex** | Detect *implementation-dependent* (ID) flaky tests via legal shuffling of under-determined Java APIs | ✅ Done | [gson](results/nondex/gson/findings.md) · [fastjson2](results/nondex/fastjson2/findings.md) |
| **iDFlakies** | Detect & classify *order-dependent* (OD) vs *non-order-dependent* (NOD) flaky tests via random test-orders | ⏳ Next | — |
| **RankF artifact** | Rank OD-relevant tests (read paper + run lightweight `RankF_O`) | ⏳ Planned | — |

## Highlight so far
Ran **NonDex 2.2.1** (in Docker, JDK 11) on two IDoFT projects and reproduced **18 catalogued ID
flaky tests** in total:
- **`google/gson`** (`e685705b`) — 12 tests → [findings](results/nondex/gson/findings.md)
- **`alibaba/fastjson2`** (`450d9fe5`) — 6 tests → [findings](results/nondex/fastjson2/findings.md)

All fail only when NonDex legally permutes `HashMap`/`HashSet` iteration and reflection field order.

## Reproduce (Docker Compose — one command)
From the repo root:
```
docker compose --profile gson      up   # google/gson       -> 12 ID tests
docker compose --profile fastjson2 up   # alibaba/fastjson2 ->  6 ID tests
```
Results land in `results/nondex/<project>/`. A non-zero exit is **expected** — that is how NonDex
signals it found flaky tests. See [docker/nondex/README.md](docker/nondex/README.md) for the plain
`docker build` / `docker run` equivalents and how to add new targets.

> NonDex 2.2.1 needs **JDK 9+** (JDK 8 fails with `Unrecognized option: --add-exports`), which is why
> the image is JDK 11.

## Repository layout
```
Papers/                 paper PDFs + Paper-Notes.md (RankF-focused notes)
docker/nondex/          Dockerfile + run-nondex.sh (the reproducible runner)
docker-compose.yml      one-command targets (profiles: gson, fastjson2)
results/nondex/         NonDex findings per project (findings.md + raw .nondex data + log)
```
