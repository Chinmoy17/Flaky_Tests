# Reproducible iDFlakies runner

A committed Dockerfile + script so anyone can rebuild the exact environment and rerun iDFlakies on a
target Maven project — no local Java required.

## What iDFlakies does (in one line)
Runs a project's **whole test suite in many random orders** and reports any test whose pass/fail
outcome **changes** between orders — that's an **order-dependent (OD) flaky test**. This is a
different bug than NonDex finds: NonDex shuffles *within* one test run (unordered API results);
iDFlakies shuffles the *order the tests themselves run in*.

## Build (once)
```powershell
docker build -t flaky-idflakies .\docker\idflakies
```

## Run
```
docker run --rm [-v "<host-results-dir>:/out"] flaky-idflakies <repo-url> <sha> <module> [rounds] [detector-type]
```

### Reproduce the kevinsawicki/http-request example
```powershell
docker run --rm -v "${PWD}\results\idflakies:/out" flaky-idflakies `
  https://github.com/kevinsawicki/http-request.git `
  2d62a3e9da726942a93cf16b6e91c0187e6c0136 `
  lib 10 random-class-method
```
- Prints the detected flaky tests and copies the full log + `.dtfixingtools` data to
  `results/idflakies/http-request/`.

## Notes
- `<module>` is the Maven module containing the tests (use `.` for the repo root).
- `rounds` = how many random test-orders to try (more rounds = more thorough, slower). Default 10.
- `detector-type` = `random-class-method` (default) runs both classes and methods in random order;
  see the [iDFlakies README](https://github.com/UT-SE-Research/iDFlakies) for other detector types.
- Same Windows-paths-with-spaces note as the NonDex runner: quote the whole `-v` value.
- Add `-v flaky-m2:/root/.m2` to cache Maven downloads across runs (same cache used by the NonDex
  image if you reuse the volume name).
