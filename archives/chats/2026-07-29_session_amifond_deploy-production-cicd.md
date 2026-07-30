# Session: Déploiement Production + CI/CD

**Date**: 2026-07-29
**Agent(s)**: deploy-fullstack, git-hygiene, session-archive
**Phase**: deploy

---

## Intent

Déployer l'ERP microfinance Django (amifond-backend) sur un VPS production avec SSL Let's Encrypt, configurer la CI/CD GitHub Actions, et pousser le code sur un nouveau dépôt GitHub privé.

## Outcome

- Application déployée et accessible en HTTPS sur `https://coopca-amifond.eu/`
- CI/CD configurée via GitHub Actions (déclenchement sur tag `v*.*.*`)
- Tag `v1.0.0` créé et déployé avec succès
- Code source poussé sur `github.com/tawounfouet/amifond-backend`

---

## Decisions

| # | Decision | Rationale | Alternatives considered |
|---|---|---|---|
| 1 | Utiliser `ENVIRONMENT=prd` comme valeur | Les settings Django ont été patchés pour accepter `prd` en plus de `production` | Utiliser `production` uniquement mais le .env.prd existait déjà |
| 2 | Let's Encrypt (certbot standalone) pour SSL | Solution standard, gratuite, avec renouvellement automatique | Self-signed, certbot webroot |
| 3 | Clé SSH dédiée pour GitHub → VPS | Séparation des accès, pas de partage de clé personnelle | Utiliser la clé root existante |
| 4 | Deploy key pour VPS → GitHub (lecture seule) | Permet git pull sur le VPS sans token | Token GitHub |
| 5 | Rsync pour le déploiement initial, puis git pull pour les màj | Git pull plus fiable pour les mises à jour incrémentales | Rsync à chaque fois |

## Files Created

| File | Purpose |
|---|---|
| `archives/chats/2026-07-29_session_deploy-production-cicd.md` | Cette archive de session |

## Files Modified

| File | Change summary |
|---|---|
| `docker/docker-compose.prd.yml` | Ajout du volume `/etc/letsencrypt:/etc/letsencrypt:ro` pour le container nginx |
| `.gitignore` | Ajout de `archives/` pour exclure les archives de session |

---

## Key Context

- **VPS**: `87.106.222.62` (Hetzner), Ubuntu, `root` user
- **Domaine**: `coopca-amifond.eu` (IONOS/1&1 registrar)
- **Ancienne IP**: `217.160.0.221` — DNS non encore propagé partout
- **DB PostgreSQL externe**: `49.13.239.42`
- **Redis externe**: `49.13.239.42:6379` (avec auth)
- **Chemin déploiement**: `/opt/amifond-backend`
- **Compose file**: `docker/docker-compose.prd.yml`
- **Settings**: `ENVIRONMENT=prd`, `DJANGO_SETTINGS_MODULE=config.settings`

## Commands Run

| Command | Purpose | Result |
|---|---|---|
| `docker compose -f docker/docker-compose.prd.yml up -d --build` | Build et démarrage des conteneurs | OK |
| `certbot certonly --standalone -d coopca-amifond.eu -d www.coopca-amifond.eu` | Obtention certificat Let's Encrypt | OK |
| `git tag v1.0.0 && git push origin v1.0.0` | Déclenchement CI/CD | OK — déploiement automatique réussi |
| `gh secret set ...` | Configuration des 35 secrets GitHub | OK |

## Issues & Workarounds

| Issue | Workaround | Status |
|---|---|---|
| `ENVIRONMENT=prd` non reconnu par settings Django | Patch dans `config/settings/__init__.py` | resolved |
| `SECURE_SSL_REDIRECT=True` en dur dans settings production | Rendu configurable via `.env.prd` | resolved |
| `drf-nested-routers` manquant dans requirements.txt | Ajouté | resolved |
| DNS de `coopca-amifond.eu` pointait encore vers `217.160.0.221` | Ajout de l'entrée dans `/etc/hosts` en attendant la propagation | open |
| `pip install` lente à cause de `psycopg2` | Utilisation de `psycopg2-binary` ou `--no-cache-dir` | open |

---

## Action Items

- [x] Déployer l'application sur le VPS
- [x] Configurer SSL Let's Encrypt
- [x] Pousser le code sur GitHub
- [x] Configurer les secrets GitHub Actions
- [x] Tagger v1.0.0 pour déclencher le déploiement CI/CD
- [ ] Supprimer l'entrée `/etc/hosts` quand le DNS sera propagé
- [ ] Vérifier les endpoints API (/api/docs/swagger/, /admin/)
- [ ] Configurer le monitoring (Sentry optionnel)

## Related Sessions

- (première session sur ce projet)

---

## Full Conversation Summary

1. Exploration du projet Django (ERP microfinance, Docker, PostgreSQL, Redis, Celery)
2. Déploiement initial sur VPS (Docker, rsync, migrations)
3. Configuration DNS (enregistrement A vers 87.106.222.62)
4. Configuration SSL Let's Encrypt (certbot standalone, redirection HTTP→HTTPS)
5. Correction de bugs (ENVIRONMENT, SECURE_SSL_REDIRECT, dépendance manquante)
6. Test des endpoints (Swagger, Admin, API → tous OK)
7. Création du dépôt GitHub et push du code
8. Configuration CI/CD GitHub Actions avec 35 secrets
9. Création du tag v1.0.0 et déploiement automatique réussi
