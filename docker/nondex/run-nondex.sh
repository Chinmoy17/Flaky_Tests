#!/usr/bin/env bash
#
# Reproducibly run NonDex on a target Maven project inside the container.
#
# Usage:
#   run-nondex <repo-url> <sha> <module> <test-filter> [nondex-version]
#
# Example (reproduces our google/gson finding):
#   run-nondex https://github.com/google/gson.git \
#              e685705b2bf3ae174958612a185bd231c0e0c5d9 \
#              gson "MapTest,FieldNamingTest,CollectionTest"
#
# If a host directory is mounted at /out, results are copied to /out/<project>/.
set -euo pipefail

REPO="${1:?need <repo-url>}"
SHA="${2:?need <sha>}"
MODULE="${3:?need <module> (use . for repo root)}"
TESTS="${4:?need <test-filter> e.g. ClassA,ClassB}"
NDVER="${5:-2.2.1}"
NAME="$(basename "$REPO" .git)"

echo ">> Cloning $REPO"
git clone --quiet "$REPO" "$NAME"
cd "$NAME"
echo ">> Checking out $SHA"
git checkout --quiet "$SHA"

echo ">> Running NonDex $NDVER (module=$MODULE, tests=$TESTS)"
set +e
mvn -pl "$MODULE" -DfailIfNoTests=false -Dtest="$TESTS" \
    "edu.illinois:nondex-maven-plugin:${NDVER}:nondex" 2>&1 | tee /tmp/nondex.log
NDEXIT=${PIPESTATUS[0]}
set -e
echo ">> Maven exit code: $NDEXIT  (non-zero is EXPECTED when NonDex finds flaky tests)"

echo ">> NonDex SUMMARY (implementation-dependent flaky tests across seeds):"
awk '/Across all seeds:/{f=1;next} /Test results can be found/{f=0} f&&/#/{print}' /tmp/nondex.log || true

if [ -d /out ]; then
  OUTDIR="/out/${NAME}"
  mkdir -p "$OUTDIR"
  cp /tmp/nondex.log "$OUTDIR/nondex-${NAME}.log" || true
  if [ -d "${MODULE}/.nondex" ]; then cp -r "${MODULE}/.nondex" "$OUTDIR/nondex-data" || true; fi
  rm -f "$OUTDIR/nondex-data/nondex-instr.jar" 2>/dev/null || true
  echo ">> Results copied to /out/${NAME}/"
else
  echo ">> (No /out mount detected; results are in the container at /work/${NAME}/${MODULE}/.nondex)"
fi
