# NonDex run — `google/gson`

Reproduction of known **Implementation-Dependent (ID)** flaky tests from IDoFT using NonDex, run entirely in Docker (no local Java).

## Environment
| Item | Value |
|------|-------|
| Tool | NonDex Maven plugin **2.2.1** |
| Container image | `maven:3.9-eclipse-temurin-11` (JDK 11.0.31) |
| Project | [`google/gson`](https://github.com/google/gson) |
| SHA | `e685705b2bf3ae174958612a185bd231c0e0c5d9` |
| Module | `gson` |
| Date | 2026-08-19 |

## Command
```bash
# inside the container, at /work/gson
mvn -pl gson -DfailIfNoTests=false \
    -Dtest=MapTest,FieldNamingTest,CollectionTest \
    edu.illinois:nondex-maven-plugin:2.2.1:nondex
```

## What NonDex does
NonDex re-runs the tests while **legally** shuffling *under-determined* Java APIs (e.g. the
iteration order of `HashMap`/`HashSet`, and the order returned by reflection such as
`Class.getDeclaredFields`). A test that passes normally but **fails under shuffling** relies on an
order the JDK never actually guarantees — an implementation-dependent (ID) flaky test.

## Result
- **Clean run (no shuffling): all selected tests PASS.**
- **Under shuffled seeds: 12 tests FAIL.** (NonDex reports this as a Maven `BUILD FAILURE` — that
  failure *is* the detection signal.)

The 12 implementation-dependent flaky tests found "across all seeds":

| # | Test |
|---|------|
| 1 | `com.google.gson.functional.MapTest#testInterfaceTypeMap` |
| 2 | `com.google.gson.functional.MapTest#testInterfaceTypeMapWithSerializer` |
| 3 | `com.google.gson.functional.CollectionTest#testWildcardCollectionField` |
| 4 | `com.google.gson.functional.CollectionTest#testObjectCollectionSerialization` |
| 5 | `com.google.gson.functional.CollectionTest#testPriorityQueue` |
| 6 | `com.google.gson.functional.CollectionTest#testCollectionOfBagOfPrimitivesSerialization` |
| 7 | `com.google.gson.functional.FieldNamingTest#testUpperCamelCase` |
| 8 | `com.google.gson.functional.FieldNamingTest#testLowerCaseWithDashes` |
| 9 | `com.google.gson.functional.FieldNamingTest#testLowerCaseWithUnderscores` |
| 10 | `com.google.gson.functional.FieldNamingTest#testUpperCamelCaseWithSpaces` |
| 11 | `com.google.gson.functional.FieldNamingTest#testIdentity` |
| 12 | `com.google.gson.functional.FieldNamingTest#testUpperCaseWithUnderscores` |

### Reproduction detail (one failing seed)
From `nondex-data/FYEG5Ll9…/config` and `.../failures`:
```
nondexMode=FULL
nondexSeed=1016066
```
11 of the 12 tests fail under this single seed; `testInterfaceTypeMapWithSerializer` surfaces under a
different seed — a good illustration of why NonDex runs multiple seeds.

## Cross-check against IDoFT
All 12 tests appear in IDoFT's `pr-data.csv` under **Category `ID`** for `google/gson` at this exact
SHA (Status: `DeveloperWontFix`). So this run **reproduces known, catalogued ID flaky tests** rather
than surfacing anything new.

## Root cause (why they flake)
These tests serialize objects/collections/maps to JSON and assert against a **hard-coded expected
string** whose element or field order depends on:
- **reflection order** — `Class.getDeclaredFields()` (field naming/expose tests), and
- **hash-based iteration order** — `HashMap`/`HashSet` (map & collection tests).

Neither order is guaranteed by the Java spec, so NonDex's legal permutation changes the output
ordering and the assertion fails.

## Repro gotcha (worth remembering)
NonDex 2.2.1 requires **JDK 9+**. On JDK 8 it fails immediately with:
```
Unrecognized option: --add-exports
Error: Could not create the Java Virtual Machine.
```
We switched the container from `…-temurin-8` to `…-temurin-11` to fix this.

## Files in this folder
- `nondex-gson.log` — full Maven/NonDex console output.
- `nondex-data/` — NonDex's `.nondex` output: one `clean_…` run + seeded runs, each with per-class
  results, `config` (mode/seed), `failures`, and JUnit XMLs; plus `test_results.html`.
