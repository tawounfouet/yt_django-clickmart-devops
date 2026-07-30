#!/bin/bash
set -euo pipefail

# Usage: deploy-app.sh <env> <branch> <gh_user> <gh_token>
#   env:      staging | production
#   branch:   stg | main
#   gh_user:  GitHub username (for ghcr.io login)
#   gh_token: GitHub token (for ghcr.io login)

ENV="${1:-}"
BRANCH="${2:-}"
GH_USER="${3:-}"
GH_TOKEN="${4:-}"

if [ -z "$ENV" ] || [ -z "$BRANCH" ]; then
    echo "Usage: $0 <staging|production> <branch> [gh_user] [gh_token]"
    exit 1
fi

# ── Paths ──────────────────────────────────────────────
if [ "$ENV" = "staging" ]; then
    APP_DIR="/opt/clickmart-stg"
    COMPOSE_FILES="-f docker-compose.yml -f docker-compose.staging.yml"
    PROJECT_NAME="clickmart-stg"
    HEALTH_URL="http://localhost:8080/"
    API_URL="http://localhost:8080/api/v1/products/"
elif [ "$ENV" = "production" ]; then
    APP_DIR="/opt/clickmart"
    COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
    PROJECT_NAME="clickmart"
    HEALTH_URL="http://localhost/"
    API_URL="http://localhost/api/v1/products/"
else
    echo "Invalid environment: $ENV (use staging|production)"
    exit 1
fi

echo "::group::Deploy $ENV — starting"

# ── Git update ─────────────────────────────────────────
echo "::group::Git fetch + reset"
cd "$APP_DIR"
git fetch origin "$BRANCH" && git reset --hard "origin/$BRANCH"
echo "✅ Git updated to $(git rev-parse --short HEAD)"
echo "::endgroup::"

# ── Docker login (ghcr.io) ─────────────────────────────
if [ -n "$GH_USER" ] && [ -n "$GH_TOKEN" ]; then
    echo "::group::Docker login ghcr.io"
    echo "$GH_TOKEN" | docker login ghcr.io -u "$GH_USER" --password-stdin
    echo "✅ ghcr.io authenticated"
    echo "::endgroup::"
fi

# ── Docker pull + up ───────────────────────────────────
echo "::group::Docker compose pull + up"
docker compose -p "$PROJECT_NAME" $COMPOSE_FILES pull
docker compose -p "$PROJECT_NAME" $COMPOSE_FILES up -d

# Nginx reload (production only — SSL config may have changed)
if [ "$ENV" = "production" ]; then
    docker compose -p "$PROJECT_NAME" exec -T nginx nginx -s reload || true
fi
echo "✅ Containers started"
echo "::endgroup::"

# ── Wait for startup ───────────────────────────────────
echo "::group::Waiting for containers to stabilize"
sleep 15
docker compose -p "$PROJECT_NAME" ps
echo "::endgroup::"

# ── Health checks ──────────────────────────────────────
echo "::group::Health checks"

check_url() {
    local label="$1"
    local url="$2"
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    if [ "$status" = "200" ]; then
        echo "✅ $label: HTTP $status"
    else
        echo "❌ $label: HTTP $status (expected 200)"
        return 1
    fi
}

EXIT_CODE=0

check_url "Frontend  ($HEALTH_URL)" "$HEALTH_URL" || EXIT_CODE=1
check_url "API       ($API_URL)" "$API_URL" || EXIT_CODE=1

# Swap check
echo "::group::Swap check"
if swapon --show 2>/dev/null | grep -q /swapfile; then
    echo "✅ Swap: active"
else
    echo "⚠️  Swap: missing (not blocking)"
fi
echo "::endgroup::"

echo "::endgroup::"   # Health checks

if [ "$EXIT_CODE" -eq 0 ]; then
    echo "✅ $ENV deployment successful"
else
    echo "❌ $ENV deployment failed — health checks did not pass"
    exit 1
fi
