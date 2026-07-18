#!/usr/bin/env bash
set -euo pipefail
export COMPASS_ROOT="${COMPASS_ROOT:-/app/content}"
mkdir -p "$COMPASS_ROOT"/{evidence,jobs,resumes,interviews,diagnoses,track,questions,rag,profile}

if [[ "${COMPASS_DEMO:-0}" == "1" ]]; then
  mkdir -p "$COMPASS_ROOT/fixtures" "$COMPASS_ROOT/evidence" "$COMPASS_ROOT/profile" "$COMPASS_ROOT/track"
  if [[ -d /opt/compass/fixtures ]]; then
    cp -rn /opt/compass/fixtures/* "$COMPASS_ROOT/fixtures/" 2>/dev/null || true
  fi
  if [[ ! -f "$COMPASS_ROOT/evidence/ev_featstore_latency.md" ]] && [[ -d /opt/compass/fixtures/demo/evidence ]]; then
    cp -n /opt/compass/fixtures/demo/evidence/*.md "$COMPASS_ROOT/evidence/" 2>/dev/null || true
    python -m compass_core.cli evidence-index --root "$COMPASS_ROOT" || true
  fi
  [[ -f /opt/compass/example_profile.json && ! -f "$COMPASS_ROOT/profile/example_profile.json" ]] \
    && cp /opt/compass/example_profile.json "$COMPASS_ROOT/profile/example_profile.json" || true
fi

case "${1:-studio}" in
  studio)
    exec python /app/apps/studio/app.py
    ;;
  live)
    cd /app/apps/interview-live
    exec python -m uvicorn main:app --host 0.0.0.0 --port "${COMPASS_LIVE_PORT:-8766}"
    ;;
  *)
    exec "$@"
    ;;
esac
