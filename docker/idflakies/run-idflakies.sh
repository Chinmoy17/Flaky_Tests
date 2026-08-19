#!/usr/bin/env bash
#
# Reproducibly run iDFlakies on a target Maven project inside the container.
#
# iDFlakies detects flaky tests by running the WHOLE test suite in many random
# orders and checking whether any test's pass/fail outcome changes between
# orders. Unlike NonDex (which needs no pom.xml changes and is invoked with a
# fully-qualified plugin coordinate), iDFlakies works the same way: we invoke
# it directly via edu.illinois.cs:idflakies-maven-plugin without touching the
# project's pom.xml.
#
# Usage:
#   run-idflakies <repo-url> <sha> <module> [rounds] [detector-type]
#
# Example (reproduces the canonical iDFlakies example project):
#   run-idflakies https://github.com/kevinsawicki/http-request.git \
#                 2d62a3e9da726942a93cf16b6e91c0187e6c0136 \
#                 lib 10 random-class-method
#
# If a host directory is mounted at /out, results are copied to /out/<project>/.
set -euo pipefail

REPO="${1:?need <repo-url>}"
SHA="${2:?need <sha>}"
MODULE="${3:?need <module> (use . for repo root)}"
ROUNDS="${4:-10}"
DETECTOR="${5:-random-class-method}"
IDFVER="2.0.0"
NAME="$(basename "$REPO" .git)"

echo ">> Cloning $REPO"
git clone --quiet "$REPO" "$NAME"
cd "$NAME"
echo ">> Checking out $SHA"
git checkout --quiet "$SHA"

# Old projects sometimes hardcode an obsolete Java language level (e.g. 1.5) directly in
# maven-compiler-plugin's <configuration>, which modern JDKs refuse to compile
# ("Source option 5 is no longer supported"). Bumping this to 1.8 only changes the
# language level the compiler accepts -- it does not change test behavior/flakiness.
echo ">> Patching any hardcoded Java 1.5 source/target to 1.8 (modern JDK compatibility)"
find . -name pom.xml -exec sed -i \
  -e 's#<source>1\.5</source>#<source>1.8</source>#g' \
  -e 's#<target>1\.5</target>#<target>1.8</target>#g' {} +

echo ">> Running iDFlakies $IDFVER (module=$MODULE, rounds=$ROUNDS, detector=$DETECTOR)"
set +e
mvn -pl "$MODULE" "edu.illinois.cs:idflakies-maven-plugin:${IDFVER}:detect" \
    -Ddetector.detector_type="$DETECTOR" \
    -Ddt.randomize.rounds="$ROUNDS" \
    -Ddt.detector.original_order.all_must_pass=false \
    2>&1 | tee /tmp/idflakies.log
IDFEXIT=${PIPESTATUS[0]}
set -e
echo ">> Maven exit code: $IDFEXIT"

# iDFlakies writes its results under <module>/.dtfixingtools/ (detection-results
# and a flaky test list). Locate it rather than hard-coding, since the exact
# layout can vary slightly by plugin version.
RESULTDIR=""
for cand in "${MODULE}/.dtfixingtools" ".dtfixingtools"; do
  if [ -d "$cand" ]; then RESULTDIR="$cand"; break; fi
done

echo ">> Flaky (order-dependent) tests detected:"
if [ -n "$RESULTDIR" ]; then
  find "$RESULTDIR" -iname "*flaky*" -o -iname "*.json" | sort
else
  echo "(no .dtfixingtools directory found -- see /tmp/idflakies.log)"
fi

if [ -d /out ]; then
  OUTDIR="/out/${NAME}"
  mkdir -p "$OUTDIR"
  cp /tmp/idflakies.log "$OUTDIR/idflakies-${NAME}.log" || true
  if [ -n "$RESULTDIR" ]; then cp -r "$RESULTDIR" "$OUTDIR/dtfixingtools" || true; fi
  echo ">> Results copied to /out/${NAME}/"
else
  echo ">> (No /out mount detected; results are in the container at /work/${NAME}/${RESULTDIR})"
fi
