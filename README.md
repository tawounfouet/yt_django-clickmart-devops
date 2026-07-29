# ClickMart — E-commerce Django + React

[![CI/CD Pipeline](https://github.com/tawounfouet/yt_django-clickmart-devops/actions/workflows/automate.yml/badge.svg)](https://github.com/tawounfouet/yt_django-clickmart-devops/actions)
[![Production](https://img.shields.io/badge/prod-webtech--dev.info-brightgreen)](https://webtech-dev.info)

Plateforme e-commerce fullstack déployée en production avec CI/CD automatisé.

---

## Stack

| Couche | Technologie |
|---|---|
| Backend | Django 5.2 + DRF 3.16 + Celery 5.6 |
| Frontend | React 19 + Vite 7 + Bootstrap 5 |
| Base de données | PostgreSQL 16 (distant) |
| Cache/Broker | Redis 7 (distant) |
| Reverse proxy | Nginx (Alpine) + SSL Let's Encrypt |
| Media storage | Cloudinary (prod) / MinIO (staging) |
| Email | Resend API |
| CI/CD | GitHub Actions → ghcr.io → Linode |
| Tests | 67 backend (Django) + 11 frontend (Vitest) |
| API docs | drf-spectacular (Swagger) |

---

## Démarrage rapide

### Dev local (Docker)

```bash
git clone git@github.com:tawounfouet/yt_django-clickmart-devops.git
cd yt_django-clickmart-devops
docker compose up -d --build
# → http://localhost
```

### Dev local (standalone)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # adapter si besoin
python manage.py migrate
python manage.py runserver
# → http://localhost:8000
```

### Staging

```bash
make up-staging
# → http://localhost:8080
```

---

## Architecture

```
Client ──▶ Nginx (80/443) ──▶ Frontend (React SPA)
                    ──▶ Backend (Gunicorn + DRF)
                           ├── PostgreSQL (49.13.239.42)
                           ├── Redis (49.13.239.42)
                           ├── Celery Worker + Beat
                           ├── Cloudinary (media)
                           └── Resend (email)
```

[Documentation complète → ARCHITECTURE.md](ARCHITECTURE.md)

---

## CI/CD

Pipeline automatique sur `git push` :

| Branche | Déclencheur |
|---|---|
| `dev` | Tests (78) |
| `stg` | Tests + Build images → Déploiement staging (:8080) |
| `main` | Tests + Build images → Déploiement production (:80/443) |

Les images Docker sont construites sur GitHub Actions et poussées vers `ghcr.io`. Le serveur Linode fait uniquement `docker pull` + `docker up` — aucun build local.

[Détail CI/CD → docs/reports/GESTION_CICD.md](docs/reports/GESTION_CICD.md)

---

## Environnements

| Environnement | URL | Branche |
|---|---|---|
| Production | [webtech-dev.info](https://webtech-dev.info) | `main` |
| Staging | `172.239.20.14:8080` | `stg` |
| Dev local | `localhost` | `dev` |

[Gestion des environnements → docs/reports/GESTION_ENVIRONNEMENTS.md](docs/reports/GESTION_ENVIRONNEMENTS.md)

---

## Agent de déploiement

```bash
@deploy-fullstack              # Déploiement (détection auto)
@deploy-fullstack production   # Déploiement prod (arrête staging)
@deploy-fullstack dry-run      # Analyse sans déploiement + rapports
@deploy-fullstack inventory    # Générer inventory.yml
```

[Documentation agent → docs/reports/AGENT_DEPLOY_FULLSTACK.md](docs/reports/AGENT_DEPLOY_FULLSTACK.md)

---

## Commandes utiles

```bash
make up-staging     # Lancer staging
make logs-staging   # Logs staging
make ps             # État des conteneurs
make clean          # Nettoyer tout

# Docker direct
docker compose -p clickmart ps
docker compose -p clickmart-stg ps
```

---

## Documentation

| Document | Sujet |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Architecture complète |
| [DRY_RUN_REPORT.md](DRY_RUN_REPORT.md) | État actuel de l'infra (auto-généré) |
| [inventory.yml](inventory.yml) | Inventaire machine-readable |
| [docs/reports/](docs/reports/) | Rapports de gestion (CI/CD, storage, email, DB, envs...) |
| [docs/analyse/](docs/analyse/) | Analyses (Terraform/Ansible, Celery...) |
| [docs/deploy/](docs/deploy/) | Guides de déploiement |
