# Rapport — Agent deploy-fullstack

**Date** : 2026-07-29
**Version** : 2.0
**Fichier** : `.opencode/agents/deploy-fullstack.md` (local) / `~/.config/opencode/agents/deploy-fullstack.md` (global)
**Auteur** : OpenCode + Thomas Awounfouet

---

## Résumé

`deploy-fullstack` est un subagent OpenCode qui automatise le déploiement d'un projet Django + React (Docker Compose) sur un VPS vierge Ubuntu 22.04/24.04. Il couvre l'intégralité du cycle : connexion SSH sécurisée, préparation serveur, déploiement du code, CI/CD GitHub Actions et SSL Let's Encrypt.

---

## Architecture

```
deploy-fullstack (subagent, temperature 0.2)
│
├── Analyse préalable (8 étapes)
│   ├── Structure Docker
│   ├── Structure du code
│   ├── Stack & framework
│   ├── Inspection Django (settings, migrations)
│   ├── Vérification dépendances Python
│   ├── État base de données
│   ├── Configuration reverse proxy
│   └── Git remote
│
├── Détection point de départ (table décisionnelle)
│
├── preflight-check (OBLIGATOIRE)
│   ├── Vérifications locales (8 items)
│   ├── Vérifications distantes (6 items)
│   └── Rapport + validation user
│
├── Phase 0 — ssh-bootstrap
│   ├── sshpass + ssh-copy-id
│   └── Vérification auth par clé
│
├── Phase 1 — server-setup
│   ├── Docker + Compose + Git
│   ├── Firewall UFW (22, 80, 443)
│   └── Création user deploy
│
├── Phase 2 — code-deploy
│   ├── Stratégie git-first (deploy key GitHub)
│   ├── Fallback rsync
│   ├── Configuration .env
│   ├── Adaptation reverse proxy
│   └── docker compose up + health check
│
├── Phase 3 — cicd (optionnel)
│   └── GitHub Actions + secrets
│
├── Phase 4 — ssl (optionnel)
│   └── Let's Encrypt + Certbot
│
├── Phase 5 — post-deploy validation (OBLIGATOIRE)
│   ├── Conteneurs + logs
│   ├── Endpoints HTTP
│   ├── Migrations Django
│   └── Statics
│
├── Mode dry-run
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

Puis : configuration `.env`, adaptation nginx, `docker compose up -d --build`, health check.

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

- **Zéro présupposition** : analyse le `docker-compose.yml` pour détecter les services, s'adapte (backend-only, fullstack, avec/sans nginx, etc.)
- **Sécurité intégrée** : user `deploy` (pas root), clé SSH, firewall UFW, groupe docker
- **Validation à chaque étape** : preflight, post-deploy, rapports structurés
- **Git-first** : stratégie de déploiement compatible CI/CD dès le départ
- **Inspection Django** : détecte les erreurs de configuration avant le déploiement
- **Dry-run** : analyse sans risque avant de déployer
- **Rollback** : retour arrière automatique en cas d'échec

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

## Retour d'expérience (sessions réelles)

L'agent a été utilisé avec succès sur deux projets :

| Projet | Serveur | Résultat |
|---|---|---|
| ClickMart (Django + React) | IONOS 87.106.222.62 | Déploiement complet from-scratch, 5 conteneurs healthy |
| Amifond (Django backend) | À déterminer | Déploiement réussi, bugs settings corrigés en amont |

**Bugs évités grâce à l'inspection Django (v2.0)** :
- `ENVIRONMENT=prd` non reconnu → corrigé avant déploiement
- `SECURE_SSL_REDIRECT` hardcodé → rendu configurable
- `drf-nested-routers` absent de requirements.txt → détecté et corrigé
- Base corrompue par migrations partielles → reset avant déploiement

---

## Commandes de référence

```bash
# Invoquer l'agent
@deploy-fullstack

# Dry-run (analyse sans déployer)
@deploy-fullstack dry-run

# Déploiement complet
IP: 87.106.222.62, user: root, mdp: xxxxx
```

## Prochaines évolutions possibles

- [ ] Intégration vault de secrets (1Password, Bitwarden)
- [ ] Support multi-environnements (staging/production)
- [ ] Détection automatique du fournisseur cloud (IONOS, Linode, AWS, etc.)
- [ ] Support Docker Swarm / Kubernetes
- [ ] Support Celery / Redis / workers asynchrones
- [ ] Export de la configuration comme template Terraform/Ansible
