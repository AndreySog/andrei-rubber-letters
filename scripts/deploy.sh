#!/usr/bin/env bash
# deploy.sh — commit, inject build SHA, push, verify, report.
# Usage:
#   cd /data/.openclaw/workspace/site && ./scripts/deploy.sh "commit message"
#
# Reads GITHUB_TOKEN from /data/.openclaw/workspace/.env.
# Must run from inside the site/ directory.

set -euo pipefail

SITE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORKSPACE_DIR="$(cd "$SITE_DIR/.." && pwd)"

if [ ! -f "$WORKSPACE_DIR/.env" ]; then
  echo "::ERROR:: no .env found at $WORKSPACE_DIR/.env" >&2
  exit 1
fi

# shellcheck disable=SC1091
. "$WORKSPACE_DIR/.env"

if [ -z "${GITHUB_TOKEN:-}" ] || [ -z "${GITHUB_USER:-}" ]; then
  echo "::ERROR:: GITHUB_TOKEN or GITHUB_USER missing in .env" >&2
  exit 1
fi

cd "$SITE_DIR"

MSG="${1:-site: deploy}"

# Step 1: commit any pending changes (without build marker yet)
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
  git add -A
  if ! git diff --cached --quiet; then
    git commit -m "$MSG"
  fi
fi

# Step 2: read SHA AFTER committing content
SHA="$(git rev-parse --short HEAD)"

# Step 3: inject SHA into index.html, commit again if it changed
INJECTED=0
if [ -f index.html ] && grep -q 'id="commit-sha"' index.html; then
  CURRENT_SHA="$(grep -oE 'commit-sha">[^<]*' index.html | sed 's/.*">//' || echo '')"
  if [ "$CURRENT_SHA" != "$SHA" ]; then
    sed -i.bak -E "s|(<span class=\"commit\">build )[^<]*(</span>)|\1$SHA\2|" index.html
    rm -f index.html.bak
    git add index.html
    if ! git diff --cached --quiet; then
      git commit -m "build: $SHA"
      SHA="$(git rev-parse --short HEAD)"
      INJECTED=1
    fi
  fi
fi

# Step 4: ensure remote uses token
REMOTE="https://${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${REPO_NAME:-andrei-ideas-site}.git"
if ! git remote get-url origin 2>/dev/null | grep -q "$GITHUB_TOKEN"; then
  git remote set-url origin "$REMOTE" 2>/dev/null || git remote add origin "$REMOTE"
fi

# Step 5: push (fast-forward only; safe to run repeatedly)
git push -u origin main 2>&1 | tail -5

# Step 6: verify deployed URLs
echo "::VERIFY::"
FIRST="$(echo "$GITHUB_USER" | cut -c1 | tr '[:lower:]' '[:upper:]')"
REST="$(echo "$GITHUB_USER" | cut -c2-)"
PG_USER="$FIRST$REST"
BASE="https://${PG_USER,,}.github.io/${REPO_NAME:-andrei-ideas-site}"
NOW="$(date +%s)"

for path in "/" "/ideas/mobius-unit.html" "/ideas/bolt-m8.html" \
            "/assets/css/main.css" "/assets/css/lock.css" \
            "/assets/js/main.js" "/assets/js/lock.js" \
            "/assets/img/bolt-m8-ris51.svg" "/assets/img/bolt-m8-nacherti.svg"; do
  code="$(curl -s -o /dev/null -w '%{http_code}' "${BASE}${path}?nocache=${NOW}")"
  printf "  %s  %s\n" "$code" "$path"
done

echo
echo "::DONE:: ${BASE}/?v=${SHA}"
echo "SHA: $SHA"