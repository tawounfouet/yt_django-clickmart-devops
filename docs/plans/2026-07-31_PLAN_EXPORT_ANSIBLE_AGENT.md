# Plan d'implémentation — Export Ansible (agent v4.1)

> **Objectif** : L'agent peut scanner un serveur existant et auto-générer/mettre à jour les fichiers de configuration Ansible
> **Version cible** : Agent v4.1
> **Durée estimée** : ~45 min

---

## 1. Vue d'ensemble

```
┌─────────────────────────────────────────────────────────┐
│              Agent deploy-fullstack v4.1                 │
│                                                          │
│  Nouvelle commande : @deploy-fullstack export           │
│                                                          │
│  1. Scan serveur ──→ détection OS, Docker, conteneurs   │
│  2. Scan projet  ──→ .env.example, docker-compose.yml   │
│  3. Génération    ──→ inventory.yml (màj)               │
│                    ──→ all.yml (màj)                     │
│                    ──→ secrets.yml.example (créer)       │
│  4. Rapport       ──→ résumé de ce qui a été détecté    │
└─────────────────────────────────────────────────────────┘
```

**Principe** : L'agent scanne le serveur et le projet local, puis génère/maintient les fichiers `inventory.yml` et `all.yml`. Si le serveur est déjà provisionné par Ansible, les fichiers sont mis à jour. Si le serveur est vierge ou provisionné manuellement, les fichiers sont créés from-scratch.

---

## 2. Étape 1 — Script `ansible-export.sh` (20 min)

**Fichier** : `infra/scripts/ansible-export.sh`

Script autonome qui peut être exécuté par l'agent ou manuellement.

### 2.1 Scan serveur (via Ansible si possible, sinon SSH)

```bash
# Détection de l'état
ansible all -i inventory.yml -m setup 2>/dev/null \
  | jq '{ip: .ansible_facts.default_ipv4.address, os: .ansible_facts.distribution, version: .ansible_facts.distribution_version, ram: .ansible_facts.memtotal_mb}'

# Détection Docker
ansible all -i inventory.yml -m shell -a "docker --version && docker compose version"

# Détection conteneurs
ansible all -i inventory.yml -m shell -a "docker compose -p clickmart ps 2>/dev/null; docker compose -p clickmart-stg ps 2>/dev/null"

# Détection SSL
ansible all -i inventory.yml -m shell -a "test -f /etc/letsencrypt/live/*/fullchain.pem && echo SSL_OK"
```

### 2.2 Scan projet local

```bash
# Extraire les variables de .env.example
grep -E '^[A-Z_]+\s*=' backend/.env.example | sed 's/=.*//' | sort

# Détecter les services depuis docker-compose.yml
grep -E '^\s{2}[a-z-]+:' docker-compose.yml | sed 's/://' | tr -d ' '
```

### 2.3 Génération inventory.yml

À partir des informations détectées :

```yaml
all:
  hosts:
    clickmart-prod:
      ansible_host: <IP_DETECTEE>
      ansible_user: deploy
      ansible_ssh_private_key_file: ~/.ssh/id_ed25519
      env: production
      domain: <DOMAINE_DETECTE>
      app_dir: /opt/clickmart
      compose_files: [docker-compose.yml, docker-compose.prod.yml]
      project_name: clickmart
      branch: main
      ssl_enabled: <DETECTE>
      health_proto: https

    clickmart-staging:
      ansible_host: <IP_DETECTEE>
      ansible_user: deploy
      ...
```

Si le fichier existe déjà → mise à jour (conserve l'existant, ajoute les nouveaux champs).

### 2.4 Génération secrets.yml.example

```yaml
---
# Généré par @deploy-fullstack export le 2026-07-31
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
```

---

## 3. Étape 2 — Intégration agent (15 min)

**Fichier** : `.opencode/agents/deploy-fullstack.md`

### 3.1 Nouvelle entrée dans la table de décision

```markdown
| `export` ou `scan` | **Mode export** : scan serveur + projet → génère inventory.yml, all.yml, secrets.yml.example |
```

### 3.2 Nouvelle section "Mode export"

```markdown
### Mode export (Ansible)

L'agent scanne le serveur et le projet pour générer/maintenir les fichiers Ansible.

1. **Scan serveur** (via Ansible ou SSH) :
   - OS, RAM, IP, distribution
   - Docker version, conteneurs actifs
   - SSL (certificats Let's Encrypt présents ?)
   - Domaines configurés dans Nginx

2. **Scan projet local** :
   - Variables dans `.env.example`
   - Services dans `docker-compose.yml`
   - Environnements détectés (production, staging)

3. **Génération** :
   - `inventory.yml` → créé ou mis à jour
   - `all.yml` → mis à jour (DB host, Redis host, media_storage, email_backend)
   - `secrets.yml.example` → template pour le user

4. **Rapport** :
   ```
   🔍 EXPORT — Rapport
   
   Serveur : Ubuntu 24.04, 961 MB RAM, Docker 28.x
   Production : https://webtech-dev.info ✅ (SSL actif)
   Staging   : http://staging.webtech-dev.info:8080 ⚠️ (non détecté)
   
   Fichiers générés :
   ✅ infra/ansible/inventory.yml (mis à jour)
   ✅ infra/ansible/secrets.yml.example (créé)
   ⚠️ infra/ansible/group_vars/secrets.yml → à créer depuis .example
   
   → Prêt pour ansible-playbook deploy.yml --limit clickmart-prod
   ```
```

---

## 4. Étape 3 — Mise à jour docs (10 min)

| Fichier | Changement |
|---|---|
| `docs/reports/AGENT_DEPLOY_FULLSTACK.md` | v4.0 → v4.1, ajout mode export |
| `docs/plans/2026-07-29_PLAN_AGENT_DEPLOIEMENT.md` | Section V4.1 — Export Ansible |
| `.opencode/agents/deploy-fullstack.md` | Mode export + table décision |

---

## 5. Checklist de suivi

| # | Tâche | Fichier | Effort | Statut |
|---|---|---|---|---|
| 1 | Créer `infra/scripts/ansible-export.sh` | `infra/scripts/` | 20 min | ⬜ |
| 2 | Ajouter "Mode export" dans l'agent | `.opencode/agents/deploy-fullstack.md` | 10 min | ⬜ |
| 3 | Table de décision : ajouter `export`/`scan` | `.opencode/agents/deploy-fullstack.md` | 5 min | ⬜ |
| 4 | Mettre à jour rapport agent → v4.1 | `docs/reports/` | 5 min | ⬜ |
| 5 | Mettre à jour plan agent | `docs/plans/` | 5 min | ⬜ |
| **Total** | | | **~45 min** | |

---

**Progression** : 0/5 tâches (0%)
