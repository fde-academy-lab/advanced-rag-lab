#!/usr/bin/env bash
# Runs on every attach. Cheap, and it answers the only question somebody has on arrival.
set -uo pipefail
cd "$(dirname "$0")/../lab-simulator" || exit 0

cat <<'BANNER'

  ┌──────────────────────────────────────────────────────────────────────────┐
  │  L.A.B. Simulator                                                        │
  │  Seven units. Five modes. Graded against a live retrieval corpus.        │
  └──────────────────────────────────────────────────────────────────────────┘

BANNER

python -m labsim next 2>/dev/null || {
  echo "  Still installing. Give it a moment, then run:  cd lab-simulator && python -m labsim next"
  exit 0
}

cat <<'HELP'
  Run tasks from the command palette (F1 → "Run Task") or in this terminal:

    python -m labsim brief F1        read it, rendered, hints collapsed
    python -m labsim hint  F1        spend one hint when you are stuck
    python -m labsim start F1 --open scaffold an attempt and open it beside the brief
    python -m labsim check F1        grade it
    python -m labsim doctor          is this machine able to run the lab?

HELP
