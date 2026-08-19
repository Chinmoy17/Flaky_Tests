# Reproducible NonDex runner

A committed Dockerfile + script so anyone can rebuild the exact environment and rerun NonDex on a
target Maven project — no local Java required.

## Build (once)
```powershell
# from the repo root
docker build -t flaky-nondex .\docker\nondex
```

## Run
```
docker run --rm [-v "<host-results-dir>:/out"] flaky-nondex <repo-url> <sha> <module> <test-filter> [nondex-version]
```

### Reproduce the google/gson finding
```powershell
docker run --rm -v "${PWD}\results\nondex:/out" flaky-nondex `
  https://github.com/google/gson.git `
  e685705b2bf3ae174958612a185bd231c0e0c5d9 `
  gson "MapTest,FieldNamingTest,CollectionTest"
```
- Prints `NonDex SUMMARY` (the flaky tests found) and copies the full log + `.nondex` data to
  `results/nondex/gson/`.
- A non-zero Maven exit code is **expected** — that's how NonDex signals it found flaky tests.

## Notes
- Base image is **JDK 11**: NonDex 2.2.1 needs JDK 9+ (JDK 8 fails with
  `Unrecognized option: --add-exports`).
- `<module>` is the Maven module containing the tests (use `.` for the repo root). `<test-filter>`
  is a Surefire `-Dtest` value (e.g. `ClassA,ClassB` or `ClassA#method`).
- **Windows paths with spaces** (like `C:\Program Files\...`) work when the whole `-v` value is
  quoted, as above. If a mount ever misbehaves, run from a space-free checkout or omit `-v` and
  `docker cp` the results out.
- **Speed up repeat runs** by caching Maven downloads across runs with a named volume:
  add `-v flaky-m2:/root/.m2` to the `docker run` command.
