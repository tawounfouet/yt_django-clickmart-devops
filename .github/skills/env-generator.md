# Skill: env-generator

## Rôle

Générer les fichiers `.env.docker` (Django) et `.env.production` (PostgreSQL)
nécessaires au déploiement Docker Compose.

## Prérequis

- IP du serveur connue (`VPS_IP`)
- Projet cloné localement avec `backend/.env.example` (optionnel mais recommandé)
- Python 3 disponible localement (pour générer SECRET_KEY)

## Procédure

### 1. Détecter le template .env.example

```bash
if [ -f backend/.env.example ]; then
    echo "✅ .env.example trouvé"
    cat backend/.env.example
else
    echo "⚠️  Pas de .env.example, génération depuis zéro"
fi
```

### 2. Générer une SECRET_KEY

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
# Exemple : K7xqL9mP2vR5wY8nA3bF6dG0hJ1kM4oQ7sT0uW3xZ6yC9...
```

### 3. Créer `backend/.env.docker`

```bash
cat > backend/.env.docker << EOF
SECRET_KEY=<SECRET_KEY_GENERE>
DEBUG=True
DB_NAME=<PROJECT_NAME>_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
ALLOWED_HOSTS=${VPS_IP},localhost,127.0.0.1,backend
CORS_ALLOWED_ORIGINS=http://${VPS_IP},http://localhost:5173
EMAIL_HOST_USER=test@test.com
EMAIL_HOST_PASSWORD=test
EOF
```

### 4. Créer `backend/.env.production`

```bash
cat > backend/.env.production << EOF
POSTGRES_DB=<PROJECT_NAME>_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
EOF
```

### 5. Vérifier

```bash
echo "=== .env.docker ===" && cat backend/.env.docker
echo "=== .env.production ===" && cat backend/.env.production
```

## Variables expliquées

| Variable | Rôle | Valeur par défaut |
|---|---|---|
| `SECRET_KEY` | Clé secrète Django | Générée aléatoirement |
| `DEBUG` | Mode debug | `True` (passer à `False` en prod réelle) |
| `DB_NAME` | Nom de la base | `<projet>_db` |
| `DB_USER` / `DB_PASSWORD` | Credentials PostgreSQL | `postgres` / `postgres` |
| `DB_HOST` | Hôte PostgreSQL | `db` (nom du service Docker) |
| `ALLOWED_HOSTS` | Domaines autorisés | IP + localhost + backend |
| `CORS_ALLOWED_ORIGINS` | Origines CORS | IP + localhost:5173 |
| `EMAIL_HOST_USER` / `PASSWORD` | Email (factice pour le dev) | `test@test.com` |

## Vérification

```
✅ backend/.env.docker créé (X variables)
✅ backend/.env.production créé
```

## Fallback

| Problème | Action |
|---|---|
| Pas de Python 3 | Utiliser `openssl rand -hex 32` pour la SECRET_KEY |
| `.env.example` différent | Adapter les variables selon le template existant |
| Variables manquantes | Ajouter les variables requises par `settings.py` |
| Projet sans `backend/` | Adapter le chemin (ex: `src/.env`) |

## Leçons ClickMart

- Sans `.env.docker`, le container backend crash au démarrage (SECRET_KEY manquante)
- Sans `.env.production`, PostgreSQL ne démarre pas (POSTGRES_DB/PASSWORD requis)
- `DB_HOST=db` est crucial : c'est le nom du service Docker, pas `localhost`
- `CORS_ALLOWED_ORIGINS` doit inclure l'IP du serveur, pas seulement localhost
- Les valeurs par défaut (`DEBUG=True`, mdp `postgres`) sont pour le DEV. En production réelle, changer.
