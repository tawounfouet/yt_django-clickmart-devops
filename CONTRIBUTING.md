# Contributing — ClickMart

> Guide pour contribuer au projet. Merci de lire ce document avant d'ouvrir une PR.

---

## Workflow Git

```
main ──── production (webtech-dev.info, ports 80/443)
  ▲
  │ merge
stg  ──── staging (port 8080, validation pré-prod)
  ▲
  │ merge
dev  ──── développement (tests uniquement, pas de déploiement)
  ▲
  │ feature branch
feat/xxx
```

### Créer une feature

```bash
git checkout dev
git pull origin dev
git checkout -b feat/ma-feature
# ... coder ...
git add .
git commit -m "feat: description"  # Conventional Commits
git push origin feat/ma-feature
# ouvrir une PR vers dev
```

### Merge vers staging puis production

```bash
# Après validation de la PR sur dev
git checkout stg && git merge dev && git push origin stg
# → CI/CD déploie automatiquement sur staging (port 8080)

# Après validation sur staging
git checkout main && git merge stg && git push origin main
# → CI/CD déploie automatiquement sur production
```

---

## Conventional Commits

Format : `type(scope): description`

| Type | Usage |
|---|---|
| `feat` | Nouvelle fonctionnalité |
| `fix` | Correction de bug |
| `docs` | Documentation |
| `refactor` | Restructuration sans changement fonctionnel |
| `perf` | Optimisation de performance |
| `test` | Ajout ou modification de tests |
| `chore` | Tâche de maintenance |
| `ci` | Configuration CI/CD |

Exemples :
```
feat: add Cloudinary media storage backend
fix: remove gcc/libpq-dev from Dockerfile (not needed)
docs: update ARCHITECTURE.md v2.0
refactor: separate static (Nginx) from media storage
```

---

## Environnement de développement

### Dev local avec Docker

```bash
docker compose up -d --build
# → http://localhost
```

Structure :
```
docker-compose.yml              # base
docker-compose.override.yml     # dev local (ports, envs)
backend/.envs/.local            # config dev
```

### Dev standalone (sans Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

---

## Tests

```bash
# Backend (67 tests)
cd backend && python manage.py test

# Frontend (11 tests)
cd frontend && npx vitest run

# Lint
cd backend && ruff check .
cd frontend && npm run lint
```

Les tests tournent automatiquement sur chaque push (GitHub Actions).

---

## Revue de code

Avant de merger vers `stg` ou `main` :
1. Tous les tests passent en CI
2. `@deploy-fullstack dry-run` — pas de régression
3. `@code-reviewer` — revue structurée
4. Secrets non exposés (vérifier `.env` dans `.gitignore`)

---

## Déploiement

Le déploiement est automatique via CI/CD. Pour déployer manuellement :

```bash
# Production
@deploy-fullstack production

# Staging
@deploy-fullstack staging

# Analyse sans déployer
@deploy-fullstack dry-run
```

---

## Documentation

| Fichier | Sujet |
|---|---|
| `ARCHITECTURE.md` | Architecture complète |
| `SDLC.md` | Cycle de développement |
| `TODO.md` | Tâches restantes |
| `DRY_RUN_REPORT.md` | État de l'infra (auto-généré) |
| `docs/reports/` | Rapports de gestion |
| `docs/analyse/` | Analyses techniques |

Mettre à jour la documentation avec `/docs` ou `@docs-writer`.

---

## Fichiers d'environnement

```
backend/.env                 ← standalone dev (gitignored)
backend/.envs/.local         ← Docker dev (gitignored)
backend/.envs/.staging       ← staging (gitignored)
backend/.envs/.prod          ← production (gitignored)
backend/.env.example         ← template (commité)
```

Ne jamais commiter de secrets. Utiliser `.env.example` comme référence.
