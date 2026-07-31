#!/bin/bash
set -euo pipefail

# ansible-export.sh — Scan server + project → generate/maintain Ansible config
# Usage: ./ansible-export.sh [--dry-run]

DRY_RUN="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ANSIBLE_DIR="$SCRIPT_DIR/ansible"
INVENTORY="$ANSIBLE_DIR/inventory.yml"
ALL_YML="$ANSIBLE_DIR/group_vars/all.yml"
SECRETS_EXAMPLE="$ANSIBLE_DIR/group_vars/secrets.yml.example"

echo "::group::🔍 Ansible Export"

# ── 1. Scan projet local ──────────────────────────────
echo "::group::Scan projet"

# Detect domain & env from existing inventory
if [ -f "$INVENTORY" ]; then
    echo "📄 inventory.yml trouvé → mise à jour"
else
    echo "📄 inventory.yml absent → création from-scratch"
fi

# Detect .env.example variables
ENV_FILE=""
for f in backend/.env.example backend/.env ../../backend/.env.example ../../backend/.env; do
    [ -f "$f" ] && { ENV_FILE="$f"; break; }
done

echo "::endgroup::"

# ── 2. Scan serveur ───────────────────────────────────
echo "::group::Scan serveur"

SERVER_OK=false
if [ -f "$INVENTORY" ]; then
    ansible all -i "$INVENTORY" -m ping 2>/dev/null && SERVER_OK=true || echo "⚠️  Serveur inaccessible"
else
    echo "⚠️  Pas d'inventory, scan serveur ignoré"
fi

if $SERVER_OK; then
    # OS
    ansible all -i "$INVENTORY" -m setup 2>/dev/null | \
        python3 -c "
import sys,json
data = json.load(sys.stdin)
for host, facts in data.get('ansible_facts', {}).items():
    print(f'  OS: {facts.get(\"ansible_distribution\",\"?\")} {facts.get(\"ansible_distribution_version\",\"?\")} | RAM: {facts.get(\"ansible_memtotal_mb\",0)} MB | IP: {facts.get(\"ansible_default_ipv4\",{}).get(\"address\",\"?\")}')
" 2>/dev/null || echo "  ⚠️  Facts indisponibles"

    # Docker
    ansible all -i "$INVENTORY" -m shell -a "docker --version 2>/dev/null && docker compose version 2>/dev/null" 2>/dev/null | grep -q "Docker version" \
        && echo "  🐳 Docker présent" || echo "  ⚠️  Docker absent"

    # Containers
    for project in clickmart clickmart-stg; do
        ansible all -i "$INVENTORY" -m shell -a "docker compose -p $project ps 2>/dev/null" 2>/dev/null | grep -q "Up" \
            && echo "  📦 $project : actif" || echo "  📦 $project : inactif"
    done

    # SSL
    ansible all -i "$INVENTORY" -m shell -a "test -d /etc/letsencrypt/live 2>/dev/null && ls /etc/letsencrypt/live/ 2>/dev/null || echo 'none'" 2>/dev/null | grep -v "SUCCESS\|WARNING\|^\"" | tail -1 | while read domain; do
        [ "$domain" != "none" ] && echo "  🔒 SSL : $domain" || echo "  🔓 SSL : absent"
    done
fi

echo "::endgroup::"

# ── 3. Génération inventory.yml ───────────────────────
echo "::group::Génération inventory.yml"

if [ "$DRY_RUN" = "--dry-run" ]; then
    echo "Dry-run → inventory.yml non modifié"
else
    cat > "$INVENTORY" << 'INVENTORY_EOF'
all:
  hosts:
    clickmart-prod:
      ansible_host: 172.239.20.14
      # ── Sur un VPS VIERGE, utiliser root pour le premier run ──
      # ansible_user: root
      # ── Une fois deploy créé, utiliser deploy ──
      ansible_user: deploy
      ansible_ssh_private_key_file: ~/.ssh/id_ed25519
      ansible_ssh_common_args: -o StrictHostKeyChecking=accept-new
      env: production
      domain: webtech-dev.info
      app_dir: /opt/clickmart
      compose_files:
        - docker-compose.yml
        - docker-compose.prod.yml
      project_name: clickmart
      branch: main
      ssl_enabled: true
      health_proto: https

    clickmart-staging:
      ansible_host: 172.239.20.14
      # ansible_user: root
      ansible_user: deploy
      ansible_ssh_private_key_file: ~/.ssh/id_ed25519
      ansible_ssh_common_args: -o StrictHostKeyChecking=accept-new
      env: staging
      domain: staging.webtech-dev.info
      app_dir: /opt/clickmart-stg
      compose_files:
        - docker-compose.yml
        - docker-compose.staging.yml
      project_name: clickmart-stg
      branch: stg
      ssl_enabled: false
      health_proto: http

  vars:
    env: production
    domain: webtech-dev.info
INVENTORY_EOF
    echo "✅ inventory.yml généré"
fi

echo "::endgroup::"

# ── 4. Génération secrets.yml.example ─────────────────
echo "::group::Génération secrets.yml.example"

if [ "$DRY_RUN" = "--dry-run" ]; then
    echo "Dry-run → secrets.yml.example non modifié"
else
    cat > "$SECRETS_EXAMPLE" << 'SECRETS_EOF'
---
# Généré par @deploy-fullstack export
# Remplacer les valeurs et renommer en secrets.yml

secret_key: "changeme-generate-with-python-secrets"
db_password: "changeme"
redis_password: "changeme"
cloudinary_cloud: "dsrbll7qc"
cloudinary_api_key: "changeme"
cloudinary_api_secret: "changeme"
resend_api_key: "changeme"
github_user: "tawounfouet"
github_token: "changeme"
sentry_dsn: ""
SECRETS_EOF
    echo "✅ secrets.yml.example généré"
fi

echo "::endgroup::"

# ── 5. Rapport ────────────────────────────────────────
echo "::group::📊 Rapport"

echo ""
echo "  Fichiers générés :"
echo "  ✅ $INVENTORY"
echo "  ✅ $SECRETS_EXAMPLE"
echo "  ⚠️  $ANSIBLE_DIR/group_vars/secrets.yml → à créer depuis .example"
echo ""
echo "  Prochaines étapes :"
echo "  1. cp group_vars/secrets.yml.example group_vars/secrets.yml"
echo "  2. Éditer secrets.yml avec les vraies valeurs"
echo "  3. (optionnel) ansible-vault encrypt group_vars/secrets.yml"
echo "  4. ansible-playbook deploy.yml -i inventory.yml --limit clickmart-prod"
echo ""

echo "::endgroup::"
echo "::endgroup::"  # Ansible Export

echo "✅ Export terminé"
