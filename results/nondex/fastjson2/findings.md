# NonDex run — `alibaba/fastjson2`

Reproduction of known **Implementation-Dependent (ID)** flaky tests from IDoFT using NonDex, run via
**Docker Compose** (no local Java).

## Environment
| Item | Value |
|------|-------|
| Tool | NonDex Maven plugin **2.2.1** |
| Container image | `flaky-nondex` (built from `maven:3.9-eclipse-temurin-11`, JDK 11) |
| Runner | `docker compose --profile fastjson2 up` |
| Project | [`alibaba/fastjson2`](https://github.com/alibaba/fastjson2) |
| SHA | `450d9fe5a39f9f911f06882a302a585b93a586fa` |
| Module | `core` |
| Date | 2026-08-19 |

## Command
```powershell
# from the repo root
docker compose --profile fastjson2 up
```
which runs, inside the container:
```bash
mvn -pl core -DfailIfNoTests=false \
    -Dtest=MapSortFieldTest,ObjectWriterSetTest,Issue507,Issue586,Issue1494 \
    edu.illinois:nondex-maven-plugin:2.2.1:nondex
```

## Result
- **Clean run (no shuffling): all selected tests PASS.**
- **Under shuffled seeds (FULL mode; seeds 933178, 974622, 1016066): 6 tests FAIL.**

The 6 implementation-dependent flaky tests found "across all seeds":

| # | Test |
|---|------|
| 1 | `com.alibaba.fastjson2.issues.Issue507#test` |
| 2 | `com.alibaba.fastjson2.issues.Issue507#test1` |
| 3 | `com.alibaba.fastjson2.writer.ObjectWriterSetTest#testJsonbSet` |
| 4 | `com.alibaba.fastjson2.features.MapSortFieldTest#test` |
| 5 | `com.alibaba.fastjson2.issues.Issue586#test` |
| 6 | `com.alibaba.fastjson2.issues_1000.Issue1494#test` |

## Cross-check against IDoFT
All 6 tests appear in IDoFT's `pr-data.csv` under **Category `ID`** for `alibaba/fastjson2` at this
exact SHA (module `core`, which has 21 ID tests total; we targeted 5 classes covering these 6).

## Root cause (why they flake)
Same family of causes as the gson run: the tests assert on serialized JSON whose key/element order
depends on **hash-based iteration** (`HashMap`/`HashSet`) or **reflection order**. The test names are
telling — `MapSortFieldTest` and `ObjectWriterSetTest` (a `Set`) are directly about map/set ordering.
NonDex legally permutes these under-determined orders, so the output no longer matches the hard-coded
expected string.

## Notes
- fastjson2 is a large multi-module project; targeting `-pl core` with a `-Dtest` filter kept the run
  to ~3 minutes (including dependency download).
- This run also validates the `docker-compose.yml` workflow end-to-end.

## Files in this folder
- `nondex-fastjson2.log` — full Maven/NonDex console output.
- `nondex-data/` — NonDex's `.nondex` output: `clean_…` run + seeded runs (`config`, `failures`,
  per-class results, JUnit XMLs, `test_results.html`).
