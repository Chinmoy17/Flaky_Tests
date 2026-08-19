# Flaky_Tests — tool exploration

Hands-on exploration of the flaky-test tooling referenced by Prof. Shanto Rahman, run reproducibly
in Docker (no local Java toolchain required). Companion reading notes for the three papers
(**RankF**, **FlakeSync**, **TSVD4J**) are in [`Papers/Paper-Notes.md`](Papers/Paper-Notes.md).

## Tool runs

| Tool | Purpose | Status | Findings |
|------|---------|--------|----------|
| **NonDex** | Detect *implementation-dependent* (ID) flaky tests via legal shuffling of under-determined Java APIs | ✅ Done | [results/nondex/gson/findings.md](results/nondex/gson/findings.md) |
| **iDFlakies** | Detect & classify *order-dependent* (OD) vs *non-order-dependent* (NOD) flaky tests via random test-orders | ⏳ Next | — |
| **RankF artifact** | Rank OD-relevant tests (read paper + run lightweight `RankF_O`) | ⏳ Planned | — |

## Highlight so far
Ran **NonDex 2.2.1** on **`google/gson`** (`e685705b`) inside `maven:3.9-eclipse-temurin-11` and
reproduced **12 known ID flaky tests** — all catalogued in IDoFT. Details and root-cause analysis:
[results/nondex/gson/findings.md](results/nondex/gson/findings.md).

## Repository layout
```
Papers/                 paper PDFs + Paper-Notes.md (RankF-focused notes)
results/
  nondex/gson/          NonDex run: findings.md + raw .nondex output + console log
.gitignore
```

## Reproducing a NonDex run (summary)
```bash
docker run -dit --name nondex-run -w /work maven:3.9-eclipse-temurin-11 bash
docker exec nondex-run bash -lc "cd /work && git clone https://github.com/google/gson.git && \
  cd gson && git checkout e685705b2bf3ae174958612a185bd231c0e0c5d9 && \
  mvn -pl gson -DfailIfNoTests=false -Dtest=MapTest,FieldNamingTest,CollectionTest \
      edu.illinois:nondex-maven-plugin:2.2.1:nondex"
```
> NonDex 2.2.1 needs **JDK 9+** (JDK 8 fails with `Unrecognized option: --add-exports`).
