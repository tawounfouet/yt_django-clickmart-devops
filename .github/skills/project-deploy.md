# Skill: project-deploy

## Rôle

Cloner le dépôt Git sur le serveur, copier les fichiers d'infrastructure,
transférer les fichiers `.env`, et lancer `docker compose up`.

## Prérequis

- Serveur prêt (Docker + Git installés)
- Fichiers `.env` générés (skill env-generator)
- Repo Git accessible (public ou credentials fournis)
- `PROJECT_NAME` défini

## Procédure

### 1. Créer le répertoire de déploiement

```bash
ssh ${VPS_USER}@${VPS_IP} "rm -rf /opt/${PROJECT_NAME} && mkdir -p /opt/${PROJECT_NAME}"
```

> On supprime d'abord pour éviter les conflits de clone dans un dossier existant.

### 2. Cloner le dépôt

```bash
ssh ${VPS_USER}@${VPS_IP} "git clone ${REPO_URL} /opt/${PROJECT_NAME}"
```

Si le repo est privé :
```bash
# Utiliser un token GitHub
ssh ${VPS_USER}@${VPS_IP} "git clone https://${GITHUB_TOKEN}@github.com/${REPO_PATH}.git /opt/${PROJECT_NAME}"
```

### 3. Détecter et copier les fichiers gitignorés

```bash
# Vérifier si les fichiers d'infra sont gitignorés
git check-ignore backend/Dockerfile 2>/dev/null && NEED_SCP=true || NEED_SCP=false

if [ "$NEED_SCP" = true ]; then
    echo "📋 Fichiers gitignorés détectés → SCP"
    scp backend/Dockerfile ${VPS_USER}@${VPS_IP}:/opt/${PROJECT_NAME}/backend/
    scp frontend/Dockerfile ${VPS_USER}@${VPS_IP}:/opt/${PROJECT_NAME}/frontend/
    scp docker-compose.yml ${VPS_USER}@${VPS_IP}:/opt/${PROJECT_NAME}/
else
    echo "✅ Fichiers d'infra déjà dans le repo"
fi
```

### 4. Transférer les fichiers `.env`

```bash
scp backend/.env.docker ${VPS_USER}@${VPS_IP}:/opt/${PROJECT_NAME}/backend/
scp backend/.env.production ${VPS_USER}@${VPS_IP}:/opt/${PROJECT_NAME}/backend/
```

> Les `.env` sont **toujours** transférés (ils ne sont jamais dans git).

### 5. Corriger les permissions (si l'utilisateur n'est pas root)

```bash
ssh ${VPS_USER}@${VPS_IP} "chown -R ${VPS_USER}:${VPS_USER} /opt/${PROJECT_NAME}"
```

> **Leçon ClickMart** : sans cette étape, `git reset --hard` échoue en Permission denied.

### 6. Configurer git safe.directory (si l'utilisateur n'est pas root)

```bash
ssh ${VPS_USER}@${VPS_IP} "git config --global --add safe.directory /opt/${PROJECT_NAME}"
```

### 7. Lancer Docker Compose

```bash
ssh ${VPS_USER}@${VPS_IP} "cd /opt/${PROJECT_NAME} && docker compose up --build -d"
```

### 8. Vérifier les containers

```bash
ssh ${VPS_USER}@${VPS_IP} "cd /opt/${PROJECT_NAME} && docker compose ps"
```

Résultat attendu : 4-5 containers avec le statut `Up` (ou `Up X seconds`).

## Vérification

```
✅ Repo cloné dans /opt/<PROJECT>
✅ Fichiers .env transférés
✅ docker compose up --build -d exécuté
✅ 4-5 containers Up
```

## Fallback

| Problème | Action |
|---|---|
| `git clone` échoue (repo privé) | Demander un token GitHub ou les credentials |
| `docker compose up` timeout | Vérifier les logs : `docker compose logs` |
| Container `Exited` | `docker compose logs <service>` pour diagnostiquer |
| Port déjà utilisé | Vérifier `lsof -i :80` ou `lsof -i :443` |
| Build échoue (mémoire) | Ajouter un fichier swap au serveur |
| Permission denied (git) | `chown -R` + `git config safe.directory` |

## Leçons ClickMart

- Le `rm -rf` avant clone évite l'erreur "destination path already exists"
- Les Dockerfiles étaient gitignorés → SCP nécessaire (détecté automatiquement)
- `chown -R deploy:deploy` crucial pour le CI/CD (git reset --hard)
- `git config --global safe.directory` nécessaire sur Ubuntu 24.04
- Le build Docker prend ~2 min la première fois, ~30s ensuite (cache)
