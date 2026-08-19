#!/usr/bin/env bash
#
# Mini "localize the culprit" runner: reuses an EXISTING iDFlakies detect() run's
# .dtfixingtools data (mounted read-only at /seed) and runs `idflakies:minimize` on
# just a small, chosen subset of the detected OD tests -- instead of all of them --
# so the delta-debugging search stays fast for a demo/spot-check.
#
# minimize searches for, per OD test:
#   - victim  -> its polluter (delta-debugging the failing order)
#   - brittle -> its state-setter (delta-debugging the passing order)
#   - a polluter-victim pair -> a cleaner (one-by-one search in-between)
#
# Usage:
#   run-idflakies-minimize <repo-url> <sha> <module> <comma-separated-fully-qualified-test-names>
#
# Requires a read-only mount at /seed containing a previous detect() run's
# .dtfixingtools directory (original-order, detection-results/flaky-lists.json, etc.)
# If a host directory is mounted at /out, results are copied to /out/<project>/.
set -euo pipefail

REPO="${1:?need <repo-url>}"
SHA="${2:?need <sha>}"
MODULE="${3:?need <module> (use . for repo root)}"
TESTS_CSV="${4:?need <comma-separated fully-qualified test names>}"
IDFVER="2.0.0"
NAME="$(basename "$REPO" .git)"

if [ ! -d /seed ]; then
  echo "ERROR: expected a previous detect() run's .dtfixingtools mounted read-only at /seed" >&2
  exit 1
fi

echo ">> Cloning $REPO"
git clone --quiet "$REPO" "$NAME"
cd "$NAME"
echo ">> Checking out $SHA"
git checkout --quiet "$SHA"

echo ">> Patching any hardcoded Java 1.5 source/target to 1.8 (modern JDK compatibility)"
find . -name pom.xml -exec sed -i \
  -e 's#<source>1\.5</source>#<source>1.8</source>#g' \
  -e 's#<target>1\.5</target>#<target>1.8</target>#g' {} +

echo ">> Reusing previous detect() results from /seed (skips rerunning all detection rounds)"
cp -r /seed "${MODULE}/.dtfixingtools"

echo ">> Trimming flaky-lists.json + list.txt down to the requested test(s): $TESTS_CSV"
DETRES="${MODULE}/.dtfixingtools/detection-results"
JQFILTER=$(echo "$TESTS_CSV" | awk -F',' '{ out=""; for (i=1;i<=NF;i++) { if (i>1) out = out " or "; out = out ".name == \"" $i "\"" } print out }')
jq ".dts |= map(select($JQFILTER))" "${DETRES}/flaky-lists.json" > "${DETRES}/flaky-lists.json.tmp"
mv "${DETRES}/flaky-lists.json.tmp" "${DETRES}/flaky-lists.json"
echo "$TESTS_CSV" | tr ',' '\n' > "${DETRES}/list.txt"
echo ">> Trimmed to $(jq '.dts | length' "${DETRES}/flaky-lists.json") test(s)"

echo ">> Running iDFlakies $IDFVER minimize (module=$MODULE)"
set +e
mvn -pl "$MODULE" "edu.illinois.cs:idflakies-maven-plugin:${IDFVER}:minimize" \
    2>&1 | tee /tmp/idflakies-minimize.log
MINEXIT=${PIPESTATUS[0]}
set -e
echo ">> Maven exit code: $MINEXIT"

MINDIR="${MODULE}/.dtfixingtools/minimized"
echo ">> Minimize results:"
if [ -d "$MINDIR" ]; then
  find "$MINDIR" -iname "*.json" | sort
else
  echo "(no .dtfixingtools/minimized directory found -- see /tmp/idflakies-minimize.log)"
fi

if [ -d /out ]; then
  OUTDIR="/out/${NAME}"
  mkdir -p "$OUTDIR"
  cp /tmp/idflakies-minimize.log "$OUTDIR/idflakies-minimize-${NAME}.log" || true
  if [ -d "$MINDIR" ]; then cp -r "$MINDIR" "$OUTDIR/minimized" || true; fi
  echo ">> Results copied to /out/${NAME}/minimized/"
else
  echo ">> (No /out mount detected; results are in the container at /work/${MINDIR})"
fi
