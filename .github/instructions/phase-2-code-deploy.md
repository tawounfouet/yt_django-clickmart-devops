# Phase 2 — Déploiement du code

## Objectif

Déployer l'application sur le serveur et la rendre accessible en HTTP.

## Skills à charger

1. `env-generator` — Générer `.env.docker` et `.env.production`
2. `project-deploy` — Cloner, SCP, docker compose up
3. `health-check` — Vérifier que l'app répond

## Déroulement

```
1. env-generator
   ├── Générer SECRET_KEY aléatoire
   ├── Créer backend/.env.docker
   │   SECRET_KEY, DEBUG=True, DB_NAME, DB_USER/PASSWORD
   │   DB_HOST=db, ALLOWED_HOSTS=<IP>, CORS_ALLOWED_ORIGINS=<IP>
   └── Créer backend/.env.production
       POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

2. project-deploy
   ├── rm -rf /opt/<PROJECT> && mkdir -p
   ├── git clone <REPO_URL> /opt/<PROJECT>
   ├── Détecter fichiers gitignorés → SCP si nécessaire
   ├── SCP backend/.env.docker et .env.production
   ├── chown -R (si user != root)
   ├── git config safe.directory
   └── docker compose up --build -d

3. health-check
   ├── docker compose ps (5 services Up)
   ├── curl http://<IP>/ → 200 (frontend)
   ├── curl http://<IP>/api/v1/products/ → 200 (API)
   ├── curl http://<IP>/admin/login/ → 200 (admin)
   ├── curl http://<IP>/static/admin/css/login.css → 200 (statics)
   └── docker compose logs backend | grep -i error
```

## Checkpoint

```
✅ 5 containers Up
✅ Frontend : HTTP 200
✅ API      : HTTP 200
✅ Admin    : HTTP 200
✅ Statics  : HTTP 200
```

→ Passer à la Phase 3 (optionnelle) ou terminer.

## URL de l'application

```
Frontend : http://<IP>/
API      : http://<IP>/api/v1/products/
Admin    : http://<IP>/admin/
Docs     : http://<IP>/api/docs/  (si DRF Spectacular)
```

## Commandes utiles post-déploiement

```bash
# Créer un superuser Django
ssh ${VPS_USER}@${VPS_IP} "cd /opt/${PROJECT_NAME} && docker compose exec backend python manage.py createsuperuser"

# Voir les logs
ssh ${VPS_USER}@${VPS_IP} "cd /opt/${PROJECT_NAME} && docker compose logs -f"

# Redémarrer un service
ssh ${VPS_USER}@${VPS_IP} "cd /opt/${PROJECT_NAME} && docker compose restart backend"
```
