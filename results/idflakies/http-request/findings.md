# iDFlakies run — `kevinsawicki/http-request`

Reproduction of known **Order-Dependent (OD)** flaky tests from IDoFT using iDFlakies, run via
**Docker Compose** (no local Java).

## Environment
| Item | Value |
|------|-------|
| Tool | iDFlakies Maven plugin **2.0.0** (`edu.illinois.cs:idflakies-maven-plugin`) |
| Container image | `flaky-idflakies` (built from `maven:3.9-eclipse-temurin-11`, JDK 11) |
| Runner | `docker compose --profile http-request up` |
| Project | [`kevinsawicki/http-request`](https://github.com/kevinsawicki/http-request) — this is the same
  project/SHA used as **iDFlakies' own canonical README example** |
| SHA | `2d62a3e9da726942a93cf16b6e91c0187e6c0136` |
| Module | `lib` |
| Detector | `random-class-method`, 10 rounds |
| Date | 2026-08-19 |

## Command
```powershell
# from the repo root
docker compose --profile http-request up
```
which runs, inside the container:
```bash
mvn -pl lib edu.illinois.cs:idflakies-maven-plugin:2.0.0:detect \
    -Ddetector.detector_type=random-class-method \
    -Ddt.randomize.rounds=10 \
    -Ddt.detector.original_order.all_must_pass=false
```

## What iDFlakies does (different from NonDex)
NonDex reshuffles *unordered API results* inside a single test run (HashMap/HashSet/reflection).
**iDFlakies reshuffles the *order the tests themselves run in*** and reruns the whole suite many
times (here: 10 random orders). A test whose **pass/fail outcome changes** depending on which other
tests ran before it is an **order-dependent (OD) flaky test** — it's implicitly relying on shared
state (static fields, files, sockets, etc.) left behind by another test.

## Result
- **163 tests located** in the `lib` module.
- Across the 10 random orders, iDFlakies found tests whose outcome flipped:

  | Round | New flaky tests found |
  |-------|------------------------|
  | 1 | 12 |
  | 2 | 11 |
  | 3 | 1 |
  | 4 | 1 |
  | 5 | 1 |
  | 6 | 1 |
  | 7 | 1 |
  | 8–10 | 0 (no new ones — detection had converged) |

- **28 distinct order-dependent (OD) tests detected in total**, e.g.:
  - `HttpRequestTest.basicProxyAuthentication`
  - `HttpRequestTest.getUrlEncodedWithUnicode`
  - `HttpRequestTest.putWithMappedQueryParams`
  - `HttpRequestTest.singleVerifier`
  - (see `dtfixingtools/detection-results/flaky-lists.json` for the full list with the exact
    passing/failing test-order for each one)

For each candidate, iDFlakies **re-verifies** it by re-running the exact recorded order and
confirming the outcome reproduces both ways, e.g. from the log:
```
Verified …basicProxyAuthentication, status: expected PASS,  got PASS
Verified …basicProxyAuthentication, status: expected ERROR, got ERROR
```
Both the passing order and the failing order reproduce reliably — confirming this is a true OD test,
not a one-off fluke.

## Cross-check against IDoFT
IDoFT lists **exactly 28** OD tests for `kevinsawicki/http-request` at this SHA (module `lib`).
**Our run detected all 28 — a 100% match**, and found **no additional/spurious ones**.

## Root cause (why they're order-dependent)
Nearly all 28 tests are `HttpRequestTest` methods that build an HTTP request against a local test
server and assert on it (e.g. query-param encoding, proxy auth, SSL socket factories). The project
uses **static/shared fields** (e.g. a shared `SSLSocketFactory` or connection/verifier singleton) that
one test can set up or mutate, and a later test then implicitly depends on that leftover state — a
classic root cause named in the RankF paper: a **state-setter** enabling a **brittle** test to pass,
or a **polluter** breaking a **victim** test that follows it.

## Repro gotcha (worth remembering)
The project's `lib/pom.xml` hardcodes an obsolete compiler level:
```xml
<source>1.5</source>
<target>1.5</target>
```
Modern JDKs (9+) reject `-source 5` outright:
```
error: Source option 5 is no longer supported. Use 6 or later.
```
Our `run-idflakies.sh` transparently patches this to `1.8` via `sed` right after checkout — this only
changes what language level the compiler *accepts*, not the compiled behavior, so it doesn't affect
the flakiness being measured.

## Files in this folder
- `idflakies-http-request.log` — full Maven/iDFlakies console output (test discovery, all 10 rounds,
  per-test PASS/ERROR verification).
- `dtfixingtools/` — iDFlakies' raw output:
  - `original-order` — the test suite's default run order.
  - `detection-results/flaky-lists.json` — **the master result**: every detected OD test plus the
    exact test-order (`intended`) that reproduces it.
  - `detection-results/random-class-method*/` and `test-runs/` — per-round/per-test raw JSON and
    Surefire-style records used to confirm each detection.
