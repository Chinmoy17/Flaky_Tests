# Prof. Shanto Rahman — Paper Notes

Notes on the three papers referenced in the email: **RankF**, **FlakeSync**, and **TSVD4J**.
The focus of this document is **RankF** (the paper you're most interested in), with shorter
summaries of the other two and an explanation of how they all fit together.

> All three papers share one author: **Shanto Rahman** (PhD researcher at UT Austin, advised by
> **August Shi**). They all sit in the same research area: **flaky tests** and **concurrency bugs**
> in Java regression testing.

---

## 0. Essential Background (read this first)

You need a handful of terms to understand any of the three papers.

- **Regression testing**: rerunning tests after every code change to catch newly introduced faults.
- **Flaky test**: a test that can **both pass and fail on the exact same version of code**. It
  gives a false signal — a failure does not necessarily mean the developer broke something.
- Two big families of flaky tests matter here:
  - **Order-Dependent (OD) tests**: pass or fail depending on the **order** tests run in. Caused by
    shared global state (static variables, files, DB, network) that other tests modify. → *RankF*
  - **Async / concurrency flaky tests (NOD — non-order-dependent)**: fail due to timing, e.g. an
    asynchronous call that isn't waited for long enough, or an unlucky thread interleaving. → *FlakeSync*
- **Thread-safety violation**: a genuine concurrency bug where two threads touch the same
  thread-unsafe data structure at the same time and at least one writes. → *TSVD4J*

### The tooling ecosystem (this is what the email's GitHub links are about)

| Tool | What it does | Relation to the papers |
|------|--------------|------------------------|
| **iDFlakies** | Runs the test suite in many **random test-orders** to **detect and classify** flaky tests as OD or NOD. | Produces the OD tests RankF works on and the test-orders RankF_O consumes. |
| **NonDex** | Detects flaky tests that rely on **under-determined Java API specs** (e.g. `HashMap` iteration order) by re-running with different *legal* implementations. | Another flaky-test detector; feeds the IDoFT dataset. |
| **IDoFT** | The **Illinois Dataset of Flaky Tests** — a curated, community database of known real-world flaky tests, their categories, and fixes. | The dataset FlakeSync (and much of this area) evaluates on. |

Mental model: **iDFlakies / NonDex = detectors** → **IDoFT = the catalogue of what was detected** →
**RankF / FlakeSync = techniques that help you debug/fix what was detected**.

---

## 1. RankF — *Ranking Relevant Tests for Order-Dependent Flaky Tests* ⭐ (main focus)

**Authors:** Shanto Rahman, Bala Naren Chanumolu, Suzzana Rafi, August Shi, Wing Lam
(UT Austin + George Mason University).
**Artifact:** https://sites.google.com/view/ranking-od-relevant-tests

### 1.1 The problem it solves

To **fix** an OD test you first have to find the *other* test that causes the order-dependent
behavior. Those causal tests are called **OD-relevant tests**. Prior techniques find them but are
**slow**, because they blindly run many irrelevant tests first:

- **OBO (one-by-one)**: pair each candidate test before the OD test and rerun — repeatedly.
- **Delta-debugging** (used inside **iFixFlakies**): binary-search the tests before the OD test.

Both ignore *how likely* each test is to be the culprit. **RankF's idea: rank tests by their
likelihood of being OD-relevant, then run them in that order** — so you hit the real one much sooner.

### 1.2 The vocabulary of OD tests (crucial)

When an OD test fails in a failing order, it shares state with another test. Shi et al.'s naming:

- **Victim** — passes alone, **fails when run *after*** some other test.
  - **Polluter** — the test that *pollutes* the shared state and makes the victim fail.
  - **Cleaner** — a test that *resets* the polluted state; run **after the polluter but before the
    victim**, it makes the victim pass again.
- **Brittle** — **fails when run alone** because it needs another test to set up state first.
  - **State-setter** — the test that sets up that state so the brittle passes.

**OD-relevant tests = polluters + state-setters + cleaners** (collectively). RankF's whole job is to
rank the ordinary tests so that these three kinds surface at the top.

```
Victim  needs → a Polluter before it to fail   (and optionally a Cleaner to recover)
Brittle needs → a State-setter before it to pass
```

### 1.3 The two approaches

RankF has two independent ranking engines for two different situations.

#### RankF_L  — the LLM approach (code-only)

Use it when you **only have the test code** and no execution history.

- Fine-tunes **BigBird** (`bigbird-roberta-base`), a transformer built for **long sequences** (it
  can ingest far more tokens than a typical LLM — important because we feed it *two* test bodies).
- **Input:** the test-method body of a *candidate* test **paired with** the OD test's body.
  **Output:** a likelihood score that the candidate is OD-relevant for that OD test.
- Builds **three separate models** — one each for scoring polluters (for victims), state-setters
  (for brittles), and cleaners (for victim/polluter pairs).
- Pipeline details:
  - **srcML** extracts the method signature + body; comments stripped.
  - Tokenized with SentencePiece + Byte-Pair Encoding; **max 2048 tokens** (99% of tuples fit;
    longer ones truncated — BigBird's hard max is 4096 but that wastes memory via padding).
  - **Freeze the first 5 layers**, fine-tune the remaining 7 (BigBird is expensive to fully train).
  - Head: BigBird 768-vector → dense 256 → 2-neuron output, ReLU, **dropout 0.4**, softmax,
    **AdamW**, **NLLLoss**, **30 epochs** with **early stopping** (patience 10).
  - **Cross-project training**: when evaluating a project, the model is trained *only on other
    projects* — simulating a developer downloading a pre-trained model. Deterministic at inference.

#### RankF_O — the test-order heuristics approach (execution history)

Use it when you **already have results from many test-orders** (e.g. you ran iDFlakies, or you
already randomize test order in CI). It's essentially free to compute (<100 ms).

Intuition: the more often a test appears **before** the OD test when the OD test is **failing**
(victim) or **passing** (brittle), and the **closer** it sits to the OD test, the more likely it's
the culprit. Each test gets a *positive class score* (likely OD-relevant) and *negative class score*.

**Five scoring heuristics:**

| Heuristic | Score given to each test before the OD test | Intuition |
|-----------|---------------------------------------------|-----------|
| **Plus One (+1)** | $+1$ | Frequently-appearing-before ⇒ more suspicious. |
| **#Methods (#M)** | $\dfrac{1}{\text{indexOf}(ot)}$ | Orders with *fewer* tests before the OD test carry more weight. |
| **Distance (D)** | $\dfrac{1}{\text{indexOf}(ot)-\text{indexOf}(gt)}$ | Tests *closer* to the OD test are more suspicious. |
| **Combined (+1, D)** | Plus One, ties broken by Distance | Combats tied scores. |
| **Combined (#M, D)** | #Methods, ties broken by Distance | Combats tied scores. |

($ot$ = the OD test, $gt$ = the given candidate test, `indexOf` = position in the test-order.)

### 1.4 Turning scores into a ranking

After scoring, RankF ranks with one of three **strategies**:

- **Positive class strategy** — sort by positive score, descending (most-likely first).
- **Negative class strategy** — sort by negative score, ascending (least-likely-*not* first).
- **Combined class strategy** — sort by (positive − negative), descending.

**Best strategy per engine (RQ3):** negative-class works best for **RankF_L**; combined-class works
best for **RankF_O**.

### 1.5 Evaluation

- **Dataset:** 155 reproduced OD tests, 34 modules, 24 open-source Java/Maven projects (from Wei et
  al.). 13,219 tests total across the modules.
- **Baselines:** OBO (`OBOavg`, `OBOmax`) and delta-debugging (`DD`).
- **Metrics:** time to *rank + confirm* the first OD-relevant test; how often the true one lands at
  **Rank-1**; the rank of the first true one; MAP score.

**Headline results:**
- RankF finds the first OD-relevant test in **~9.4–14.1 s median**, vs **34.2–118.5 s** for the best
  baseline.
- Example (state-setters): RankF_L / RankF_O median **59.5 s / 13.3 s** vs **489.5 s / 118.5 s** for
  OBOavg / DD.
- **RankF_O is the fastest** for the majority of modules (36/56 across the three tables) and its
  ranking cost is negligible. **RankF_L** is pricier (it runs an LLM) but provides a full ranking of
  *every* test, useful if you want to find *multiple* OD-relevant tests.
- ~45% (9/20) of brittles already have their state-setter at **Rank-1** for RankF_O.

**Secondary findings:**
- **~20 test-orders** are enough for RankF_O; more didn't help (and slightly hurt).
- **Plus One** is generally the best heuristic (except for finding the first state-setter).
- SHAP analysis shows RankF_L learns **shared tokens between genuinely related tests** — and it
  beats a plain TF-IDF code-similarity baseline, so it captures more than surface similarity.
- **Un-fine-tuned GPT-3.5** performed *worse* than the fine-tuned BigBird model.

### 1.6 Limitations & future work

- Doesn't handle OD tests that need **two or more** tests together to flip (rare in practice).
- Depends on **srcML** parsing and BigBird padding quirks for tiny methods.
- **Future:** feed richer signals (dynamic execution traces) and **combine** RankF_L and RankF_O so
  one guides the other.

### 1.7 One-paragraph takeaway

> RankF reframes "find the test that breaks my order-dependent test" as a **ranking problem**. Given
> an OD test, it scores every other test by how likely it is to be the polluter/state-setter/cleaner
> — either from **test code via a fine-tuned BigBird LLM (RankF_L)** or from **historical test-order
> outcomes via cheap positional heuristics (RankF_O)** — then runs them best-first. This finds the
> culprit several times faster than the delta-debugging and one-by-one baselines used by prior repair
> tools like iFixFlakies.

---

## 2. FlakeSync — *Automatically Repairing Async Flaky Tests* (ICSE 2024)

**Authors:** Shanto Rahman, August Shi. **Artifact:** https://sites.google.com/view/flakesync/home

- **Target:** *async flaky tests* — the two most common flaky categories (async-wait + concurrency),
  which fail because code isn't properly **synchronized** (a wait that's too short, an unlucky
  interleaving). Developers usually "fix" these by bumping `Thread.sleep(...)`, which is unreliable
  and slow.
- **Idea:** introduce real synchronization for that specific test instead of guessing wait times.
  Two components:
  - **CritSearch** finds the **critical point** — the code that *must* run early; if delayed, the
    test fails. It injects delays, minimizes their locations with delta-debugging, then walks up the
    call stack to the "root method" and pinpoints the boundary line.
  - **BarrierSearch** finds the **barrier point** — the code that must **wait** until the critical
    point has executed. It replaces the guesswork with a `Thread.yield()` loop that spins until the
    critical point is done.
- **Results:** of 176 known flaky tests, 80 are true async flaky tests; FlakeSync repairs
  **83.75%** of them. Median runtime **overhead of the fixed test is 1.00×** (essentially free,
  unlike padded sleeps). Submitted **10 pull requests → 3 accepted, 0 rejected**; one merged with
  *"LGTM, thanks, it's really great work."*
- **Cost:** the *search* is expensive (median ~59 min per test) but fully automated and one-time.

---

## 3. TSVD4J — *Thread-Safety Violation Detection for Java* (ICSE 2023, tool demo)

**Authors:** Shanto Rahman, Chengpeng Li, August Shi. **Artifact:** https://github.com/UT-SE-Research/TSVD4J

- **Target:** *thread-safety violations* — two threads accessing the same thread-unsafe structure
  (e.g. a non-synchronized `List`/`Map`/`Vector`) concurrently with at least one write.
- **Idea:** port Microsoft's **TSVD** (originally .NET) to **Java**, and extend it. It uses **ASM**
  to instrument bytecode, replacing tracked read/write API calls with proxy methods. The runtime
  **injects a delay (~100 ms)** around each access; if another thread touches the same object within
  that window and one access is a write, it reports a **conflicting-pair** (a potential violation).
- **Key extension:** also track **object field accesses** (`getfield`/`putfield`), not just
  collection API calls — and this contributed the most detections.
- **Usage:** ships as a **Maven plugin** — `mvn tsvd4j:tsvd4j` — so it drops into any Maven project.
- **Results:** on 12 apps it found **55 conflicting-pairs** vs **17** for RV-Predict, at comparable
  runtime.

---

## 4. How the three papers connect

```
        detect & classify                catalogue                    debug / repair
   ┌────────────────────────┐        ┌─────────────┐        ┌───────────────────────────────┐
   │ iDFlakies (OD vs NOD)  │  ───▶  │    IDoFT    │  ───▶  │ RankF     → find OD-relevant   │
   │ NonDex (API-spec order)│        │  (dataset)  │        │ FlakeSync → repair async flaky │
   └────────────────────────┘        └─────────────┘        │ TSVD4J    → find concurrency   │
                                                            └───────────────────────────────┘
```

- **RankF** helps you **locate** the cause of an **OD** flaky test (a prerequisite for fixing it).
- **FlakeSync** helps you **repair** an **async/NOD** flaky test.
- **TSVD4J** helps you **detect** genuine **thread-safety** concurrency bugs.

They are complementary stages of the same pipeline: **detect → catalogue → localize → repair**.

---

## 5. Quick glossary

| Term | Meaning |
|------|---------|
| **Flaky test** | Passes and fails on the same code. |
| **OD test** | Order-Dependent flaky test. |
| **NOD test** | Non-Order-Dependent flaky test (often async/concurrency). |
| **Victim** | Passes alone, fails after a *polluter*. |
| **Polluter** | Corrupts shared state → makes a victim fail. |
| **Cleaner** | Resets shared state → lets a polluted victim pass. |
| **Brittle** | Fails alone; needs a *state-setter* first. |
| **State-setter** | Sets up state so a brittle passes. |
| **OD-relevant test** | A polluter, state-setter, or cleaner. |
| **Critical point** (FlakeSync) | Code that must run early or the test fails. |
| **Barrier point** (FlakeSync) | Code that must wait for the critical point. |
| **Conflicting-pair** (TSVD4J) | Two code locations forming a potential thread-safety violation. |
| **Artifact** | The downloadable code/data/tool that accompanies a paper. |
