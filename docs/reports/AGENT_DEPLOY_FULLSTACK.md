# Rapport — Agent deploy-fullstack

**Date** : 2026-07-30
**Version** : 4.1
**Fichier** : `.opencode/agents/deploy-fullstack.md`

---

## Résumé

`deploy-fullstack` est un subagent OpenCode qui automatise le déploiement d'un projet Django + React (Docker Compose) sur un VPS vierge Ubuntu 22.04/24.04. Il couvre l'intégralité du cycle : connexion SSH sécurisée, préparation serveur, déploiement du code, CI/CD GitHub Actions et SSL Let's Encrypt.

---

## Architecture

```
deploy-fullstack (subagent, temperature 0.2)
│
├── Détection point de départ (table décisionnelle)
│   ├── inventory   → génère inventory.yml
│   ├── dry-run     → analyse complète + rapports
│   ├── production  → déploie prod (arrête staging)
│   └── staging     → déploie staging (arrête prod)
│
├── Analyse préalable (11 étapes)
│   ├── Structure Docker
│   ├── Structure du code et environnements
│   ├── Stack & framework
│   ├── Inspection Django (settings, migrations, ENVIRONMENT)
│   ├── Vérification dépendances Python
│   ├── État base de données
│   ├── Configuration reverse proxy
│   ├── Git remote
│   ├── Détection fournisseur cloud (9 providers)
│   ├── Services asynchrones (Celery/Redis)
│   └── Détection multi-environnements
│
├── preflight-check (OBLIGATOIRE)
│   ├── Vérifications locales (8 items)
│   ├── Vérifications distantes (7 items)
│   └── Rapport + validation user
│
├── Phase 0 — ssh-bootstrap
│   ├── sshpass + ssh-copy-id
│   └── Vérification auth par clé
│
├── Phase 1 — server-setup
│   ├── **Mode Ansible (défaut)** : `ansible-playbook --tags docker`
│   │   ├── Docker + Compose + Git + UFW + fail2ban
│   │   └── Création user deploy + ghcr.io login
│   └── Mode manuel (fallback) : SSH inline
│
├── Phase 2 — code-deploy
│   ├── **Mode Ansible (défaut)** : `ansible-playbook --tags app`
│   │   ├── Clone repo + template .env.prod
│   │   └── docker compose pull + up
│   ├── Mode manuel (fallback) : rsync ou git clone
│   └── Health check
│
├── Phase 3 — cicd (optionnel)
│   └── **Mode Ansible** : `ansible-playbook --tags cicd` → `gh secret set`
│
├── Phase 4 — ssl (production uniquement)
│   └── **Mode Ansible** : `ansible-playbook --tags ssl` → bootstrap HTTP → Certbot → HTTPS
│
├── Phase 5 — post-deploy validation (OBLIGATOIRE)
│   ├── Conteneurs + logs
│   ├── Endpoints HTTP
│   ├── Migrations Django
│   ├── Statics
│   └── Celery workers (ping, queues)
│
├── Mode dry-run
│   ├── Analyse 11 étapes + preflight (sans rien toucher)
│   ├── Génère/maj DRY_RUN_REPORT.md (document vivant)
│   └── Génère/maj inventory.yml (machine-readable)
│
├── Commande inventory
│   └── Génère/maj inventory.yml uniquement (pas d'analyse)
│
├── Rollback automatique
└── Synchronisation serveur → dépôt
```

---

## Détail des phases

### Analyse préalable (8 étapes)

Avant toute action, l'agent inspecte le projet :

| Étape | Description | Détecte |
|---|---|---|
| 1. Structure Docker | Analyse `docker-compose.yml` | Services build vs image |
| 2. Structure code | Arborescence, Dockerfiles | Chemins de build |
| 3. Stack | Framework, langages | Django, React, etc. |
| 4. Inspection Django | Analyse `config/settings/` | `ENVIRONMENT` mismatch, `SECURE_SSL_REDIRECT` hardcodé, `DEBUG` forcé, `ALLOWED_HOSTS` statique |
| 5. Dépendances | Cross-ref imports ↔ requirements.txt | Modules importés mais absents |
| 6. Base de données | `showmigrations --plan` | Migrations en attente/erreur |
| 7. Reverse proxy | Config nginx | Domaine, ports, SSL |
| 8. Git remote | `git remote get-url origin` | URL du dépôt |

**Exemple de sortie** :
```
Profil détecté : fullstack Django + React + Nginx + PostgreSQL
Django settings  : config/settings/production.py via ENVIRONMENT=production
⚠️  SECURE_SSL_REDIRECT hardcodé → à rendre configurable
✅ ALLOWED_HOSTS dynamique via config()
✅ Dépendances OK (0 manquantes)
Git remote       : git@github.com:user/repo.git
```

### Détection du point de départ

| Input user | Phase de démarrage |
|---|---|
| `inventory` | Génère/maj `inventory.yml` uniquement |
| `dry-run` | Analyse complète + DRY_RUN_REPORT.md + inventory.yml |
| `production` ou `prod` | Déploiement production (arrête staging avant) |
| `staging` ou `stg` | Déploiement staging (arrête prod avant) |
| IP + user + mot de passe | Phase 0 (ssh-bootstrap) |
| IP + user + clé SSH ok | Phase 1 (server-setup) |
| Serveur prêt (Docker/Git/UFW) | Phase 2 (code-deploy) |
| App déployée, pas de CI/CD | Phase 3 (cicd) |
| App déployée, domaine configuré | Phase 4 (ssl) |

### preflight-check

Vérifie 14 prérequis répartis en 3 niveaux de criticité :

| Niveau | Icône | Comportement |
|---|---|---|
| Bloquant | ❌ | STOP — corrige avant de continuer |
| Conditionnel | ✅ si phase X | Bloquant seulement si la phase concernée est nécessaire |
| Avertissement | ⚠️ | WARN — signale mais continue |
| Bonus | ❌ NON | Informe sans bloquer |

### Phase 0 : ssh-bootstrap

Configure l'authentification SSH par clé quand le user n'a que IP + user + mot de passe :
1. Installe `sshpass` localement (macOS : `brew install sshpass`)
2. Vérifie/crée une clé SSH locale (`~/.ssh/id_ed25519`)
3. Copie la clé sur le serveur : `sshpass -p 'mdp' ssh-copy-id root@IP`
4. Vérifie : `ssh root@IP "echo OK"`

### Phase 1 : server-setup

1. `apt update && apt upgrade -y`
2. Docker depuis le dépôt officiel (`curl -fsSL https://get.docker.com | sh`)
3. Docker Compose (inclus)
4. Git
5. Firewall UFW (ports 22, 80, 443)
6. **Création user `deploy`** : groupe docker, sudo NOPASSWD, même clé SSH, propriétaire de `/opt/app`

⛔ Après cette phase, plus aucune commande en root.

### Phase 2 : code-deploy

**Stratégie git-first** :
1. Génère une clé SSH sur le serveur
2. L'ajoute au dépôt GitHub via `gh repo deploy-key add`
3. Clone le dépôt
4. Fallback rsync si gh CLI indisponible

**Sélection d'environnement** : l'agent demande `production` ou `staging` si le projet a plusieurs environnements. Utilise les fichiers Compose appropriés :

```bash
# Production
docker compose -p clickmart -f docker-compose.yml -f docker-compose.prod.yml up -d --build
# Staging
docker compose -p clickmart-stg -f docker-compose.yml -f docker-compose.staging.yml up -d --build
```

**Règle anti-OOM** : avant de déployer, l'agent vérifie si l'autre environnement tourne et l'arrête. Les deux stacks ne doivent jamais coexister sur un VPS < 2 Go.

Puis : configuration `.envs/.prod` ou `.envs/.staging`, adaptation nginx, health check.

### Phase 3 : cicd (optionnel)

Configure GitHub Actions avec secrets `SSH_HOST`, `SSH_USER`=deploy, `SSH_KEY`, `ENV_FILE`.

### Phase 4 : ssl (optionnel)

Let's Encrypt avec Certbot (service Docker) + renouvellement automatique 12h.

### Phase 5 : post-deploy validation (obligatoire)

Après chaque déploiement :
- Conteneurs : statut (Up/healthy)
- Logs : scan erreurs/exceptions
- Endpoints HTTP : `/`, `/api/`, `/admin/` (codes 200/301)
- Migrations Django : `showmigrations --plan`
- Statics : `/static/` accessible
- Health check : endpoint `/api/health/` si présent

### Mode dry-run

Analyse complète sans rien toucher. Le user dit "dry-run", "simulation" ou "à blanc".

**Fichiers générés** :
- `DRY_RUN_REPORT.md` — rapport humain (Parties A/B/C/D + Annexe), document vivant de l'état du projet
- `inventory.yml` — inventaire machine-readable (YAML structuré : server, containers, celery, django, ssl, cicd, firewall...)

Si les fichiers existent déjà, ils sont mis à jour (problèmes résolus déplacés, nouveaux problèmes ajoutés). Si rien n'a changé, seule la date est mise à jour.

### Commande inventory

`@deploy-fullstack inventory` génère ou met à jour uniquement `inventory.yml` sans refaire l'analyse complète. Lecture rapide de `DRY_RUN_REPORT.md` + `docker-compose.yml` + `settings.py`.

### Rollback

En cas d'échec : `docker compose down` → `git stash` → `docker compose up` (version précédente).

### Synchronisation serveur → dépôt

Après chaque modif sur le serveur, propose de `scp` les fichiers modifiés vers le dépôt local.

---

## Permissions

```yaml
permission:
  bash: allow
  read: allow
  write: allow
  edit: allow
  glob: allow
  grep: allow
  task: allow
  question: allow
```

Accès complet à l'écosystème de fichiers et commandes. Température à 0.2 pour des réponses déterministes.

---

## Déploiement dual (local + global)

| Emplacement | Portée | Contenu |
|---|---|---|
| `~/.config/opencode/agents/deploy-fullstack.md` | Tous les projets | Version générique (400 lignes) |
| `.opencode/agents/deploy-fullstack.md` | Ce projet uniquement | Version spécifique ClickMart (194 lignes) |

La version locale **prend le dessus** sur la globale si elle existe. La version globale est agnostique : elle inspecte le projet avant d'agir.

---

## Points forts

- **Zéro présupposition** : analyse le `docker-compose.yml` pour détecter les services, s'adapte (backend-only, fullstack, avec/sans nginx, Celery, etc.)
- **Sécurité intégrée** : user `deploy` (pas root), clé SSH, firewall UFW, groupe docker
- **Multi-environnement** : production/staging avec `-p project`, stacks isolées, arrêt automatique de l'autre environnement
- **Validation à chaque étape** : preflight, post-deploy, rapports structurés
- **Git-first** : stratégie de déploiement compatible CI/CD dès le départ
- **Inspection Django** : détecte les erreurs de configuration avant le déploiement
- **Dry-run** : analyse sans risque avant de déployer, génère DRY_RUN_REPORT.md + inventory.yml
- **Rollback** : retour arrière automatique en cas d'échec
- **Documentation vivante** : DRY_RUN_REPORT.md et inventory.yml mis à jour automatiquement

## Historique des améliorations

| Version | Date | Changements |
|---|---|---|
| 1.0 | 2026-07-28 | Agent initial : phases 1-4, 7 skills |
| 1.1 | 2026-07-29 | Conversion `.yml` → `.md` (format reconnu par OpenCode) |
| 1.2 | 2026-07-29 | Ajout phase 0 (ssh-bootstrap), table détection point de départ |
| 1.3 | 2026-07-29 | Ajout preflight-check (14 prérequis, 3 niveaux de criticité) |
| 1.4 | 2026-07-29 | Création user `deploy` (plus de root après phase 1) |
| 1.5 | 2026-07-29 | Version globale + adaptation backend-only |
| 2.0 | 2026-07-29 | Inspection Django, git-first, post-deploy validation, dry-run, rollback, synchro serveur→dépôt |
| 2.1 | 2026-07-29 | Support Celery/Redis, détection fournisseur cloud (9 providers), multi-environnements |
| 3.0 | 2026-07-29 | Commande `inventory`, `@deploy-fullstack production\|staging`, règle anti-OOM, DRY_RUN_REPORT.md + inventory.yml auto-générés, mode dry-run enrichi (annexe de raisonnement)
| 4.0 | 2026-07-30 | **Intégration Ansible** : playbook comme moteur par défaut, préparation secrets, fallback manuel déprécié |
| 4.1 | 2026-07-31 | **Mode export** : scan serveur + projet → génère inventory.yml + secrets.yml.example |

## Retour d'expérience (sessions réelles)

L'agent a été utilisé avec succès sur trois déploiements :

| Projet | Serveur | Résultat |
|---|---|---|
| ClickMart (Django + React) | IONOS 87.106.222.62 | Déploiement complet from-scratch, 5→8 conteneurs healthy |
| ClickMart (Django + React + Celery) | Linode 172.239.20.14 | Production webtech-dev.info, CI/CD actif |
| Amifond (Django backend) | À déterminer | Déploiement réussi, bugs settings corrigés en amont |

**Bugs évités grâce à l'inspection Django (v2.0+)** :
- `ENVIRONMENT=prd` non reconnu → corrigé avant déploiement
- `SECURE_SSL_REDIRECT` hardcodé → rendu configurable
- `drf-nested-routers` absent de requirements.txt → détecté et corrigé
- Base corrompue par migrations partielles → reset avant déploiement
- `celery.py` parasite → import circulaire → détecté et supprimé
- `SECRET_KEY` faible → régénérée
- CORS origines HTTPS manquantes → ajoutées
- env_file merge (Docker Compose) → corrigé par suppression de la base
- Nginx DNS caching → `resolver 127.0.0.11` ajouté

## Commandes de référence

```bash
# Invoquer l'agent
@deploy-fullstack                    # Déploiement (demande l'environnement)
@deploy-fullstack production         # Déploiement production (arrête staging)
@deploy-fullstack staging            # Déploiement staging (arrête prod)
@deploy-fullstack dry-run            # Analyse sans déployer + rapports
@deploy-fullstack inventory          # Générer/maj inventory.yml uniquement

# Déploiement from-scratch
IP: 87.106.222.62, user: root, mdp: xxxxx
```

## Prochaines évolutions possibles

- [x] ~~Support multi-environnements (staging/production)~~
- [x] ~~Détection automatique du fournisseur cloud (IONOS, Linode, AWS, etc.)~~
- [x] ~~Support Celery / Redis / workers asynchrones~~
- [ ] Intégration vault de secrets (1Password, Bitwarden)
- [ ] Support Docker Swarm / Kubernetes
- [x] Export de la configuration comme template Terraform/Ansible (v4.1 — scan serveur → génère inventory)
- [x] **Intégration Ansible** — playbook comme moteur de déploiement par défaut (v4.0)
- [ ] Auto-détection du type de CI/CD (GitHub Actions, GitLab CI, etc.)
- [ ] Notification post-déploiement (Slack, Discord, email)
