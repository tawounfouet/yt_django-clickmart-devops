# Instructions principales — Déploiement Fullstack

## Quand m'activer

L'utilisateur veut déployer un projet Django + React (Docker Compose) sur un VPS vierge.
Il fournit : IP du serveur, credentials SSH, et optionnellement un domaine.

## Règles fondamentales

1. **Idempotence** — chaque étape peut être exécutée plusieurs fois sans effet de bord.
   Vérifier l'état avant d'agir (ex: Docker déjà installé → ne pas réinstaller).

2. **Points d'arrêt** — ne jamais continuer si une étape critique échoue.
   Signaler l'erreur, proposer une solution, attendre confirmation.

3. **Vérification systématique** — après chaque phase, valider le succès.
   curl, docker compose ps, logs.

4. **Ne jamais supposer** — toujours vérifier l'OS, les versions, les chemins.
   Le serveur peut être Ubuntu 22.04, 24.04, ou autre.

5. **Rollback possible** — en cas d'échec, proposer de revenir à l'état précédent.
   `docker compose down` permet de tout arrêter proprement.

6. **Phases optionnelles** — CI/CD et SSL peuvent être sautés si l'utilisateur le demande.
   Le déploiement HTTP (phases 1+2) est le minimum viable.

## Entrées requises

| Variable | Description | Exemple |
|---|---|---|
| `VPS_IP` | Adresse IP du serveur | `172.239.20.14` |
| `VPS_USER` | Utilisateur SSH | `root` |
| `SSH_KEY` | Chemin clé privée SSH | `~/.ssh/id_rsa` |

Optionnelles :

| Variable | Description | Phase |
|---|---|---|
| `DOMAIN` | Nom de domaine | Phase 4 |
| `EMAIL` | Email pour Let's Encrypt | Phase 4 |

## Détection automatique

- **REPO_URL** : détecté via `git remote get-url origin` dans le répertoire courant
- **PROJECT_NAME** : extrait du nom du repo ou du dossier courant
- **PROJECT_STRUCTURE** : analysé pour détecter `backend/Dockerfile`, `docker-compose.yml`, etc.

## Déroulement séquentiel

### Phase 1 — Préparation serveur

```
Objectif : le serveur est prêt à recevoir l'application.

Étapes :
  1. ssh-connect      → Vérifier SSH, détecter l'OS, vérifier les ressources
  2. docker-install   → Installer Docker + Compose + Git
  3. firewall-guide   → Générer les instructions d'ouverture de ports

Checkpoint : Docker --version OK, ports 80/443 demandés à l'utilisateur.
```

### Phase 2 — Déploiement du code

```
Objectif : l'application est en ligne en HTTP.

Étapes :
  1. env-generator    → Créer .env.docker et .env.production
  2. project-deploy   → Cloner le repo, copier les fichiers, docker compose up
  3. health-check     → Vérifier que tous les endpoints répondent

Checkpoint : curl http://<IP>/ → HTTP 200
```

### Phase 3 — CI/CD

```
Objectif : déploiement automatique à chaque git push.

Étapes :
  1. github-cicd      → Créer le workflow, configurer les secrets

Checkpoint : pipeline GitHub Actions passe.
```

### Phase 4 — SSL + Domaine

```
Objectif : HTTPS activé avec certificat Let's Encrypt.

Étapes :
  1. dns-guide        → Instructions pour configurer les DNS
  2. ssl-setup        → Certbot + Nginx HTTPS + renouvellement auto

Checkpoint : curl https://<DOMAIN>/ → HTTP 200
```

## Résumé de sortie attendu

```
✅ Déploiement terminé
   URL : http://<IP>/
   Admin : http://<IP>/admin/
   API : http://<IP>/api/v1/products/

📋 Prochaines étapes suggérées :
   - Créer un superuser : ssh <USER>@<IP> "docker compose exec backend python manage.py createsuperuser"
   - Configurer un domaine : relancer avec l'option --domain
   - Activer HTTPS : relancer avec l'option --ssl
```

## Erreurs connues et solutions

| Erreur | Cause probable | Solution |
|---|---|---|
| `Permission denied (publickey)` | Clé SSH incorrecte | Vérifier `SSH_KEY`, tester `ssh -i <KEY>` |
| `docker: command not found` | Docker mal installé | Relancer docker-install |
| `Cannot connect to the Docker daemon` | Service Docker non démarré | `systemctl start docker` |
| `Error: No such container` | docker compose pas dans le bon dossier | Vérifier `cd /opt/<PROJECT>` |
| `DisallowedHost` | ALLOWED_HOSTS manque l'IP | Vérifier `.env.docker` |
| `relation does not exist` | Migrations non appliquées | Le `command` docker-compose fait `migrate` |
| `502 Bad Gateway` | Backend pas encore prêt | Attendre 30s, le healthcheck Docker gère |
| `404 sur /static/` | Volume static pas monté | Vérifier docker-compose volumes |
