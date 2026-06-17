#!/usr/bin/env bash
# One-command public launch of the AGORA repo. Run from the repo root.
# One-time setup: install GitHub CLI (https://cli.github.com) then: gh auth login
#   usage: bash scripts/launch_github.sh [repo-name] [public|private]
set -euo pipefail
REPO="${1:-agora}"; VIS="${2:-public}"
command -v gh >/dev/null || { echo "Install GitHub CLI then run 'gh auth login'"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "Run 'gh auth login' first"; exit 1; }
# public-facing README (preserve the dev one)
if [ -f README.md ] && [ ! -f docs/README_dev.md ]; then mkdir -p docs; cp README.md docs/README_dev.md; fi
cp GITHUB_README.md README.md
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || git init -q
git add -A
git commit -q -m "AGORA public launch: open model + manifesto" || echo "(nothing to commit)"
if gh repo view "$REPO" >/dev/null 2>&1; then git push -u origin HEAD; else
  gh repo create "$REPO" --"$VIS" --source=. --remote=origin --push \
    --description "Open, consistency-gated model of AI's distributional impact on the European economy."; fi
gh repo edit --add-topic artificial-intelligence,economics,inequality,universal-basic-capital,european-union,stock-flow-consistent,open-data 2>/dev/null || true
[ -f AGORA_Manifesto.pdf ] && gh release create v1.0 AGORA_Manifesto.pdf \
  -t "AGORA v1.0 — Owning the Machine" -n "Open model + 12-page study. Permanent DOI on Zenodo." 2>/dev/null || true
echo "Done -> $(gh repo view --json url -q .url 2>/dev/null)"
